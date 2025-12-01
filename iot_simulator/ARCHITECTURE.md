# HP Printer Simulator Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    HP PRINTER SIMULATOR                          │
│                 (HP LaserJet Enterprise M609dn)                  │
│                                                                   │
│  IP: 192.168.1.100                                               │
│  MAC: A0:B3:CC:D4:E5:F6                                          │
│  Hostname: HPLJ-M609-001                                         │
│  UUID: 12345678-90ab-cdef-1234-567890abcdef                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   Windows    │    │    Linux     │      │   macOS      │
│   Clients    │    │   Clients    │      │   Clients    │
└──────────────┘    └──────────────┘      └──────────────┘
```

## Network Services Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Server Components                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  WS-Discovery Server (UDP 3702)                             │    │
│  │  • Multicast: 239.255.255.250                               │    │
│  │  • Sends Hello announcements                                │    │
│  │  • Responds to Probe/Resolve                                │    │
│  │  • Purpose: Windows printer discovery                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  LLMNR Server (UDP 5355)                                    │    │
│  │  • Multicast: 224.0.0.252                                   │    │
│  │  • Resolves hostname to IP                                  │    │
│  │  • Purpose: Name resolution without DNS                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SNMP Server (UDP 161)                                      │    │
│  │  • Community: public                                        │    │
│  │  • MIB-II support                                           │    │
│  │  • Printer MIB (RFC 3805)                                   │    │
│  │  • HP Enterprise OIDs                                       │    │
│  │  • Purpose: Device information                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  JetDirect Server (TCP 9100)                                │    │
│  │  • Raw printing protocol                                    │    │
│  │  • PJL command support                                      │    │
│  │  • Print job acceptance                                     │    │
│  │  • Job logging to files                                     │    │
│  │  • Purpose: Print job submission                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Web Server (TCP 80)                                        │    │
│  │  • HP Embedded Web Server UI                                │    │
│  │  • Status, Supplies, Network pages                          │    │
│  │  • Device Info, Print Quality                               │    │
│  │  • Purpose: Web-based management                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Windows Discovery Flow

```
┌───────────────┐
│   Windows PC  │
└───────┬───────┘
        │
        │ 1. Send WS-Discovery Probe
        │    Multicast to 239.255.255.250:3702
        ▼
┌───────────────────────┐
│  WS-Discovery Server  │
│  (UDP 3702)           │
└───────┬───────────────┘
        │
        │ 2. Reply with ProbeMatch
        │    Device: HP LaserJet Enterprise M609dn
        │    Address: urn:uuid:12345678-...
        │    XAddrs: http://192.168.1.100:5357/WSDPrinter
        ▼
┌───────────────┐
│   Windows PC  │
└───────┬───────┘
        │
        │ 3. Resolve hostname via LLMNR
        │    Query: HPLJ-M609-001
        │    Multicast to 224.0.0.252:5355
        ▼
┌───────────────────────┐
│   LLMNR Server        │
│   (UDP 5355)          │
└───────┬───────────────┘
        │
        │ 4. Reply with IP address
        │    HPLJ-M609-001 = 192.168.1.100
        ▼
┌───────────────┐
│   Windows PC  │
└───────┬───────┘
        │
        │ 5. SNMP query for printer info
        │    snmpget -v2c -c public 192.168.1.100 ...
        ▼
┌───────────────────────┐
│   SNMP Server         │
│   (UDP 161)           │
└───────┬───────────────┘
        │
        │ 6. Reply with printer details
        │    Model: HP LaserJet Enterprise M609dn
        │    Manufacturer: Hewlett-Packard
        │    Serial: JPBCS12345
        ▼
┌───────────────┐
│   Windows PC  │
│               │
│ Downloads HP  │
│ driver auto   │
│               │
│ ✓ Printer     │
│   Added!      │
└───────────────┘
```

## Print Job Flow

```
┌───────────────┐
│   Application │
│  (Word, PDF)  │
└───────┬───────┘
        │
        │ Print command
        ▼
┌───────────────┐
│ Windows Print │
│   Spooler     │
└───────┬───────┘
        │
        │ Convert to printer format
        │ (PCL, PostScript, or PDF)
        ▼
┌───────────────┐
│  HP Printer   │
│   Driver      │
└───────┬───────┘
        │
        │ TCP connection to port 9100
        │ Send print job data
        ▼
┌───────────────────────┐
│  JetDirect Server     │
│  (TCP 9100)           │
└───────┬───────────────┘
        │
        ├─→ Detect document type (PDF/PS/PCL)
        ├─→ Estimate page count
        ├─→ Save to file: print_jobs/job_X_TIMESTAMP.ext
        ├─→ Create log entry
        └─→ Update print_log.json
            
┌──────────────────────────────────────┐
│  print_jobs/                         │
│  ├── job_1_20231201_143022.pdf       │
│  ├── job_2_20231201_143155.ps        │
│  ├── job_3_20231201_144301.pcl       │
│  └── print_log.json                  │
│      [{                              │
│        "job_id": 1,                  │
│        "timestamp": "2023-12-01...", │
│        "source_ip": "192.168.1.50",  │
│        "document_type": "PDF",       │
│        "pages": 3,                   │
│        "size_bytes": 45678,          │
│        "status": "completed"         │
│      }]                              │
└──────────────────────────────────────┘
```

## File System Structure

```
iot_simulator/
│
├── server.py                       # Main daemon controller
├── core_logger.py                  # Logging system
│
├── config_hp_printer.json          # Printer configuration
│
├── servers/                        # Server implementations
│   ├── shared.py                   # Common utilities
│   ├── printer_web_server.py       # HTTP server (port 80)
│   ├── snmp_server.py              # SNMP server (port 161)
│   ├── jetdirect_server.py         # JetDirect (port 9100)
│   ├── ws_discovery_server.py      # WS-Discovery (port 3702)
│   └── llmnr_server.py             # LLMNR (port 5355)
│
├── print_jobs/                     # Print job storage (created at runtime)
│   ├── job_*.pdf                   # Saved print jobs
│   ├── job_*.ps
│   ├── job_*.pcl
│   └── print_log.json              # Job metadata
│
├── logs/                           # Server logs (created at runtime)
│   ├── printer_web_server.log
│   ├── snmp_server.log
│   ├── jetdirect_server.log
│   ├── ws_discovery.log
│   └── llmnr_server.log
│
└── Documentation/
    ├── PRINTER_README.md           # Main documentation
    ├── WINDOWS_DISCOVERY.md        # Windows setup guide
    ├── WINDOWS_ENHANCEMENT_SUMMARY.md
    └── test_windows_discovery.sh   # Test script
```

## Protocol Port Map

```
┌─────────────────────────────────────────────────────────┐
│                      Network Ports                       │
├────────┬─────────┬────────────┬──────────────────────────┤
│  Port  │  Proto  │  Service   │  Purpose                 │
├────────┼─────────┼────────────┼──────────────────────────┤
│   80   │  TCP    │  HTTP      │  Web interface           │
│  161   │  UDP    │  SNMP      │  Device queries          │
│  3702  │  UDP    │  WS-Disc   │  Windows discovery       │
│  5355  │  UDP    │  LLMNR     │  Name resolution         │
│  9100  │  TCP    │  JetDirect │  Print jobs              │
└────────┴─────────┴────────────┴──────────────────────────┘
```

## Multicast Groups

```
┌─────────────────────────────────────────────────────────┐
│               Multicast Subscriptions                    │
├──────────────────┬──────────┬──────────────────────────┤
│  Address         │  Port    │  Service                 │
├──────────────────┼──────────┼──────────────────────────┤
│ 239.255.255.250  │  3702    │  WS-Discovery            │
│ 224.0.0.252      │  5355    │  LLMNR                   │
└──────────────────┴──────────┴──────────────────────────┘
```

## Data Flow Summary

```
Discovery:  Windows → WS-Discovery (3702) → Printer Found
Naming:     Windows → LLMNR (5355) → IP Resolution
Info:       Windows → SNMP (161) → Printer Details
Web:        Browser → HTTP (80) → Management UI
Printing:   App → Windows → Driver → JetDirect (9100) → File Storage
```

## Component Dependencies

```
┌─────────────────┐
│  server.py      │  Main controller
└────────┬────────┘
         │
         ├──→ core_logger.py          (Logging)
         │
         ├──→ config_hp_printer.json  (Configuration)
         │
         └──→ servers/
              │
              ├──→ shared.py           (Common utilities)
              │
              ├──→ printer_web_server.py   (Web UI)
              │
              ├──→ snmp_server.py          (SNMP)
              │
              ├──→ jetdirect_server.py     (Printing)
              │     └──→ print_jobs/       (Storage)
              │
              ├──→ ws_discovery_server.py  (Discovery)
              │
              └──→ llmnr_server.py         (Name resolution)
```

## Security Boundaries

```
┌────────────────────────────────────────────────────────┐
│              TESTING ENVIRONMENT ONLY                  │
│                                                        │
│  ⚠️  NO AUTHENTICATION                                 │
│  ⚠️  NO ENCRYPTION                                     │
│  ⚠️  ACCEPTS ALL CONNECTIONS                           │
│  ⚠️  DO NOT USE IN PRODUCTION                          │
│                                                        │
│  Suitable for:                                         │
│  ✓ Isolated lab networks                              │
│  ✓ Virtual machines                                   │
│  ✓ Testing and development                            │
│  ✓ Security research                                  │
└────────────────────────────────────────────────────────┘
```
