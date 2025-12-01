#!/usr/bin/env python3
"""
HP Printer Web Server Simulator
Simulates HP Embedded Web Server (EWS) interface
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args
import ipaddress

logger = get_logger("printer_web_server")

# Global config variables
SYSTEM_NAME = ""
IP = ""
MAC = ""
HOSTNAME = ""
SERIAL = ""
MODEL = ""
FIRMWARE = ""
LOCATION = ""
CONTACT = ""
PAGE_COUNT = 0
TONER_LEVEL = 0
TONER_CAPACITY = 0
PAPER_TRAY1 = 0
PAPER_TRAY2 = 0
OUTPUT_TRAY = 0

# HTML Templates
HTML_HEAD = """
<!DOCTYPE html>
<html>
<head>
    <title>HP {model} - Embedded Web Server</title>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: #f5f5f5;
            color: #333;
        }}
        header {{ 
            background: linear-gradient(135deg, #0096D6 0%, #0073A8 100%);
            color: white; 
            padding: 20px 30px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        header h1 {{ 
            font-size: 24px; 
            font-weight: 500;
            margin-bottom: 5px;
        }}
        header .subtitle {{ 
            font-size: 14px; 
            opacity: 0.9;
        }}
        nav {{ 
            background: #fff;
            padding: 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-bottom: 3px solid #0096D6;
        }}
        nav a {{ 
            display: inline-block;
            padding: 15px 25px;
            text-decoration: none; 
            color: #333;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            font-weight: 500;
        }}
        nav a:hover {{ 
            background-color: #f0f0f0;
            border-bottom-color: #0096D6;
        }}
        .container {{
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 20px;
        }}
        .card {{ 
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .card h2 {{ 
            color: #0096D6;
            margin-bottom: 20px;
            font-size: 20px;
            border-bottom: 2px solid #0096D6;
            padding-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        .info-item {{ 
            padding: 12px;
            background: #f9f9f9;
            border-radius: 5px;
            border-left: 4px solid #0096D6;
        }}
        .info-label {{ 
            font-weight: 600;
            color: #555;
            display: block;
            margin-bottom: 5px;
            font-size: 13px;
            text-transform: uppercase;
        }}
        .info-value {{ 
            font-size: 16px;
            color: #333;
        }}
        .status-ok {{ 
            color: #28a745;
            font-weight: 600;
        }}
        .status-warning {{ 
            color: #ffc107;
            font-weight: 600;
        }}
        .status-error {{ 
            color: #dc3545;
            font-weight: 600;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            transition: width 0.3s;
        }}
        .progress-warning {{ background: linear-gradient(90deg, #ffc107, #ffb300); }}
        .progress-error {{ background: linear-gradient(90deg, #dc3545, #c82333); }}
        footer {{ 
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            margin-top: 50px;
        }}
        .logo {{
            font-size: 28px;
            font-weight: bold;
            letter-spacing: -1px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        table th {{
            background: #0096D6;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 500;
        }}
        table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        table tr:hover {{
            background: #f9f9f9;
        }}
        .alert {{
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .alert-success {{
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }}
        .alert-info {{
            background: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }}
    </style>
</head>
"""

def HTML_INDEX():
    toner_percent = int((TONER_LEVEL / TONER_CAPACITY) * 100) if TONER_CAPACITY > 0 else 0
    toner_class = "progress-fill"
    if toner_percent < 20:
        toner_class += " progress-error"
    elif toner_percent < 40:
        toner_class += " progress-warning"
    
    status_class = "status-ok"
    status_text = "Ready"
    
    if toner_percent < 10:
        status_class = "status-error"
        status_text = "Toner Low - Replace Soon"
    elif toner_percent < 20:
        status_class = "status-warning"
        status_text = "Toner Low"
    
    return f"""
{HTML_HEAD}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
    </nav>
    <div class="container">
        <div class="alert alert-success">
            <strong>Device Status:</strong> <span class="{status_class}">{status_text}</span>
        </div>
        
        <div class="card">
            <h2>Device Overview</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Model</span>
                    <span class="info-value">{MODEL}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Serial Number</span>
                    <span class="info-value">{SERIAL}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Hostname</span>
                    <span class="info-value">{HOSTNAME}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Firmware Version</span>
                    <span class="info-value">{FIRMWARE}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Total Pages Printed</span>
                    <span class="info-value">{PAGE_COUNT:,}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Location</span>
                    <span class="info-value">{LOCATION}</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Toner Status</h2>
            <div class="info-item" style="background: white;">
                <span class="info-label">Black Toner Level</span>
                <div class="progress-bar">
                    <div class="{toner_class}" style="width: {toner_percent}%">
                        {toner_percent}%
                    </div>
                </div>
                <p style="margin-top: 10px; color: #666; font-size: 14px;">
                    Approximate pages remaining: {int(TONER_LEVEL * 0.8)}
                </p>
            </div>
        </div>

        <div class="card">
            <h2>Paper Trays</h2>
            <table>
                <tr>
                    <th>Tray</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Sheets</th>
                </tr>
                <tr>
                    <td>Tray 1</td>
                    <td>Multipurpose</td>
                    <td>Letter/A4</td>
                    <td><span class="status-ok">Ready</span></td>
                    <td>{PAPER_TRAY1} / 250</td>
                </tr>
                <tr>
                    <td>Tray 2</td>
                    <td>Main</td>
                    <td>Letter/A4</td>
                    <td><span class="status-ok">Ready</span></td>
                    <td>{PAPER_TRAY2} / 500</td>
                </tr>
                <tr>
                    <td>Output Tray</td>
                    <td>Standard</td>
                    <td>-</td>
                    <td><span class="status-ok">Ready</span></td>
                    <td>{OUTPUT_TRAY} / 150</td>
                </tr>
            </table>
        </div>
    </div>
    <footer>
        &copy; Copyright 2025 HP Development Company, L.P. | Embedded Web Server
    </footer>
</body>
</html>
    """

def HTML_SUPPLIES():
    toner_percent = int((TONER_LEVEL / TONER_CAPACITY) * 100) if TONER_CAPACITY > 0 else 0
    toner_class = "progress-fill"
    if toner_percent < 20:
        toner_class += " progress-error"
    elif toner_percent < 40:
        toner_class += " progress-warning"
    
    return f"""
{HTML_HEAD}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
    </nav>
    <div class="container">
        <div class="card">
            <h2>Supplies Status</h2>
            <div class="alert alert-info">
                Supply levels are approximate. Actual levels may vary.
            </div>
            
            <div style="margin-top: 30px;">
                <div class="info-item" style="background: white; margin-bottom: 30px;">
                    <span class="info-label">Black Toner Cartridge (CF237A)</span>
                    <div class="progress-bar">
                        <div class="{toner_class}" style="width: {toner_percent}%">
                            {toner_percent}%
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding: 10px; background: #f9f9f9; border-radius: 5px;">
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                            <div>
                                <strong>Status:</strong> {"OK" if toner_percent > 20 else "Low - Order Soon"}
                            </div>
                            <div>
                                <strong>Part Number:</strong> CF237A
                            </div>
                            <div>
                                <strong>Approximate Pages:</strong> {int(TONER_LEVEL * 0.8)}
                            </div>
                            <div>
                                <strong>Capacity:</strong> {TONER_CAPACITY:,} pages
                            </div>
                        </div>
                    </div>
                </div>

                <div class="info-item" style="background: white;">
                    <span class="info-label">Maintenance Kit</span>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 75%">
                            75%
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding: 10px; background: #f9f9f9; border-radius: 5px;">
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                            <div>
                                <strong>Status:</strong> OK
                            </div>
                            <div>
                                <strong>Part Number:</strong> CF254A
                            </div>
                            <div>
                                <strong>Pages until replacement:</strong> 50,218
                            </div>
                            <div>
                                <strong>Service interval:</strong> 200,000 pages
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Order Supplies</h2>
            <p style="margin-bottom: 15px;">Original HP supplies are designed to work with your printer for consistent, reliable results.</p>
            <div class="info-grid">
                <div class="info-item">
                    <strong>HP.com</strong><br>
                    Visit <a href="http://www.hp.com/buy/supplies" style="color: #0096D6;">www.hp.com/buy/supplies</a>
                </div>
                <div class="info-item">
                    <strong>Support</strong><br>
                    Call 1-800-HP-INVENT<br>
                    (1-800-474-6836)
                </div>
            </div>
        </div>
    </div>
    <footer>
        &copy; Copyright 2025 HP Development Company, L.P. | Embedded Web Server
    </footer>
</body>
</html>
    """

def HTML_NETWORK():
    return f"""
{HTML_HEAD}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
    </nav>
    <div class="container">
        <div class="card">
            <h2>Network Configuration</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Hostname</span>
                    <span class="info-value">{HOSTNAME}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">IP Address</span>
                    <span class="info-value">{IP}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">MAC Address</span>
                    <span class="info-value">{MAC}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Connection Status</span>
                    <span class="info-value"><span class="status-ok">Connected</span></span>
                </div>
                <div class="info-item">
                    <span class="info-label">Link Speed</span>
                    <span class="info-value">1000 Mbps Full Duplex</span>
                </div>
                <div class="info-item">
                    <span class="info-label">DHCP</span>
                    <span class="info-value">Enabled</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Network Services</h2>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Port</th>
                    <th>Status</th>
                    <th>Description</th>
                </tr>
                <tr>
                    <td>HTTP</td>
                    <td>80</td>
                    <td><span class="status-ok">Enabled</span></td>
                    <td>Web Management Interface</td>
                </tr>
                <tr>
                    <td>SNMP</td>
                    <td>161</td>
                    <td><span class="status-ok">Enabled</span></td>
                    <td>Network Monitoring</td>
                </tr>
                <tr>
                    <td>HP JetDirect</td>
                    <td>9100</td>
                    <td><span class="status-ok">Enabled</span></td>
                    <td>Raw Printing</td>
                </tr>
                <tr>
                    <td>LPD</td>
                    <td>515</td>
                    <td><span class="status-ok">Enabled</span></td>
                    <td>Line Printer Daemon</td>
                </tr>
                <tr>
                    <td>IPP</td>
                    <td>631</td>
                    <td><span class="status-ok">Enabled</span></td>
                    <td>Internet Printing Protocol</td>
                </tr>
            </table>
        </div>

        <div class="card">
            <h2>Device Discovery</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Bonjour Name</span>
                    <span class="info-value">{HOSTNAME}._pdl-datastream._tcp</span>
                </div>
                <div class="info-item">
                    <span class="info-label">LLMNR</span>
                    <span class="info-value">Enabled</span>
                </div>
                <div class="info-item">
                    <span class="info-label">WS-Discovery</span>
                    <span class="info-value">Enabled</span>
                </div>
                <div class="info-item">
                    <span class="info-label">SNMP v1/v2c</span>
                    <span class="info-value">Public Community</span>
                </div>
            </div>
        </div>
    </div>
    <footer>
        &copy; Copyright 2025 HP Development Company, L.P. | Embedded Web Server
    </footer>
</body>
</html>
    """

def HTML_INFO():
    return f"""
{HTML_HEAD}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
    </nav>
    <div class="container">
        <div class="card">
            <h2>Device Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Product Name</span>
                    <span class="info-value">{MODEL}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Serial Number</span>
                    <span class="info-value">{SERIAL}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Firmware Version</span>
                    <span class="info-value">{FIRMWARE}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Firmware Date</span>
                    <span class="info-value">2024-09-08</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Model Number</span>
                    <span class="info-value">K0Q18A</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Product Number</span>
                    <span class="info-value">K0Q18A#BGJ</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Usage Statistics</h2>
            <table>
                <tr>
                    <th>Counter</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Total Pages Printed</td>
                    <td>{PAGE_COUNT:,}</td>
                </tr>
                <tr>
                    <td>Black Pages Printed</td>
                    <td>{PAGE_COUNT:,}</td>
                </tr>
                <tr>
                    <td>Duplex Pages</td>
                    <td>{int(PAGE_COUNT * 0.6):,}</td>
                </tr>
                <tr>
                    <td>Jam Events</td>
                    <td>12</td>
                </tr>
                <tr>
                    <td>Mispick Events</td>
                    <td>8</td>
                </tr>
            </table>
        </div>

        <div class="card">
            <h2>Device Details</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Print Technology</span>
                    <span class="info-value">Laser</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Print Speed</span>
                    <span class="info-value">Up to 71 ppm</span>
                </div>
                <div class="info-item">
                    <span class="info-label">First Page Out</span>
                    <span class="info-value">5.6 seconds</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Processor</span>
                    <span class="info-value">1.2 GHz</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Memory</span>
                    <span class="info-value">512 MB</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Duty Cycle</span>
                    <span class="info-value">300,000 pages/month</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Location Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Location</span>
                    <span class="info-value">{LOCATION}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Contact</span>
                    <span class="info-value">{CONTACT}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Asset Number</span>
                    <span class="info-value">ASSET-{SERIAL[:8]}</span>
                </div>
            </div>
        </div>
    </div>
    <footer>
        &copy; Copyright 2025 HP Development Company, L.P. | Embedded Web Server
    </footer>
</body>
</html>
    """

def HTML_PRINT_QUALITY():
    return f"""
{HTML_HEAD}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
    </nav>
    <div class="container">
        <div class="card">
            <h2>Print Quality Tools</h2>
            <p style="margin-bottom: 20px;">Use these tools to maintain and troubleshoot print quality issues.</p>
            
            <div class="info-grid">
                <div class="info-item">
                    <strong>Clean Printheads</strong><br>
                    <p style="margin: 10px 0; color: #666;">Clean the printheads to resolve streaks or spots.</p>
                    <button style="padding: 8px 16px; background: #0096D6; color: white; border: none; border-radius: 4px; cursor: pointer;">Start Cleaning</button>
                </div>
                <div class="info-item">
                    <strong>Calibrate Printer</strong><br>
                    <p style="margin: 10px 0; color: #666;">Calibrate to ensure optimal print quality.</p>
                    <button style="padding: 8px 16px; background: #0096D6; color: white; border: none; border-radius: 4px; cursor: pointer;">Start Calibration</button>
                </div>
                <div class="info-item">
                    <strong>Print Test Page</strong><br>
                    <p style="margin: 10px 0; color: #666;">Print a test page to check quality.</p>
                    <button style="padding: 8px 16px; background: #0096D6; color: white; border: none; border-radius: 4px; cursor: pointer;">Print Test Page</button>
                </div>
                <div class="info-item">
                    <strong>Print Diagnostic Page</strong><br>
                    <p style="margin: 10px 0; color: #666;">Print diagnostic information.</p>
                    <button style="padding: 8px 16px; background: #0096D6; color: white; border: none; border-radius: 4px; cursor: pointer;">Print Diagnostic</button>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Print Settings</h2>
            <table>
                <tr>
                    <th>Setting</th>
                    <th>Current Value</th>
                </tr>
                <tr>
                    <td>Print Quality</td>
                    <td>Normal (600 dpi)</td>
                </tr>
                <tr>
                    <td>Toner Density</td>
                    <td>Level 3 (Normal)</td>
                </tr>
                <tr>
                    <td>EconoMode</td>
                    <td>Off</td>
                </tr>
                <tr>
                    <td>Resolution Enhancement (REt)</td>
                    <td>On</td>
                </tr>
            </table>
        </div>
    </div>
    <footer>
        &copy; Copyright 2025 HP Development Company, L.P. | Embedded Web Server
    </footer>
</body>
</html>
    """

class HPPrinterHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to use our logger"""
        pass
    
    def do_GET(self):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) GET {self.path}")
        
        if self.path == "/" or self.path == "/index.html" or self.path == "/hp/device/this.LCDispatcher":
            html = HTML_INDEX()
            self.respond(200, html)
        elif self.path == "/supplies" or self.path == "/hp/device/InternalPages/Index?id=SuppliesStatus":
            html = HTML_SUPPLIES()
            self.respond(200, html)
        elif self.path == "/network" or self.path == "/hp/device/InternalPages/Index?id=NetworkingTab":
            html = HTML_NETWORK()
            self.respond(200, html)
        elif self.path == "/info" or self.path == "/hp/device/DeviceInformation/Index":
            html = HTML_INFO()
            self.respond(200, html)
        elif self.path == "/print-quality" or self.path == "/hp/device/InternalPages/Index?id=PrintQuality":
            html = HTML_PRINT_QUALITY()
            self.respond(200, html)
        # API endpoints that might be queried
        elif self.path.startswith("/DevMgmt/"):
            self.respond_json(200, {
                "Status": "Ready",
                "StatusCode": 10001,
                "Model": MODEL,
                "SerialNumber": SERIAL
            })
        elif self.path.startswith("/ePrint/"):
            self.respond_json(200, {"ePrintStatus": "disabled"})
        else:
            self.respond(404, "<h1>404 Not Found</h1>")
    
    def respond(self, status, content):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) Response: {status}")
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Server', 'HP-ChaiSOE/2.0')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def respond_json(self, status, data):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) JSON Response: {status}")
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Server', 'HP-ChaiSOE/2.0')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def get_client_ip_and_version(client_address):
    raw_ip = client_address[0]
    try:
        ip_obj = ipaddress.ip_address(raw_ip)
        if ip_obj.version == 6 and ip_obj.ipv4_mapped:
            return str(ip_obj.ipv4_mapped), "IPv4"
        else:
            return str(ip_obj), f"IPv{ip_obj.version}"
    except ValueError:
        return "Unknown", "Unknown"

def run(port=80):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, HPPrinterHandler)
    logger.info(f"HP Printer Web Server listening on port {port}")
    print(f"HP Printer Embedded Web Server running on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    port, config = parse_args()
    
    # Load global config
    SYSTEM_NAME = config.get('system_name', 'HP LaserJet')
    IP = config.get('ip', '192.168.1.100')
    MAC = config.get('mac', '00:00:00:00:00:00')
    HOSTNAME = config.get('hostname', 'HPLJ')
    SERIAL = config.get('serial', 'UNKNOWN')
    MODEL = config.get('model', 'HP LaserJet')
    FIRMWARE = config.get('firmware', '1.0.0')
    LOCATION = config.get('location', 'Office')
    CONTACT = config.get('contact', 'Admin')
    PAGE_COUNT = config.get('page_count', 0)
    TONER_LEVEL = config.get('toner_level', 100)
    TONER_CAPACITY = config.get('toner_capacity', 10000)
    PAPER_TRAY1 = config.get('paper_tray1', 250)
    PAPER_TRAY2 = config.get('paper_tray2', 500)
    OUTPUT_TRAY = config.get('output_tray', 0)
    
    logger.info(f"Starting web server for {MODEL} (S/N: {SERIAL})")
    
    run(port)
