# HP Printer System Impersonation Guide

This guide explains how to configure a Ubuntu 24.04 system to fully impersonate an HP LaserJet printer on the network.

## Overview

The `impersonate_hp_printer.sh` script performs comprehensive system configuration to make your Ubuntu machine appear as an HP LaserJet Enterprise M609dn printer on the network. This includes:

- **MAC Address Spoofing**: Changes network interface MAC to HP printer MAC
- **Hostname Configuration**: Sets system hostname to printer name
- **Network Discovery**: Configures Avahi/Bonjour for printer discovery
- **DHCP Identity**: Configures DHCP client to announce as printer
- **System Banners**: Updates login banners with printer information
- **Firewall Rules**: Opens necessary printer service ports
- **Persistence**: Creates systemd services to maintain configuration across reboots

## ⚠️ Important Warnings

**LEGAL & ETHICAL USE ONLY**
- Only use this in authorized testing environments
- Do not use on production networks without permission
- This is for security testing, research, and education only
- Unauthorized network impersonation may violate laws and policies

**SYSTEM CHANGES**
- This script makes significant system-level changes
- All original settings are backed up to `/root/hp_printer_backup/`
- You can restore original settings with `sudo ./impersonate_hp_printer.sh stop`

## Prerequisites

### System Requirements
- Ubuntu 24.04 LTS (or similar Debian-based system)
- Root/sudo access
- Active network interface (ethernet or wireless)

### Install Required Packages
```bash
sudo apt-get update
sudo apt-get install -y \
    avahi-daemon \
    avahi-utils \
    net-tools \
    iproute2 \
    systemd
```

### Optional Packages
```bash
# For additional SNMP support (if not using Python SNMP server)
sudo apt-get install -y snmpd snmp

# For firewall management
sudo apt-get install -y ufw
```

## Installation

1. **Download the script**
   ```bash
   cd /path/to/iot_simulator
   chmod +x impersonate_hp_printer.sh
   ```

2. **Review configuration** (edit script if needed)
   ```bash
   # Default configuration in script:
   HP_MAC_ADDRESS="A0:B3:CC:D4:E5:F6"
   HP_HOSTNAME="HPLJ-M609-001"
   HP_MODEL="HP LaserJet Enterprise M609dn"
   HP_SERIAL="JPBCS12345"
   INTERFACE="eth0"  # Auto-detected if possible
   ```

## Usage

### Start Impersonation

```bash
sudo ./impersonate_hp_printer.sh start
```

This will:
1. ✅ Auto-detect your network interface
2. ✅ Backup current configuration
3. ✅ Change MAC address to HP printer MAC
4. ✅ Change hostname to printer name
5. ✅ Configure Avahi for mDNS/Bonjour discovery
6. ✅ Set up DHCP client identifier
7. ✅ Configure system banners
8. ✅ Open firewall ports
9. ✅ Create persistence services

**Sample Output:**
```
╔════════════════════════════════════════════════════════════════╗
║        HP Printer Network Impersonation Script                 ║
║        Ubuntu 24.04 System Configuration Tool                  ║
╚════════════════════════════════════════════════════════════════╝

[INFO] Starting HP printer impersonation...
[INFO] Auto-detected network interface: ens33
[INFO] Created backup directory: /root/hp_printer_backup
[INFO] Backing up current configuration...
[INFO] Backed up current hostname: ubuntu-server
[INFO] Backed up MAC address: 00:0c:29:3a:5b:7c
[INFO] Changing MAC address to A0:B3:CC:D4:E5:F6...
[INFO] MAC address successfully changed to A0:B3:CC:D4:E5:F6
[INFO] MAC persistence service created and enabled
[INFO] Changing hostname to HPLJ-M609-001...
[INFO] Hostname successfully changed to HPLJ-M609-001
[INFO] Configuring Avahi (mDNS/Bonjour) for printer discovery...
[INFO] Avahi configured for printer discovery
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO] HP Printer impersonation configured successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Check Status

```bash
sudo ./impersonate_hp_printer.sh status
```

This shows:
- Current network configuration
- MAC address (original vs spoofed)
- Hostname
- Service status (Avahi, MAC persistence)
- Backup information

**Sample Output:**
```
Current System Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Network Configuration:
  Hostname:        HPLJ-M609-001
  Interface:       ens33
  Current MAC:     a0:b3:cc:d4:e5:f6
  Status:          ✓ Spoofed as HP Printer
  IP Address:      192.168.1.100

HP Printer Identity:
  Target MAC:      A0:B3:CC:D4:E5:F6
  Target Hostname: HPLJ-M609-001
  Model:           HP LaserJet Enterprise M609dn
  Serial:          JPBCS12345

Services Status:
  MAC Persistence: ✓ Enabled
  Avahi (mDNS):    ✓ Running

Backup Status:
  Backup Location: /root/hp_printer_backup
  Original MAC:    00:0c:29:3a:5b:7c
  Original Host:   ubuntu-server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Stop Impersonation (Restore Original Config)

```bash
sudo ./impersonate_hp_printer.sh stop
```

This will:
1. ✅ Restore original hostname
2. ✅ Restore original MAC address
3. ✅ Restore hosts file
4. ✅ Remove systemd persistence service
5. ✅ Remove Avahi printer service
6. ✅ Restore SNMP configuration
7. ✅ Restore NetworkManager settings

## Complete Setup Guide

### Step 1: Configure System Identity

```bash
# Make script executable
chmod +x impersonate_hp_printer.sh

# Start impersonation
sudo ./impersonate_hp_printer.sh start
```

### Step 2: Start Printer Simulator Services

```bash
# Copy printer configuration
cp config_hp_printer.json config.json

# Start the IoT simulator daemon
sudo python3 server.py start

# Verify services are running
sudo python3 server.py status
```

### Step 3: Verify Network Presence

```bash
# Check if printer is discoverable via Avahi
avahi-browse -a -t

# Check MAC address
ip link show

# Check hostname
hostname

# Test SNMP (from another machine)
snmpwalk -v2c -c public YOUR_IP 1.3.6.1.2.1.1

# Test web interface
curl http://YOUR_IP/
```

### Step 4: Test from Another Machine

```bash
# Scan for the printer
nmap -p 80,161,9100 YOUR_IP

# SNMP query
snmpget -v2c -c public YOUR_IP 1.3.6.1.2.1.1.5.0  # hostname
snmpget -v2c -c public YOUR_IP 1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0  # model

# Browse web interface
firefox http://YOUR_IP/

# Test JetDirect
printf '\x1b%%-12345X@PJL INFO ID\r\n\x1b%%-12345X' | nc YOUR_IP 9100

# Discover via Avahi/Bonjour
avahi-browse -r _printer._tcp
```

## What Gets Changed

### Network Configuration
- **MAC Address**: Interface MAC changed to HP printer MAC
- **Hostname**: System hostname changed to printer name
- **DHCP Client ID**: DHCP announces as printer
- **DNS/mDNS**: Avahi broadcasts printer services

### System Files Modified
- `/etc/hostname` - Hostname configuration
- `/etc/hosts` - Local hostname resolution
- `/etc/avahi/services/hp-printer.service` - mDNS printer announcement
- `/etc/systemd/system/hp-printer-mac.service` - MAC persistence
- `/etc/issue` - Login banner
- `/etc/motd` - Message of the day

### Firewall Ports Opened
- TCP 80 - HTTP (Web interface)
- UDP 161 - SNMP
- TCP 9100 - HP JetDirect
- TCP 515 - LPD (Line Printer Daemon)
- TCP 631 - IPP (Internet Printing Protocol)

### Backup Location
All original configurations are backed up to:
```
/root/hp_printer_backup/
├── hostname.bak          # Original hostname
├── hosts.bak            # Original /etc/hosts
├── mac_address.bak      # Original MAC address
├── interface.bak        # Network interface name
└── snmpd.conf.bak       # Original SNMP config (if exists)
```

## Network Discovery Results

After running the script, your system will appear on the network as:

### Hostname Resolution
- **DNS Hostname**: HPLJ-M609-001
- **mDNS Name**: HPLJ-M609-001.local

### Avahi/Bonjour Services
- `_printer._tcp` - Generic printer
- `_pdl-datastream._tcp` - HP JetDirect
- `_http._tcp` - Web interface

### SNMP Identification
- **sysName**: HPLJ-M609-001
- **sysDescr**: HP LaserJet Enterprise M609dn
- **sysObjectID**: 1.3.6.1.4.1.11.2.3.9.1 (HP Enterprise)

### ARP Table Entry
```
? (192.168.1.100) at a0:b3:cc:d4:e5:f6 [ether] on eth0
```

## Customization

Edit the script to customize the printer identity:

```bash
# Edit these variables at the top of the script
HP_MAC_ADDRESS="A0:B3:CC:D4:E5:F6"     # Any valid MAC
HP_HOSTNAME="HPLJ-M609-001"            # Printer hostname
HP_MODEL="HP LaserJet Enterprise M609dn"  # Model name
HP_SERIAL="JPBCS12345"                 # Serial number
INTERFACE="eth0"                       # Network interface (auto-detected)
```

You should also update `config_hp_printer.json` to match:
```json
{
  "globals": {
    "system_name": "HP LaserJet Enterprise M609dn",
    "ip": "192.168.1.100",
    "mac": "A0:B3:CC:D4:E5:F6",
    "hostname": "HPLJ-M609-001",
    "serial": "JPBCS12345",
    ...
  }
}
```

## Troubleshooting

### MAC Address Not Changing
```bash
# Check if NetworkManager is managing the interface
nmcli device status

# Temporarily disable NetworkManager for the interface
sudo nmcli device set eth0 managed no

# Manually change MAC
sudo ip link set eth0 down
sudo ip link set eth0 address A0:B3:CC:D4:E5:F6
sudo ip link set eth0 up
```

### Interface Auto-Detection Fails
```bash
# List all interfaces
ip link show

# Edit script and manually set INTERFACE variable
INTERFACE="ens33"  # or your interface name
```

### MAC Address Reverts After Reboot
```bash
# Check if persistence service is enabled
sudo systemctl status hp-printer-mac.service

# Manually enable
sudo systemctl enable hp-printer-mac.service
sudo systemctl start hp-printer-mac.service
```

### Avahi Not Broadcasting
```bash
# Check Avahi status
sudo systemctl status avahi-daemon

# Restart Avahi
sudo systemctl restart avahi-daemon

# Test local discovery
avahi-browse -a -t

# Check service file
cat /etc/avahi/services/hp-printer.service
```

### Firewall Blocking Connections
```bash
# Check UFW status
sudo ufw status

# Temporarily disable for testing
sudo ufw disable

# Or add rules manually
sudo ufw allow 80/tcp
sudo ufw allow 161/udp
sudo ufw allow 9100/tcp
```

### Network Connection Lost After MAC Change
```bash
# Some networks use MAC filtering or DHCP reservations
# You may need to:

# 1. Renew DHCP lease
sudo dhclient -r eth0
sudo dhclient eth0

# 2. Restart NetworkManager
sudo systemctl restart NetworkManager

# 3. Use a MAC address that's already authorized on the network
```

## Verification Checklist

After setup, verify these items:

- [ ] MAC address changed: `ip link show eth0 | grep ether`
- [ ] Hostname changed: `hostname`
- [ ] Avahi running: `systemctl status avahi-daemon`
- [ ] Printer discoverable: `avahi-browse -r _printer._tcp`
- [ ] Web server accessible: `curl http://localhost/`
- [ ] SNMP responding: `snmpget -v2c -c public localhost 1.3.6.1.2.1.1.5.0`
- [ ] JetDirect accessible: `nc -zv localhost 9100`
- [ ] Firewall configured: `sudo ufw status`
- [ ] Backup created: `ls -la /root/hp_printer_backup/`

## Security Considerations

### On Your Test Network
- Inform network administrators before running
- Use isolated test networks when possible
- Don't interfere with real printers
- Monitor for conflicts with existing devices

### MAC Address Conflicts
- If another device has the same MAC, you'll cause network issues
- Use unique MAC addresses not present on your network
- HP MAC ranges typically start with: 00:17:08, 00:1E:0B, A0:B3:CC, etc.

### Cleanup After Testing
```bash
# Always restore original configuration
sudo ./impersonate_hp_printer.sh stop

# Stop simulator services
cd /path/to/iot_simulator
sudo python3 server.py stop

# Verify restoration
sudo ./impersonate_hp_printer.sh status
```

## Integration with Other Tools

### With Nmap
```bash
nmap -sV -p 80,161,9100 YOUR_IP
nmap --script snmp-info YOUR_IP
```

### With Metasploit
```ruby
use auxiliary/scanner/snmp/snmp_enum
set RHOSTS YOUR_IP
run
```

### With Forescout
The simulated printer should be detected and classified by Forescout CounterACT as an HP printer based on:
- MAC OUI (HP vendor)
- SNMP fingerprinting
- Open ports (80, 161, 9100)
- HTTP Server header: "HP-ChaiSOE/2.0"
- mDNS/Bonjour services

## Advanced Configuration

### Multiple Printer Instances
Run multiple simulators on different IPs using Docker or VMs:
```bash
# VM 1: HP LaserJet M609
sudo ./impersonate_hp_printer.sh start

# VM 2: Edit script for different model
HP_MODEL="HP Color LaserJet Pro M454dn"
HP_SERIAL="JPBCS67890"
HP_MAC_ADDRESS="A0:B3:CC:D4:E5:F7"
```

### Integration with External DHCP
Configure your DHCP server to assign specific IPs based on MAC:
```
# dhcpd.conf
host hp-printer {
    hardware ethernet A0:B3:CC:D4:E5:F6;
    fixed-address 192.168.1.100;
    option host-name "HPLJ-M609-001";
}
```

## References

- [HP Printer MIB Documentation](http://www.hp.com/rnd/software/snmp/)
- [RFC 3805 - Printer MIB v2](https://tools.ietf.org/html/rfc3805)
- [HP JetDirect Protocol](https://developers.hp.com/hp-linux-imaging-and-printing)
- [Avahi/Bonjour](https://avahi.org/)

## Support

For issues or questions:
1. Check logs: `/var/log/syslog` and `/root/hp_printer_backup/`
2. Run status command: `sudo ./impersonate_hp_printer.sh status`
3. Review firewall: `sudo ufw status verbose`
4. Check network: `ip addr show` and `ip route show`

---

**Remember**: This tool is for authorized security testing only. Always restore original configuration after testing.
