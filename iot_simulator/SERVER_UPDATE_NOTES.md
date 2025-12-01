# Server.py Update - Configuration File Support

## Summary of Changes

The `server.py` daemon has been enhanced to support **multiple configuration files**, making it easy to switch between different device simulations without modifying files.

## What Changed

### 1. **Added argparse for Command-Line Arguments**
- Replaced simple argument parsing with `argparse` module
- Added `--config` / `-c` parameter for specifying configuration files
- Added built-in help with examples

### 2. **Enhanced load_config() Function**
- Now accepts optional `config_file` parameter
- Validates file existence before loading
- Provides clear error messages for missing or invalid files
- Logs which configuration file is being used

### 3. **Added status Command**
- New command to check if daemon is running
- Shows PID of main daemon
- Lists all subprocess PIDs and their status

### 4. **Updated start() and restart() Functions**
- Both now accept `config_file` parameter
- Automatically passes config selection to daemon process

### 5. **Improved Error Handling**
- File not found errors
- Invalid JSON parsing errors
- Stale PID file detection

## New Usage Examples

### Before (Old Way)
```bash
# Had to manually copy config files
cp config_hp_printer.json config.json
sudo python3 server.py start

# To switch devices
sudo python3 server.py stop
cp config.json config.json
sudo python3 server.py start
```

### After (New Way)
```bash
# Start directly with any config
sudo python3 server.py start --config config_hp_printer.json

# Switch devices easily
sudo python3 server.py restart --config config.json

# Check status
sudo python3 server.py status
```

## Backwards Compatibility

✅ **Fully backwards compatible** - existing usage still works:

```bash
# Old commands still work (uses config.json by default)
python3 server.py start
python3 server.py stop
python3 server.py restart
```

## Benefits

### 1. **No File Copying Required**
- Keep multiple configs without overwriting `config.json`
- Each config maintains its original name

### 2. **Easy Device Switching**
```bash
# Medical device
sudo python3 server.py start --config config.json

# HP Printer
sudo python3 server.py restart --config config_hp_printer.json

# Custom device
sudo python3 server.py restart --config config_custom.json
```

### 3. **Better Testing Workflow**
```bash
# Test multiple configurations in sequence
for config in config*.json; do
    echo "Testing $config..."
    sudo python3 server.py start --config "$config"
    # Run tests...
    sudo python3 server.py stop
done
```

### 4. **Clearer Status Reporting**
```bash
$ sudo python3 server.py status
Daemon is running with PID 12345
Running 3 subprocess(es):
  - PID 12346: Running
  - PID 12347: Running
  - PID 12348: Running
```

### 5. **Better Error Messages**
```bash
$ sudo python3 server.py start --config missing.json
[ERROR] Configuration file not found: missing.json

$ sudo python3 server.py start --config bad.json
[ERROR] Invalid JSON in config file: Expecting ',' delimiter: line 5 column 3
```

## Command Reference

### All Available Commands

```bash
# Start with specific config
python3 server.py start --config <file>

# Start with default config
python3 server.py start

# Stop daemon
python3 server.py stop

# Restart with new config
python3 server.py restart --config <file>

# Check status
python3 server.py status

# Get help
python3 server.py --help
```

## Updated Scripts

The following scripts have been updated to use the new functionality:

### 1. **setup_hp_printer.sh**
```bash
# Now uses --config parameter directly
python3 server.py start --config config_hp_printer.json
```

### 2. **Documentation Updates**
- `PRINTER_README.md` - Updated usage examples
- `QUICK_REFERENCE.md` - Updated command reference
- `SERVER_USAGE.md` - New comprehensive guide

## Integration Examples

### With System Impersonation
```bash
# HP Printer setup
sudo ./impersonate_hp_printer.sh start
sudo python3 server.py start --config config_hp_printer.json

# Medical device setup
sudo ./impersonate_hp_printer.sh stop
sudo python3 server.py restart --config config.json
```

### Automated Testing
```bash
#!/bin/bash
# test_all_configs.sh

configs=(
    "config.json"
    "config_hp_printer.json"
)

for config in "${configs[@]}"; do
    echo "Testing $config..."
    sudo python3 server.py start --config "$config"
    
    # Wait for services to start
    sleep 5
    
    # Run tests
    sudo ./test_printer_simulator.sh
    
    # Stop
    sudo python3 server.py stop
    sleep 2
done
```

### Development Workflow
```bash
# Develop and test new device config
nano config_new_device.json

# Test it
sudo python3 server.py start --config config_new_device.json

# Check logs
tail -f logs/*.out

# If issues, stop and fix
sudo python3 server.py stop
nano config_new_device.json

# Try again
sudo python3 server.py start --config config_new_device.json
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

## Files Modified

1. **server.py** - Core daemon script
   - Added `argparse` import
   - Enhanced `load_config()` with parameter
   - Updated `start()` and `restart()` functions
   - Added `status()` function
   - Added `parse_arguments()` function

2. **setup_hp_printer.sh** - Quick setup script
   - Updated to use `--config config_hp_printer.json`
   - Removed unnecessary config file copying

3. **Documentation** - Multiple files updated
   - `PRINTER_README.md`
   - `QUICK_REFERENCE.md`
   - `SERVER_USAGE.md` (new)

## Testing

Test the new functionality:

```bash
# Test help
python3 server.py --help

# Test with HP printer config
sudo python3 server.py start --config config_hp_printer.json
sudo python3 server.py status

# Test default config
sudo python3 server.py restart
sudo python3 server.py status

# Test stop
sudo python3 server.py stop
sudo python3 server.py status

# Test error handling
python3 server.py start --config nonexistent.json
```

## Recommendations

### Naming Convention
Use descriptive names for configs:
```
config.json                      # Default/original device
config_hp_printer.json           # HP LaserJet printer
config_hp_color.json             # HP Color printer
config_siemens_multix.json       # Siemens medical device
config_cisco_switch.json         # Cisco network switch
```

### Documentation
Add comments to your configs:
```json
{
  "_description": "HP LaserJet Enterprise M609dn - Production Config",
  "_created": "2025-12-01",
  "_author": "IT Security Team",
  "globals": {
    ...
  }
}
```

### Version Control
Keep all configs in version control:
```bash
git add config*.json
git commit -m "Add multiple device configurations"
```

## Future Enhancements

Potential future improvements:
- [ ] List available config files: `python3 server.py list`
- [ ] Validate config before starting: `python3 server.py validate --config file.json`
- [ ] Config templates: `python3 server.py create --template printer`
- [ ] Hot reload: `python3 server.py reload --config new.json`

## Summary

✅ **Flexible Configuration**: Specify any config file at runtime  
✅ **Easy Switching**: Change device types without file manipulation  
✅ **Better Status**: New status command shows running state  
✅ **Backwards Compatible**: Existing usage patterns still work  
✅ **Improved Errors**: Clear error messages for common issues  
✅ **Enhanced Testing**: Easier to test multiple configurations  

The updated `server.py` makes managing multiple device simulations simple and efficient!
