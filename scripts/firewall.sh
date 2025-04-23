#!/bin/sh
# Firewall and NAT configuration for Alpine Wi-Fi Bridge

# Source utility functions
. ./scripts/utils.sh

# Detect firewall system and set up appropriate commands
detect_firewall_system() {
    # Check if nftables is the primary firewall system
    if command -v nft >/dev/null 2>&1 && [ ! -e "/proc/net/ip_tables_names" ]; then
        log "Detected nftables as primary firewall system."
        FIREWALL_TYPE="nftables"
    else
        log "Using iptables for firewall configuration."
        FIREWALL_TYPE="iptables"
    fi
}

# Configure NAT and firewall rules
setup_firewall() {
    if [ -z "$ETH_IFACE" ]; then
        log "Skipping NAT configuration as no Ethernet interface is available."
        return
    fi
    
    # Detect which firewall system to use
    detect_firewall_system
    
    if [ "$FIREWALL_TYPE" = "nftables" ]; then
        setup_nftables_firewall
    else
        setup_iptables_firewall
    fi
}

# Configure NAT and firewall using nftables
setup_nftables_firewall() {
    log "Setting up NAT with nftables..."
    
    # Check if nft is available
    if ! command -v nft >/dev/null 2>&1; then
        log "nft command not found. Falling back to iptables..."
        setup_iptables_firewall
        return
    fi
    
    # Create a basic nftables configuration file
    local nft_file="/etc/nftables/alpine-wifi-bridge.nft"
    mkdir -p "$(dirname "$nft_file")" || warn_continue "Failed to create nftables directory."
    
    local subnet="${ETH_STATIC_IP%.*}.0/${ETH_SUBNET}"
    
    cat > "$nft_file" << EOF
#!/usr/sbin/nft -f

flush ruleset

table ip nat {
    chain prerouting {
        type nat hook prerouting priority -100; policy accept;
    }
    
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;
        oifname "$WLAN_IFACE" masquerade
    }
}

table ip filter {
    chain input {
        type filter hook input priority 0; policy accept;
        iifname "$ETH_IFACE" accept
        icmp type echo-request accept
    }
    
    chain forward {
        type filter hook forward priority 0; policy accept;
        iifname "$ETH_IFACE" oifname "$WLAN_IFACE" ct state related,established accept
        iifname "$WLAN_IFACE" oifname "$ETH_IFACE" accept
        ct state related,established accept
        iifname "$ETH_IFACE" accept
        ip saddr $subnet ip daddr $subnet accept
        icmp type echo-request accept
    }
    
    chain output {
        type filter hook output priority 0; policy accept;
        oifname "$WLAN_IFACE" accept
        icmp type echo-request accept
    }
}
EOF
    
    # Apply the nftables rules
    log "Applying nftables rules..."
    nft -f "$nft_file" || {
        warn_continue "Failed to apply nftables rules. Falling back to iptables..."
        setup_iptables_firewall
    }
    
    # Make sure nftables service is enabled
    if [ -f "/etc/init.d/nftables" ]; then
        rc-update add nftables default 2>/dev/null || warn_continue "Failed to enable nftables service."
    fi
    
    # Create a script to load nftables rules at boot
    local nft_script="/etc/local.d/nftables.start"
    mkdir -p "$(dirname "$nft_script")" || warn_continue "Failed to create local.d directory."
    
    cat > "$nft_script" << EOF
#!/bin/sh
# Load nftables rules
/usr/sbin/nft -f $nft_file
exit 0
EOF
    
    chmod +x "$nft_script" || warn_continue "Failed to make nftables script executable."
}

# Configure NAT and firewall using iptables
setup_iptables_firewall() {
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

# Save firewall rules
save_firewall_rules() {
    # If we're using nftables, rules are already saved in the setup_nftables_firewall function
    if [ "$FIREWALL_TYPE" = "nftables" ]; then
        log "nftables rules already saved during setup."
        return
    fi
    
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