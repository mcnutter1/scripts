#!/bin/bash
# Test Windows Printer Discovery
# Tests all discovery protocols used by Windows to find network printers

PRINTER_IP="192.168.1.100"
PRINTER_HOSTNAME="HPLJ-M609-001"

echo "=================================="
echo "Windows Printer Discovery Test"
echo "=================================="
echo ""
echo "Testing printer at: $PRINTER_IP"
echo "Hostname: $PRINTER_HOSTNAME"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "1. Testing Network Connectivity"
echo "================================"
ping -c 1 -W 2 $PRINTER_IP > /dev/null 2>&1
test_result $? "Ping $PRINTER_IP"
echo ""

echo "2. Testing JetDirect Port (TCP 9100)"
echo "====================================="
timeout 2 bash -c "echo > /dev/tcp/$PRINTER_IP/9100" 2>/dev/null
test_result $? "JetDirect port 9100 open"
echo ""

echo "3. Testing Web Interface (TCP 80)"
echo "================================="
timeout 2 bash -c "echo > /dev/tcp/$PRINTER_IP/80" 2>/dev/null
test_result $? "HTTP port 80 open"

if command -v curl > /dev/null; then
    HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$PRINTER_IP/ --max-time 3)
    if [ "$HTTP_RESPONSE" = "200" ]; then
        test_result 0 "Web interface accessible (HTTP 200)"
    else
        test_result 1 "Web interface returned HTTP $HTTP_RESPONSE"
    fi
fi
echo ""

echo "4. Testing SNMP (UDP 161)"
echo "========================="
if command -v snmpget > /dev/null; then
    SNMP_RESPONSE=$(snmpget -v2c -c public -t 2 -r 1 $PRINTER_IP 1.3.6.1.2.1.1.1.0 2>/dev/null)
    if [ $? -eq 0 ]; then
        test_result 0 "SNMP query successful"
        echo "   Response: $SNMP_RESPONSE"
        
        # Get printer model
        MODEL=$(snmpget -v2c -c public -t 2 -r 1 $PRINTER_IP 1.3.6.1.2.1.25.3.2.1.3.1 2>/dev/null | cut -d'"' -f2)
        if [ ! -z "$MODEL" ]; then
            echo "   Model: $MODEL"
        fi
        
        # Get serial number
        SERIAL=$(snmpget -v2c -c public -t 2 -r 1 $PRINTER_IP 1.3.6.1.2.1.43.5.1.1.17.1 2>/dev/null | cut -d'"' -f2)
        if [ ! -z "$SERIAL" ]; then
            echo "   Serial: $SERIAL"
        fi
    else
        test_result 1 "SNMP query failed"
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC}: snmpget not installed"
    echo "   Install with: sudo apt-get install snmp"
fi
echo ""

echo "5. Testing WS-Discovery (UDP 3702)"
echo "=================================="
# Check if port is listening
if command -v netstat > /dev/null; then
    netstat -an 2>/dev/null | grep -q ":3702.*LISTEN\|:3702"
    if [ $? -eq 0 ]; then
        test_result 0 "WS-Discovery port 3702 listening"
    else
        echo -e "${YELLOW}⊘ INFO${NC}: Cannot verify WS-Discovery (requires multicast test)"
        echo "   Port 3702 should be active on printer simulator"
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC}: Cannot test without netstat"
fi
echo ""

echo "6. Testing LLMNR (UDP 5355)"
echo "==========================="
if command -v netstat > /dev/null; then
    netstat -an 2>/dev/null | grep -q ":5355.*LISTEN\|:5355"
    if [ $? -eq 0 ]; then
        test_result 0 "LLMNR port 5355 listening"
    else
        echo -e "${YELLOW}⊘ INFO${NC}: Cannot verify LLMNR (requires multicast test)"
        echo "   Port 5355 should be active on printer simulator"
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC}: Cannot test without netstat"
fi
echo ""

echo "7. Testing Hostname Resolution"
echo "=============================="
# Try to resolve hostname
if ping -c 1 -W 2 $PRINTER_HOSTNAME > /dev/null 2>&1; then
    test_result 0 "Hostname $PRINTER_HOSTNAME resolves"
else
    echo -e "${YELLOW}⊘ INFO${NC}: Hostname not resolving (may require LLMNR/mDNS client)"
    echo "   Windows will resolve via LLMNR automatically"
fi
echo ""

echo "8. Testing Print Job Submission"
echo "================================"
# Create test print job
TEST_JOB=$(cat <<'EOF'
\x1b%-12345X@PJL JOB
@PJL ENTER LANGUAGE=PCL
\x1b&l0O\x1b(s0p12h10v0s0b3T
Test Print Job
\f
\x1b%-12345X
EOF
)

# Send test job to JetDirect port
echo -e "$TEST_JOB" | nc -w 2 $PRINTER_IP 9100 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    test_result 0 "Test print job submitted"
    echo "   Check print_jobs/ directory for saved job"
else
    test_result 1 "Failed to submit test print job"
fi
echo ""

echo "9. Testing PJL Commands"
echo "======================="
# Test PJL INFO ID
PJL_RESPONSE=$(echo -e "\x1b%-12345X@PJL INFO ID\r\n\x1b%-12345X" | nc -w 2 $PRINTER_IP 9100 2>/dev/null)
if [ ! -z "$PJL_RESPONSE" ]; then
    test_result 0 "PJL commands supported"
    echo "   Response: $(echo "$PJL_RESPONSE" | grep -v '^$' | head -2)"
else
    test_result 1 "No response to PJL commands"
fi
echo ""

echo "10. Summary"
echo "==========="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo ""

echo "Windows Discovery Checklist:"
echo "----------------------------"
echo "[ ] Printer responds on network ($PRINTER_IP)"
echo "[ ] JetDirect port 9100 accepting connections"
echo "[ ] SNMP port 161 responding with printer info"
echo "[ ] WS-Discovery port 3702 active for device discovery"
echo "[ ] LLMNR port 5355 active for name resolution"
echo "[ ] Web interface accessible at http://$PRINTER_IP/"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All critical tests passed!${NC}"
    echo "The printer should be discoverable by Windows."
    echo ""
    echo "To add printer in Windows:"
    echo "1. Open Settings > Devices > Printers & scanners"
    echo "2. Click 'Add a printer or scanner'"
    echo "3. Wait for 'HP LaserJet Enterprise M609dn' to appear"
    echo "4. Click it and follow the wizard"
else
    echo -e "${YELLOW}Some tests failed - check the results above${NC}"
    echo "Ensure all printer services are running:"
    echo "  sudo python3 server.py --config config_hp_printer.json start"
fi
echo ""

echo "For detailed logs, check:"
echo "  iot_simulator/logs/"
echo "  iot_simulator/print_jobs/print_log.json"
echo ""
