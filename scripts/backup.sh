#!/bin/sh
# Backup and restore functionality for Alpine Wi-Fi Bridge

# Source utility functions
. ./scripts/utils.sh

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
    iptables -D FORWARD -s "${ETH_STATIC_IP%.*}.0/${ETH_SUBNET}" -d "${ETH_STATIC_IP%.*}.0/${ETH_SUBNET}" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove local network traffic rule."
    iptables -D INPUT -i "$ETH_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove notebook input rule."
    iptables -D OUTPUT -o "$WLAN_IFACE" -j ACCEPT 2>/dev/null || warn_continue "Failed to remove notebook output rule."
    iptables -D INPUT -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP input rule."
    iptables -D OUTPUT -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP output rule."
    iptables -D FORWARD -p icmp -j ACCEPT 2>/dev/null || warn_continue "Failed to remove ICMP forwarding rule."

    # Remove static IP from the Ethernet interface
    if [ -n "$ETH_IFACE" ] && ip addr show "$ETH_IFACE" | grep -q "$ETH_STATIC_IP"; then
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