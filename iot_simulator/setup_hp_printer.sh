#!/bin/bash
###############################################################################
# Quick Setup Script for HP Printer Simulator
# 
# This script performs a complete setup of the HP printer simulation
# including system impersonation and service startup.
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

print_header() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║           HP LaserJet Printer Simulator - Quick Setup             ║
║                                                                   ║
║     Complete system configuration and service deployment          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

install_dependencies() {
    log_info "Installing required dependencies..."
    
    apt-get update -qq
    apt-get install -y -qq \
        python3 \
        python3-pip \
        avahi-daemon \
        avahi-utils \
        net-tools \
        iproute2 \
        netcat \
        curl \
        snmp \
        snmp-mibs-downloader 2>/dev/null || true
    
    log_info "Dependencies installed successfully"
}

setup_config() {
    log_info "Setting up printer configuration..."
    
    if [[ -f "$SCRIPT_DIR/config_hp_printer.json" ]]; then
        # No need to copy - we'll use --config parameter
        log_info "Using config_hp_printer.json directly"
    else
        log_error "config_hp_printer.json not found!"
        exit 1
    fi
}

configure_system() {
    log_info "Configuring system to impersonate HP printer..."
    
    if [[ -x "$SCRIPT_DIR/impersonate_hp_printer.sh" ]]; then
        "$SCRIPT_DIR/impersonate_hp_printer.sh" start
    else
        log_error "impersonate_hp_printer.sh not found or not executable!"
        exit 1
    fi
}

start_services() {
    log_info "Starting printer simulator services..."
    
    if [[ -f "$SCRIPT_DIR/server.py" ]]; then
        cd "$SCRIPT_DIR"
        python3 server.py start --config config_hp_printer.json
        sleep 3
        log_info "Simulator services started"
    else
        log_error "server.py not found!"
        exit 1
    fi
}

verify_setup() {
    log_info "Verifying setup..."
    echo ""
    
    local all_ok=true
    
    # Check hostname
    if [[ "$(hostname)" == "HPLJ-M609-001" ]]; then
        echo -e "  ${GREEN}✓${NC} Hostname: $(hostname)"
    else
        echo -e "  ${RED}✗${NC} Hostname: $(hostname) (expected: HPLJ-M609-001)"
        all_ok=false
    fi
    
    # Check MAC address (find primary interface)
    local interface=$(ip route | grep default | awk '{print $5}' | head -n1)
    if [[ -n "$interface" ]]; then
        local mac=$(ip link show "$interface" | grep "link/ether" | awk '{print $2}')
        if [[ "$mac" == "a0:b3:cc:d4:e5:f6" ]]; then
            echo -e "  ${GREEN}✓${NC} MAC Address: $mac"
        else
            echo -e "  ${YELLOW}⚠${NC} MAC Address: $mac (expected: a0:b3:cc:d4:e5:f6)"
            all_ok=false
        fi
    fi
    
    # Check services
    local checks=(
        "80:HTTP Web Interface"
        "161:SNMP"
        "9100:JetDirect"
    )
    
    for check in "${checks[@]}"; do
        IFS=':' read -r port name <<< "$check"
        if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
            echo -e "  ${GREEN}✓${NC} Port $port ($name) is listening"
        else
            echo -e "  ${RED}✗${NC} Port $port ($name) is not listening"
            all_ok=false
        fi
    done
    
    # Check Avahi
    if systemctl is-active --quiet avahi-daemon; then
        echo -e "  ${GREEN}✓${NC} Avahi daemon is running"
    else
        echo -e "  ${RED}✗${NC} Avahi daemon is not running"
        all_ok=false
    fi
    
    echo ""
    
    if $all_ok; then
        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "Setup completed successfully! 🎉"
        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_warn "Setup completed with warnings. Check the items marked above."
        log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
}

show_access_info() {
    local ip=$(ip -4 addr show $(ip route | grep default | awk '{print $5}' | head -n1) 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1 | head -n1)
    
    echo ""
    log_info "Access Information:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${GREEN}Web Interface:${NC}"
    echo "    http://localhost/"
    if [[ -n "$ip" ]]; then
        echo "    http://$ip/"
    fi
    echo ""
    echo -e "  ${GREEN}Test Commands:${NC}"
    echo "    # SNMP Query"
    if [[ -n "$ip" ]]; then
        echo "    snmpget -v2c -c public $ip 1.3.6.1.2.1.1.5.0"
    else
        echo "    snmpget -v2c -c public localhost 1.3.6.1.2.1.1.5.0"
    fi
    echo ""
    echo "    # JetDirect Test"
    if [[ -n "$ip" ]]; then
        echo "    printf '\\x1b%%-12345X@PJL INFO ID\\r\\n\\x1b%%-12345X' | nc $ip 9100"
    else
        echo "    printf '\\x1b%%-12345X@PJL INFO ID\\r\\n\\x1b%%-12345X' | nc localhost 9100"
    fi
    echo ""
    echo "    # Discover via Avahi"
    echo "    avahi-browse -r _printer._tcp"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "Logs are stored in: $SCRIPT_DIR/logs/"
    log_info "To stop: sudo python3 $SCRIPT_DIR/server.py stop"
    log_info "To restore system: sudo $SCRIPT_DIR/impersonate_hp_printer.sh stop"
    echo ""
}

main() {
    print_header
    check_root
    
    log_info "Starting HP Printer Simulator setup..."
    echo ""
    
    install_dependencies
    setup_config
    configure_system
    start_services
    
    echo ""
    verify_setup
    show_access_info
}

main "$@"
