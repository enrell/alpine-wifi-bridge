#!/bin/sh

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

# Function to restore the network settings
restore_settings() {
    log "Restoring network settings to the original state..."

    # Disable IP forwarding
    log "Disabling IP forwarding..."
    echo 0 > /proc/sys/net/ipv4/ip_forward || warn_continue "Failed to disable IP forwarding."
    
    # Remove IP forwarding rule in sysctl.conf if exists
    if grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        sed -i '/net.ipv4.ip_forward=1/d' /etc/sysctl.conf || warn_continue "Failed to remove IP forwarding from sysctl.conf."
    fi

    # Remove NAT iptables rules
    log "Removing iptables NAT rules..."
    iptables -t nat -D POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE 2>/dev/null || warn_continue "Failed to remove NAT POSTROUTING rule."
    iptables -D FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || warn_continue "Failed to remove FORWARD rule (inbound)."
    iptables -D FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove FORWARD rule (outbound)."

    # Remove static IP from the Ethernet interface
    if ip addr show "$ETH_IFACE" | grep -q "10.42.0.1"; then
        log "Removing static IP from Ethernet interface ($ETH_IFACE)..."
        ip addr flush dev "$ETH_IFACE" || warn_continue "Failed to remove IP from $ETH_IFACE."
    fi

    # Remove default route for Wi-Fi (if set)
    ip route del default via 192.168.0.1 dev "$WLAN_IFACE" 2>/dev/null || warn_continue "Failed to remove default route via Wi-Fi."

    # Stop the wpa_supplicant service if it was started
    log "Stopping wpa_supplicant service..."
    pkill wpa_supplicant || warn_continue "Failed to stop wpa_supplicant."

    # Restore network interfaces to original state (down interfaces)
    ip link set "$WLAN_IFACE" down || warn_continue "Failed to bring down $WLAN_IFACE."
    ip link set "$ETH_IFACE" down || warn_continue "Failed to bring down $ETH_IFACE."

    # Optionally remove wpa_supplicant configuration (if the user wants to revert everything)
    # rm -f /etc/wpa_supplicant/wpa_supplicant.conf || warn_continue "Failed to remove Wi-Fi configuration file."

    log "Network settings restored successfully."
}

log "Starting Wi-Fi and Internet Sharing Configuration Script..."

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    error_exit "This script must be run as root. Use 'sudo'."
fi

# Check if we need to restore settings or configure new ones
if [ "$1" = "--restore" ]; then
    restore_settings
    exit 0
fi

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
    wpa_passphrase "$SSID" "$PASSWORD" > "$WPA_CONF" || error_exit "Failed to generate wpa_supplicant configuration."
    log "Wi-Fi configuration saved to $WPA_CONF."
else
    log "Using existing Wi-Fi configuration at $WPA_CONF."
fi

log "Connecting to Wi-Fi using $WLAN_IFACE..."
wpa_supplicant -B -i "$WLAN_IFACE" -c "$WPA_CONF" || error_exit "Failed to start wpa_supplicant. Check your Wi-Fi configuration."

log "Requesting IP for $WLAN_IFACE via DHCP..."
udhcpc -i "$WLAN_IFACE" || error_exit "Failed to obtain an IP address for $WLAN_IFACE."

# Check and configure Ethernet interface
log "Checking for Ethernet interface..."
ETH_IFACE=$(ip link | grep -E "^[0-9]+: eth" | awk -F': ' '{print $2}' | head -n 1)
if [ -z "$ETH_IFACE" ]; then
    warn_continue "No Ethernet interface found. Skipping Ethernet configuration."
else
    log "Using Ethernet interface: $ETH_IFACE"
    log "Setting up static IP for $ETH_IFACE..."
    ip addr flush dev "$ETH_IFACE"
    ip addr add 10.42.0.1/24 dev "$ETH_IFACE" || warn_continue "Failed to set IP for $ETH_IFACE."
    ip link set "$ETH_IFACE" up || warn_continue "Failed to bring up $ETH_IFACE."
fi

# Set default route
log "Adding default route via $WLAN_IFACE..."
ip route replace default via 192.168.0.1 dev "$WLAN_IFACE" || warn_continue "Failed to set default route."

# Enable IP forwarding
log "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward || warn_continue "Failed to enable IP forwarding."
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf || warn_continue "Failed to make IP forwarding permanent."
fi

# Configure NAT with iptables
if [ -n "$ETH_IFACE" ]; then
    log "Setting up NAT with iptables..."
    iptables -t nat -C POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE 2>/dev/null || \
        iptables -t nat -A POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE || warn_continue "Failed to set up NAT."
    iptables -C FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -i "$ETH_IFACE" -o "$WLAN_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT || warn_continue "Failed to allow forwarding from $ETH_IFACE to $WLAN_IFACE."
    iptables -C FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -i "$WLAN_IFACE" -o "$ETH_IFACE" -j ACCEPT || warn_continue "Failed to allow forwarding from $WLAN_IFACE to $ETH_IFACE."
else
    log "Skipping NAT configuration as no Ethernet interface is available."
fi

# Save iptables rules
log "Saving iptables rules..."
/etc/init.d/iptables save || warn_continue "Failed to save iptables rules."

# Restart networking services
log "Restarting network services..."
rc-service networking restart || warn_continue "Failed to restart networking services."

log "Configuration complete! If both interfaces are active, internet sharing should now be working."
