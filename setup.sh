#!/bin/sh
# Main script for Alpine Wi-Fi Bridge

# Source all component scripts
. ./scripts/utils.sh
. ./scripts/backup.sh
. ./scripts/network.sh
. ./scripts/firewall.sh
. ./scripts/portforward.sh

# Configuration file path
CONFIG_PATH="./config/settings.conf"
RUNTIME_CONFIG="/etc/alpine-wifi-bridge/config"

# Display banner
display_banner() {
    echo "=================================================="
    echo "      Alpine Wi-Fi to Ethernet Bridge Setup       "
    echo "=================================================="
    echo ""
}

# Main setup function
setup() {
    display_banner
    
    # Check for root privileges
    check_root
    
    # Load configuration
    load_config "$CONFIG_PATH"
    
    # Create configuration directory if it doesn't exist
    mkdir -p "$CONFIG_DIR" || warn_continue "Failed to create configuration directory."
    
    # Backup current network configuration before making changes
    backup_network_config
    
    # Install required packages
    install_packages
    
    # Detect network interfaces
    detect_interfaces
    
    # Setup Wi-Fi connection
    setup_wifi
    
    # Detect gateway IP
    detect_gateway_ip
    
    # Setup Ethernet interface
    setup_ethernet
    
    # Setup routing
    setup_routing
    
    # Setup firewall and NAT
    setup_firewall
    
    # Setup port forwarding if enabled
    setup_port_forwarding
    
    # Save firewall rules
    save_firewall_rules
    
    # Save runtime configuration
    save_config "$RUNTIME_CONFIG"
    
    # Restart networking services if needed
    if [ -f "/etc/init.d/networking" ]; then
        log "Restarting network services..."
        /etc/init.d/networking restart || warn_continue "Failed to restart networking services."
    else
        log "No networking service found. Skipping restart."
    fi
    
    log "Configuration complete! If both interfaces are active, internet sharing should now be working."
    if [ "$ENABLE_PORT_FORWARDING" = "true" ]; then
        log "Port forwarding is enabled. Traffic to Alpine's WLAN IP will be redirected to $PC_IP."
    fi
    log "To restore settings, run: $0 --restore"
}

# Restore function
restore() {
    display_banner
    
    # Check for root privileges
    check_root
    
    # Load configuration
    if [ -f "$RUNTIME_CONFIG" ]; then
        load_config "$RUNTIME_CONFIG"
    else
        load_config "$CONFIG_PATH"
    fi
    
    # Remove port forwarding rules if enabled
    if [ "$ENABLE_PORT_FORWARDING" = "true" ]; then
        remove_port_forwarding
    fi
    
    # Restore settings
    restore_settings
    
    log "Settings restored successfully."
}

# Main function
main() {
    if [ "$1" = "--restore" ]; then
        restore
    else
        setup
    fi
}

# Run main function with all arguments
main "$@" 