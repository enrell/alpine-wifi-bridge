#!/bin/sh

# Configuration file to store settings
CONFIG_FILE="/etc/alpine-wifi-bridge/config"
BACKUP_DIR="/etc/alpine-wifi-bridge/backup"
# Default gateway IP (will be auto-detected if possible)
DEFAULT_GATEWAY="192.168.0.1"

# Function for formatted logging
log() {
    echo "[INFO] $1"
}

# Function for error handling with a fallback to skip steps
warn_continue() {
    echo "[WARNING] $1 - Skipping this step."
}

# Function for critical errors that require stopping
error_exit() {
    echo "[ERROR] $1"
    exit 1
}

# Function to create backup of network configuration
backup_network_config() {
    log "Creating backup of network configuration..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR" || warn_continue "Failed to create backup directory."
    
    # Backup current network configuration
    if [ ! -f "$BACKUP_DIR/network_config.bak" ]; then
        log "Backing up current network configuration..."
        
        # Backup IP forwarding state
        cat /proc/sys/net/ipv4/ip_forward > "$BACKUP_DIR/ip_forward.bak" || warn_continue "Failed to backup IP forwarding state."
        
        # Backup iptables rules
        iptables-save > "$BACKUP_DIR/iptables.bak" || warn_continue "Failed to backup iptables rules."
        
        # Backup interface configurations
        ip addr show > "$BACKUP_DIR/ip_addr.bak" || warn_continue "Failed to backup interface configurations."
        ip route show > "$BACKUP_DIR/ip_route.bak" || warn_continue "Failed to backup routing table."
        
        # Mark backup as complete
        touch "$BACKUP_DIR/network_config.bak" || warn_continue "Failed to create backup marker file."
        
        log "Network configuration backup completed."
    else
        log "Network configuration backup already exists. Skipping backup."
    fi
}

# Function to restore the network settings
restore_settings() {
    log "Restoring network settings to the original state..."

    # Load configuration if it exists
    if [ -f "$CONFIG_FILE" ]; then
        log "Loading configuration from $CONFIG_FILE"
        . "$CONFIG_FILE"
    else
        log "No configuration file found. Using default interface detection."
        # Detect interfaces
        WLAN_IFACE=$(ip link | grep -E "^[0-9]+: wlan" | awk -F': ' '{print $2}' | head -n 1)
        ETH_IFACE=$(ip link | grep -E "^[0-9]+: eth" | awk -F': ' '{print $2}' | head -n 1)
    fi

    # Disable IP forwarding
    log "Disabling IP forwarding..."
    echo 0 > /proc/sys/net/ipv4/ip_forward || warn_continue "Failed to disable IP forwarding."
    
    # Remove IP forwarding rule in sysctl.conf if exists
    if grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        sed -i '/net.ipv4.ip_forward=1/d' /etc/sysctl.conf || warn_continue "Failed to remove IP forwarding from sysctl.conf."
    fi

    # Remove NAT iptables rules
    log "Removing iptables NAT rules..."
    # Basic NAT rules
    iptables -t nat -D POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE 2>/dev/null || warn_continue "Failed to remove NAT POSTROUTING rule."
    iptables -D FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || warn_continue "Failed to remove FORWARD rule (inbound)."
    iptables -D FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove FORWARD rule (outbound)."
    
    # Enhanced rules
    log "Removing enhanced iptables rules..."
    iptables -D FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || warn_continue "Failed to remove established connections rule."
    iptables -D FORWARD -i "$ETH_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove outgoing connections rule."
    iptables -D FORWARD -s 10.42.0.0/24 -d 10.42.0.0/24 -j ACCEPT 2>/dev/null || warn_continue "Failed to remove local network traffic rule."
    iptables -D INPUT -i "$ETH_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove notebook input rule."
    iptables -D OUTPUT -o "$WLAN_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove notebook output rule."
    iptables -D INPUT -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP input rule."
    iptables -D OUTPUT -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP output rule."
    iptables -D FORWARD -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP forwarding rule."

    # Remove static IP from the Ethernet interface
    if [ -n "$ETH_IFACE" ] && ip addr show "$ETH_IFACE" | grep -q "10.42.0.1"; then
        log "Removing static IP from Ethernet interface ($ETH_IFACE)..."
        ip addr flush dev "$ETH_IFACE" || warn_continue "Failed to remove IP from $ETH_IFACE."
    fi

    # Remove default route for Wi-Fi (if set)
    if [ -n "$WLAN_IFACE" ] && [ -n "$GATEWAY_IP" ]; then
        ip route del default via "$GATEWAY_IP" dev "$WLAN_IFACE" 2>/dev/null || warn_continue "Failed to remove default route via Wi-Fi."
    fi

    # Stop the wpa_supplicant service if it was started
    log "Stopping wpa_supplicant service..."
    pkill wpa_supplicant || warn_continue "Failed to stop wpa_supplicant."

    # Restore network interfaces to original state (down interfaces)
    if [ -n "$WLAN_IFACE" ]; then
        ip link set "$WLAN_IFACE" down || warn_continue "Failed to bring down $WLAN_IFACE."
    fi
    
    if [ -n "$ETH_IFACE" ]; then
        ip link set "$ETH_IFACE" down || warn_continue "Failed to bring down $ETH_IFACE."
    fi

    # Restore from backup if available
    if [ -f "$BACKUP_DIR/iptables.bak" ]; then
        log "Restoring iptables rules from backup..."
        iptables-restore < "$BACKUP_DIR/iptables.bak" || warn_continue "Failed to restore iptables rules from backup."
    fi

    log "Network settings restored successfully."
}

# Function to detect gateway IP
detect_gateway_ip() {
    log "Detecting gateway IP address..."
    
    # Try to get the gateway IP from the routing table
    DETECTED_GW=$(ip route | grep "default via" | grep "$WLAN_IFACE" | awk '{print $3}' | head -n 1)
    
    if [ -n "$DETECTED_GW" ]; then
        log "Detected gateway IP: $DETECTED_GW"
        GATEWAY_IP="$DETECTED_GW"
    else
        log "Could not auto-detect gateway IP. Using default: $DEFAULT_GATEWAY"
        GATEWAY_IP="$DEFAULT_GATEWAY"
        
        # Ask user if they want to specify a different gateway
        echo "Do you want to specify a different gateway IP? (y/n)"
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            echo "Enter the gateway IP address:"
            read -r custom_gateway
            if [ -n "$custom_gateway" ]; then
                GATEWAY_IP="$custom_gateway"
                log "Using custom gateway IP: $GATEWAY_IP"
            fi
        fi
    fi
}

log "Starting Wi-Fi and Internet Sharing Configuration Script..."

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    error_exit "This script must be run as root. Use 'sudo'."
fi

# Create configuration directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")" || warn_continue "Failed to create configuration directory."

# Check if we need to restore settings or configure new ones
if [ "$1" = "--restore" ]; then
    restore_settings
    exit 0
fi

# Load configuration if it exists
if [ -f "$CONFIG_FILE" ]; then
    log "Loading configuration from $CONFIG_FILE"
    . "$CONFIG_FILE"
fi

# Backup current network configuration before making changes
backup_network_config

# Install necessary packages except udhcpc (assumed to be pre-installed)
log "Installing required packages..."
apk update || error_exit "Failed to update package lists."
apk add --no-cache iptables wireless-tools wpa_supplicant || error_exit "Failed to install required packages."

# Check and configure Wi-Fi interface
log "Checking for Wi-Fi interface..."
WLAN_IFACE=$(ip link | grep -E "^[0-9]+: wlan" | awk -F': ' '{print $2}' | head -n 1)
if [ -z "$WLAN_IFACE" ]; then
    error_exit "No Wi-Fi interface found. Ensure your device has a Wi-Fi adapter."
fi
log "Using Wi-Fi interface: $WLAN_IFACE"

# Configure Wi-Fi
WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
if [ ! -f "$WPA_CONF" ]; then
    log "Wi-Fi configuration not found. Creating a new one..."
    echo "Enter the SSID of the Wi-Fi network:"
    read SSID
    echo "Enter the password for the Wi-Fi network:"
    read -s PASSWORD
    [ -z "$SSID" ] && error_exit "SSID cannot be empty."
    [ -z "$PASSWORD" ] && error_exit "Password cannot be empty."
    
    # Create wpa_supplicant directory if it doesn't exist
    mkdir -p "$(dirname "$WPA_CONF")" || error_exit "Failed to create wpa_supplicant directory."
    
    wpa_passphrase "$SSID" "$PASSWORD" > "$WPA_CONF" || error_exit "Failed to generate wpa_supplicant configuration."
    log "Wi-Fi configuration saved to $WPA_CONF."
else
    log "Using existing Wi-Fi configuration at $WPA_CONF."
fi

# Check if wpa_supplicant is already running
if ! pgrep -x wpa_supplicant > /dev/null; then
    log "Connecting to Wi-Fi using $WLAN_IFACE..."
    wpa_supplicant -B -i "$WLAN_IFACE" -c "$WPA_CONF" || error_exit "Failed to start wpa_supplicant. Check your Wi-Fi configuration."
else
    log "wpa_supplicant is already running. Skipping Wi-Fi connection setup."
fi

# Check if interface already has an IP address
if ! ip addr show "$WLAN_IFACE" | grep -q "inet "; then
    log "Requesting IP for $WLAN_IFACE via DHCP..."
    udhcpc -i "$WLAN_IFACE" || error_exit "Failed to obtain an IP address for $WLAN_IFACE."
else
    log "$WLAN_IFACE already has an IP address. Skipping DHCP request."
fi

# Detect gateway IP
detect_gateway_ip

# Check and configure Ethernet interface
log "Checking for Ethernet interface..."
ETH_IFACE=$(ip link | grep -E "^[0-9]+: eth" | awk -F': ' '{print $2}' | head -n 1)
if [ -z "$ETH_IFACE" ]; then
    warn_continue "No Ethernet interface found. Skipping Ethernet configuration."
else
    log "Using Ethernet interface: $ETH_IFACE"
    
    # Check if the interface already has the static IP
    if ! ip addr show "$ETH_IFACE" | grep -q "10.42.0.1/24"; then
        log "Setting up static IP for $ETH_IFACE..."
        ip addr flush dev "$ETH_IFACE"
        ip addr add 10.42.0.1/24 dev "$ETH_IFACE" || warn_continue "Failed to set IP for $ETH_IFACE."
    else
        log "$ETH_IFACE already has the correct static IP. Skipping IP configuration."
    fi
    
    # Ensure the interface is up
    if ! ip link show "$ETH_IFACE" | grep -q "state UP"; then
        ip link set "$ETH_IFACE" up || warn_continue "Failed to bring up $ETH_IFACE."
    else
        log "$ETH_IFACE is already up. Skipping interface activation."
    fi
fi

# Set default route if not already set
if ! ip route | grep -q "default via .* dev $WLAN_IFACE"; then
    log "Adding default route via $GATEWAY_IP on $WLAN_IFACE..."
    ip route replace default via "$GATEWAY_IP" dev "$WLAN_IFACE" || warn_continue "Failed to set default route."
else
    log "Default route via $WLAN_IFACE already exists. Skipping route configuration."
fi

# Enable IP forwarding if not already enabled
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    log "Enabling IP forwarding..."
    echo 1 > /proc/sys/net/ipv4/ip_forward || warn_continue "Failed to enable IP forwarding."
else
    log "IP forwarding is already enabled. Skipping."
fi

# Make IP forwarding persistent if not already configured
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf || warn_continue "Failed to make IP forwarding permanent."
else
    log "Persistent IP forwarding is already configured. Skipping."
fi

# Configure NAT with iptables
if [ -n "$ETH_IFACE" ]; then
    log "Setting up NAT with iptables..."
    
    # Basic NAT configuration - check before adding
    iptables -t nat -C POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE 2>/dev/null || \
        iptables -t nat -A POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE || warn_continue "Failed to set up NAT."
    
    iptables -C FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT || warn_continue "Failed to allow forwarding from $ETH_IFACE to $WLAN_IFACE."
    
    iptables -C FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT || warn_continue "Failed to allow forwarding from $WLAN_IFACE to $ETH_IFACE."
    
    # Enhanced rules to allow all traffic to pass freely - check before adding
    log "Setting up enhanced rules for unrestricted network communication..."
    
    # Allow all established connections
    iptables -C FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT || warn_continue "Failed to allow established connections."
    
    # Allow all outgoing connections
    iptables -C FORWARD -i "$ETH_IFACE" -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -i "$ETH_IFACE" -j ACCEPT || warn_continue "Failed to allow all outgoing connections from $ETH_IFACE."
    
    # Allow all traffic between devices in the local network
    iptables -C FORWARD -s 10.42.0.0/24 -d 10.42.0.0/24 -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -s 10.42.0.0/24 -d 10.42.0.0/24 -j ACCEPT || warn_continue "Failed to allow traffic between local devices."
    
    # Allow all traffic to the notebook (bridging device)
    iptables -C INPUT -i "$ETH_IFACE" -j ACCEPT 2>/dev/null || \
        iptables -A INPUT -i "$ETH_IFACE" -j ACCEPT || warn_continue "Failed to allow traffic to the notebook from $ETH_IFACE."
    
    # Allow traffic from the notebook to any destination
    iptables -C OUTPUT -o "$WLAN_IFACE" -j ACCEPT 2>/dev/null || \
        iptables -A OUTPUT -o "$WLAN_IFACE" -j ACCEPT || warn_continue "Failed to allow traffic from notebook to any destination via $WLAN_IFACE."
    
    # Allow ICMP (ping) traffic in all directions
    iptables -C INPUT -p icmp -j ACCEPT 2>/dev/null || \
        iptables -A INPUT -p icmp -j ACCEPT || warn_continue "Failed to allow ICMP input."
    
    iptables -C OUTPUT -p icmp -j ACCEPT 2>/dev/null || \
        iptables -A OUTPUT -p icmp -j ACCEPT || warn_continue "Failed to allow ICMP output."
    
    iptables -C FORWARD -p icmp -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -p icmp -j ACCEPT || warn_continue "Failed to allow ICMP forwarding."

else
    log "Skipping NAT configuration as no Ethernet interface is available."
fi

# Save iptables rules
log "Saving iptables rules..."
if [ -d "/etc/init.d" ] && [ -f "/etc/init.d/iptables" ]; then
    /etc/init.d/iptables save || warn_continue "Failed to save iptables rules using init.d script."
else
    # Alternative method to save iptables rules for Alpine Linux
    mkdir -p /etc/iptables
    iptables-save > /etc/iptables/rules.v4 || warn_continue "Failed to save iptables rules to file."
    
    # Create a local.d script to load iptables rules at boot (Alpine Linux approach)
    mkdir -p /etc/local.d
    cat > /etc/local.d/iptables.start << EOF
#!/bin/sh
# Load iptables rules
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
    chmod +x /etc/local.d/iptables.start || warn_continue "Failed to make iptables restore script executable."
    
    # Ensure local service is enabled
    rc-update add local default 2>/dev/null || warn_continue "Failed to enable local service for startup scripts."
fi

# Save configuration for future runs
log "Saving configuration for future runs..."
cat > "$CONFIG_FILE" << EOF
# Alpine Wi-Fi Bridge Configuration
# Generated on $(date)
WLAN_IFACE="$WLAN_IFACE"
ETH_IFACE="$ETH_IFACE"
GATEWAY_IP="$GATEWAY_IP"
EOF

# Restart networking services if needed
if [ -f "/etc/init.d/networking" ]; then
    log "Restarting network services..."
    /etc/init.d/networking restart || warn_continue "Failed to restart networking services."
else
    log "No networking service found. Skipping restart."
fi

log "Configuration complete! If both interfaces are active, internet sharing should now be working."
log "To restore settings, run: $0 --restore"
