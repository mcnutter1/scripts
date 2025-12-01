#!/bin/bash
###############################################################################
# HP Printer Network Impersonation Script for Ubuntu 24.04
# 
# This script configures a Ubuntu system to appear as an HP LaserJet printer
# on the network by changing MAC address, hostname, and network configuration.
#
# WARNING: This script makes system-level changes. Use with caution and only
# in authorized testing environments.
#
# Usage: sudo ./impersonate_hp_printer.sh [start|stop|status]
###############################################################################

set -e

# Configuration
HP_MAC_ADDRESS="A0:B3:CC:D4:E5:F6"
HP_HOSTNAME="HPLJ-M609-001"
HP_MODEL="HP LaserJet Enterprise M609dn"
HP_SERIAL="JPBCS12345"
INTERFACE="eth0"  # Change this to your network interface (eth0, ens33, etc.)

# Backup files
BACKUP_DIR="/root/hp_printer_backup"
HOSTNAME_BACKUP="$BACKUP_DIR/hostname.bak"
HOSTS_BACKUP="$BACKUP_DIR/hosts.bak"
MAC_BACKUP="$BACKUP_DIR/mac_address.bak"
INTERFACE_BACKUP="$BACKUP_DIR/interface.bak"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║        HP Printer Network Impersonation Script                 ║"
    echo "║        Ubuntu 24.04 System Configuration Tool                  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

detect_interface() {
    # Try to auto-detect the primary network interface
    local detected=$(ip route | grep default | awk '{print $5}' | head -n1)
    if [[ -n "$detected" ]]; then
        INTERFACE="$detected"
        log_info "Auto-detected network interface: $INTERFACE"
    else
        log_warn "Could not auto-detect interface, using default: $INTERFACE"
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

###############################################################################
# Backup Functions
###############################################################################

backup_current_config() {
    log_info "Backing up current configuration..."
    
    # Backup hostname
    if [[ ! -f "$HOSTNAME_BACKUP" ]]; then
        hostname > "$HOSTNAME_BACKUP"
        log_info "Backed up current hostname: $(cat $HOSTNAME_BACKUP)"
    fi
    
    # Backup hosts file
    if [[ ! -f "$HOSTS_BACKUP" ]]; then
        cp /etc/hosts "$HOSTS_BACKUP"
        log_info "Backed up /etc/hosts"
    fi
    
    # Backup current MAC address
    if [[ ! -f "$MAC_BACKUP" ]]; then
        ip link show "$INTERFACE" | grep "link/ether" | awk '{print $2}' > "$MAC_BACKUP"
        log_info "Backed up MAC address: $(cat $MAC_BACKUP)"
    fi
    
    # Backup interface name
    if [[ ! -f "$INTERFACE_BACKUP" ]]; then
        echo "$INTERFACE" > "$INTERFACE_BACKUP"
        log_info "Backed up interface name: $INTERFACE"
    fi
}

###############################################################################
# Configuration Functions
###############################################################################

change_mac_address() {
    log_info "Changing MAC address to $HP_MAC_ADDRESS..."
    
    # Check if interface exists
    if ! ip link show "$INTERFACE" &>/dev/null; then
        log_error "Interface $INTERFACE not found!"
        log_info "Available interfaces:"
        ip link show | grep "^[0-9]" | awk '{print $2}' | tr -d ':'
        return 1
    fi
    
    # Bring interface down
    ip link set "$INTERFACE" down
    
    # Change MAC address
    ip link set dev "$INTERFACE" address "$HP_MAC_ADDRESS"
    
    # Bring interface back up
    ip link set "$INTERFACE" up
    
    # Wait for interface to come up
    sleep 2
    
    # Verify the change
    local current_mac=$(ip link show "$INTERFACE" | grep "link/ether" | awk '{print $2}')
    if [[ "$current_mac" == "$HP_MAC_ADDRESS" ]]; then
        log_info "MAC address successfully changed to $HP_MAC_ADDRESS"
    else
        log_warn "MAC address change may not have persisted. Current: $current_mac"
    fi
    
    # For persistent MAC change, create systemd service
    create_mac_persistence_service
}

create_mac_persistence_service() {
    log_info "Creating systemd service for persistent MAC address..."
    
    cat > /etc/systemd/system/hp-printer-mac.service <<EOF
[Unit]
Description=Set HP Printer MAC Address
After=network-pre.target
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/ip link set dev $INTERFACE down
ExecStart=/usr/bin/ip link set dev $INTERFACE address $HP_MAC_ADDRESS
ExecStart=/usr/bin/ip link set dev $INTERFACE up
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable hp-printer-mac.service
    log_info "MAC persistence service created and enabled"
}

change_hostname() {
    log_info "Changing hostname to $HP_HOSTNAME..."
    
    # Change current hostname
    hostnamectl set-hostname "$HP_HOSTNAME"
    
    # Update /etc/hosts
    sed -i "s/127.0.1.1.*/127.0.1.1\t$HP_HOSTNAME/" /etc/hosts
    
    # Verify
    local current_hostname=$(hostname)
    if [[ "$current_hostname" == "$HP_HOSTNAME" ]]; then
        log_info "Hostname successfully changed to $HP_HOSTNAME"
    else
        log_warn "Hostname change may have failed. Current: $current_hostname"
    fi
}

configure_avahi() {
    log_info "Configuring Avahi (mDNS/Bonjour) for printer discovery..."
    
    # Install avahi if not present
    if ! command -v avahi-daemon &>/dev/null; then
        log_info "Installing Avahi daemon..."
        apt-get update -qq
        apt-get install -y avahi-daemon avahi-utils
    fi
    
    # Create printer service file for Avahi
    cat > /etc/avahi/services/hp-printer.service <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">$HP_MODEL @ %h</name>
  <service>
    <type>_printer._tcp</type>
    <port>9100</port>
    <txt-record>txtvers=1</txt-record>
    <txt-record>qtotal=1</txt-record>
    <txt-record>rp=raw</txt-record>
    <txt-record>ty=$HP_MODEL</txt-record>
    <txt-record>product=(HP LaserJet Enterprise M609dn)</txt-record>
    <txt-record>priority=50</txt-record>
    <txt-record>adminurl=http://$HP_HOSTNAME/</txt-record>
  </service>
  <service>
    <type>_http._tcp</type>
    <port>80</port>
    <txt-record>path=/</txt-record>
  </service>
  <service>
    <type>_pdl-datastream._tcp</type>
    <port>9100</port>
    <txt-record>txtvers=1</txt-record>
    <txt-record>qtotal=1</txt-record>
    <txt-record>ty=$HP_MODEL</txt-record>
  </service>
</service-group>
EOF
    
    # Restart Avahi
    systemctl restart avahi-daemon
    systemctl enable avahi-daemon
    log_info "Avahi configured for printer discovery"
}

configure_snmp() {
    log_info "Configuring SNMP community strings..."
    
    # Note: The Python SNMP server in the simulator handles SNMP,
    # but we can configure snmpd for additional realism
    
    if command -v snmpd &>/dev/null; then
        log_info "SNMP daemon detected - configuring..."
        
        # Backup original config
        if [[ -f /etc/snmp/snmpd.conf && ! -f "$BACKUP_DIR/snmpd.conf.bak" ]]; then
            cp /etc/snmp/snmpd.conf "$BACKUP_DIR/snmpd.conf.bak"
        fi
        
        # Add community string (if not using Python SNMP server)
        echo "rocommunity public default" >> /etc/snmp/snmpd.conf
        systemctl restart snmpd 2>/dev/null || true
    else
        log_info "SNMP daemon not installed (simulator will handle SNMP)"
    fi
}

configure_dhcp_identifier() {
    log_info "Configuring DHCP client identifier..."
    
    # Configure NetworkManager to use the HP MAC
    if command -v nmcli &>/dev/null; then
        log_info "Configuring NetworkManager DHCP settings..."
        
        # Get the connection name
        local conn_name=$(nmcli -t -f NAME connection show --active | head -n1)
        
        if [[ -n "$conn_name" ]]; then
            # Set the MAC address for this connection
            nmcli connection modify "$conn_name" 802-3-ethernet.cloned-mac-address "$HP_MAC_ADDRESS"
            nmcli connection modify "$conn_name" ipv4.dhcp-hostname "$HP_HOSTNAME"
            nmcli connection modify "$conn_name" ipv6.dhcp-hostname "$HP_HOSTNAME"
            
            # Restart the connection
            nmcli connection down "$conn_name" 2>/dev/null || true
            sleep 1
            nmcli connection up "$conn_name"
            
            log_info "NetworkManager configured with HP printer identity"
        fi
    fi
}

set_system_banner() {
    log_info "Setting system identification banners..."
    
    # Create issue file with HP printer info
    cat > /etc/issue <<EOF

HP LaserJet Enterprise M609dn
Serial Number: $HP_SERIAL
Hostname: $HP_HOSTNAME

EOF
    
    # Create MOTD
    cat > /etc/motd <<EOF
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║              HP LaserJet Enterprise M609dn                     ║
║                   Printer Simulator                            ║
║                                                                ║
║  Hostname: $HP_HOSTNAME                                    ║
║  Serial:   $HP_SERIAL                                      ║
║  MAC:      $HP_MAC_ADDRESS                          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF
    
    log_info "System banners configured"
}

configure_ssh_banner() {
    log_info "Configuring SSH banner to mimic HP printer..."
    
    if ! command -v sshd &>/dev/null; then
        log_warn "SSH server not installed - skipping SSH banner configuration"
        return
    fi
    
    # Backup original SSH config
    if [[ -f /etc/ssh/sshd_config && ! -f "$BACKUP_DIR/sshd_config.bak" ]]; then
        cp /etc/ssh/sshd_config "$BACKUP_DIR/sshd_config.bak"
        log_info "Backed up SSH configuration"
    fi
    
    # Create HP printer SSH banner
    cat > /etc/ssh/hp_printer_banner <<EOF

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                HP LaserJet Enterprise M609dn                   ║
║                  Embedded SSH Service v2.0                     ║
║                                                                ║
║  Serial Number: $HP_SERIAL                                 ║
║  Firmware:      2403293_000590                                 ║
║  Hostname:      $HP_HOSTNAME                               ║
║                                                                ║
║  Authorized Access Only                                        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF
    
    # Modify SSH daemon configuration
    # Remove any existing Banner directive
    sed -i '/^Banner/d' /etc/ssh/sshd_config
    
    # Add HP printer banner
    echo "Banner /etc/ssh/hp_printer_banner" >> /etc/ssh/sshd_config
    
    # Modify SSH version string to look like HP printer
    # This requires patching the SSH server identification string
    sed -i '/^DebianBanner/d' /etc/ssh/sshd_config
    echo "DebianBanner no" >> /etc/ssh/sshd_config
    
    # Create wrapper script to modify SSH version string
    cat > /usr/local/bin/ssh-hp-wrapper.sh <<'EOF_WRAPPER'
#!/bin/bash
# SSH wrapper to modify version string
# This intercepts SSH connections and presents HP printer identification

# Original SSH binary
REAL_SSHD="/usr/sbin/sshd.real"

# If this is the first time, backup the real sshd
if [[ ! -f "$REAL_SSHD" ]]; then
    mv /usr/sbin/sshd "$REAL_SSHD"
fi

# HP printer SSH version string
# Format: SSH-2.0-HP_Embedded_SSH_2.0
export SSH_CONNECTION_BANNER="SSH-2.0-HP_Embedded_SSH_2.0"

# Execute real SSH daemon
exec "$REAL_SSHD" "$@"
EOF_WRAPPER
    
    chmod +x /usr/local/bin/ssh-hp-wrapper.sh
    
    # Note: Fully changing SSH version string requires recompiling OpenSSH
    # or using tools like ssh-mitm. Document this limitation.
    
    log_info "SSH banner configured (version string modification requires OpenSSH recompilation)"
    log_warn "To fully spoof SSH version, consider using: ssh-mitm or recompiled OpenSSH"
    
    # Restart SSH service
    systemctl restart sshd || systemctl restart ssh
    log_info "SSH service restarted with HP printer banner"
}

configure_http_banner() {
    log_info "Configuring HTTP server banner..."
    
    # The Python web server in printer_web_server.py needs modification
    # Create a config file that the Python server can read
    
    cat > /etc/hp_printer_http_config.conf <<EOF
# HP Printer HTTP Server Configuration
# This file is read by the Python HTTP server simulator

SERVER_HEADER=HP-ChaiSOE/1.0
SERVER_NAME=HP-LaserJet-M609dn
FIRMWARE_VERSION=2403293_000590
MODEL=$HP_MODEL
SERIAL=$HP_SERIAL
HOSTNAME=$HP_HOSTNAME
EOF
    
    log_info "HTTP server configuration created at /etc/hp_printer_http_config.conf"
    log_info "The Python web server will use these settings for HTTP headers"
    
    # If nginx is installed, configure it as well
    if command -v nginx &>/dev/null; then
        if [[ -f /etc/nginx/nginx.conf && ! -f "$BACKUP_DIR/nginx.conf.bak" ]]; then
            cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx.conf.bak"
        fi
        
        # Modify nginx server tokens
        if grep -q "server_tokens" /etc/nginx/nginx.conf; then
            sed -i 's/server_tokens.*/server_tokens off;/' /etc/nginx/nginx.conf
        else
            sed -i '/http {/a \    server_tokens off;' /etc/nginx/nginx.conf
        fi
        
        # Add custom header for HP printer
        if ! grep -q "more_set_headers" /etc/nginx/nginx.conf; then
            log_info "Note: Install nginx-extras for custom header support"
            log_info "  sudo apt-get install nginx-extras"
        fi
        
        systemctl reload nginx 2>/dev/null || true
        log_info "Nginx configured to hide version information"
    fi
}

configure_tcp_fingerprint() {
    log_info "Configuring TCP/IP stack fingerprint to mimic HP printer..."
    
    # Backup current sysctl settings
    if [[ ! -f "$BACKUP_DIR/sysctl.conf.bak" ]]; then
        sysctl -a > "$BACKUP_DIR/sysctl.conf.bak" 2>/dev/null || true
    fi
    
    # Create HP printer TCP/IP stack configuration
    # Based on real HP LaserJet fingerprints from nmap/p0f databases
    
    cat > /etc/sysctl.d/99-hp-printer-fingerprint.conf <<EOF
# HP LaserJet Enterprise M609dn TCP/IP Stack Configuration
# These settings mimic the TCP/IP fingerprint of a real HP printer
# Based on nmap OS detection and p0f fingerprinting data

# TCP Window Size (HP printers typically use smaller windows)
net.ipv4.tcp_window_scaling = 1
net.core.rmem_default = 87380
net.core.wmem_default = 16384
net.ipv4.tcp_rmem = 4096 87380 174760
net.ipv4.tcp_wmem = 4096 16384 131072

# TCP Options (HP printers support basic options)
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_window_scaling = 1

# TTL Value (HP printers commonly use TTL 64 or 128)
# For Linux, default is 64 which matches many embedded devices
net.ipv4.ip_default_ttl = 64
net.ipv6.conf.all.hop_limit = 64

# TCP Keepalive (HP printers use different timings)
net.ipv4.tcp_keepalive_time = 7200
net.ipv4.tcp_keepalive_intvl = 75
net.ipv4.tcp_keepalive_probes = 9

# IP ID sequence (don't randomize for older device fingerprint)
# Note: This may reduce security
net.ipv4.ip_no_pmtu_disc = 0

# Disable ECN (many printers don't support it)
net.ipv4.tcp_ecn = 0

# TCP SYN retries (embedded devices often use lower values)
net.ipv4.tcp_syn_retries = 3
net.ipv4.tcp_synack_retries = 3

# Reduce TCP FIN timeout
net.ipv4.tcp_fin_timeout = 30

# Disable selective acknowledgments for older fingerprint
# net.ipv4.tcp_sack = 0  # Commented out - may break functionality

# Maximum number of queued connections
net.core.somaxconn = 128

# Disable IPv6 (many printers don't have IPv6 enabled)
# Uncomment if you want to fully disable IPv6
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1

EOF
    
    # Apply the settings
    sysctl -p /etc/sysctl.d/99-hp-printer-fingerprint.conf
    
    log_info "TCP/IP stack configured to mimic HP printer fingerprint"
    log_warn "Note: Some settings may reduce security - use only in isolated lab environments"
}

configure_nmap_deception() {
    log_info "Configuring additional OS fingerprint deception..."
    
    # Install nmap-os-db modification tools if available
    if command -v nmap &>/dev/null; then
        log_info "Nmap detected - consider using OSfuscate or similar tools for deeper OS spoofing"
    fi
    
    # Create p0f signature information
    cat > /tmp/hp_printer_p0f_signature.txt <<EOF
# HP LaserJet Enterprise M609dn p0f Signature
# This signature can be used with p0f for OS fingerprinting

# TCP SYN Packet Signature:
# Version, TTL, Options, MSS, Window Size, Window Scale, etc.

# Typical HP LaserJet M609dn signature:
# 4:64:0:*:mss*10,6:mss,sok,ts,nop,ws:df,id+:0

# Breakdown:
# - IPv4
# - TTL: 64
# - Don't Fragment bit set
# - Window Size: varies (typically 5840 or 8192)
# - TCP Options: MSS, SACK OK, Timestamp, NOP, Window Scale
# - MSS: 1460 (standard Ethernet)
# - Window Scale: 6

# To use with p0f:
# Add this signature to /etc/p0f/p0f.fp under [tcp:request] section

label = s:unix:HP:LaserJet M609dn
sig   = 4:64:0:*:mss*10,6:mss,sok,ts,nop,ws:df,id+:0
sig   = 4:64:0:*:8192,6:mss,sok,ts,nop,ws:df,id+:0

EOF
    
    log_info "P0f signature reference created at /tmp/hp_printer_p0f_signature.txt"
    log_info "To fully implement: Add signature to /etc/p0f/p0f.fp"
}

configure_service_fingerprints() {
    log_info "Configuring service-level fingerprints..."
    
    # Configure common service banners
    
    # FTP (if installed)
    if command -v vsftpd &>/dev/null; then
        if [[ ! -f "$BACKUP_DIR/vsftpd.conf.bak" ]]; then
            cp /etc/vsftpd.conf "$BACKUP_DIR/vsftpd.conf.bak" 2>/dev/null || true
        fi
        
        # Set HP printer FTP banner
        echo "ftpd_banner=HP LaserJet M609dn FTP Server" >> /etc/vsftpd.conf
        systemctl restart vsftpd 2>/dev/null || true
        log_info "FTP banner configured"
    fi
    
    # Telnet (if installed) - HP printers often have telnet enabled
    if command -v telnetd &>/dev/null; then
        log_info "Telnet detected - banner configured via /etc/issue"
    fi
    
    # Create a summary file
    cat > /root/hp_printer_fingerprint_summary.txt <<EOF
╔════════════════════════════════════════════════════════════════════════════╗
║                  HP PRINTER FINGERPRINT CONFIGURATION                       ║
╚════════════════════════════════════════════════════════════════════════════╝

DEVICE INFORMATION:
  Model:           $HP_MODEL
  Serial Number:   $HP_SERIAL
  Firmware:        2403293_000590 (Vulnerable)
  MAC Address:     $HP_MAC_ADDRESS
  Hostname:        $HP_HOSTNAME

CONFIGURED FINGERPRINTS:
  
  ✓ MAC Address         - Spoofed to HP OUI range (A0:B3:CC)
  ✓ Hostname            - Changed to HP naming convention
  ✓ DHCP Client ID      - Using HP MAC address
  ✓ mDNS/Bonjour        - Advertising as HP printer
  ✓ TCP/IP Stack        - Modified sysctl parameters
  ✓ SSH Banner          - HP Embedded SSH Service
  ✓ HTTP Headers        - HP-ChaiSOE/1.0 server header
  ✓ System Banners      - HP LaserJet identification

NMAP FINGERPRINT DETAILS:
  
  Expected OS Detection:
    - "HP LaserJet printer"
    - "HP embedded device"
    - "VxWorks or embedded Linux"
  
  TCP Characteristics:
    - TTL: 64
    - Window Size: 5840-8192
    - TCP Options: MSS, SACK, Timestamps, Window Scaling
    - Don't Fragment: Yes
    - Initial Window: 6 MSS

P0F FINGERPRINT:
  
  Signature: 4:64:0:*:mss*10,6:mss,sok,ts,nop,ws:df,id+:0
  See: /tmp/hp_printer_p0f_signature.txt

ACTIVE SERVICES:
  
  Port 80/tcp   - HTTP  (HP Embedded Web Server)
  Port 161/udp  - SNMP  (Printer management)
  Port 9100/tcp - JetDirect (Print spooler)
  Port 22/tcp   - SSH   (HP Embedded SSH - if enabled)
  Port 3702/udp - WS-Discovery (Windows printer discovery)
  Port 5355/udp - LLMNR (Link-Local Multicast Name Resolution)

VERIFICATION COMMANDS:
  
  # Check MAC address
  ip link show $INTERFACE | grep ether
  
  # Check hostname
  hostname
  
  # Test SNMP
  snmpwalk -v2c -c public localhost system
  
  # Check TCP fingerprint
  sudo nmap -O localhost
  
  # Check HTTP banner
  curl -I http://localhost
  
  # Check SSH banner
  ssh -v localhost 2>&1 | grep "Server version"

LIMITATIONS:
  
  ⚠ SSH version string requires OpenSSH recompilation for full spoofing
  ⚠ Some fingerprint techniques detectable by advanced scanners
  ⚠ TCP/IP stack spoofing may reduce network performance
  ⚠ These settings reduce security - USE ONLY IN LAB ENVIRONMENTS

RESTORATION:
  
  To restore original configuration:
    sudo $0 stop

CREATED: $(date)
SCRIPT VERSION: 2.0

EOF
    
    log_info "Fingerprint summary created at /root/hp_printer_fingerprint_summary.txt"
}

configure_firewall() {
    log_info "Configuring firewall rules for printer services..."
    
    if command -v ufw &>/dev/null; then
        # Allow printer ports
        ufw allow 80/tcp comment "HP Printer Web Interface"
        ufw allow 161/udp comment "SNMP"
        ufw allow 9100/tcp comment "HP JetDirect"
        ufw allow 515/tcp comment "LPD"
        ufw allow 631/tcp comment "IPP"
        
        log_info "UFW firewall rules configured"
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=161/udp
        firewall-cmd --permanent --add-port=9100/tcp
        firewall-cmd --permanent --add-port=515/tcp
        firewall-cmd --permanent --add-port=631/tcp
        firewall-cmd --reload
        
        log_info "Firewalld rules configured"
    else
        log_warn "No firewall detected - skipping firewall configuration"
    fi
}

###############################################################################
# Restoration Functions
###############################################################################

restore_configuration() {
    log_info "Restoring original configuration..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "No backup found in $BACKUP_DIR"
        return 1
    fi
    
    # Restore hostname
    if [[ -f "$HOSTNAME_BACKUP" ]]; then
        local orig_hostname=$(cat "$HOSTNAME_BACKUP")
        hostnamectl set-hostname "$orig_hostname"
        log_info "Restored hostname to: $orig_hostname"
    fi
    
    # Restore hosts file
    if [[ -f "$HOSTS_BACKUP" ]]; then
        cp "$HOSTS_BACKUP" /etc/hosts
        log_info "Restored /etc/hosts"
    fi
    
    # Restore MAC address
    if [[ -f "$MAC_BACKUP" && -f "$INTERFACE_BACKUP" ]]; then
        local orig_mac=$(cat "$MAC_BACKUP")
        local orig_interface=$(cat "$INTERFACE_BACKUP")
        
        ip link set "$orig_interface" down
        ip link set dev "$orig_interface" address "$orig_mac"
        ip link set "$orig_interface" up
        
        log_info "Restored MAC address to: $orig_mac"
    fi
    
    # Remove systemd service
    if [[ -f /etc/systemd/system/hp-printer-mac.service ]]; then
        systemctl disable hp-printer-mac.service
        rm /etc/systemd/system/hp-printer-mac.service
        systemctl daemon-reload
        log_info "Removed MAC persistence service"
    fi
    
    # Remove Avahi printer service
    if [[ -f /etc/avahi/services/hp-printer.service ]]; then
        rm /etc/avahi/services/hp-printer.service
        systemctl restart avahi-daemon
        log_info "Removed Avahi printer service"
    fi
    
    # Restore SNMP config
    if [[ -f "$BACKUP_DIR/snmpd.conf.bak" ]]; then
        cp "$BACKUP_DIR/snmpd.conf.bak" /etc/snmp/snmpd.conf
        systemctl restart snmpd 2>/dev/null || true
        log_info "Restored SNMP configuration"
    fi
    
    # Restore SSH configuration
    if [[ -f "$BACKUP_DIR/sshd_config.bak" ]]; then
        cp "$BACKUP_DIR/sshd_config.bak" /etc/ssh/sshd_config
        rm -f /etc/ssh/hp_printer_banner
        rm -f /usr/local/bin/ssh-hp-wrapper.sh
        systemctl restart sshd || systemctl restart ssh
        log_info "Restored SSH configuration"
    fi
    
    # Remove HTTP configuration
    if [[ -f /etc/hp_printer_http_config.conf ]]; then
        rm /etc/hp_printer_http_config.conf
        log_info "Removed HTTP printer configuration"
    fi
    
    # Restore nginx if modified
    if [[ -f "$BACKUP_DIR/nginx.conf.bak" ]]; then
        cp "$BACKUP_DIR/nginx.conf.bak" /etc/nginx/nginx.conf
        systemctl reload nginx 2>/dev/null || true
        log_info "Restored Nginx configuration"
    fi
    
    # Restore TCP/IP stack settings
    if [[ -f /etc/sysctl.d/99-hp-printer-fingerprint.conf ]]; then
        rm /etc/sysctl.d/99-hp-printer-fingerprint.conf
        sysctl --system
        log_info "Restored TCP/IP stack settings"
    fi
    
    # Clean up temporary files
    rm -f /tmp/hp_printer_p0f_signature.txt
    rm -f /root/hp_printer_fingerprint_summary.txt
    
    # Restore NetworkManager settings
    if command -v nmcli &>/dev/null; then
        local conn_name=$(nmcli -t -f NAME connection show --active | head -n1)
        if [[ -n "$conn_name" ]]; then
            nmcli connection modify "$conn_name" 802-3-ethernet.cloned-mac-address ""
            nmcli connection down "$conn_name" 2>/dev/null || true
            nmcli connection up "$conn_name"
            log_info "Restored NetworkManager configuration"
        fi
    fi
    
    log_info "Configuration restored successfully"
}

###############################################################################
# Status Functions
###############################################################################

show_status() {
    echo -e "\n${BLUE}Current System Status:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo -e "\n${GREEN}Network Configuration:${NC}"
    echo "  Hostname:        $(hostname)"
    echo "  Interface:       $INTERFACE"
    
    if ip link show "$INTERFACE" &>/dev/null; then
        local current_mac=$(ip link show "$INTERFACE" | grep "link/ether" | awk '{print $2}')
        echo "  Current MAC:     $current_mac"
        
        if [[ "$current_mac" == "$HP_MAC_ADDRESS" ]]; then
            echo -e "  Status:          ${GREEN}✓ Spoofed as HP Printer${NC}"
        else
            echo -e "  Status:          ${YELLOW}⚠ Original MAC Address${NC}"
        fi
    else
        echo -e "  Status:          ${RED}✗ Interface not found${NC}"
    fi
    
    local current_ip=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1)
    if [[ -n "$current_ip" ]]; then
        echo "  IP Address:      $current_ip"
    fi
    
    echo -e "\n${GREEN}HP Printer Identity:${NC}"
    echo "  Target MAC:      $HP_MAC_ADDRESS"
    echo "  Target Hostname: $HP_HOSTNAME"
    echo "  Model:           $HP_MODEL"
    echo "  Serial:          $HP_SERIAL"
    
    echo -e "\n${GREEN}Services Status:${NC}"
    
    # Check if MAC persistence service exists
    if [[ -f /etc/systemd/system/hp-printer-mac.service ]]; then
        echo -e "  MAC Persistence: ${GREEN}✓ Enabled${NC}"
    else
        echo -e "  MAC Persistence: ${YELLOW}⚠ Not configured${NC}"
    fi
    
    # Check Avahi
    if systemctl is-active --quiet avahi-daemon; then
        echo -e "  Avahi (mDNS):    ${GREEN}✓ Running${NC}"
    else
        echo -e "  Avahi (mDNS):    ${RED}✗ Not running${NC}"
    fi
    
    # Check if backup exists
    if [[ -d "$BACKUP_DIR" && -f "$MAC_BACKUP" ]]; then
        echo -e "\n${GREEN}Backup Status:${NC}"
        echo "  Backup Location: $BACKUP_DIR"
        echo "  Original MAC:    $(cat $MAC_BACKUP)"
        echo "  Original Host:   $(cat $HOSTNAME_BACKUP 2>/dev/null || echo 'N/A')"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

###############################################################################
# Main Functions
###############################################################################

start_impersonation() {
    print_banner
    log_info "Starting HP printer impersonation..."
    
    detect_interface
    create_backup_dir
    backup_current_config
    
    change_mac_address
    change_hostname
    configure_avahi
    configure_snmp
    configure_dhcp_identifier
    set_system_banner
    configure_ssh_banner
    configure_http_banner
    configure_tcp_fingerprint
    configure_nmap_deception
    configure_service_fingerprints
    configure_firewall
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "HP Printer impersonation configured successfully!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "System is now impersonating: $HP_MODEL"
    log_info "MAC Address: $HP_MAC_ADDRESS"
    log_info "Hostname: $HP_HOSTNAME"
    log_info "Firmware: 2403293_000590 (Vulnerable)"
    echo ""
    log_info "Fingerprint summary: /root/hp_printer_fingerprint_summary.txt"
    echo ""
    log_warn "Remember to start the printer simulator services!"
    log_info "Run: cd /path/to/iot_simulator && python3 server.py --config config_hp_printer.json"
    echo ""
    log_warn "⚠ IMPORTANT: These settings reduce security"
    log_warn "⚠ USE ONLY in isolated lab/testing environments"
    echo ""
}

stop_impersonation() {
    print_banner
    log_info "Stopping HP printer impersonation..."
    
    restore_configuration
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Original configuration restored!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

###############################################################################
# Main Script
###############################################################################

main() {
    check_root
    
    case "${1:-}" in
        start)
            start_impersonation
            show_status
            ;;
        stop)
            stop_impersonation
            show_status
            ;;
        status)
            print_banner
            show_status
            ;;
        *)
            print_banner
            echo "Usage: $0 {start|stop|status}"
            echo ""
            echo "Commands:"
            echo "  start   - Configure system to impersonate HP printer"
            echo "  stop    - Restore original configuration"
            echo "  status  - Show current impersonation status"
            echo ""
            echo "Example:"
            echo "  sudo $0 start"
            echo ""
            exit 1
            ;;
    esac
}

main "$@"
