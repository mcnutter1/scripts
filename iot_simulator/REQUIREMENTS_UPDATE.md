# Requirements and Dependencies Update - Summary

## Overview

Updated the `requirements.txt` file and created comprehensive installation documentation for the IoT Simulator system.

## Changes Made

### 1. Updated requirements.txt

**File**: `/iot_simulator/requirements.txt`

**What was added:**
```txt
# Primary dependency
paramiko>=2.11.0  # For SSH server functionality

# All other components use Python standard library only!
# - http.server, socket, json, argparse, threading, etc.
```

**Key points:**
- ✅ Only **ONE** external dependency: `paramiko` (for SSH server)
- ✅ All printer simulator components use standard library
- ✅ Comprehensive documentation with:
  - System-level dependencies (apt packages)
  - Optional dependencies (SNMP, development tools)
  - Installation instructions
  - Platform-specific notes

### 2. Created INSTALLATION.md

**File**: `/iot_simulator/INSTALLATION.md`

Comprehensive installation guide covering:
- System requirements
- Quick installation (Ubuntu, macOS, other Linux)
- Detailed step-by-step installation
- Optional components (virtual env, SNMP MIBs, dev tools)
- Privilege requirements (port binding, system impersonation)
- Verification steps
- Troubleshooting common issues
- Post-installation configuration
- Firewall setup
- Uninstallation

### 3. Created check_installation.sh

**File**: `/iot_simulator/check_installation.sh`

Automated installation checker that verifies:
- ✅ Python 3.7+ installed
- ✅ pip3 available
- ✅ Python packages (paramiko, standard library)
- ✅ System tools (ip, avahi-browse, snmpget, nc, curl)
- ✅ Avahi daemon status
- ✅ Project files present
- ✅ Configuration files valid JSON
- ✅ Permissions for port binding
- ✅ Port availability (80, 161, 9100)
- ✅ Firewall configuration

**Usage:**
```bash
chmod +x check_installation.sh
./check_installation.sh
```

## Dependency Analysis

### Python Standard Library (No Installation Needed)

All these are built into Python:
- `http.server` - Web server
- `socket` - Network communication
- `json` - Configuration parsing
- `argparse` - Command-line parsing
- `threading` - Concurrent connections
- `logging` - Logging system
- `ipaddress` - IP validation
- `datetime` - Timestamps
- `struct` - Binary data
- `subprocess` - Process management
- `signal` - Process control
- `os`, `sys` - System operations

### Third-Party Dependencies

Only **1** external package required:
- `paramiko>=2.11.0` - SSH server implementation

### System Packages (via apt/yum)

**Required for full functionality:**
- `python3` - Python interpreter
- `python3-pip` - Package installer
- `avahi-daemon` - mDNS/Bonjour discovery
- `net-tools` - Network utilities
- `iproute2` - IP routing utilities

**Optional but recommended:**
- `avahi-utils` - Avahi tools (avahi-browse)
- `snmp` - SNMP command-line tools
- `snmp-mibs-downloader` - SNMP MIB files
- `netcat` - Network testing
- `curl` - HTTP testing

## Installation Commands

### Minimal Installation
```bash
# Only Python dependencies
pip3 install -r requirements.txt
```

### Complete Installation (Ubuntu)
```bash
# System packages
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip \
    avahi-daemon avahi-utils \
    net-tools iproute2 \
    netcat curl snmp

# Python packages
pip3 install -r requirements.txt

# Make scripts executable
chmod +x *.sh
```

### Quick Check
```bash
# Run installation checker
./check_installation.sh
```

## Platform Support

### Ubuntu 24.04 LTS ✅ (Fully Supported)
- All features work
- System impersonation supported
- MAC spoofing supported
- Hostname changes supported

### Other Linux ⚠️ (Mostly Supported)
- Simulator works fully
- System impersonation may vary by distro
- Some tools may have different names

### macOS ⚠️ (Simulator Only)
- Simulator components work
- System impersonation NOT supported
- No MAC spoofing capability
- Use for development/testing only

### Windows ❌ (Not Supported)
- System impersonation scripts are Linux-specific
- Simulator might work under WSL2

## Files Updated/Created

1. ✅ `requirements.txt` - Updated with dependencies and documentation
2. ✅ `INSTALLATION.md` - Comprehensive installation guide
3. ✅ `check_installation.sh` - Automated installation checker

## Verification

### Before Starting

Run the installation checker:
```bash
./check_installation.sh
```

Expected output:
```
✓ Python 3 installed: 3.11.x
✓ Python version is 3.7 or higher
✓ pip3 installed: 23.x.x
✓ paramiko installed: 2.11.x
✓ All standard library modules available
✓ ip command available
✓ Avahi daemon installed
✓ Avahi daemon is running
✓ All project files present
✓ Configurations are valid JSON
...

Installation looks good!
```

### Manual Verification

```bash
# Check Python
python3 --version

# Check pip
pip3 --version

# Check paramiko
python3 -c "import paramiko; print(paramiko.__version__)"

# Check system tools
which ip avahi-browse snmpget

# Validate configs
python3 -m json.tool config_hp_printer.json
```

## Common Issues and Solutions

### Issue: paramiko not installed
```bash
pip3 install paramiko
```

### Issue: Permission denied on ports < 1024
```bash
# Option 1: Run with sudo
sudo python3 server.py start --config config_hp_printer.json

# Option 2: Grant capability
sudo setcap 'cap_net_bind_service=+ep' $(which python3)
```

### Issue: Avahi not installed
```bash
sudo apt-get install avahi-daemon avahi-utils
sudo systemctl start avahi-daemon
```

### Issue: Port already in use
```bash
# Check what's using it
sudo lsof -i :80

# Stop conflicting service
sudo systemctl stop apache2
```

## Integration with Existing Documentation

The new installation documentation complements existing docs:

- `PRINTER_README.md` - Printer simulator features and usage
- `IMPERSONATION_GUIDE.md` - System impersonation details
- `QUICK_REFERENCE.md` - Command reference
- `SERVER_USAGE.md` - server.py usage
- **`INSTALLATION.md`** - Installation and setup (NEW)

## Testing the Installation

### Quick Test
```bash
# 1. Check installation
./check_installation.sh

# 2. Start simulator
sudo python3 server.py start --config config_hp_printer.json

# 3. Check status
sudo python3 server.py status

# 4. Test web interface
curl http://localhost/

# 5. Stop
sudo python3 server.py stop
```

### Full Test
```bash
# Run comprehensive test suite
sudo ./test_printer_simulator.sh
```

## Best Practices

### Use Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Check Before Running
```bash
./check_installation.sh
```

### Run with Appropriate Privileges
```bash
# For privileged ports
sudo python3 server.py start --config config_hp_printer.json

# Or grant capability once
sudo setcap 'cap_net_bind_service=+ep' $(which python3)
python3 server.py start --config config_hp_printer.json
```

### Keep Dependencies Updated
```bash
pip3 install --upgrade paramiko
```

## Summary

✅ **Minimal dependencies** - Only 1 external Python package  
✅ **Standard library focused** - Most code uses built-in modules  
✅ **Well documented** - Comprehensive installation guide  
✅ **Automated checking** - Installation verification script  
✅ **Platform support** - Clear notes for Ubuntu, Linux, macOS  
✅ **Easy installation** - Simple pip install for Python deps  
✅ **Troubleshooting** - Common issues and solutions documented  

The IoT Simulator system is now fully documented with clear installation instructions and dependency requirements!
