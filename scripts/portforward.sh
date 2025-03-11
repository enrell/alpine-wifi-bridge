#!/bin/sh
# Port forwarding configuration for Alpine Wi-Fi Bridge

# Source utility functions
. ./scripts/utils.sh

# Setup port forwarding from Alpine (WLAN) to PC (ETH)
setup_port_forwarding() {
    log "Setting up port forwarding..."
    
    # Check if port forwarding is enabled in config
    if [ "$ENABLE_PORT_FORWARDING" != "true" ]; then
        log "Port forwarding is disabled in configuration. Skipping."
        return
    fi
    
    # Check if we have necessary parameters
    if [ -z "$PC_IP" ]; then
        log "PC_IP is not set in configuration. Skipping port forwarding."
        return
    fi
    
    # Get the IP address of the WLAN interface
    WLAN_IP=$(ip -4 addr show "$WLAN_IFACE" | grep -oP 'inet \K[\d.]+')
    if [ -z "$WLAN_IP" ]; then
        warn_continue "Could not determine IP address of WLAN interface. Skipping port forwarding."
        return
    fi
    
    log "Setting up traffic redirection from $WLAN_IP to $PC_IP"
    
    # DNAT rule to redirect all traffic coming to the Alpine machine to the PC
    iptables -t nat -C PREROUTING -d "$WLAN_IP" -j DNAT --to-destination "$PC_IP" 2>/dev/null || \
        iptables -t nat -A PREROUTING -d "$WLAN_IP" -j DNAT --to-destination "$PC_IP" || \
        warn_continue "Failed to set up DNAT rule for port forwarding."
    
    # Allow forwarding of packets to the PC
    iptables -C FORWARD -d "$PC_IP" -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -d "$PC_IP" -j ACCEPT || \
        warn_continue "Failed to allow forwarding to PC."
    
    # Add masquerading rule if it doesn't exist already
    iptables -t nat -C POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE 2>/dev/null || \
        iptables -t nat -A POSTROUTING -o "$WLAN_IFACE" -j MASQUERADE || \
        warn_continue "Failed to set up masquerading for responses."
    
    log "Port forwarding setup complete. Traffic to $WLAN_IP will be redirected to $PC_IP"
}

# Remove port forwarding rules
remove_port_forwarding() {
    # Get the IP address of the WLAN interface if not passed
    if [ -z "$WLAN_IP" ]; then
        WLAN_IP=$(ip -4 addr show "$WLAN_IFACE" | grep -oP 'inet \K[\d.]+')
    fi
    
    if [ -z "$WLAN_IP" ] || [ -z "$PC_IP" ]; then
        warn_continue "Could not determine IP addresses for removing port forwarding rules."
        return
    fi
    
    log "Removing port forwarding from $WLAN_IP to $PC_IP"
    
    # Remove DNAT rule
    iptables -t nat -D PREROUTING -d "$WLAN_IP" -j DNAT --to-destination "$PC_IP" 2>/dev/null || \
        warn_continue "Failed to remove DNAT rule for port forwarding."
    
    # Remove forward rule
    iptables -D FORWARD -d "$PC_IP" -j ACCEPT 2>/dev/null || \
        warn_continue "Failed to remove forwarding rule to PC."
    
    log "Port forwarding rules removed."
} 