# Windows Printer Discovery Setup Guide

## Overview

The HP printer simulator now includes full Windows printer discovery support, allowing Windows systems to automatically find and add the printer using the standard "Add Printer" wizard.

## Discovery Protocols Implemented

### 1. WS-Discovery (Web Services Discovery)
- **Port**: UDP 3702
- **Purpose**: Primary Windows printer discovery protocol
- **Features**: 
  - Responds to Probe and Resolve requests
  - Sends Hello announcements on startup
  - Identifies as a network printer device

### 2. LLMNR (Link-Local Multicast Name Resolution)
- **Port**: UDP 5355
- **Purpose**: Hostname resolution without DNS
- **Features**:
  - Resolves printer hostname to IP address
  - Works on local network without DNS server
  - Microsoft's replacement for NetBIOS in modern Windows

### 3. SNMP (Simple Network Management Protocol)
- **Port**: UDP 161
- **Purpose**: Printer information and status queries
- **Features**:
  - Provides printer model, status, and capabilities
  - Returns toner levels, page counts
  - Full Printer MIB (RFC 3805) support

### 4. HP JetDirect
- **Port**: TCP 9100
- **Purpose**: Raw printing protocol
- **Features**:
  - Accepts print jobs from Windows
  - Saves jobs to files with metadata
  - Maintains detailed print log
  - Supports PJL commands

### 5. Web Interface
- **Port**: TCP 80
- **Purpose**: Printer management and status
- **Features**:
  - HP Embedded Web Server interface
  - Status, supplies, and network information
  - Looks like authentic HP printer web interface

## Windows Discovery Process

When you use "Add Printer" in Windows, the following happens:

1. **Initial Discovery (WS-Discovery)**
   - Windows sends multicast Probe to 239.255.255.250:3702
   - Simulator responds with printer information and IP address
   - Windows discovers the printer as "HP LaserJet Enterprise M609dn"

2. **Hostname Resolution (LLMNR)**
   - Windows queries for hostname "HPLJ-M609-001"
   - Simulator responds with IP address 192.168.1.100
   - Enables Windows to access printer by name

3. **Printer Information (SNMP)**
   - Windows queries SNMP for printer details
   - Gets model, manufacturer, capabilities, status
   - Used to select correct printer driver

4. **Print Job Submission (JetDirect)**
   - Windows sends print jobs to port 9100
   - Simulator accepts and logs all print data
   - Jobs saved to `print_jobs/` directory

## Setting Up for Windows Discovery

### 1. Configure Firewall

The simulator needs these UDP/TCP ports open:

```bash
sudo ufw allow 80/tcp      # Web interface
sudo ufw allow 161/udp     # SNMP
sudo ufw allow 3702/udp    # WS-Discovery
sudo ufw allow 5355/udp    # LLMNR
sudo ufw allow 9100/tcp    # JetDirect
```

### 2. Start the Printer Simulator

```bash
cd /path/to/iot_simulator
sudo python3 server.py --config config_hp_printer.json start
```

**Note**: Root/sudo required for ports 80 and 161.

### 3. Verify Services are Running

Check that all discovery services are active:

```bash
sudo netstat -tulpn | grep -E '(80|161|3702|5355|9100)'
```

You should see:
```
udp        0      0 0.0.0.0:161        0.0.0.0:*         python3
udp        0      0 0.0.0.0:3702       0.0.0.0:*         python3
udp        0      0 0.0.0.0:5355       0.0.0.0:*         python3
tcp        0      0 0.0.0.0:80         0.0.0.0:*         python3
tcp        0      0 0.0.0.0:9100       0.0.0.0:*         python3
```

### 4. Test Discovery from Windows

#### Method 1: Add Printer Wizard
1. Open **Settings** > **Devices** > **Printers & scanners**
2. Click **Add a printer or scanner**
3. Windows will automatically discover "HP LaserJet Enterprise M609dn"
4. Click on it and follow the wizard
5. Windows will download and install HP driver automatically

#### Method 2: Manual IP Address
1. Click **"The printer that I want isn't listed"**
2. Select **"Add a printer using a TCP/IP address or hostname"**
3. Enter:
   - **Hostname or IP**: 192.168.1.100 (or HPLJ-M609-001)
   - **Port**: 9100
   - **Protocol**: Raw
4. Windows will query the printer and auto-detect model
5. Install driver when prompted

#### Method 3: Command Line
```powershell
# Test WS-Discovery
Test-NetConnection -ComputerName 192.168.1.100 -Port 3702

# Test JetDirect
Test-NetConnection -ComputerName 192.168.1.100 -Port 9100

# Ping hostname
ping HPLJ-M609-001
```

## Print Job Logging

All print jobs sent to the simulator are saved and logged:

### Print Jobs Directory
```
iot_simulator/
  print_jobs/
    job_1_20231201_143022.pdf        # Saved print job files
    job_2_20231201_143155.ps
    job_3_20231201_144301.pcl
    print_log.json                    # Detailed log
```

### Print Log Format
```json
[
  {
    "job_id": 1,
    "timestamp": "2023-12-01T14:30:22.123456",
    "source_ip": "192.168.1.50",
    "source_port": 54321,
    "document_type": "PDF",
    "pages": 3,
    "size_bytes": 45678,
    "filename": "job_1_20231201_143022.pdf",
    "status": "completed"
  }
]
```

### Viewing Print Logs

```bash
# View print log
cat iot_simulator/print_jobs/print_log.json | python3 -m json.tool

# List all print jobs
ls -lh iot_simulator/print_jobs/

# Monitor print jobs in real-time
tail -f iot_simulator/logs/jetdirect_server.log
```

## Troubleshooting Windows Discovery

### Printer Not Appearing in Discovery

1. **Check WS-Discovery service**:
   ```bash
   sudo netstat -an | grep 3702
   tail -f iot_simulator/logs/ws_discovery.log
   ```

2. **Verify multicast is working**:
   ```bash
   # On Linux
   ip maddr show
   
   # On Windows (PowerShell)
   netsh interface ipv4 show joins
   ```

3. **Check firewall**:
   - Ensure UDP 3702 and 5355 are open
   - Check both Linux and Windows firewalls
   - Allow multicast traffic

### Hostname Not Resolving

1. **Test LLMNR**:
   ```bash
   tail -f iot_simulator/logs/llmnr_server.log
   ```

2. **Try IP instead of hostname** in Windows
3. **Check network adapter settings** - LLMNR must be enabled

### Windows Can't Connect to Printer

1. **Verify JetDirect port**:
   ```bash
   nc -zv 192.168.1.100 9100
   telnet 192.168.1.100 9100
   ```

2. **Check printer status** via web interface:
   ```
   http://192.168.1.100/
   ```

3. **Test SNMP**:
   ```bash
   snmpget -v2c -c public 192.168.1.100 1.3.6.1.2.1.1.1.0
   ```

## Advanced Configuration

### Change Printer Identity

Edit `config_hp_printer.json`:

```json
{
  "globals": {
    "system_name": "Your Printer Name",
    "ip": "192.168.1.100",
    "mac": "A0:B3:CC:D4:E5:F6",
    "hostname": "YOUR-PRINTER",
    "uuid": "12345678-90ab-cdef-1234-567890abcdef",
    "model": "HP LaserJet Enterprise M609dn"
  }
}
```

**Important**: UUID should be unique. Generate new one:
```bash
python3 -c "import uuid; print(str(uuid.uuid4()))"
```

### Network Isolation Testing

To test printer discovery on isolated network:

1. **Create virtual network**:
   ```bash
   # Using VirtualBox or VMware
   # Set network adapter to "Internal Network" or "Host-only"
   ```

2. **Configure static IP** on both systems
3. **Disable external DNS** to test LLMNR
4. **Monitor discovery traffic**:
   ```bash
   sudo tcpdump -i any -nn port 3702 or port 5355
   ```

## Protocol Comparison

| Protocol | Port | Transport | Purpose | Windows Version |
|----------|------|-----------|---------|-----------------|
| WS-Discovery | 3702 | UDP Multicast | Device discovery | Vista+ |
| LLMNR | 5355 | UDP Multicast | Name resolution | Vista+ |
| SNMP | 161 | UDP | Device info | All |
| JetDirect | 9100 | TCP | Print jobs | All |
| HTTP | 80 | TCP | Web interface | All |

## Security Considerations

**This is a SIMULATION for testing purposes.**

- No authentication required
- Accepts all print jobs
- Responds to all discovery requests
- Suitable for isolated lab/test networks only
- DO NOT use on production networks

## References

- [MS-WSDISCO]: Web Services Discovery Protocol
- [MS-LLMNR]: Link-Local Multicast Name Resolution
- RFC 3805: Printer MIB v2
- HP JetDirect Protocol Specification
- Windows Print Services Architecture

## Support

For issues or questions:
1. Check logs in `iot_simulator/logs/`
2. Verify all services are running
3. Test each protocol individually
4. Review this documentation

---

**Last Updated**: December 2023  
**Compatible With**: Windows 7, 8, 10, 11, Server 2008+
