#!/usr/bin/env python3
"""
HP Printer Web Server Simulator
Simulates HP Embedded Web Server (EWS) interface
Includes admin panel for viewing print jobs
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import sys
import os
import json
from datetime import datetime
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args
import ipaddress

logger = get_logger("printer_web_server")

# Admin credentials (username: admin, password: admin123)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# Session management
active_sessions = {}

# Print jobs directory
PRINT_JOBS_DIR = os.path.join(os.path.dirname(__file__), '..', 'print_jobs')
PRINT_LOG_FILE = os.path.join(PRINT_JOBS_DIR, 'print_log.json')

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
def HTML_HEAD():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>HP {MODEL} - Embedded Web Server</title>
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
{HTML_HEAD()}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server | Firmware: {FIRMWARE}</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
        <a href="/admin" style="float: right; background: rgba(0,150,214,0.1);">🔐 Admin</a>
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
{HTML_HEAD()}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server | Firmware: {FIRMWARE}</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
        <a href="/admin" style="float: right; background: rgba(0,150,214,0.1);">🔐 Admin</a>
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
{HTML_HEAD()}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server | Firmware: {FIRMWARE}</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
        <a href="/admin" style="float: right; background: rgba(0,150,214,0.1);">🔐 Admin</a>
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
{HTML_HEAD()}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server | Firmware: {FIRMWARE}</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
        <a href="/admin" style="float: right; background: rgba(0,150,214,0.1);">🔐 Admin</a>
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
{HTML_HEAD()}
<body>
    <header>
        <div class="logo">HP</div>
        <h1>{MODEL}</h1>
        <div class="subtitle">Embedded Web Server | Firmware: {FIRMWARE}</div>
    </header>
    <nav>
        <a href="/">Status</a>
        <a href="/supplies">Supplies Status</a>
        <a href="/network">Network</a>
        <a href="/info">Device Information</a>
        <a href="/print-quality">Print Quality</a>
        <a href="/admin" style="float: right; background: rgba(0,150,214,0.1);">🔐 Admin</a>
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


# Admin Panel HTML Templates

def HTML_ADMIN_LOGIN(error_msg=""):
    """Admin login page"""
    error_html = f'<div class="alert alert-error">{error_msg}</div>' if error_msg else ''
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - HP {MODEL}</title>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0096D6 0%, #0073A8 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .login-container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            width: 400px;
        }}
        h1 {{
            color: #0096D6;
            margin-bottom: 10px;
            font-size: 24px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 600;
        }}
        input[type="text"],
        input[type="password"] {{
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        input[type="text"]:focus,
        input[type="password"]:focus {{
            outline: none;
            border-color: #0096D6;
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: #0096D6;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }}
        button:hover {{
            background: #0073A8;
        }}
        .alert-error {{
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #dc3545;
        }}
        .back-link {{
            text-align: center;
            margin-top: 20px;
        }}
        .back-link a {{
            color: #0096D6;
            text-decoration: none;
        }}
        .back-link a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Admin Panel</h1>
        <div class="subtitle">HP {MODEL}</div>
        {error_html}
        <form method="POST" action="/admin/login">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="back-link">
            <a href="/">← Back to Printer Home</a>
        </div>
    </div>
</body>
</html>
    """


def HTML_ADMIN_DASHBOARD():
    """Admin dashboard - print jobs list"""
    # Load print log
    print_jobs = []
    if os.path.exists(PRINT_LOG_FILE):
        try:
            with open(PRINT_LOG_FILE, 'r') as f:
                print_jobs = json.load(f)
        except:
            pass
    
    # Reverse to show newest first
    print_jobs = list(reversed(print_jobs))
    
    # Build table rows
    rows_html = ""
    if not print_jobs:
        rows_html = '<tr><td colspan="8" style="text-align: center; padding: 30px; color: #666;">No print jobs recorded yet</td></tr>'
    else:
        for job in print_jobs:
            job_id = job.get('job_id', 'N/A')
            timestamp = job.get('timestamp', 'N/A')
            if timestamp != 'N/A':
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            source_ip = job.get('source_ip', 'N/A')
            doc_type = job.get('document_type', 'Unknown')
            pages = job.get('pages', 0)
            size_kb = int(job.get('size_bytes', 0) / 1024)
            filename = job.get('filename', 'N/A')
            status = job.get('status', 'unknown')
            
            status_badge = 'status-ok' if status == 'completed' else 'status-warning'
            
            rows_html += f"""
                <tr>
                    <td>{job_id}</td>
                    <td>{timestamp}</td>
                    <td>{source_ip}</td>
                    <td><span class="doc-type-badge">{doc_type}</span></td>
                    <td>{pages}</td>
                    <td>{size_kb:,} KB</td>
                    <td><span class="{status_badge}">{status}</span></td>
                    <td>
                        <a href="/admin/download?file={filename}" class="btn-download">📥 Download</a>
                        <a href="/admin/view?file={filename}" class="btn-view">👁️ View</a>
                    </td>
                </tr>
            """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - Print Jobs</title>
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
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        header h1 {{ font-size: 24px; }}
        .logout-btn {{
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .logout-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .container {{
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            color: #0096D6;
        }}
        .stat-label {{
            margin-top: 5px;
            color: #666;
            font-size: 14px;
        }}
        .card {{
            background: white;
            padding: 25px;
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
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #0096D6;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .doc-type-badge {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-ok {{
            color: #28a745;
            font-weight: 600;
        }}
        .status-warning {{
            color: #ffc107;
            font-weight: 600;
        }}
        .btn-download,
        .btn-view {{
            display: inline-block;
            padding: 6px 12px;
            margin: 0 2px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 12px;
            transition: background 0.3s;
        }}
        .btn-download {{
            background: #0096D6;
            color: white;
        }}
        .btn-download:hover {{
            background: #0073A8;
        }}
        .btn-view {{
            background: #6c757d;
            color: white;
        }}
        .btn-view:hover {{
            background: #5a6268;
        }}
        .refresh-btn {{
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            margin-bottom: 20px;
            text-decoration: none;
            display: inline-block;
        }}
        .refresh-btn:hover {{
            background: #218838;
        }}
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {{
            window.location.reload();
        }}, 30000);
    </script>
</head>
<body>
    <header>
        <h1>🔐 Admin Panel - Print Jobs</h1>
        <a href="/admin/logout" class="logout-btn">Logout</a>
    </header>
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(print_jobs)}</div>
                <div class="stat-label">Total Print Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(j.get('pages', 0) for j in print_jobs)}</div>
                <div class="stat-label">Total Pages</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(j.get('size_bytes', 0) for j in print_jobs) / 1024 / 1024:.1f} MB</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>
        
        <a href="/admin" class="refresh-btn">🔄 Refresh</a>
        
        <div class="card">
            <h2>Print Job History</h2>
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Timestamp</th>
                        <th>Source IP</th>
                        <th>Type</th>
                        <th>Pages</th>
                        <th>Size</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    """


def HTML_ADMIN_VIEW_JOB(filename, file_content, file_type):
    """View print job details"""
    # For binary files, show hex dump preview
    preview_html = ""
    if file_type in ['pdf', 'ps', 'pcl', 'prn']:
        # Show first 1000 bytes as hex
        hex_preview = ' '.join(f'{b:02x}' for b in file_content[:1000])
        preview_html = f"""
        <div class="code-block">
            <h3>File Preview (First 1000 bytes - Hex)</h3>
            <pre style="font-family: monospace; font-size: 12px; background: #f5f5f5; padding: 15px; overflow-x: auto;">{hex_preview}</pre>
        </div>
        """
        
        # Try to detect if it's text-based
        try:
            text_preview = file_content[:2000].decode('utf-8', errors='ignore')
            if text_preview.isprintable() or '%PDF' in text_preview or '%!PS' in text_preview:
                preview_html += f"""
                <div class="code-block">
                    <h3>Text Preview (if readable)</h3>
                    <pre style="font-family: monospace; font-size: 12px; background: #f5f5f5; padding: 15px; overflow-x: auto; white-space: pre-wrap;">{text_preview[:2000]}</pre>
                </div>
                """
        except:
            pass
    
    file_size_kb = len(file_content) / 1024
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>View Job - {filename}</title>
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
        header h1 {{ font-size: 24px; }}
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
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .info-item {{
            padding: 12px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            font-size: 13px;
        }}
        .info-value {{
            margin-top: 5px;
            font-size: 16px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 600;
            transition: background 0.3s;
        }}
        .btn-primary {{
            background: #0096D6;
            color: white;
        }}
        .btn-primary:hover {{
            background: #0073A8;
        }}
        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #5a6268;
        }}
        .code-block {{
            margin-top: 20px;
        }}
        .code-block h3 {{
            margin-bottom: 10px;
            color: #555;
        }}
    </style>
</head>
<body>
    <header>
        <h1>📄 View Print Job</h1>
    </header>
    <div class="container">
        <div class="card">
            <h2>File Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Filename</div>
                    <div class="info-value">{filename}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">File Type</div>
                    <div class="info-value">{file_type.upper()}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">File Size</div>
                    <div class="info-value">{file_size_kb:.2f} KB</div>
                </div>
            </div>
            <a href="/admin/download?file={filename}" class="btn btn-primary">📥 Download File</a>
            <a href="/admin" class="btn btn-secondary">← Back to Admin Panel</a>
        </div>
        
        <div class="card">
            {preview_html if preview_html else '<p>No preview available for this file type.</p>'}
        </div>
    </div>
</body>
</html>
    """


class HPPrinterHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to use our logger"""
        pass
    
    def get_session_token(self):
        """Extract session token from cookies"""
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session='):
                return cookie.split('=')[1]
        return None
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        token = self.get_session_token()
        if token and token in active_sessions:
            return True
        return False
    
    def set_session_cookie(self, token):
        """Set session cookie"""
        self.send_header('Set-Cookie', f'session={token}; Path=/; HttpOnly')
    
    def clear_session_cookie(self):
        """Clear session cookie"""
        self.send_header('Set-Cookie', 'session=; Path=/; Max-Age=0')
    
    def do_GET(self):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) GET {self.path}")
        
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        # Admin routes
        if path.startswith('/admin'):
            if path == '/admin' or path == '/admin/':
                if not self.is_authenticated():
                    self.redirect('/admin/login')
                    return
                html = HTML_ADMIN_DASHBOARD()
                self.respond(200, html)
                
            elif path == '/admin/login':
                html = HTML_ADMIN_LOGIN()
                self.respond(200, html)
                
            elif path == '/admin/logout':
                token = self.get_session_token()
                if token and token in active_sessions:
                    del active_sessions[token]
                self.redirect_with_clear_cookie('/')
                
            elif path == '/admin/download':
                if not self.is_authenticated():
                    self.redirect('/admin/login')
                    return
                    
                filename = query.get('file', [''])[0]
                if filename:
                    filepath = os.path.join(PRINT_JOBS_DIR, filename)
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        try:
                            with open(filepath, 'rb') as f:
                                content = f.read()
                            self.send_file_download(filename, content)
                        except Exception as e:
                            logger.error(f"Error reading file {filename}: {e}")
                            self.respond(500, f"<h1>Error reading file</h1><p>{str(e)}</p>")
                    else:
                        self.respond(404, "<h1>File not found</h1>")
                else:
                    self.respond(400, "<h1>No file specified</h1>")
                    
            elif path == '/admin/view':
                if not self.is_authenticated():
                    self.redirect('/admin/login')
                    return
                    
                filename = query.get('file', [''])[0]
                if filename:
                    filepath = os.path.join(PRINT_JOBS_DIR, filename)
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        try:
                            with open(filepath, 'rb') as f:
                                content = f.read()
                            file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
                            html = HTML_ADMIN_VIEW_JOB(filename, content, file_type)
                            self.respond(200, html)
                        except Exception as e:
                            logger.error(f"Error reading file {filename}: {e}")
                            self.respond(500, f"<h1>Error reading file</h1><p>{str(e)}</p>")
                    else:
                        self.respond(404, "<h1>File not found</h1>")
                else:
                    self.respond(400, "<h1>No file specified</h1>")
            else:
                self.respond(404, "<h1>404 Not Found</h1>")
            return
        
        # Regular printer pages
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
    
    def do_POST(self):
        """Handle POST requests (login form)"""
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) POST {self.path}")
        
        if self.path == '/admin/login':
            # Read form data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            form_data = parse_qs(post_data)
            
            username = form_data.get('username', [''])[0]
            password = form_data.get('password', [''])[0]
            
            # Validate credentials
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
                # Create session
                token = secrets.token_urlsafe(32)
                active_sessions[token] = {
                    'username': username,
                    'created': datetime.now().isoformat(),
                    'ip': client_ip
                }
                logger.info(f"Admin login successful from {client_ip}")
                
                # Redirect to admin panel with session cookie
                self.send_response(302)
                self.send_header('Location', '/admin')
                self.set_session_cookie(token)
                self.end_headers()
            else:
                # Login failed
                logger.warning(f"Failed admin login attempt from {client_ip}")
                html = HTML_ADMIN_LOGIN("Invalid username or password")
                self.respond(401, html)
        else:
            self.respond(404, "<h1>404 Not Found</h1>")
    
    def redirect(self, location):
        """Send redirect response"""
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()
    
    def redirect_with_clear_cookie(self, location):
        """Send redirect and clear session cookie"""
        self.send_response(302)
        self.send_header('Location', location)
        self.clear_session_cookie()
        self.end_headers()
    
    def send_file_download(self, filename, content):
        """Send file as download"""
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) Downloading: {filename}")
        
        # Determine content type
        content_type = 'application/octet-stream'
        if filename.endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.endswith('.ps'):
            content_type = 'application/postscript'
        
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Server', 'HP-ChaiSOE/1.0')
        self.send_header('X-HP-ChaiServer', 'ChaiSOE/1.0')
        self.send_header('X-HP-Firmware-Version', FIRMWARE)
        self.end_headers()
        self.wfile.write(content)
    
    def respond(self, status, content):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) Response: {status}")
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Server', 'HP-ChaiSOE/1.0')
        self.send_header('X-HP-ChaiServer', 'ChaiSOE/1.0')
        self.send_header('X-HP-Firmware-Version', FIRMWARE)
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def respond_json(self, status, data):
        client_ip, ip_version = get_client_ip_and_version(self.client_address)
        logger.info(f"{client_ip} ({ip_version}) JSON Response: {status}")
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Server', 'HP-ChaiSOE/1.0')
        self.send_header('X-HP-ChaiServer', 'ChaiSOE/1.0')
        self.send_header('X-HP-Firmware-Version', FIRMWARE)
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
