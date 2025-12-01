# Server.py Configuration File Usage Guide

## Overview

The `server.py` daemon has been updated to support multiple configuration files, allowing you to easily switch between different device simulations (e.g., medical device, HP printer, etc.) without modifying files.

## New Features

### 1. **Custom Configuration File Support**
You can now specify which configuration file to use via command-line argument:

```bash
python3 server.py start --config config_hp_printer.json
```

### 2. **Status Command**
New `status` command to check if the daemon is running:

```bash
python3 server.py status
```

### 3. **Improved Help**
Built-in help with examples:

```bash
python3 server.py --help
```

## Command Reference

### Start with Default Config
```bash
# Uses config.json by default
python3 server.py start
```

### Start with Custom Config
```bash
# HP Printer simulation
python3 server.py start --config config_hp_printer.json

# Medical device simulation (original)
python3 server.py start --config config.json

# Any custom config file
python3 server.py start --config my_custom_config.json
```

### Check Status
```bash
python3 server.py status
```

**Output:**
```
Daemon is running with PID 12345
Running 3 subprocess(es):
  - PID 12346: Running
  - PID 12347: Running
  - PID 12348: Running
```

### Stop Daemon
```bash
python3 server.py stop
```

### Restart with Different Config
```bash
# Stop current daemon and start with new config
python3 server.py restart --config config_hp_printer.json
```

## Usage Examples

### Example 1: Switch Between Device Types

```bash
# Start with medical device (MULTIX)
python3 server.py start --config config.json

# Later, switch to HP printer
python3 server.py stop
python3 server.py start --config config_hp_printer.json

# Or use restart
python3 server.py restart --config config_hp_printer.json
```

### Example 2: Test Multiple Configurations

```bash
# Test HP printer config
python3 server.py start --config config_hp_printer.json
# ... do testing ...
python3 server.py stop

# Test medical device config
python3 server.py start --config config.json
# ... do testing ...
python3 server.py stop
```

### Example 3: Run Different Configs in Sequence

```bash
#!/bin/bash
# Test script to validate all configurations

configs=("config.json" "config_hp_printer.json")

for config in "${configs[@]}"; do
    echo "Testing $config..."
    python3 server.py start --config "$config"
    sleep 5
    python3 server.py status
    # Run tests here...
    python3 server.py stop
    sleep 2
done
```

## Command-Line Arguments

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `start` | Start the daemon |
| `stop` | Stop the daemon |
| `restart` | Restart the daemon |
| `status` | Check daemon status |

### Optional Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--config` | `-c` | Path to configuration file | `config.json` |
| `--help` | `-h` | Show help message | - |

## Configuration File Format

All configuration files should follow this format:

```json
{
  "globals": {
    "system_name": "Device Name",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "hostname": "DEVICE-001",
    "serial": "SN123456",
    ...
  },
  "servers": [
    {
      "path": "servers/server_name.py",
      "port": 80
    },
    ...
  ]
}
```

## Error Handling

### Configuration File Not Found
```bash
$ python3 server.py start --config missing.json
[ERROR] Configuration file not found: missing.json
```

### Invalid JSON
```bash
$ python3 server.py start --config bad.json
[ERROR] Invalid JSON in config file: Expecting ',' delimiter: line 5 column 3 (char 123)
```

### Daemon Already Running
```bash
$ python3 server.py start
Daemon already running.
```

## Integration with System Impersonation

When using the HP printer simulator with system impersonation:

```bash
# Step 1: Configure system identity
sudo ./impersonate_hp_printer.sh start

# Step 2: Start simulator with HP config
sudo python3 server.py start --config config_hp_printer.json

# Step 3: Verify everything
sudo python3 server.py status
sudo ./test_printer_simulator.sh
```

## Best Practices

### 1. **Use Descriptive Config Names**
```bash
config_hp_printer.json           # HP LaserJet printer
config_siemens_multix.json       # Siemens medical device
config_cisco_switch.json         # Network switch
```

### 2. **Keep Default Config Generic**
Use `config.json` as a template or default device:
```bash
cp config_hp_printer.json config.json
python3 server.py start  # Uses config.json
```

### 3. **Test Configs Before Deployment**
```bash
# Validate JSON syntax
python3 -m json.tool config_hp_printer.json

# Start in foreground for testing (modify start() to skip fork)
python3 server.py start --config config_hp_printer.json
```

### 4. **Document Your Configs**
Add a README or comment in each config:
```json
{
  "_comment": "HP LaserJet Enterprise M609dn - Production Config",
  "globals": {
    ...
  }
}
```

## Troubleshooting

### Can't Switch Configs?
Make sure to stop the daemon first:
```bash
python3 server.py stop
python3 server.py start --config new_config.json
```

### Services Not Starting?
Check the logs:
```bash
tail -f logs/*.err
tail -f logs/*.out
```

### Stale PID File?
```bash
# If daemon shows running but isn't
python3 server.py stop  # Cleans up PID files
python3 server.py start --config config.json
```

### Need to Force Stop?
```bash
# Kill all related processes
pkill -f server.py
rm -f my_daemon.pid my_daemon_subprocesses.pid
```

## Advanced Usage

### Scripting with Different Configs

```bash
#!/bin/bash
# rotate_device_simulations.sh

devices=("config_hp_printer.json" "config.json")
interval=3600  # 1 hour

for device in "${devices[@]}"; do
    echo "Starting simulation: $device"
    sudo python3 server.py start --config "$device"
    
    echo "Running for ${interval} seconds..."
    sleep $interval
    
    echo "Stopping simulation"
    sudo python3 server.py stop
    sleep 5
done
```

### Dynamic Config Selection

```bash
#!/bin/bash
# select_device.sh

echo "Select device to simulate:"
echo "1) HP Printer"
echo "2) Siemens Medical Device"
echo "3) Custom"

read -p "Choice: " choice

case $choice in
    1) config="config_hp_printer.json" ;;
    2) config="config.json" ;;
    3) read -p "Enter config file: " config ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

sudo python3 server.py start --config "$config"
```

## Backwards Compatibility

The default behavior is preserved:

```bash
# Old way still works (uses config.json)
python3 server.py start
python3 server.py stop
python3 server.py restart

# New way with explicit config
python3 server.py start --config config.json
```

## Help Output

```bash
$ python3 server.py --help

usage: server.py [-h] [--config CONFIG] {start,stop,restart,status}

IoT Device Simulator Daemon

positional arguments:
  {start,stop,restart,status}
                        Action to perform: start, stop, restart, or status

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Path to configuration file (default: config.json)

Examples:
  # Start with default config.json
  python server.py start
  
  # Start with custom config file
  python server.py start --config config_hp_printer.json
  
  # Stop the daemon
  python server.py stop
  
  # Restart with different config
  python server.py restart --config config_hp_printer.json
```

## Summary

The updated `server.py` provides:
- ✅ Flexible configuration file selection
- ✅ Status checking capability
- ✅ Better error handling and validation
- ✅ Backwards compatibility
- ✅ Improved help and documentation
- ✅ Easy switching between device simulations

This makes it simple to manage multiple device simulations and switch between them as needed!
