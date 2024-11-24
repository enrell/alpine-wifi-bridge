#!/bin/sh

# Script to monitor and maintain network connectivity
# Runs continuously in the background and takes corrective actions as needed

# Define constants
WLAN_IFACE="wlan0"
DEFAULT_GATEWAY="192.168.0.1"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1"
}

# Function to log warnings
warn() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1"
}

# Function to log errors
error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >&2
}

# Function to check Wi-Fi connection
check_wifi_connection() {
    log "Checking Wi-Fi connection on $WLAN_IFACE..."
    if ! iw dev "$WLAN_IFACE" link | grep -q "Connected to"; then
        warn "Wi-Fi is disconnected. Attempting to reconnect..."
        wpa_cli -i "$WLAN_IFACE" reconfigure >/dev/null 2>&1 || warn "Failed to reconfigure Wi-Fi."
        sleep 5
        if ! iw dev "$WLAN_IFACE" link | grep -q "Connected to"; then
            error "Wi-Fi reconnection failed. Check your network settings."
        else
            log "Wi-Fi reconnected successfully."
        fi
    else
        log "Wi-Fi is connected."
    fi
}

# Function to check default route
check_default_route() {
    log "Checking default route..."
    if ! ip route | grep -q "default via $DEFAULT_GATEWAY dev $WLAN_IFACE"; then
        warn "Default route missing. Adding route via $DEFAULT_GATEWAY..."
        ip route add default via "$DEFAULT_GATEWAY" dev "$WLAN_IFACE" || error "Failed to add default route."
    else
        log "Default route is correctly configured."
    fi
}

# Function to check link status
check_link_status() {
    log "Checking link status for $WLAN_IFACE..."
    if ! ip link show "$WLAN_IFACE" | grep -q "state UP"; then
        warn "Link $WLAN_IFACE is down. Attempting to bring it up..."
        ip link set "$WLAN_IFACE" up || error "Failed to bring up $WLAN_IFACE."
    else
        log "Link $WLAN_IFACE is up."
    fi
}

# Function to ensure WLAN IP assignment
check_dhcp_assignment() {
    log "Checking IP assignment on $WLAN_IFACE..."
    if ! ip addr show "$WLAN_IFACE" | grep -q "inet "; then
        warn "No IP assigned to $WLAN_IFACE. Running udhcpc..."
        udhcpc -i "$WLAN_IFACE" -q >/dev/null 2>&1 || error "Failed to obtain IP address for $WLAN_IFACE."
    else
        log "IP is correctly assigned to $WLAN_IFACE."
    fi
}

# Monitoring loop
log "Starting network monitoring..."
while true; do
    check_wifi_connection       # Ensure Wi-Fi stays connected
    check_default_route         # Ensure default route is present
    check_link_status           # Ensure link is up
    check_dhcp_assignment       # Ensure IP is assigned
    sleep 10                    # Monitor every 10 seconds
done
