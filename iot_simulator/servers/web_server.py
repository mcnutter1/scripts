from http.server import ThreadingHTTPServer, HTTPServer, BaseHTTPRequestHandler
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args
import ipaddress

logger = get_logger("web_server")


SERIAL = ""
MAC = ""
IP = ""
HOSTNAME = ""


HTML_HEAD = """
<!DOCTYPE html>
   <html>
   <head>
    <title>Siemens MULTIX Impact C - System Interface</title>
    <style>
        body { font-family: Arial, background-color: #f4f4f4; margin: 0; }
        header { background-color: #003366; color: white; padding: 15px; }
        nav { background: #e4e4e4; padding: 10px; }
        section { padding: 20px; }
        footer { background-color: #003366; color: white; text-align: center; padding: 10px; position: fixed; width: 100%; bottom: 0; }
        .status-ok { color: green; font-weight: bold; }
        .label {} font-weight: bold; }]
    </style>
</head>
"""

def HTML_INDEX():
   return f"""
{HTML_HEAD}
<body>
    <header>
        <h1>Siemens Healthineers - MULTIX Impact C</h1>
        <p>System Control Interface v1.42.08</p>
    </header>
    <nav>
        <a href="/">System Status</a> | 
        <a href="/dicom">DICOM Configuration</a> | 
        <a href="/network">Network Settings</a>
    </nav>
    <section>
        <h2>System Status</h2>
        <p><span class="label">Device ID:</span> MXC-4203781</p>
        <p><span class="label">Serial:</span> {SERIAL}</p>
        <p><span class="label">Status:</span> <span class="status-ok">Operational</span></p>
        <p><span class="label">Last QA Check:</span> 2025-05-01</p>
        <p><span class="label">Tube Temperature:</span> 36.8°C</p>
        <p><span class="label">Exposure Counter:</span> 18432</p>
    </section>
    <footer>
        Siemens Medical Systems &copy; 2025
    </footer>
</body>
</html>
   """

def HTML_DICOM(): 
   return f"""
{HTML_HEAD}
<body>
    <header>
        <h1>Siemens Healthineers - MULTIX Impact C</h1>
        <p>System Control Interface v1.42.08</p>
    </header>
    <nav>
        <a href="/">System Status</a> | 
        <a href="/dicom">DICOM Configuration</a> | 
        <a href="/network">Network Settings</a>
    </nav>
    <section>
<h2>DICOM Node Settings</h2>
<ul>
    <li>AET: MULTIXCX</li>
    <li>Port: 104</li>
    <li>Remote AET: USMA-PACS1</li>
    <li>Remote IP: 10.14.101.89</li>
</ul>
</section>
<a href="/">Back to status</a>
</body>
</html>
"""

def HTML_NETWORK(): 
   return f"""
{HTML_HEAD}
    <header>
        <h1>Siemens Healthineers - MULTIX Impact C</h1>
        <p>System Control Interface v1.42.08</p>
    </header>
    <nav>
        <a href="/">System Status</a> | 
        <a href="/dicom">DICOM Configuration</a> | 
        <a href="/network">Network Settings</a>
    </nav>
    <section>
<body>
<h2>Network Configuration</h2>
<ul>
    <li>IP Address: {IP}</li>
    <li>MAC Address: {MAC}</li>
    <li>Hostname: {HOSTNAME}</li>
</ul>
<a href="/">Back to status</a>
</body>
</html>
"""

class SiemensHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) Received request: {self.path}")
        if self.path == "/" or self.path == "/index.html":
            html = HTML_INDEX()
            #self.send_header('Content-type', 'text/html')
            #self.end_headers()
            self.respond(200, html)
        elif self.path == "/dicom":
            html = HTML_DICOM()
            self.respond(200, html)
        elif self.path == "/network":
            html = HTML_NETWORK()
            self.respond(200, html)
        else:
            self.respond(404, "<h1>404 Not Found</h1>")

    def respond(self, status, content):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) Sent Response: {self.path} {status}")
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

def get_client_ip_and_version(client_address):
    raw_ip = client_address[0]

    try:
        ip_obj = ipaddress.ip_address(raw_ip)

        if ip_obj.version == 6 and ip_obj.ipv4_mapped:
            # It's an IPv4-mapped IPv6 address
            return str(ip_obj.ipv4_mapped), "IPv4"
        else:
            return str(ip_obj), f"IPv{ip_obj.version}"

    except ValueError:
        return "Unavailable", "Unknown"


def run(port=8080):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, SiemensHandler)  # Changed to ThreadingHTTPServer
    print("Simulated Siemens MULTIX Impact C web interface running on port 80...")
    httpd.serve_forever()



if __name__ == "__main__":
    port, config = parse_args()
    SERIAL = config.get('serial')
    MAC = config.get('mac')
    IP = config.get('ip')
    HOSTNAME = config.get('hostname')
    logger.info(f"System identity: {config.get('system_name')}")
    run(port)
