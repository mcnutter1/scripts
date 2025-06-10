
import requests
import socket
import time
import ipaddress

ip_range = '45.42.173.128/26'
ports = [3389]
TIMEOUT = 3

def scan_ip_port(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            result = s.connect_ex((str(ip), port))
            if result == 0:
                try:
                    s.sendall(b'\r\n')
                    banner = s.recv(1024).decode(errors='ignore')
                except Exception as e:
                    banner = f"No banner received or error: {str(e)}"
                return (True, banner.strip())
            else:
                return (False, "Connection refused or timed out")
    except Exception as e:
        return (False, f"Error: {str(e)}")


def check_bluekeep_vuln(target_ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((target_ip, 3389))
        pre_auth_pkt = b"\x03\x00\x00\x13\x0e\xe0\x00\x00\x00\x00\x00\x00\x00\x01\x00\x08\x00\x03\x00\x00\x00"
        sock.send(pre_auth_pkt)
        data = sock.recv(1024)
        if b"\x03\x00\x00\x0c" in data:
            return f"[+] {target_ip} is likely VULNERABLE to BlueKeep!"
        else:
            return f"[-] {target_ip} is likely patched :("
    except:
        return f"[-] {target_ip} is either not up or not vulnerable"


if __name__ == "__main__":
    network = ipaddress.ip_network(ip_range, strict=False)
    for ip in network.hosts():
        print(f"\nScanning IP: {ip}")
        for port in ports:
            open_status, response = scan_ip_port(ip, port)
            print(f"  Port {port}: {'Open' if open_status else 'Closed'}\n    Response: {response}")
            if open_status:
                if port == 3389:
                    vuln_status = check_bluekeep_vuln(str(ip))
                    print(vuln_status)



