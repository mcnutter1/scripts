#!/bin/bash
###############################################################################
# Installation Check Script
# Verifies that all dependencies and requirements are properly installed
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

log_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║           IoT Simulator - Installation Check                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

check_python() {
    log_info "Checking Python installation..."
    
    if command -v python3 &>/dev/null; then
        local version=$(python3 --version | awk '{print $2}')
        log_pass "Python 3 installed: $version"
        
        # Check if version is 3.7 or higher
        local major=$(echo "$version" | cut -d. -f1)
        local minor=$(echo "$version" | cut -d. -f2)
        if [[ $major -ge 3 && $minor -ge 7 ]]; then
            log_pass "Python version is 3.7 or higher"
        else
            log_warn "Python version is lower than 3.7 (some features may not work)"
        fi
    else
        log_fail "Python 3 not found (required)"
    fi
}

check_pip() {
    log_info "Checking pip installation..."
    
    if command -v pip3 &>/dev/null; then
        local version=$(pip3 --version | awk '{print $2}')
        log_pass "pip3 installed: $version"
    else
        log_fail "pip3 not found (required for installing dependencies)"
    fi
}

check_python_packages() {
    log_info "Checking Python packages..."
    
    # Check paramiko (only required for SSH server)
    if python3 -c "import paramiko" 2>/dev/null; then
        local version=$(python3 -c "import paramiko; print(paramiko.__version__)" 2>/dev/null)
        log_pass "paramiko installed: $version"
    else
        log_warn "paramiko not installed (only needed for SSH server)"
    fi
    
    # Check standard library modules
    local modules=("socket" "http.server" "json" "argparse" "threading" "logging")
    local all_ok=true
    for module in "${modules[@]}"; do
        if python3 -c "import ${module//./ }" 2>/dev/null; then
            : # Module exists, don't print for brevity
        else
            log_fail "Standard library module '$module' not available"
            all_ok=false
        fi
    done
    
    if $all_ok; then
        log_pass "All standard library modules available"
    fi
}

check_system_tools() {
    log_info "Checking system tools..."
    
    # Required tools
    local required=("ip:iproute2")
    for tool_pkg in "${required[@]}"; do
        IFS=':' read -r tool pkg <<< "$tool_pkg"
        if command -v "$tool" &>/dev/null; then
            log_pass "$tool command available"
        else
            log_fail "$tool command not found (install package: $pkg)"
        fi
    done
    
    # Optional but recommended tools
    local optional=(
        "avahi-browse:avahi-utils"
        "snmpget:snmp"
        "nc:netcat"
        "curl:curl"
    )
    
    for tool_pkg in "${optional[@]}"; do
        IFS=':' read -r tool pkg <<< "$tool_pkg"
        if command -v "$tool" &>/dev/null; then
            log_pass "$tool command available (optional)"
        else
            log_warn "$tool command not found (optional, install: $pkg)"
        fi
    done
}

check_avahi() {
    log_info "Checking Avahi daemon..."
    
    if command -v avahi-daemon &>/dev/null; then
        log_pass "Avahi daemon installed"
        
        if systemctl is-active --quiet avahi-daemon 2>/dev/null; then
            log_pass "Avahi daemon is running"
        elif service avahi-daemon status &>/dev/null; then
            log_pass "Avahi daemon is running (SysV)"
        else
            log_warn "Avahi daemon installed but not running"
        fi
    else
        log_warn "Avahi daemon not installed (needed for mDNS discovery)"
    fi
}

check_files() {
    log_info "Checking project files..."
    
    # Required files
    local required=(
        "server.py"
        "core_logger.py"
        "config.json"
        "config_hp_printer.json"
        "requirements.txt"
        "servers/shared.py"
        "servers/printer_web_server.py"
        "servers/snmp_server.py"
        "servers/jetdirect_server.py"
    )
    
    for file in "${required[@]}"; do
        if [[ -f "$file" ]]; then
            log_pass "File exists: $file"
        else
            log_fail "File missing: $file"
        fi
    done
    
    # Optional scripts
    local optional=(
        "impersonate_hp_printer.sh"
        "setup_hp_printer.sh"
        "test_printer_simulator.sh"
    )
    
    for file in "${optional[@]}"; do
        if [[ -f "$file" ]]; then
            log_pass "Script exists: $file"
            if [[ -x "$file" ]]; then
                log_pass "  └─ Script is executable"
            else
                log_warn "  └─ Script is not executable (run: chmod +x $file)"
            fi
        else
            log_warn "Script missing: $file (optional)"
        fi
    done
}

check_config_files() {
    log_info "Checking configuration files..."
    
    for config in config.json config_hp_printer.json; do
        if [[ -f "$config" ]]; then
            if python3 -m json.tool "$config" > /dev/null 2>&1; then
                log_pass "$config is valid JSON"
            else
                log_fail "$config is invalid JSON"
            fi
        fi
    done
}

check_permissions() {
    log_info "Checking permissions..."
    
    if [[ $EUID -eq 0 ]]; then
        log_pass "Running as root (can bind to privileged ports)"
    else
        log_warn "Not running as root (may need sudo for ports < 1024)"
        
        # Check if Python has capability
        if command -v getcap &>/dev/null; then
            local python_path=$(which python3)
            if getcap "$python_path" 2>/dev/null | grep -q "cap_net_bind_service"; then
                log_pass "Python has cap_net_bind_service capability"
            else
                log_info "To bind to low ports without sudo, run:"
                log_info "  sudo setcap 'cap_net_bind_service=+ep' $(which python3)"
            fi
        fi
    fi
}

check_ports() {
    log_info "Checking if required ports are available..."
    
    local ports=(80 161 9100)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
            log_warn "Port $port is already in use (may conflict)"
        else
            log_pass "Port $port is available"
        fi
    done
}

check_firewall() {
    log_info "Checking firewall configuration..."
    
    if command -v ufw &>/dev/null; then
        if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
            log_warn "UFW firewall is active (may need to allow ports 80, 161, 9100)"
            log_info "  To allow: sudo ufw allow 80/tcp && sudo ufw allow 161/udp && sudo ufw allow 9100/tcp"
        else
            log_pass "UFW firewall is inactive"
        fi
    elif command -v firewall-cmd &>/dev/null; then
        if sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
            log_warn "firewalld is active (may need to allow ports)"
        else
            log_pass "firewalld is inactive"
        fi
    else
        log_info "No common firewall detected"
    fi
}

show_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Installation Check Summary${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASS"
    echo -e "  ${RED}Failed:${NC}   $FAIL"
    echo -e "  ${YELLOW}Warnings:${NC} $WARN"
    echo ""
    
    if [[ $FAIL -eq 0 ]]; then
        echo -e "${GREEN}✓ Installation looks good!${NC}"
        echo ""
        echo "You can now start the simulator:"
        echo "  sudo python3 server.py start --config config_hp_printer.json"
        echo ""
    elif [[ $FAIL -le 3 ]]; then
        echo -e "${YELLOW}⚠ Minor issues detected${NC}"
        echo ""
        echo "Installation should work, but you may need to:"
        echo "  1. Install missing optional packages"
        echo "  2. Fix file permissions"
        echo "  3. Configure firewall rules"
        echo ""
    else
        echo -e "${RED}✗ Installation has problems${NC}"
        echo ""
        echo "Please install missing dependencies:"
        echo "  pip3 install -r requirements.txt"
        echo "  sudo apt-get install python3-pip avahi-daemon"
        echo ""
        echo "See INSTALLATION.md for detailed instructions"
        echo ""
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

show_next_steps() {
    if [[ $FAIL -eq 0 ]]; then
        echo -e "${BLUE}Next Steps:${NC}"
        echo ""
        echo "1. Start the HP printer simulator:"
        echo "   sudo ./setup_hp_printer.sh"
        echo ""
        echo "2. Or start manually:"
        echo "   sudo ./impersonate_hp_printer.sh start"
        echo "   sudo python3 server.py start --config config_hp_printer.json"
        echo ""
        echo "3. Test the installation:"
        echo "   sudo ./test_printer_simulator.sh"
        echo ""
        echo "4. Access the web interface:"
        echo "   http://localhost/"
        echo ""
    fi
}

main() {
    print_header
    
    check_python
    echo ""
    
    check_pip
    echo ""
    
    check_python_packages
    echo ""
    
    check_system_tools
    echo ""
    
    check_avahi
    echo ""
    
    check_files
    echo ""
    
    check_config_files
    echo ""
    
    check_permissions
    echo ""
    
    check_ports
    echo ""
    
    check_firewall
    echo ""
    
    show_summary
    show_next_steps
}

main "$@"
