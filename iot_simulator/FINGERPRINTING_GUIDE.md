# OS and Service Fingerprinting Guide

## Overview
This document explains how the HP LaserJet Enterprise M609dn simulator implements OS and service fingerprinting deception to appear as a real HP printer when scanned by network reconnaissance tools.

---

## Table of Contents
1. [HTTP Server Fingerprinting](#http-server-fingerprinting)
2. [SSH Banner Modification](#ssh-banner-modification)
3. [TCP/IP Stack Fingerprinting](#tcpip-stack-fingerprinting)
4. [Nmap OS Detection](#nmap-os-detection)
5. [P0f Passive Fingerprinting](#p0f-passive-fingerprinting)
6. [Testing and Verification](#testing-and-verification)

---

## HTTP Server Fingerprinting

### Implementation
The Python HTTP server (`printer_web_server.py`) sends HP-specific HTTP headers with every response:

**HTTP Response Headers:**
```http
Server: HP-ChaiSOE/1.0
X-HP-ChaiServer: ChaiSOE/1.0
X-HP-Firmware-Version: 2403293_000590
```

###Details
- **Server Header:** `HP-ChaiSOE/1.0`
  - ChaiSOE = Chai Service Oriented Execution
  - This is HP's proprietary embedded web server framework
  - Version 1.0 is commonly found on HP LaserJet Enterprise printers

- **X-HP-ChaiServer:** Custom HP header identifying the server technology

- **X-HP-Firmware-Version:** Reports the firmware version (including vulnerable version for testing)

### Testing HTTP Headers
```bash
# Test HTTP headers
curl -I http://192.168.1.100/

# Expected output:
# HTTP/1.0 200 OK
# Server: HP-ChaiSOE/1.0
# X-HP-ChaiServer: ChaiSOE/1.0
# X-HP-Firmware-Version: 2403293_000590
# Content-type: text/html; charset=utf-8

# Using wget
wget --server-response -O /dev/null http://192.168.1.100/

# Using nmap http-headers script
nmap --script http-headers -p 80 192.168.1.100
```

### Code Location
File: `servers/printer_web_server.py`

Functions modified:
- `respond()` - Adds headers to all HTML responses
- `respond_json()` - Adds headers to JSON API responses
- `send_file_download()` - Adds headers to file downloads

---

## SSH Banner Modification

### Implementation
The `impersonate_hp_printer.sh` script modifies the SSH server to display an HP printer banner:

**SSH Banner:**
```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                HP LaserJet Enterprise M609dn                   ║
║                  Embedded SSH Service v2.0                     ║
║                                                                ║
║  Serial Number: JPBCS12345                                     ║
║  Firmware:      2403293_000590                                 ║
║  Hostname:      HPLJ-M609-001                                  ║
║                                                                ║
║  Authorized Access Only                                        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

### Configuration Files
1. **Banner File:** `/etc/ssh/hp_printer_banner`
2. **SSH Config:** `/etc/ssh/sshd_config` (modified)
   ```
   Banner /etc/ssh/hp_printer_banner
   DebianBanner no
   ```

### SSH Version String
**Limitation:** OpenSSH's version string (e.g., "OpenSSH_9.3p1 Ubuntu") is hardcoded in the binary.

**Options for Full Spoofing:**
1. **Recompile OpenSSH** with modified version string
2. **Use ssh-mitm** - SSH man-in-the-middle proxy
3. **Use Dropbear SSH** - Lighter SSH server with easier modification

**Example SSH Version Modification (requires recompilation):**
```c
// In OpenSSH source: version.h
#define SSH_VERSION    "SSH-2.0-HP_Embedded_SSH_2.0"
```

### Testing SSH Banner
```bash
# Connect and view banner
ssh 192.168.1.100

# View SSH version string
ssh -v 192.168.1.100 2>&1 | grep "Server version"

# Non-interactive banner grab
nc 192.168.1.100 22

# Nmap SSH version detection
nmap -sV -p 22 192.168.1.100
```

### Current Limitations
⚠️ **The SSH version string still shows as OpenSSH unless recompiled**

Example of what scanners see:
```
22/tcp open  ssh     OpenSSH 9.3p1 Ubuntu
```

To fully spoof, you need custom SSH server or recompiled OpenSSH.

---

## TCP/IP Stack Fingerprinting

### Implementation
The `impersonate_hp_printer.sh` script modifies kernel TCP/IP parameters via sysctl to mimic HP printer network behavior.

**Configuration File:** `/etc/sysctl.d/99-hp-printer-fingerprint.conf`

### Modified TCP/IP Parameters

#### Window Sizes
```bash
net.core.rmem_default = 87380
net.core.wmem_default = 16384
net.ipv4.tcp_rmem = 4096 87380 174760
net.ipv4.tcp_wmem = 4096 16384 131072
```
HP printers typically use smaller send buffers than modern Linux systems.

#### TCP Options
```bash
net.ipv4.tcp_timestamps = 1        # Enable timestamps
net.ipv4.tcp_sack = 1              # Enable selective ACK
net.ipv4.tcp_window_scaling = 1    # Enable window scaling
```

#### TTL (Time To Live)
```bash
net.ipv4.ip_default_ttl = 64
net.ipv6.conf.all.hop_limit = 64
```
HP printers commonly use TTL=64 (matching many embedded Linux devices).

#### TCP Keepalive
```bash
net.ipv4.tcp_keepalive_time = 7200   # 2 hours
net.ipv4.tcp_keepalive_intvl = 75    # 75 seconds
net.ipv4.tcp_keepalive_probes = 9    # 9 probes
```

#### ECN (Explicit Congestion Notification)
```bash
net.ipv4.tcp_ecn = 0  # Disabled (many printers don't support)
```

#### Connection Limits
```bash
net.ipv4.tcp_syn_retries = 3
net.ipv4.tcp_synack_retries = 3
net.ipv4.tcp_fin_timeout = 30
net.core.somaxconn = 128
```

### Applying Changes
```bash
# The impersonate script does this automatically:
sudo sysctl -p /etc/sysctl.d/99-hp-printer-fingerprint.conf

# Verify changes:
sysctl net.ipv4.ip_default_ttl
sysctl net.ipv4.tcp_window_scaling
```

### Impact on Nmap Scanning
These TCP/IP stack modifications affect how Nmap's OS detection interprets the system:

**Nmap looks at:**
- TTL values
- TCP window size
- TCP options (timestamps, SACK, window scaling)
- IP ID sequence
- TCP initial window
- ICMP responses

---

## Nmap OS Detection

### How Nmap Detects Operating Systems

Nmap sends specially crafted packets and analyzes responses:

1. **TCP SYN to open port**
2. **TCP SYN to closed port**
3. **TCP ACK to closed port**
4. **Various ICMP probes**
5. **UDP probes**

### HP Printer TCP/IP Fingerprint Characteristics

**Typical HP LaserJet M609dn signature:**
```
# TCP SYN Response:
- Window Size: 5840 or 8192
- TTL: 64
- Don't Fragment: Yes
- TCP Options: MSS, SACK OK, Timestamp, NOP, Window Scale
- MSS: 1460 (Ethernet)
- Window Scale Factor: 6
- Initial Congestion Window: 10

# IP ID Sequence:
- Incremental (not random)

# TCP Sequence Number:
- Random (RFC 1948 compliant)
```

### Testing with Nmap
```bash
# Full OS detection
sudo nmap -O -v 192.168.1.100

# OS detection with aggressive timing
sudo nmap -O -T4 192.168.1.100

# OS detection with version detection
sudo nmap -O -sV 192.168.1.100

# Detailed OS fingerprint
sudo nmap -O --osscan-guess --script=banner 192.168.1.100
```

### Expected Nmap Results
```
Device type: printer
Running: HP embedded
OS CPE: cpe:/h:hp:laserjet
OS details: HP LaserJet printer or HP embedded device

Network Distance: 1 hop
Service Info: Device: printer

OS and Service detection performed.
```

### Nmap Fingerprint Database
HP printer signatures in Nmap's `nmap-os-db` typically look like:

```
Fingerprint HP LaserJet Enterprise M609dn
Class HP | embedded | | printer
CPE cpe:/h:hp:laserjet

SEQ(SP=64-70%GCD=1-6%ISR=D6-E4%TI=I%CI=I%II=I%SS=S|O%TS=7|8)
OPS(O1=M5B4NW6|M109NW6%O2=M5B4NW6%O3=M109NW6%O4=M5B4NW6%O5=M5B4NW6%O6=M109)
WIN(W1=3890%W2=3890%W3=3890%W4=3890%W5=3890%W6=3890)
ECN(R=Y%DF=Y%T=40%W=3908%O=M5B4NW6%CC=Y%Q=)
T1(R=Y%DF=Y%T=40%S=O%A=S+%F=AS%RD=0%Q=)
```

---

## P0f Passive Fingerprinting

### What is P0f?
P0f is a passive OS fingerprinting tool that identifies operating systems by analyzing network traffic without sending any packets.

### HP Printer P0f Signature

**File:** `/tmp/hp_printer_p0f_signature.txt` (created by impersonate script)

**Signature Format:**
```
label = s:unix:HP:LaserJet M609dn
sig   = 4:64:0:*:mss*10,6:mss,sok,ts,nop,ws:df,id+:0
sig   = 4:64:0:*:8192,6:mss,sok,ts,nop,ws:df,id+:0
```

**Breakdown:**
- `4` - IPv4
- `64` - TTL value
- `0` - No special quirks
- `*` - Wildcard for packet size
- `mss*10,6` - Window size = MSS × 10, Window Scale = 6
- `mss,sok,ts,nop,ws` - TCP options order: MSS, SACK OK, Timestamp, NOP, Window Scale
- `df,id+` - Don't Fragment bit set, incrementing IP ID
- `0` - Zero special flags

### Adding to P0f Database
```bash
# Backup original
sudo cp /etc/p0f/p0f.fp /etc/p0f/p0f.fp.bak

# Add HP printer signature to [tcp:request] section
sudo nano /etc/p0f/p0f.fp

# Add these lines:
label = s:unix:HP:LaserJet M609dn
sig   = 4:64:0:*:mss*10,6:mss,sok,ts,nop,ws:df,id+:0

# Restart p0f
sudo systemctl restart p0f
```

### Testing P0f Detection
```bash
# Run p0f in promiscuous mode
sudo p0f -i eth0

# Generate traffic from another machine
ping 192.168.1.100
curl http://192.168.1.100

# P0f output should show:
# -> 192.168.1.100:80 - HP LaserJet M609dn
```

---

## Testing and Verification

### Complete Verification Checklist

#### 1. HTTP Fingerprinting
```bash
# Test HTTP headers
curl -I http://192.168.1.100/
# Verify: Server: HP-ChaiSOE/1.0

# Test with Nmap
nmap --script http-headers -p 80 192.168.1.100
```

#### 2. SSH Banner
```bash
# Test SSH banner
ssh -v 192.168.1.100
# Verify: HP LaserJet banner appears

# Non-interactive test
nc 192.168.1.100 22
```

#### 3. TCP/IP Stack
```bash
# Check TTL
sudo hping3 -S -p 80 -c 1 192.168.1.100
# Verify: TTL=64

# Check TCP options
sudo nmap -O -v 192.168.1.100
# Verify: Window size, TCP options match HP printer
```

#### 4. Nmap OS Detection
```bash
# Full scan
sudo nmap -O -sV -v 192.168.1.100

# Expected output should include:
# - Device type: printer
# - Running: HP embedded
# - OS details: HP LaserJet
```

#### 5. Service Banners
```bash
# SNMP
snmpwalk -v2c -c public 192.168.1.100 system
# Verify: sysDescr = HP LaserJet Enterprise M609dn

# HTTP Title
curl -s http://192.168.1.100 | grep title
# Verify: <title>HP LaserJet Enterprise M609dn - Embedded Web Server</title>
```

#### 6. MAC Address
```bash
# Check ARP table
arp -a | grep 192.168.1.100
# Verify: a0:b3:cc:d4:e5:f6 (HP OUI)

# Or use nmap
sudo nmap -sn 192.168.1.100
# Verify: MAC Address: A0:B3:CC:D4:E5:F6 (Hewlett Packard)
```

### Comprehensive Network Scan
```bash
#!/bin/bash
# Complete fingerprint verification script

IP="192.168.1.100"

echo "=== HTTP Server Fingerprint ==="
curl -I http://$IP/

echo -e "\n=== SSH Banner ==="
timeout 3 nc $IP 22 2>/dev/null || echo "SSH not responding"

echo -e "\n=== Nmap OS Detection ==="
sudo nmap -O -v $IP 2>/dev/null | grep -A 10 "OS details"

echo -e "\n=== SNMP Information ==="
snmpwalk -v2c -c public $IP system 2>/dev/null | head -5

echo -e "\n=== MAC Address ==="
arp -a | grep $IP || sudo nmap -sn $IP | grep MAC

echo -e "\n=== Service Detection ==="
nmap -sV -p 80,161,9100,22 $IP
```

---

## Comparison: Before vs After

### Before Fingerprint Modifications
```
Nmap scan:
  OS: Linux 5.15 - 6.x
  Device type: general purpose
  Running: Linux 5.X|6.X
  
HTTP Headers:
  Server: BaseHTTP/0.6 Python/3.11.x
  
SSH:
  SSH-2.0-OpenSSH_9.3p1 Ubuntu-1ubuntu3
  
MAC:
  (Original system MAC - random vendor)
```

### After Fingerprint Modifications
```
Nmap scan:
  OS: HP LaserJet printer or HP embedded device
  Device type: printer
  Running: HP embedded
  CPE: cpe:/h:hp:laserjet
  
HTTP Headers:
  Server: HP-ChaiSOE/1.0
  X-HP-ChaiServer: ChaiSOE/1.0
  X-HP-Firmware-Version: 2403293_000590
  
SSH:
  Banner: HP LaserJet Enterprise M609dn
  Banner: Embedded SSH Service v2.0
  Version: SSH-2.0-OpenSSH... (still needs recompilation)
  
MAC:
  A0:B3:CC:D4:E5:F6 (Hewlett Packard)
```

---

## Advanced Topics

### Creating Custom TCP/IP Fingerprints

To create fingerprints for other devices:

1. **Capture real device traffic:**
```bash
sudo tcpdump -i eth0 -w capture.pcap host <real_printer_ip>
```

2. **Analyze with Wireshark:**
   - Look at TCP SYN packets
   - Note TCP options, window size, TTL
   - Check IP ID patterns

3. **Extract parameters:**
   - Initial window
   - TCP options and order
   - Window scale factor
   - MSS value
   - TTL
   - IP ID increment pattern

4. **Apply to sysctl:**
   - Modify `/etc/sysctl.d/99-hp-printer-fingerprint.conf`
   - Adjust window sizes, options, TTL

### Evading Advanced Fingerprinting

Some advanced scanners look for:
- **Clock skew** - Analyze timestamp differences
- **Behavioral patterns** - How the system responds to malformed packets
- **Application layer** - Deep inspection of protocols

**Mitigation strategies:**
- Use virtual machines with NTP synchronization
- Implement proper protocol handling
- Test against multiple scanners (Nmap, Nessus, Shodan, etc.)

---

## Troubleshooting

### Issue: Nmap still detects as Linux
**Solution:**
- Verify sysctl settings are applied: `sysctl -a | grep tcp`
- Check TCP window size: `ss -tin`
- Ensure no conflicting firewall rules
- Try with `-O --osscan-guess` for more aggressive detection

### Issue: HTTP headers not showing HP banner
**Solution:**
- Verify Python server is running
- Check with `curl -I` for raw headers
- Ensure no reverse proxy is modifying headers
- Check printer_web_server.py has correct Server header

### Issue: SSH banner not appearing
**Solution:**
- Verify `/etc/ssh/hp_printer_banner` exists
- Check `sshd_config` has `Banner` directive
- Restart SSH: `sudo systemctl restart sshd`
- Test with telnet: `telnet <IP> 22`

### Issue: MAC address reverts on reboot
**Solution:**
- Check if `hp-printer-mac.service` is enabled
- Verify: `systemctl status hp-printer-mac.service`
- Manually re-run: `sudo impersonate_hp_printer.sh start`

---

## Security Implications

⚠️ **WARNING:** These fingerprint modifications reduce system security:

1. **Reduced TCP performance** - Smaller windows may slow network throughput
2. **Disabled security features** - ECN disabled, reduced retry counts
3. **Predictable behavior** - Makes system easier to fingerprint by attackers
4. **Authentication bypass** - SSH banner may confuse administrators

**ONLY use in isolated lab environments for authorized testing!**

---

## References

- [Nmap OS Detection](https://nmap.org/book/osdetect.html)
- [P0f Documentation](https://lcamtuf.coredump.cx/p0f3/)
- [HP ChaiServer Documentation](https://developers.hp.com/hp-linux-imaging-and-printing)
- [TCP/IP Fingerprinting Techniques](https://en.wikipedia.org/wiki/TCP/IP_stack_fingerprinting)
- [OpenSSH Configuration](https://man.openbsd.org/sshd_config)

---

**Document Version:** 1.0  
**Last Updated:** December 1, 2025  
**Related:** [impersonate_hp_printer.sh](impersonate_hp_printer.sh), [VULNERABLE_FIRMWARE.md](VULNERABLE_FIRMWARE.md)
