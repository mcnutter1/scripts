# HP Printer Simulator - Quick Reference

## 🚀 Quick Start

### One-Command Setup (Ubuntu 24.04)
```bash
sudo ./setup_hp_printer.sh
```

### Manual Setup
```bash
# 1. Configure system identity
sudo ./impersonate_hp_printer.sh start

# 2. Start simulator services (using config file directly)
sudo python3 server.py start --config config_hp_printer.json
```

## 📋 Command Reference

### System Impersonation
```bash
sudo ./impersonate_hp_printer.sh start   # Start impersonation
sudo ./impersonate_hp_printer.sh stop    # Restore original config
sudo ./impersonate_hp_printer.sh status  # Check status
```

### Simulator Services
```bash
# Start with default config (config.json)
sudo python3 server.py start

# Start with specific config
sudo python3 server.py start --config config_hp_printer.json

# Stop services
sudo python3 server.py stop

# Check status
sudo python3 server.py status

# Restart with different config
sudo python3 server.py restart --config config_hp_printer.json
```

## 🔧 Testing Commands

### Web Interface
```bash
# Local access
curl http://localhost/

# Browser access
firefox http://localhost/
firefox http://localhost/supplies
firefox http://localhost/network
```

### SNMP Queries
```bash
# System info
snmpget -v2c -c public localhost 1.3.6.1.2.1.1.5.0  # Hostname
snmpget -v2c -c public localhost 1.3.6.1.2.1.1.1.0  # Description

# Printer info
snmpget -v2c -c public localhost 1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0  # Model
snmpget -v2c -c public localhost 1.3.6.1.2.1.43.10.2.1.4.1.1          # Page count
snmpget -v2c -c public localhost 1.3.6.1.2.1.43.11.1.1.6.1.1          # Toner level

# Walk entire printer MIB
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.43
```

### JetDirect (Port 9100)
```bash
# Query printer ID
printf '\x1b%%-12345X@PJL INFO ID\r\n\x1b%%-12345X' | nc localhost 9100

# Query status
printf '\x1b%%-12345X@PJL INFO STATUS\r\n\x1b%%-12345X' | nc localhost 9100

# Send test print
echo "Test print job" | nc localhost 9100

# Send file
cat document.txt | nc localhost 9100
```

### Network Discovery
```bash
# Avahi/Bonjour discovery
avahi-browse -a -t
avahi-browse -r _printer._tcp

# Nmap scan
nmap -p 80,161,9100 localhost
nmap -sV localhost
nmap --script snmp-info localhost
```

## 🔍 Verification

### Check System Identity
```bash
hostname                    # Should show: HPLJ-M609-001
ip link show                # Should show MAC: a0:b3:cc:d4:e5:f6
ip addr show                # Check IP address
```

### Check Services
```bash
# Check listening ports
sudo netstat -tuln | grep -E ':(80|161|9100)'
sudo ss -tuln | grep -E ':(80|161|9100)'

# Check processes
ps aux | grep python3 | grep server

# Check systemd services
systemctl status avahi-daemon
systemctl status hp-printer-mac.service
```

### Check Logs
```bash
# Service logs
tail -f logs/printer_web_server.py.out
tail -f logs/snmp_server.py.out
tail -f logs/jetdirect_server.py.out

# Error logs
tail -f logs/*.err

# System log
tail -f /var/log/syslog | grep -i printer
```

## 📊 Configuration Files

### Main Configuration
```bash
config_hp_printer.json   # HP printer configuration template
config.json              # Active configuration (copy from above)
```

### Key Settings to Customize
```json
{
  "globals": {
    "system_name": "HP LaserJet Enterprise M609dn",
    "ip": "192.168.1.100",          # Your IP
    "mac": "A0:B3:CC:D4:E5:F6",     # Printer MAC
    "hostname": "HPLJ-M609-001",    # Printer hostname
    "serial": "JPBCS12345",         # Serial number
    "page_count": 45782,            # Total pages printed
    "toner_level": 68,              # Toner remaining
    "toner_capacity": 10000         # Max toner pages
  }
}
```

## 🌐 Network Services

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Web Interface | 80 | TCP | HP Embedded Web Server |
| SNMP | 161 | UDP | Device monitoring |
| JetDirect | 9100 | TCP | Raw printing |
| LPD | 515 | TCP | Line printer daemon |
| IPP | 631 | TCP | Internet Printing Protocol |

## 🎯 Printer Identity

```
Model:    HP LaserJet Enterprise M609dn
Serial:   JPBCS12345
Hostname: HPLJ-M609-001
MAC:      A0:B3:CC:D4:E5:F6
IP:       192.168.1.100 (DHCP or static)
```

## 🔐 Default Credentials

```
SNMP Community: public (read-only)
Web Interface:  No authentication required
```

## 🛠️ Troubleshooting

### Service Won't Start
```bash
# Check if ports are in use
sudo lsof -i :80
sudo lsof -i :161
sudo lsof -i :9100

# Kill conflicting processes
sudo pkill -f printer_web_server
sudo pkill -f snmp_server
sudo pkill -f jetdirect_server
```

### MAC Address Not Changing
```bash
# Manual MAC change
sudo ip link set eth0 down
sudo ip link set eth0 address A0:B3:CC:D4:E5:F6
sudo ip link set eth0 up

# Check NetworkManager
sudo nmcli device set eth0 managed no
```

### Can't Access Web Interface
```bash
# Check if service is running
curl -v http://localhost/

# Check firewall
sudo ufw status
sudo ufw allow 80/tcp

# Check logs
tail -f logs/printer_web_server.py.err
```

### SNMP Not Responding
```bash
# Test locally
snmpget -v2c -c public localhost 1.3.6.1.2.1.1.1.0

# Check if port is open
sudo netstat -uln | grep 161

# Check logs
tail -f logs/snmp_server.py.out
```

## 📁 Directory Structure

```
iot_simulator/
├── config_hp_printer.json          # HP printer config template
├── config.json                      # Active config
├── server.py                        # Main daemon
├── impersonate_hp_printer.sh        # System impersonation script
├── setup_hp_printer.sh              # Quick setup script
├── PRINTER_README.md                # Full documentation
├── IMPERSONATION_GUIDE.md           # Impersonation guide
├── QUICK_REFERENCE.md               # This file
├── servers/
│   ├── printer_web_server.py        # HTTP server (port 80)
│   ├── snmp_server.py               # SNMP server (port 161)
│   ├── jetdirect_server.py          # JetDirect (port 9100)
│   └── shared.py                    # Shared utilities
└── logs/
    ├── printer_web_server.py.out    # Web server output
    ├── snmp_server.py.out           # SNMP output
    └── jetdirect_server.py.out      # JetDirect output
```

## 🔄 Backup & Restore

### Backup Location
```
/root/hp_printer_backup/
├── hostname.bak        # Original hostname
├── hosts.bak          # Original /etc/hosts
├── mac_address.bak    # Original MAC
└── interface.bak      # Interface name
```

### Restore Original Config
```bash
sudo ./impersonate_hp_printer.sh stop
```

## 📡 Remote Testing

### From Another Machine
```bash
# Replace IP with your printer simulator IP
PRINTER_IP="192.168.1.100"

# Web interface
curl http://$PRINTER_IP/
firefox http://$PRINTER_IP/

# SNMP
snmpwalk -v2c -c public $PRINTER_IP 1.3.6.1.2.1.1
snmpget -v2c -c public $PRINTER_IP 1.3.6.1.2.1.1.5.0

# JetDirect
printf '\x1b%%-12345X@PJL INFO ID\r\n\x1b%%-12345X' | nc $PRINTER_IP 9100

# Network scan
nmap -p 80,161,9100 $PRINTER_IP
nmap -sV $PRINTER_IP

# Avahi discovery
avahi-browse -r _printer._tcp
```

## 💡 Tips & Tricks

### Change Toner Level
Edit `config.json`:
```json
"toner_level": 25,        # Low toner
"toner_capacity": 10000
```
Restart services to apply.

### Simulate Print Job
```bash
# Send a test document
cat << EOF | nc localhost 9100
\x1b%-12345X@PJL
@PJL JOB NAME="Test Job"
@PJL ENTER LANGUAGE=PCL
Test page content
\x1b%-12345X
EOF
```

### Monitor Network Traffic
```bash
# Capture printer traffic
sudo tcpdump -i any -n port 80 or port 161 or port 9100

# Wireshark filter
ip.addr == 192.168.1.100
```

### Performance Testing
```bash
# Concurrent web requests
ab -n 1000 -c 10 http://localhost/

# SNMP stress test
for i in {1..100}; do
  snmpget -v2c -c public localhost 1.3.6.1.2.1.1.5.0 &
done
```

## 📞 Common Use Cases

### Security Testing
- Test vulnerability scanners
- Practice printer-specific exploits
- Evaluate network monitoring tools

### Development
- Test print queue management
- Develop printer discovery tools
- Create SNMP monitoring dashboards

### Training
- Demonstrate printer reconnaissance
- Teach SNMP enumeration
- Show network device fingerprinting

## ⚠️ Important Notes

1. **Use in authorized environments only**
2. **Always restore original configuration after testing**
3. **Don't interfere with production networks**
4. **Monitor for MAC address conflicts**
5. **Check firewall rules after setup**

## 🆘 Emergency Stop

```bash
# Stop everything immediately
sudo python3 server.py stop
sudo ./impersonate_hp_printer.sh stop
sudo systemctl restart NetworkManager
```

---

**Quick Help**: For full documentation, see `PRINTER_README.md` and `IMPERSONATION_GUIDE.md`
