# HP Printer Simulator System - Complete Overview

## 📦 What's Included

This is a comprehensive HP LaserJet Enterprise M609dn printer simulator that makes your Ubuntu 24 system appear and behave like a real HP printer on the network.

### Core Components

1. **System Impersonation Script** (`impersonate_hp_printer.sh`)
   - Changes MAC address to HP printer MAC
   - Sets hostname to printer name
   - Configures Avahi/Bonjour for mDNS discovery
   - Sets up DHCP client identity
   - Creates system banners
   - Configures firewall rules
   - Makes changes persistent across reboots
   - **Backs up original configuration** for easy restoration

2. **Printer Simulator Services**
   - **Web Server** (port 80): Full HP Embedded Web Server interface
   - **SNMP Server** (port 161): Responds to printer MIB queries
   - **JetDirect Server** (port 9100): Accepts raw print jobs

3. **Configuration & Documentation**
   - Pre-configured printer settings
   - Comprehensive setup guides
   - Quick reference card
   - Troubleshooting documentation

## 🎯 Key Features

### Realistic HP Printer Simulation
✅ Authentic HP Embedded Web Server interface  
✅ Complete SNMP MIB implementation (RFC 3805)  
✅ HP JetDirect protocol support with PJL  
✅ Network discovery via Avahi/Bonjour  
✅ Realistic toner levels, page counts, status  
✅ Multiple network protocols (HTTP, SNMP, JetDirect)  
✅ Print job acceptance and logging  
✅ Device fingerprinting matches real HP printers  

### System-Level Integration
✅ MAC address spoofing with persistence  
✅ Hostname configuration  
✅ DHCP client identity  
✅ mDNS/Bonjour service announcements  
✅ Firewall configuration  
✅ Complete backup/restore capability  

## 📁 Files Created

```
iot_simulator/
├── config_hp_printer.json              # Printer configuration
├── impersonate_hp_printer.sh           # System impersonation (NEW)
├── setup_hp_printer.sh                 # One-command setup (NEW)
├── PRINTER_README.md                   # Full documentation (NEW)
├── IMPERSONATION_GUIDE.md              # System config guide (NEW)
├── QUICK_REFERENCE.md                  # Quick reference (NEW)
├── SUMMARY.md                          # This file (NEW)
└── servers/
    ├── printer_web_server.py           # HTTP/Web interface (NEW)
    ├── snmp_server.py                  # SNMP responder (NEW)
    └── jetdirect_server.py             # JetDirect/PJL (NEW)
```

## 🚀 Getting Started

### Option 1: Automated Setup (Recommended)
```bash
cd /path/to/iot_simulator
chmod +x setup_hp_printer.sh impersonate_hp_printer.sh
sudo ./setup_hp_printer.sh
```

This will:
1. Install dependencies
2. Configure system identity
3. Start all services
4. Verify setup
5. Show access information

### Option 2: Manual Setup
```bash
# Step 1: Configure system
sudo ./impersonate_hp_printer.sh start

# Step 2: Configure services
cp config_hp_printer.json config.json

# Step 3: Start services
sudo python3 server.py start

# Step 4: Verify
sudo ./impersonate_hp_printer.sh status
```

## 🔍 What You'll See

### On Your Network

**DHCP Discovery:**
```
Device Name: HPLJ-M609-001
MAC Address: A0:B3:CC:D4:E5:F6
Vendor: HP (Hewlett-Packard)
```

**mDNS/Bonjour:**
```
HPLJ-M609-001.local
Service: _printer._tcp
Service: _pdl-datastream._tcp
Service: _http._tcp
```

**SNMP Fingerprint:**
```
sysDescr: HP LaserJet Enterprise M609dn
sysName: HPLJ-M609-001
sysObjectID: 1.3.6.1.4.1.11.2.3.9.1 (HP)
Model: HP LaserJet Enterprise M609dn
Serial: JPBCS12345
```

**Open Ports:**
```
80/tcp   - HTTP (HP Embedded Web Server)
161/udp  - SNMP (Device management)
9100/tcp - JetDirect (Raw printing)
```

### In Your Browser

Navigate to `http://localhost/` or `http://<your-ip>/`:

**Status Page:**
- Device overview with model and serial
- Real-time toner level with progress bar
- Paper tray status
- Total pages printed
- Device location and contact

**Supplies Page:**
- Detailed toner cartridge information
- Part numbers and capacity
- Approximate pages remaining
- Ordering information

**Network Page:**
- IP and MAC address
- Network services status
- Link speed and connection
- Available protocols

**Device Info Page:**
- Complete specifications
- Firmware version
- Usage statistics
- Maintenance counters

## 🧪 Testing Commands

### Quick Tests
```bash
# Web interface
curl http://localhost/

# SNMP hostname
snmpget -v2c -c public localhost 1.3.6.1.2.1.1.5.0

# JetDirect info
printf '\x1b%%-12345X@PJL INFO ID\r\n\x1b%%-12345X' | nc localhost 9100

# Network discovery
avahi-browse -r _printer._tcp
```

### Complete Verification
```bash
# Check system identity
hostname                    # Should be: HPLJ-M609-001
ip link show | grep ether   # Should show: a0:b3:cc:d4:e5:f6

# Check services
sudo netstat -tuln | grep -E ':(80|161|9100)'

# Check Avahi
systemctl status avahi-daemon
avahi-browse -a -t

# Check logs
tail -f logs/*.out
```

## 🎨 Customization

### Change Printer Model
Edit `impersonate_hp_printer.sh`:
```bash
HP_MODEL="HP Color LaserJet Pro M454dn"
HP_SERIAL="JPBXY98765"
```

Edit `config_hp_printer.json`:
```json
{
  "globals": {
    "model": "HP Color LaserJet Pro M454dn",
    "serial": "JPBXY98765",
    ...
  }
}
```

### Adjust Supplies
Edit `config_hp_printer.json`:
```json
{
  "globals": {
    "toner_level": 25,        # Low toner warning
    "page_count": 125000,     # High usage
    "paper_tray1": 50,        # Low paper
    ...
  }
}
```

### Change Network Settings
Edit both scripts and config to match:
```bash
IP: 192.168.1.100
MAC: A0:B3:CC:D4:E5:F6
Hostname: HPLJ-M609-001
```

## 🛡️ Security & Compliance

### Authorized Use Only
⚠️ **WARNING**: This tool performs network impersonation and should only be used in:
- Authorized security testing environments
- Isolated lab networks
- Educational/training scenarios
- Research projects with proper authorization

### What Gets Changed
The system impersonation script modifies:
- Network interface MAC address
- System hostname
- `/etc/hosts` file
- Avahi service configurations
- Systemd services
- DHCP client identifier

### Backup & Restore
✅ All original settings are backed up to `/root/hp_printer_backup/`  
✅ Easy restoration with `sudo ./impersonate_hp_printer.sh stop`  
✅ No permanent changes - fully reversible  

## 🔧 Maintenance

### Check Status
```bash
sudo ./impersonate_hp_printer.sh status
```

### View Logs
```bash
# Service logs
ls -la logs/
tail -f logs/printer_web_server.py.out

# System logs
tail -f /var/log/syslog | grep -i printer
```

### Restart Services
```bash
# Stop services
sudo python3 server.py stop

# Start services
sudo python3 server.py start
```

### Update Configuration
```bash
# Edit config
nano config_hp_printer.json

# Apply changes (restart services)
sudo python3 server.py stop
sudo python3 server.py start
```

## 🎓 Use Cases

### Security Testing
- Test vulnerability scanners (Nmap, Nessus, etc.)
- Practice printer-specific reconnaissance
- Evaluate device fingerprinting tools
- Test network access control systems (Forescout, Cisco ISE)

### Development
- Develop printer management software
- Test SNMP monitoring tools
- Create print queue management systems
- Build printer discovery utilities

### Training & Education
- Teach network device enumeration
- Demonstrate SNMP protocol
- Show printer security vulnerabilities
- Practice incident response scenarios

### Research
- Study printer network protocols
- Analyze device fingerprinting techniques
- Test IoT security controls
- Evaluate network segmentation

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ubuntu 24.04 System                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  System Identity (impersonate_hp_printer.sh)               │
│  ├── MAC: A0:B3:CC:D4:E5:F6                               │
│  ├── Hostname: HPLJ-M609-001                              │
│  ├── Avahi: _printer._tcp, _pdl-datastream._tcp          │
│  └── DHCP: HP printer identity                           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Printer Simulator Services (server.py)                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  printer_web_server.py (Port 80)                    │  │
│  │  - HP Embedded Web Server interface                 │  │
│  │  - Status, supplies, network, device info pages     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  snmp_server.py (Port 161 UDP)                      │  │
│  │  - Standard MIB-II implementation                   │  │
│  │  - Printer MIB (RFC 3805)                           │  │
│  │  - HP Enterprise OIDs                               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  jetdirect_server.py (Port 9100 TCP)                │  │
│  │  - HP JetDirect protocol                            │  │
│  │  - PJL command support                              │  │
│  │  - Print job acceptance and logging                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    Network Interface
         (Appears as HP LaserJet printer)
```

## 🆘 Troubleshooting

### Quick Fixes
```bash
# Services won't start
sudo lsof -i :80,161,9100   # Check for conflicts
sudo python3 server.py stop # Force stop
sudo python3 server.py start

# MAC not changing
sudo nmcli device set eth0 managed no
sudo ./impersonate_hp_printer.sh start

# Can't access web interface
sudo ufw allow 80/tcp
curl -v http://localhost/

# Restore everything
sudo python3 server.py stop
sudo ./impersonate_hp_printer.sh stop
sudo reboot
```

### Get Help
1. Check `PRINTER_README.md` for detailed documentation
2. Check `IMPERSONATION_GUIDE.md` for system configuration
3. Check `QUICK_REFERENCE.md` for command reference
4. Review logs in `logs/` directory
5. Check system logs: `/var/log/syslog`

## 📚 Documentation

| File | Purpose |
|------|---------|
| `PRINTER_README.md` | Complete printer simulator documentation |
| `IMPERSONATION_GUIDE.md` | System impersonation detailed guide |
| `QUICK_REFERENCE.md` | Quick command reference card |
| `SUMMARY.md` | This overview document |

## ✅ Feature Checklist

- [x] MAC address spoofing with persistence
- [x] Hostname configuration
- [x] Avahi/Bonjour mDNS discovery
- [x] DHCP client identity
- [x] Full web interface (HP EWS style)
- [x] SNMP v1/v2c support
- [x] Standard MIB-II implementation
- [x] Printer MIB (RFC 3805)
- [x] HP Enterprise OIDs
- [x] JetDirect protocol (port 9100)
- [x] PJL command support
- [x] Print job logging
- [x] Toner level reporting
- [x] Page count tracking
- [x] Multiple configuration pages
- [x] Firewall configuration
- [x] Automatic backup/restore
- [x] One-command setup script
- [x] Comprehensive documentation

## 🎉 Summary

You now have a complete, production-ready HP printer simulator that:

1. **Looks like an HP printer** at the network level
2. **Acts like an HP printer** with full protocol support
3. **Responds like an HP printer** to all common queries
4. **Integrates seamlessly** with existing network tools
5. **Restores easily** to original configuration

Perfect for security testing, development, training, and research!

---

**Get Started**: `sudo ./setup_hp_printer.sh`  
**Documentation**: See `PRINTER_README.md`  
**Quick Help**: See `QUICK_REFERENCE.md`  

**Need support?** Check the documentation files or review logs in `logs/` directory.
