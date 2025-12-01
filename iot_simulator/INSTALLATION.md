# Installation Guide - IoT Simulator

Complete installation instructions for the IoT Simulator system including HP printer simulation.

## System Requirements

### Operating System
- **Primary**: Ubuntu 24.04 LTS (for full system impersonation)
- **Alternative**: Any Linux distribution (limited impersonation features)
- **Development**: macOS (simulator only, no system impersonation)
- **Minimum**: Python 3.7+

### Hardware
- **CPU**: 1 core minimum (2+ cores recommended)
- **RAM**: 512 MB minimum (1 GB+ recommended)
- **Disk**: 100 MB free space
- **Network**: Active network interface (ethernet or wireless)

## Quick Installation

### Ubuntu 24.04 (Recommended - Full Features)

```bash
# 1. Clone or download the repository
cd /path/to/scripts/iot_simulator

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Install system packages
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    avahi-daemon \
    avahi-utils \
    net-tools \
    iproute2 \
    netcat \
    snmp \
    snmp-mibs-downloader

# 4. Make scripts executable
chmod +x *.sh

# 5. Run the HP printer setup (includes system impersonation)
sudo ./setup_hp_printer.sh
```

### macOS (Simulator Only)

```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python 3
brew install python3

# 3. Install Python dependencies
pip3 install -r requirements.txt

# 4. Start simulator (no system impersonation on macOS)
python3 server.py start --config config_hp_printer.json

# Note: System impersonation (MAC spoofing, hostname change) 
# is not supported on macOS. Use Linux for full functionality.
```

### Other Linux Distributions

```bash
# Debian/Ubuntu-based
sudo apt-get install -y python3 python3-pip avahi-daemon net-tools iproute2

# RHEL/CentOS/Fedora-based
sudo yum install -y python3 python3-pip avahi net-tools iproute

# Arch-based
sudo pacman -S python python-pip avahi net-tools iproute2

# Install Python dependencies
pip3 install -r requirements.txt

# Make scripts executable
chmod +x *.sh
```

## Detailed Installation

### Step 1: Python Dependencies

The project requires minimal Python dependencies:

```bash
# Install Python packages
pip3 install -r requirements.txt

# Or manually install required package
pip3 install paramiko>=2.11.0
```

**What gets installed:**
- `paramiko` - SSH server functionality (only required if using SSH server)

**Everything else uses Python standard library:**
- No external dependencies needed for web, SNMP, or JetDirect servers!

### Step 2: System Packages (Ubuntu/Debian)

```bash
# Update package list
sudo apt-get update

# Core packages
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv

# Network tools
sudo apt-get install -y \
    net-tools \
    iproute2 \
    netcat \
    curl

# Avahi (mDNS/Bonjour)
sudo apt-get install -y \
    avahi-daemon \
    avahi-utils

# SNMP tools (optional - for testing)
sudo apt-get install -y \
    snmp \
    snmp-mibs-downloader \
    snmpd

# Firewall (if not already installed)
sudo apt-get install -y ufw
```

### Step 3: File Permissions

```bash
# Navigate to iot_simulator directory
cd /path/to/iot_simulator

# Make all shell scripts executable
chmod +x *.sh

# Verify permissions
ls -la *.sh
```

### Step 4: Configuration

```bash
# The configuration files are already included:
# - config.json (Siemens medical device)
# - config_hp_printer.json (HP printer)

# Verify configuration files exist
ls -la config*.json

# Optionally, validate JSON syntax
python3 -m json.tool config_hp_printer.json
```

### Step 5: Test Basic Functionality

```bash
# Test help
python3 server.py --help

# Test configuration loading (dry run)
python3 -c "import json; print(json.load(open('config_hp_printer.json'))['globals']['system_name'])"

# Should output: HP LaserJet Enterprise M609dn
```

## Optional Components

### Virtual Environment (Recommended)

Use a Python virtual environment to isolate dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies in venv
pip install -r requirements.txt

# Later, deactivate when done
deactivate
```

### SNMP MIBs (For Testing)

```bash
# Download SNMP MIBs (optional but useful for testing)
sudo apt-get install -y snmp-mibs-downloader

# Configure SNMP to use downloaded MIBs
sudo sed -i 's/mibs :/# mibs :/g' /etc/snmp/snmp.conf

# Test SNMP with MIB names
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1
```

### Development Tools (Optional)

```bash
# Install development dependencies
pip3 install pytest pytest-cov pylint black flake8

# Or uncomment dev dependencies in requirements.txt and:
pip3 install -r requirements.txt
```

## Privilege Requirements

### Binding to Low Ports (< 1024)

The simulator needs to bind to privileged ports:
- Port 80 (HTTP)
- Port 161 (SNMP)

**Option 1: Run as root** (simplest but less secure)
```bash
sudo python3 server.py start --config config_hp_printer.json
```

**Option 2: Grant Python capability** (recommended)
```bash
# Grant Python the capability to bind to low ports
sudo setcap 'cap_net_bind_service=+ep' $(which python3)

# Now you can run without sudo
python3 server.py start --config config_hp_printer.json
```

**Option 3: Use alternative ports** (for testing)
Edit `config_hp_printer.json`:
```json
{
  "servers": [
    {"path": "servers/printer_web_server.py", "port": 8080},
    {"path": "servers/snmp_server.py", "port": 1161},
    {"path": "servers/jetdirect_server.py", "port": 9100}
  ]
}
```

### System Impersonation Privileges

The `impersonate_hp_printer.sh` script requires root:

```bash
# Must run with sudo
sudo ./impersonate_hp_printer.sh start

# Changes MAC address, hostname, network config
# All changes are backed up to /root/hp_printer_backup/
```

## Verification

### Test Installation

Run the test suite to verify everything is working:

```bash
# Make test script executable
chmod +x test_printer_simulator.sh

# Run comprehensive tests
sudo ./test_printer_simulator.sh
```

### Manual Verification

```bash
# 1. Check Python version
python3 --version
# Should be 3.7 or higher

# 2. Check Python dependencies
pip3 show paramiko

# 3. Check system tools
which ip
which avahi-browse
which snmpget

# 4. Check files exist
ls -la config_hp_printer.json
ls -la servers/printer_web_server.py
ls -la servers/snmp_server.py
ls -la servers/jetdirect_server.py

# 5. Validate configurations
python3 -m json.tool config_hp_printer.json > /dev/null && echo "JSON valid"
```

## Troubleshooting Installation

### Python Not Found
```bash
# Install Python 3
sudo apt-get install python3 python3-pip

# Or check if python3 is installed
which python3
```

### pip Not Found
```bash
# Install pip
sudo apt-get install python3-pip

# Or use alternative
python3 -m ensurepip --upgrade
```

### Permission Denied Errors
```bash
# Use sudo for system changes
sudo ./impersonate_hp_printer.sh start
sudo python3 server.py start --config config_hp_printer.json

# Or grant capabilities (see above)
```

### Package Installation Fails
```bash
# Update package lists
sudo apt-get update

# Fix broken dependencies
sudo apt-get install -f

# Try installing packages individually
sudo apt-get install python3
sudo apt-get install avahi-daemon
```

### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :80
sudo lsof -i :161

# Stop conflicting service
sudo systemctl stop apache2  # or nginx, etc.

# Or use alternative ports (see above)
```

### Avahi Not Starting
```bash
# Check Avahi status
systemctl status avahi-daemon

# Start Avahi
sudo systemctl start avahi-daemon

# Enable on boot
sudo systemctl enable avahi-daemon
```

## Post-Installation

### Firewall Configuration

```bash
# If using UFW
sudo ufw allow 80/tcp
sudo ufw allow 161/udp
sudo ufw allow 9100/tcp
sudo ufw status

# If using firewalld
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=161/udp
sudo firewall-cmd --permanent --add-port=9100/tcp
sudo firewall-cmd --reload
```

### Enable Services on Boot (Optional)

```bash
# The simulator doesn't auto-start by default
# To enable, create a systemd service:

sudo tee /etc/systemd/system/iot-simulator.service > /dev/null <<EOF
[Unit]
Description=IoT Device Simulator
After=network.target

[Service]
Type=forking
WorkingDirectory=/path/to/iot_simulator
ExecStart=/usr/bin/python3 /path/to/iot_simulator/server.py start --config config_hp_printer.json
ExecStop=/usr/bin/python3 /path/to/iot_simulator/server.py stop
User=root
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable iot-simulator.service
sudo systemctl start iot-simulator.service
```

## Quick Start After Installation

```bash
# HP Printer simulation with full system impersonation
sudo ./setup_hp_printer.sh

# Or manual start
sudo ./impersonate_hp_printer.sh start
sudo python3 server.py start --config config_hp_printer.json

# Verify it's working
sudo python3 server.py status
curl http://localhost/
```

## Uninstallation

```bash
# Stop services
sudo python3 server.py stop

# Restore system configuration
sudo ./impersonate_hp_printer.sh stop

# Remove Python packages
pip3 uninstall -y paramiko

# Remove system packages (optional)
sudo apt-get remove --purge avahi-daemon

# Remove files
cd ..
rm -rf iot_simulator
```

## Getting Help

- Check logs: `tail -f logs/*.out logs/*.err`
- Run tests: `sudo ./test_printer_simulator.sh`
- Check status: `sudo python3 server.py status`
- View documentation: `cat PRINTER_README.md`
- System status: `sudo ./impersonate_hp_printer.sh status`

## Summary

**Minimum Installation:**
```bash
pip3 install -r requirements.txt
python3 server.py start --config config_hp_printer.json
```

**Full Installation (Ubuntu):**
```bash
sudo apt-get update && sudo apt-get install -y python3-pip avahi-daemon
pip3 install -r requirements.txt
chmod +x *.sh
sudo ./setup_hp_printer.sh
```

That's it! You're ready to simulate network devices.
