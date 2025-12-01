#!/bin/bash
###############################################################################
# HP Printer Simulator - System Test Script
# 
# Comprehensive testing script to verify all components are working correctly
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         HP Printer Simulator - System Test Suite                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

test_hostname() {
    log_test "Testing hostname configuration..."
    local hostname=$(hostname)
    if [[ "$hostname" == "HPLJ-M609-001" ]]; then
        log_pass "Hostname is correctly set to: $hostname"
    else
        log_fail "Hostname is: $hostname (expected: HPLJ-M609-001)"
    fi
}

test_mac_address() {
    log_test "Testing MAC address configuration..."
    local interface=$(ip route | grep default | awk '{print $5}' | head -n1)
    if [[ -z "$interface" ]]; then
        log_skip "Could not detect network interface"
        return
    fi
    
    local mac=$(ip link show "$interface" | grep "link/ether" | awk '{print $2}')
    if [[ "$mac" == "a0:b3:cc:d4:e5:f6" ]]; then
        log_pass "MAC address is correctly set to: $mac"
    else
        log_fail "MAC address is: $mac (expected: a0:b3:cc:d4:e5:f6)"
    fi
}

test_web_server() {
    log_test "Testing web server (port 80)..."
    if curl -s -f http://localhost/ > /dev/null; then
        log_pass "Web server is responding on port 80"
        
        # Test specific pages
        if curl -s http://localhost/ | grep -q "HP LaserJet"; then
            log_pass "Web content contains HP LaserJet branding"
        fi
        
        if curl -s http://localhost/supplies | grep -q "Toner"; then
            log_pass "Supplies page is accessible"
        fi
        
        if curl -s http://localhost/network | grep -q "Network"; then
            log_pass "Network page is accessible"
        fi
    else
        log_fail "Web server is not responding on port 80"
    fi
}

test_snmp() {
    log_test "Testing SNMP server (port 161)..."
    
    if ! command -v snmpget &>/dev/null; then
        log_skip "snmpget command not available (install snmp package)"
        return
    fi
    
    # Test system description
    local result=$(snmpget -v2c -c public -t 2 localhost 1.3.6.1.2.1.1.5.0 2>/dev/null)
    if [[ $? -eq 0 && -n "$result" ]]; then
        log_pass "SNMP server is responding"
        
        # Test printer-specific OIDs
        if snmpget -v2c -c public -t 2 localhost 1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0 2>/dev/null | grep -q "HP"; then
            log_pass "SNMP printer model OID is responding"
        fi
    else
        log_fail "SNMP server is not responding on port 161"
    fi
}

test_jetdirect() {
    log_test "Testing JetDirect server (port 9100)..."
    
    if ! command -v nc &>/dev/null; then
        log_skip "netcat (nc) command not available"
        return
    fi
    
    # Test if port is listening
    if timeout 2 bash -c "echo > /dev/tcp/localhost/9100" 2>/dev/null; then
        log_pass "JetDirect port 9100 is listening"
        
        # Test PJL command
        local response=$(printf '\x1b%%-12345X@PJL INFO ID\r\n\x1b%%-12345X' | timeout 2 nc localhost 9100 2>/dev/null)
        if [[ -n "$response" && "$response" =~ "HP" ]]; then
            log_pass "JetDirect PJL commands are working"
        fi
    else
        log_fail "JetDirect port 9100 is not accessible"
    fi
}

test_avahi() {
    log_test "Testing Avahi/mDNS discovery..."
    
    if ! command -v avahi-browse &>/dev/null; then
        log_skip "avahi-browse command not available"
        return
    fi
    
    if systemctl is-active --quiet avahi-daemon; then
        log_pass "Avahi daemon is running"
        
        # Check if printer service is advertised
        local services=$(timeout 3 avahi-browse -p -t _printer._tcp 2>/dev/null | grep "^=" || true)
        if [[ -n "$services" ]]; then
            log_pass "Printer service is being advertised via mDNS"
        else
            log_fail "Printer service not found in mDNS"
        fi
    else
        log_fail "Avahi daemon is not running"
    fi
}

test_ports() {
    log_test "Testing open ports..."
    
    local ports=(80 161 9100)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
            log_pass "Port $port is listening"
        else
            log_fail "Port $port is not listening"
        fi
    done
}

test_logs() {
    log_test "Testing log files..."
    
    local log_files=(
        "logs/printer_web_server.py.out"
        "logs/snmp_server.py.out"
        "logs/jetdirect_server.py.out"
    )
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            log_pass "Log file exists: $log_file"
        else
            log_fail "Log file missing: $log_file"
        fi
    done
}

test_config() {
    log_test "Testing configuration files..."
    
    if [[ -f "config.json" ]]; then
        log_pass "config.json exists"
        
        if grep -q "HP LaserJet" config.json; then
            log_pass "Configuration contains HP printer settings"
        fi
    else
        log_fail "config.json not found"
    fi
    
    if [[ -f "config_hp_printer.json" ]]; then
        log_pass "config_hp_printer.json template exists"
    fi
}

test_backup() {
    log_test "Testing backup files..."
    
    if [[ -d "/root/hp_printer_backup" ]]; then
        log_pass "Backup directory exists: /root/hp_printer_backup"
        
        local backup_files=("hostname.bak" "hosts.bak" "mac_address.bak")
        for file in "${backup_files[@]}"; do
            if [[ -f "/root/hp_printer_backup/$file" ]]; then
                log_pass "Backup file exists: $file"
            fi
        done
    else
        log_skip "Backup directory not found (impersonation may not be active)"
    fi
}

test_systemd_services() {
    log_test "Testing systemd services..."
    
    if [[ -f "/etc/systemd/system/hp-printer-mac.service" ]]; then
        log_pass "MAC persistence service exists"
        
        if systemctl is-enabled --quiet hp-printer-mac.service 2>/dev/null; then
            log_pass "MAC persistence service is enabled"
        fi
    else
        log_skip "MAC persistence service not configured"
    fi
}

show_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}Test Summary${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  Tests Failed: ${RED}$TESTS_FAILED${NC}"
    echo -e "  Total Tests:  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ All tests passed! System is fully operational.${NC}"
    else
        echo -e "${YELLOW}⚠ Some tests failed. Check the output above for details.${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

main() {
    print_header
    
    echo "Starting comprehensive system tests..."
    echo ""
    
    test_hostname
    test_mac_address
    echo ""
    
    test_web_server
    echo ""
    
    test_snmp
    echo ""
    
    test_jetdirect
    echo ""
    
    test_avahi
    echo ""
    
    test_ports
    echo ""
    
    test_logs
    echo ""
    
    test_config
    echo ""
    
    test_backup
    echo ""
    
    test_systemd_services
    echo ""
    
    show_summary
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
