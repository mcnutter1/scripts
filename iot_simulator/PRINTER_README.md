# HP Printer Simulator

This is a comprehensive HP LaserJet printer simulator that simulates an HP LaserJet Enterprise M609dn with full network functionality and **Windows printer discovery support**.

## Features

The simulator includes five main server components:

### 1. **SNMP Server** (Port 161)
- Responds to SNMP queries with printer-specific OIDs
- Supports standard MIB-II objects
- Implements Printer MIB (RFC 3805)
- Supports HP Enterprise OIDs
- Provides device info, status, supplies, page counts, and more

### 2. **HP JetDirect Server** (Port 9100)
- Implements HP JetDirect raw printing protocol
- Accepts print jobs over TCP port 9100
- **Saves all print jobs to files** with metadata logging
- Supports PJL (Printer Job Language) commands
- Responds to printer status queries
- Logs print job information (type, size, estimated pages)
- Maintains detailed print log in JSON format

### 3. **Embedded Web Server** (Port 80)
- Full HP-style web interface with authentic styling
- **Status page**: Device overview, toner levels, paper trays
- **Supplies page**: Detailed supply information and ordering
- **Network page**: Network configuration and services
- **Device Info page**: Complete device details and usage statistics
- **Print Quality page**: Maintenance tools and settings

### 4. **WS-Discovery Server** (Port 3702)
- Windows Web Services Discovery protocol
- Enables Windows "Add Printer" wizard discovery
- Responds to Probe and Resolve requests
- Sends Hello announcements on startup
- **Makes printer automatically appear in Windows printer search**

### 5. **LLMNR Server** (Port 5355)
- Link-Local Multicast Name Resolution
- Enables hostname resolution without DNS
- Windows systems can find printer by hostname
- Works on isolated networks

## Windows Printer Discovery

**The printer is now fully discoverable by Windows!**

When you use Windows "Add Printer" wizard, the simulator:
- ✅ Appears automatically in the device list
- ✅ Shows as "HP LaserJet Enterprise M609dn"
- ✅ Provides all printer information via SNMP
- ✅ Accepts print jobs via JetDirect
- ✅ Resolves hostname without DNS server

See **[WINDOWS_DISCOVERY.md](WINDOWS_DISCOVERY.md)** for complete details on:
- How Windows discovery works
- Setting up firewall rules
- Testing discovery protocols
- Troubleshooting discovery issues
- Print job logging and monitoring

## Configuration

The simulator uses `config_hp_printer.json` for configuration:

```json
{
  "globals": {
    "system_name": "HP LaserJet Enterprise M609dn",
    "ip": "192.168.1.100",
    "mac": "A0:B3:CC:D4:E5:F6",
    "hostname": "HPLJ-M609-001",
    "uuid": "12345678-90ab-cdef-1234-567890abcdef",
    "serial": "JPBCS12345",
    "model": "HP LaserJet Enterprise M609dn",
    "firmware": "2409081_052604",
    "location": "Building A - Floor 2",
    "contact": "IT Department",
    "page_count": 45782,
    "toner_level": 68,
    "toner_capacity": 10000,
    "paper_tray1": 250,
    "paper_tray2": 500,
    "output_tray": 150
  },
  "servers": [...]
}
```

## Running the Simulator

### Prerequisites

Make sure you have Python 3.x installed and the required permissions to bind to low ports (80, 161).

### Start the Simulator

```bash
# Navigate to the iot_simulator directory
cd /path/to/iot_simulator

# Start with HP printer configuration
sudo python3 server.py start --config config_hp_printer.json

# Or use the quick setup script
sudo ./setup_hp_printer.sh
```

### Binding to Privileged Ports

Since ports 80 and 161 are privileged (< 1024), you may need to:

**Option 1: Run as root (not recommended)**
```bash
sudo python3 server.py start
```

**Option 2: Grant Python capability to bind to low ports (Linux)**
```bash
sudo setcap 'cap_net_bind_service=+ep' $(which python3)
```

**Option 3: Use alternative ports (modify config_hp_printer.json)**
```json
{
  "servers": [
    {"path": "servers/printer_web_server.py", "port": 8080},
    {"path": "servers/snmp_server.py", "port": 1161},
    {"path": "servers/jetdirect_server.py", "port": 9100}
  ]
}
```

## Testing the Simulator

### Test Web Interface
Open a browser and navigate to:
- `http://localhost/` (or `http://localhost:8080` if using alternative port)
- View status, supplies, network, device info, and print quality pages

### Test SNMP
```bash
# Get system description
snmpget -v2c -c public localhost:161 1.3.6.1.2.1.1.1.0

# Get printer model
snmpget -v2c -c public localhost:161 1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0

# Get page count
snmpget -v2c -c public localhost:161 1.3.6.1.2.1.43.10.2.1.4.1.1

# Get toner level
snmpget -v2c -c public localhost:161 1.3.6.1.2.1.43.11.1.1.6.1.1

# Walk printer MIB
snmpwalk -v2c -c public localhost:161 1.3.6.1.2.1.43
```

### Test JetDirect Printing
```bash
# Send a test print job
echo "Test print job" | nc localhost 9100

# Query printer status using PJL
printf '\x1b%%-12345X@PJL INFO ID\r\n@PJL INFO STATUS\r\n\x1b%%-12345X' | nc localhost 9100

# Send a simple text print
cat document.txt | nc localhost 9100

# Test with a PDF (if printer supports raw PDF)
cat document.pdf | nc localhost 9100
```

### Network Scanner Detection
The simulated printer should be detected by network scanning tools:
- **Nmap**: Will detect open ports 80, 161, 9100
- **SNMP scanners**: Will identify as HP LaserJet printer
- **Printer discovery tools**: Should detect via SNMP and HTTP

```bash
# Scan for printer
nmap -p 80,161,9100 localhost

# SNMP scan
nmap -sU -p 161 --script=snmp-info localhost
```

## Logs

Logs are stored in the `logs/` directory:
- `printer_web_server.py.out` - Web server output
- `printer_web_server.py.err` - Web server errors
- `snmp_server.py.out` - SNMP server output
- `snmp_server.py.err` - SNMP server errors
- `jetdirect_server.py.out` - JetDirect server output
- `jetdirect_server.py.err` - JetDirect server errors

## Stopping the Simulator

```bash
python3 server.py stop
```

## Check Status

```bash
# Check if daemon is running
python3 server.py status

# Check which services are running
ps aux | grep python3 | grep server
```

## Switch Between Device Types

The simulator now supports multiple configuration files:

```bash
# Run HP printer simulation
sudo python3 server.py start --config config_hp_printer.json

# Stop and switch to medical device
sudo python3 server.py stop
sudo python3 server.py start --config config.json

# Or use restart
sudo python3 server.py restart --config config.json
```

## Customization

You can customize the printer by editing `config_hp_printer.json`:
- Change model name and serial number
- Adjust toner levels and page counts
- Modify network settings (IP, MAC, hostname)
- Update location and contact information
- Change paper tray capacities

## Realistic Simulation Features

✅ **Authentic HP Web Interface**: Mimics real HP Embedded Web Server design  
✅ **SNMP MIB Support**: Implements standard printer MIB objects  
✅ **JetDirect Protocol**: Accepts raw print jobs and PJL commands  
✅ **Status Reporting**: Reports toner levels, page counts, device status  
✅ **Network Services**: Multiple protocols (HTTP, SNMP, JetDirect)  
✅ **Print Job Logging**: Tracks print jobs with size and type detection  

## Use Cases

- **Security testing**: Test vulnerability scanners against printer targets
- **Network discovery**: Test device discovery and enumeration tools
- **SNMP monitoring**: Test SNMP management and monitoring systems
- **Print management**: Test print queue management and tracking software
- **Penetration testing**: Practice printer-specific attack vectors
- **Development**: Test applications that interact with printers

## Notes

- The SNMP implementation is simplified but responds to common OIDs
- JetDirect accepts print jobs but doesn't render them (logs only)
- Web interface is read-only (no configuration changes applied)
- Designed for testing and simulation purposes only

## Troubleshooting

**Port binding errors**: Make sure ports aren't already in use:
```bash
# Check if ports are in use
sudo lsof -i :80
sudo lsof -i :161
sudo lsof -i :9100
```

**SNMP not responding**: Make sure UDP port 161 is open and not blocked by firewall

**Can't access web interface**: Check that port 80 (or alternative) is accessible and not blocked

## Architecture

```
config_hp_printer.json
    ↓
server.py (daemon)
    ↓
    ├── servers/printer_web_server.py (HTTP on port 80)
    ├── servers/snmp_server.py (SNMP on UDP port 161)
    └── servers/jetdirect_server.py (TCP on port 9100)
```

Each server runs as a separate process managed by the main daemon.
