# HP Printer Simulator - Windows Discovery Enhancement Summary

## What Was Added

### New Server Components

1. **WS-Discovery Server** (`servers/ws_discovery_server.py`)
   - Port: UDP 3702
   - Multicast group: 239.255.255.250
   - Implements Web Services Discovery protocol
   - Makes printer discoverable by Windows "Add Printer" wizard
   - Sends Hello announcements on startup
   - Responds to Probe and Resolve requests

2. **LLMNR Server** (`servers/llmnr_server.py`)
   - Port: UDP 5355
   - Multicast group: 224.0.0.252
   - Implements Link-Local Multicast Name Resolution
   - Enables hostname resolution without DNS
   - Allows Windows to find printer by name (HPLJ-M609-001)

### Enhanced Existing Components

3. **JetDirect Server** (Enhanced)
   - Now saves ALL print jobs to files
   - Creates `print_jobs/` directory automatically
   - Saves jobs with timestamps and type-specific extensions (.pdf, .ps, .pcl)
   - Maintains detailed JSON log of all print jobs
   - Logs: timestamp, source IP, document type, pages, size, status
   - Better error handling and logging

### Configuration Updates

4. **config_hp_printer.json**
   - Added `uuid` field for WS-Discovery device identification
   - Added WS-Discovery server entry (port 3702)
   - Added LLMNR server entry (port 5355)
   - Now runs 5 server components simultaneously

### Documentation

5. **WINDOWS_DISCOVERY.md**
   - Complete guide to Windows printer discovery
   - Explains all discovery protocols
   - Firewall configuration instructions
   - Step-by-step Windows setup guide
   - Troubleshooting section
   - Print job logging documentation

6. **test_windows_discovery.sh**
   - Automated test script for all discovery protocols
   - Tests connectivity, ports, SNMP, WS-Discovery, LLMNR
   - Submits test print job
   - Color-coded results
   - Detailed output with pass/fail for each test

7. **Updated PRINTER_README.md**
   - Added Windows discovery features section
   - Updated server component list
   - References to new documentation

## How It Works

### Discovery Flow

```
Windows "Add Printer" Wizard
       ↓
1. Sends WS-Discovery Probe (multicast to 239.255.255.250:3702)
       ↓
2. Simulator responds with printer info and IP
       ↓
3. Windows queries hostname via LLMNR (224.0.0.252:5355)
       ↓
4. Simulator responds with IP address
       ↓
5. Windows queries SNMP for printer details (161/udp)
       ↓
6. Simulator provides model, manufacturer, capabilities
       ↓
7. Windows downloads HP driver automatically
       ↓
8. User confirms, printer is added
       ↓
9. Print jobs sent to JetDirect port (9100/tcp)
       ↓
10. Simulator saves jobs and logs metadata
```

### Print Job Handling

When a print job is received:

1. **Receive**: JetDirect server accepts connection on port 9100
2. **Parse**: Detects document type (PDF, PostScript, PCL)
3. **Estimate**: Counts estimated pages
4. **Save**: Writes job to `print_jobs/job_X_TIMESTAMP.ext`
5. **Log**: Appends entry to `print_jobs/print_log.json`
6. **Update**: Increments page counter

Example log entry:
```json
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
```

## Required Ports

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| 80 | TCP | HTTP | Web interface |
| 161 | UDP | SNMP | Printer info queries |
| 3702 | UDP | WS-Discovery | Windows device discovery |
| 5355 | UDP | LLMNR | Hostname resolution |
| 9100 | TCP | JetDirect | Print job submission |

## Firewall Configuration

```bash
# Allow all required ports
sudo ufw allow 80/tcp
sudo ufw allow 161/udp
sudo ufw allow 3702/udp
sudo ufw allow 5355/udp
sudo ufw allow 9100/tcp
```

## Running the Enhanced Simulator

```bash
# Start all services
cd iot_simulator
sudo python3 server.py --config config_hp_printer.json start

# Verify all services
sudo netstat -tulpn | grep -E '(80|161|3702|5355|9100)'

# Test discovery
./test_windows_discovery.sh

# Monitor print jobs
tail -f logs/jetdirect_server.log
tail -f logs/ws_discovery.log

# View print log
cat print_jobs/print_log.json | python3 -m json.tool
```

## Testing from Windows

### Method 1: Automatic Discovery
1. Open **Settings** → **Devices** → **Printers & scanners**
2. Click **Add a printer or scanner**
3. Wait 5-10 seconds
4. "HP LaserJet Enterprise M609dn" should appear
5. Click it and follow wizard

### Method 2: Manual IP
1. Click **"The printer that I want isn't listed"**
2. Select **"Add a printer using a TCP/IP address or hostname"**
3. Enter IP: `192.168.1.100` or hostname: `HPLJ-M609-001`
4. Port: `9100`, Protocol: `Raw`
5. Windows auto-detects model

### Method 3: Command Line Test
```powershell
# Test connectivity
Test-NetConnection -ComputerName 192.168.1.100 -Port 9100

# Resolve hostname
ping HPLJ-M609-001

# Check discovery
Get-Printer -Name "HP*"
```

## File Structure

```
iot_simulator/
├── config_hp_printer.json          # Updated with new servers
├── PRINTER_README.md                # Updated main documentation
├── WINDOWS_DISCOVERY.md             # NEW: Windows discovery guide
├── test_windows_discovery.sh        # NEW: Discovery test script
├── servers/
│   ├── printer_web_server.py        # Fixed CSS rendering
│   ├── snmp_server.py               # Existing
│   ├── jetdirect_server.py          # ENHANCED: Job logging
│   ├── ws_discovery_server.py       # NEW: Windows discovery
│   └── llmnr_server.py              # NEW: Name resolution
├── print_jobs/                      # NEW: Print job storage
│   ├── job_1_20231201_143022.pdf    # Saved print jobs
│   ├── job_2_20231201_143155.ps
│   └── print_log.json               # Job metadata log
└── logs/                            # Server logs
    ├── jetdirect_server.log
    ├── ws_discovery.log
    └── llmnr_server.log
```

## Key Improvements

✅ **Full Windows compatibility** - Printer appears in Add Printer wizard automatically  
✅ **No DNS required** - LLMNR handles hostname resolution  
✅ **Print job persistence** - All jobs saved with metadata  
✅ **Complete logging** - Track every print job with details  
✅ **Professional appearance** - Fixed CSS, looks like real HP printer  
✅ **Easy testing** - Automated test script validates everything  
✅ **Comprehensive docs** - Complete setup and troubleshooting guides  

## Security Note

**This is a simulation for testing purposes only.**

- No authentication required
- Accepts all print jobs from any source
- Responds to all discovery requests
- Suitable for isolated lab/test environments only
- **DO NOT deploy on production networks**

## Troubleshooting Quick Reference

**Printer not appearing in Windows:**
- Check WS-Discovery service is running (port 3702)
- Verify firewall allows UDP 3702 and 5355
- Ensure multicast is enabled on network interface

**Hostname not resolving:**
- Check LLMNR service is running (port 5355)
- Verify Windows LLMNR is enabled
- Try using IP address instead

**Print jobs not saving:**
- Check `print_jobs/` directory exists and is writable
- Review `logs/jetdirect_server.log` for errors
- Ensure sufficient disk space

**Web interface CSS not loading:**
- Now fixed in `printer_web_server.py`
- Clear browser cache
- Verify HTTP service on port 80

## Next Steps

1. **Start the simulator** with enhanced configuration
2. **Run test script** to verify all protocols
3. **Add printer in Windows** to test discovery
4. **Send test print job** and verify it's saved
5. **Review print logs** in `print_jobs/print_log.json`

---

**Total Enhancement:**
- 2 new server components
- 1 enhanced server component
- 3 new documentation files
- 1 new test script
- 1 new print job logging system
- Complete Windows discovery support
