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
    configure_firewall
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "HP Printer impersonation configured successfully!"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "System is now impersonating: $HP_MODEL"
    log_info "MAC Address: $HP_MAC_ADDRESS"
    log_info "Hostname: $HP_HOSTNAME"
    echo ""
    log_warn "Remember to start the printer simulator services!"
    log_info "Run: cd /path/to/iot_simulator && python3 server.py start"
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
