#!/bin/sh
# Firewall and NAT configuration for Alpine Wi-Fi Bridge

# Source utility functions
. ./scripts/utils.sh

# Configure NAT and firewall rules
setup_firewall() {
    if [ -z "$ETH_IFACE" ]; then
        log "Skipping NAT configuration as no Ethernet interface is available."
        return
    fi
    
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
    local subnet="${ETH_STATIC_IP%.*}.0/${ETH_SUBNET}"
    iptables -C FORWARD -s "$subnet" -d "$subnet" -j ACCEPT 2>/dev/null || \
        iptables -A FORWARD -s "$subnet" -d "$subnet" -j ACCEPT || warn_continue "Failed to allow traffic between local devices."
    
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
}

# Save iptables rules
save_firewall_rules() {
    log "Saving iptables rules..."
    
    if [ -d "/etc/init.d" ] && [ -f "/etc/init.d/iptables" ]; then
        /etc/init.d/iptables save || warn_continue "Failed to save iptables rules using init.d script."
    else
        # Alternative method to save iptables rules for Alpine Linux
        mkdir -p "$(dirname "$IPTABLES_RULES")" || warn_continue "Failed to create iptables directory."
        iptables-save > "$IPTABLES_RULES" || warn_continue "Failed to save iptables rules to file."
        
        # Create a local.d script to load iptables rules at boot (Alpine Linux approach)
        mkdir -p "$(dirname "$IPTABLES_SCRIPT")" || warn_continue "Failed to create local.d directory."
        cat > "$IPTABLES_SCRIPT" << EOF
#!/bin/sh
# Load iptables rules
/sbin/iptables-restore < $IPTABLES_RULES
exit 0
EOF
        chmod +x "$IPTABLES_SCRIPT" || warn_continue "Failed to make iptables restore script executable."
        
        # Ensure local service is enabled
        rc-update add local default 2>/dev/null || warn_continue "Failed to enable local service for startup scripts."
    fi
} 