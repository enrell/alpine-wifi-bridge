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

# Check for conflicting network management tools
check_network_conflicts() {
    log "Checking for conflicting network management tools..."
    
    # Check for NetworkManager
    if command -v nmcli >/dev/null 2>&1 || [ -f "/etc/init.d/networkmanager" ]; then
        echo "NetworkManager detected, which may conflict with this script."
        echo "Do you want to disable NetworkManager for this session? (y/n)"
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            if [ -f "/etc/init.d/networkmanager" ]; then
                log "Stopping NetworkManager..."
                /etc/init.d/networkmanager stop || warn_continue "Failed to stop NetworkManager."
            elif [ -f "/etc/init.d/NetworkManager" ]; then
                log "Stopping NetworkManager..."
                /etc/init.d/NetworkManager stop || warn_continue "Failed to stop NetworkManager."
            else
                warn_continue "Could not find NetworkManager service to stop."
            fi
        else
            warn_continue "Continuing with NetworkManager active. This may cause conflicts."
        fi
    fi
    
    # Check for systemd-networkd
    if [ -d "/run/systemd/system" ] && systemctl is-active systemd-networkd >/dev/null 2>&1; then
        echo "systemd-networkd detected, which may conflict with this script."
        echo "Do you want to disable systemd-networkd for this session? (y/n)"
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            log "Stopping systemd-networkd..."
            systemctl stop systemd-networkd || warn_continue "Failed to stop systemd-networkd."
        else
            warn_continue "Continuing with systemd-networkd active. This may cause conflicts."
        fi
    fi
    
    # Check for connman
    if command -v connmanctl >/dev/null 2>&1 || [ -f "/etc/init.d/connman" ]; then
        echo "ConnMan detected, which may conflict with this script."
        echo "Do you want to disable ConnMan for this session? (y/n)"
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            if [ -f "/etc/init.d/connman" ]; then
                log "Stopping ConnMan..."
                /etc/init.d/connman stop || warn_continue "Failed to stop ConnMan."
            else
                warn_continue "Could not find ConnMan service to stop."
            fi
        else
            warn_continue "Continuing with ConnMan active. This may cause conflicts."
        fi
    fi
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
    
    # Check for conflicting network management tools
    check_network_conflicts
    
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
    elif [ -f "/etc/init.d/network" ]; then
        log "Restarting network services..."
        /etc/init.d/network restart || warn_continue "Failed to restart networking services."
    else
        log "No networking service found. Manually restarting interfaces..."
        ip link set "$WLAN_IFACE" down && ip link set "$WLAN_IFACE" up
        [ -n "$ETH_IFACE" ] && ip link set "$ETH_IFACE" down && ip link set "$ETH_IFACE" up
    fi
    
    log "Configuration complete! If both interfaces are active, internet sharing should now be working."
    if [ "$ENABLE_PORT_FORWARDING" = "true" ]; then
        if [ -z "$PC_IP" ]; then
            log "Port forwarding is enabled but PC_IP is not set. Port forwarding will not work."
            log "Set PC_IP in your configuration file to enable port forwarding."
        else
            log "Port forwarding is enabled. Traffic to Alpine's WLAN IP will be redirected to $PC_IP."
        fi
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