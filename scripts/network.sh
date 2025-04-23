#!/bin/sh
# Network configuration for Alpine Wi-Fi Bridge

# Source utility functions
. ./scripts/utils.sh

# Configure Wi-Fi connection
setup_wifi() {
    log "Setting up Wi-Fi connection..."
    
    # Configure Wi-Fi
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
        
        # Handle special characters in passwords by using a temporary file
        log "Generating wpa_supplicant configuration..."
        
        # Create a temporary file for the password to avoid shell interpretation issues
        TEMP_FILE=$(mktemp)
        echo -n "$PASSWORD" > "$TEMP_FILE"
        
        # Use wpa_passphrase with the password file
        wpa_passphrase "$SSID" "$(cat "$TEMP_FILE")" > "$WPA_CONF" 2>/dev/null
        
        # Secure delete the temporary file
        rm -f "$TEMP_FILE"
        
        # Check if the configuration was created successfully
        if [ ! -s "$WPA_CONF" ]; then
            log "Failed to generate configuration with wpa_passphrase. Creating manual configuration..."
            
            # Create a basic configuration manually
            cat > "$WPA_CONF" << EOF
ctrl_interface=/var/run/wpa_supplicant
update_config=1

network={
    ssid="$SSID"
    psk="$PASSWORD"
    key_mgmt=WPA-PSK
}
EOF
            log "Manual Wi-Fi configuration created."
        else
            log "Wi-Fi configuration saved to $WPA_CONF."
        fi
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
        udhcpc -i "$WLAN_IFACE" -t 10 -T 2 || error_exit "Failed to obtain an IP address for $WLAN_IFACE."
    else
        log "$WLAN_IFACE already has an IP address. Skipping DHCP request."
    fi
    
    # Verify connectivity
    log "Verifying network connectivity..."
    if ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
        log "Network connectivity confirmed."
    else
        warn_continue "Could not verify internet connectivity. The Wi-Fi connection may not be working properly."
    fi
}

# Configure Ethernet interface
setup_ethernet() {
    if [ -z "$ETH_IFACE" ]; then
        warn_continue "No Ethernet interface found. Skipping Ethernet configuration."
        return
    fi
    
    log "Setting up Ethernet interface..."
    
    # Check if the interface already has the static IP
    if ! ip addr show "$ETH_IFACE" | grep -q "$ETH_STATIC_IP/$ETH_SUBNET"; then
        log "Setting up static IP for $ETH_IFACE..."
        ip addr flush dev "$ETH_IFACE"
        ip addr add "$ETH_STATIC_IP/$ETH_SUBNET" dev "$ETH_IFACE" || warn_continue "Failed to set IP for $ETH_IFACE."
    else
        log "$ETH_IFACE already has the correct static IP. Skipping IP configuration."
    fi
    
    # Ensure the interface is up
    if ! ip link show "$ETH_IFACE" | grep -q "state UP"; then
        ip link set "$ETH_IFACE" up || warn_continue "Failed to bring up $ETH_IFACE."
    else
        log "$ETH_IFACE is already up. Skipping interface activation."
    fi
}

# Configure routing
setup_routing() {
    log "Setting up routing..."
    
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
}

# Install required packages
install_packages() {
    log "Installing required packages..."
    apk update || error_exit "Failed to update package lists."
    
    # Check Alpine version to determine package requirements
    ALPINE_VERSION=$(cat /etc/alpine-release 2>/dev/null || echo "unknown")
    log "Detected Alpine Linux version: $ALPINE_VERSION"
    
    # Install base packages
    log "Installing base networking packages..."
    apk add --no-cache wireless-tools wpa_supplicant || error_exit "Failed to install wireless packages."
    
    # Check if we need iptables or iptables-nft (for nftables compatibility)
    if command -v nft >/dev/null 2>&1; then
        log "nftables detected, installing iptables-nft for compatibility..."
        apk add --no-cache iptables-nft || {
            log "Failed to install iptables-nft, falling back to standard iptables..."
            apk add --no-cache iptables || error_exit "Failed to install iptables packages."
        }
    else
        log "Installing standard iptables..."
        apk add --no-cache iptables || error_exit "Failed to install iptables packages."
    fi
    
    # Create required directories if they don't exist
    for dir in "/etc/wpa_supplicant" "/etc/iptables" "/etc/local.d"; do
        if [ ! -d "$dir" ]; then
            log "Creating directory: $dir"
            mkdir -p "$dir" || warn_continue "Failed to create directory: $dir"
        fi
    done
} 