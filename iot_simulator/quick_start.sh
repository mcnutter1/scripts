#!/bin/bash
# Quick Start - HP Printer Simulator with Windows Discovery
# This script helps you get the printer simulator running quickly

set -e

echo "========================================="
echo "HP Printer Simulator - Quick Start"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (sudo)${NC}"
    echo "Reason: Ports 80 and 161 require root privileges"
    echo ""
    echo "Run with: sudo $0"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}

echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"
echo "================================"

# Check Python
if command -v python3 > /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python3 installed: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python3 not found"
    echo "Install with: sudo apt-get install python3"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "config_hp_printer.json" ]; then
    echo -e "${YELLOW}⚠${NC} Not in iot_simulator directory"
    if [ -d "iot_simulator" ]; then
        cd iot_simulator
        echo "Changed to iot_simulator directory"
    else
        echo -e "${RED}ERROR: Cannot find iot_simulator directory${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}Step 2: Checking Firewall${NC}"
echo "========================="

# Check if ufw is installed
if command -v ufw > /dev/null; then
    echo "Configuring firewall rules..."
    
    ufw allow 80/tcp > /dev/null 2>&1 || true
    ufw allow 161/udp > /dev/null 2>&1 || true
    ufw allow 3702/udp > /dev/null 2>&1 || true
    ufw allow 5355/udp > /dev/null 2>&1 || true
    ufw allow 9100/tcp > /dev/null 2>&1 || true
    
    echo -e "${GREEN}✓${NC} Firewall rules configured"
    echo "  - TCP 80 (Web)"
    echo "  - UDP 161 (SNMP)"
    echo "  - UDP 3702 (WS-Discovery)"
    echo "  - UDP 5355 (LLMNR)"
    echo "  - TCP 9100 (JetDirect)"
else
    echo -e "${YELLOW}⚠${NC} UFW not installed - firewall rules not configured"
    echo "You may need to manually configure your firewall"
fi

echo ""
echo -e "${BLUE}Step 3: Creating Directories${NC}"
echo "============================="

# Create directories
mkdir -p print_jobs logs
chown -R $ACTUAL_USER:$ACTUAL_USER print_jobs logs

echo -e "${GREEN}✓${NC} Created print_jobs/ directory"
echo -e "${GREEN}✓${NC} Created logs/ directory"

echo ""
echo -e "${BLUE}Step 4: Validating Configuration${NC}"
echo "================================="

if [ -f "config_hp_printer.json" ]; then
    echo -e "${GREEN}✓${NC} config_hp_printer.json found"
    
    # Extract key values
    IP=$(grep -o '"ip": *"[^"]*"' config_hp_printer.json | head -1 | cut -d'"' -f4)
    HOSTNAME=$(grep -o '"hostname": *"[^"]*"' config_hp_printer.json | head -1 | cut -d'"' -f4)
    MODEL=$(grep -o '"model": *"[^"]*"' config_hp_printer.json | head -1 | cut -d'"' -f4)
    
    echo "  IP Address: $IP"
    echo "  Hostname: $HOSTNAME"
    echo "  Model: $MODEL"
else
    echo -e "${RED}✗${NC} config_hp_printer.json not found"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 5: Starting Printer Simulator${NC}"
echo "==================================="

# Check if already running
if python3 server.py --config config_hp_printer.json status 2>/dev/null | grep -q "running"; then
    echo -e "${YELLOW}⚠${NC} Simulator is already running"
    echo ""
    read -p "Do you want to restart it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping current instance..."
        python3 server.py --config config_hp_printer.json stop
        sleep 2
    else
        echo "Keeping current instance running"
        exit 0
    fi
fi

# Start the simulator
echo "Starting all services..."
python3 server.py --config config_hp_printer.json start

sleep 3

echo ""
echo -e "${BLUE}Step 6: Verifying Services${NC}"
echo "==========================="

# Check if services are running
SERVICES_OK=true

check_port() {
    PORT=$1
    SERVICE=$2
    if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
        echo -e "${GREEN}✓${NC} $SERVICE (port $PORT) - Running"
    else
        echo -e "${RED}✗${NC} $SERVICE (port $PORT) - NOT running"
        SERVICES_OK=false
    fi
}

check_port 80 "Web Interface"
check_port 161 "SNMP Server"
check_port 3702 "WS-Discovery"
check_port 5355 "LLMNR"
check_port 9100 "JetDirect"

echo ""

if [ "$SERVICES_OK" = true ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}✓ All services started successfully!${NC}"
    echo -e "${GREEN}=========================================${NC}"
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}⚠ Some services failed to start${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo "Check logs in: logs/"
    exit 1
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Printer Simulator Ready!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Printer Information:"
echo "  Model: $MODEL"
echo "  IP Address: $IP"
echo "  Hostname: $HOSTNAME"
echo ""
echo "Access Methods:"
echo "  Web Interface: http://$IP/"
echo "  SNMP: snmpget -v2c -c public $IP ..."
echo "  Print: Send jobs to $IP:9100"
echo ""
echo "Windows Discovery:"
echo "  1. Open Settings > Devices > Printers & scanners"
echo "  2. Click 'Add a printer or scanner'"
echo "  3. Wait for '$MODEL' to appear"
echo "  4. Click it and follow the wizard"
echo ""
echo "Useful Commands:"
echo "  Status:    sudo python3 server.py --config config_hp_printer.json status"
echo "  Stop:      sudo python3 server.py --config config_hp_printer.json stop"
echo "  Restart:   sudo python3 server.py --config config_hp_printer.json restart"
echo "  Logs:      tail -f logs/*.log"
echo "  Print Log: cat print_jobs/print_log.json | python3 -m json.tool"
echo ""
echo "Testing:"
echo "  Run test script: ./test_windows_discovery.sh"
echo ""
echo "Documentation:"
echo "  Main docs:     PRINTER_README.md"
echo "  Windows setup: WINDOWS_DISCOVERY.md"
echo "  Architecture:  ARCHITECTURE.md"
echo ""
echo -e "${GREEN}Happy testing!${NC}"
echo ""
