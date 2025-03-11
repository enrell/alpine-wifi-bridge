#!/bin/sh
# Utility functions for the Alpine Wi-Fi Bridge

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

# Load configuration from file
load_config() {
    local config_file="$1"
    
    if [ -f "$config_file" ]; then
        log "Loading configuration from $config_file"
        . "$config_file"
    else
        error_exit "Configuration file not found: $config_file"
    fi
    
    # Set default values for empty settings
    if [ -z "$CONFIG_DIR" ]; then
        CONFIG_DIR="/etc/alpine-wifi-bridge"
    fi
    
    if [ -z "$BACKUP_DIR" ]; then
        BACKUP_DIR="/etc/alpine-wifi-bridge/backup"
    fi
    
    if [ -z "$ETH_STATIC_IP" ]; then
        ETH_STATIC_IP="10.42.0.1"
    fi
    
    if [ -z "$ETH_SUBNET" ]; then
        ETH_SUBNET="24"
    fi
    
    if [ -z "$WPA_CONF" ]; then
        WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
    fi
    
    if [ -z "$IPTABLES_RULES" ]; then
        IPTABLES_RULES="/etc/iptables/rules.v4"
    fi
    
    if [ -z "$IPTABLES_SCRIPT" ]; then
        IPTABLES_SCRIPT="/etc/local.d/iptables.start"
    fi
}

# Detect network interfaces if not specified in config
detect_interfaces() {
    # Detect WLAN interface if not specified
    if [ -z "$WLAN_IFACE" ]; then
        log "Detecting Wi-Fi interface..."
        WLAN_IFACE=$(ip link | grep -E "^[0-9]+: wlan" | awk -F': ' '{print $2}' | head -n 1)
        if [ -z "$WLAN_IFACE" ]; then
            error_exit "No Wi-Fi interface found. Ensure your device has a Wi-Fi adapter."
        fi
    fi
    log "Using Wi-Fi interface: $WLAN_IFACE"
    
    # Detect Ethernet interface if not specified
    if [ -z "$ETH_IFACE" ]; then
        log "Detecting Ethernet interface..."
        ETH_IFACE=$(ip link | grep -E "^[0-9]+: eth" | awk -F': ' '{print $2}' | head -n 1)
        if [ -z "$ETH_IFACE" ]; then
            warn_continue "No Ethernet interface found. Skipping Ethernet configuration."
        else
            log "Using Ethernet interface: $ETH_IFACE"
        fi
    else
        log "Using configured Ethernet interface: $ETH_IFACE"
    fi
}

# Function to detect gateway IP
detect_gateway_ip() {
    if [ -n "$GATEWAY_IP" ]; then
        log "Using configured gateway IP: $GATEWAY_IP"
        return
    fi
    
    log "Detecting gateway IP address..."
    
    # Try to get the gateway IP from the routing table
    DETECTED_GW=$(ip route | grep "default via" | grep "$WLAN_IFACE" | awk '{print $3}' | head -n 1)
    
    if [ -n "$DETECTED_GW" ]; then
        log "Detected gateway IP: $DETECTED_GW"
        GATEWAY_IP="$DETECTED_GW"
    else
        log "Could not auto-detect gateway IP. Using default: 192.168.0.1"
        GATEWAY_IP="192.168.0.1"
        
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

# Check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "This script must be run as root. Use 'sudo'."
    fi
}

# Save current configuration to file
save_config() {
    local config_file="$1"
    
    log "Saving configuration to $config_file..."
    mkdir -p "$(dirname "$config_file")" || warn_continue "Failed to create configuration directory."
    
    cat > "$config_file" << EOF
# Alpine Wi-Fi Bridge Configuration
# Generated on $(date)
WLAN_IFACE="$WLAN_IFACE"
ETH_IFACE="$ETH_IFACE"
GATEWAY_IP="$GATEWAY_IP"
ETH_STATIC_IP="$ETH_STATIC_IP"
ETH_SUBNET="$ETH_SUBNET"
WPA_CONF="$WPA_CONF"
CONFIG_DIR="$CONFIG_DIR"
BACKUP_DIR="$BACKUP_DIR"
IPTABLES_RULES="$IPTABLES_RULES"
IPTABLES_SCRIPT="$IPTABLES_SCRIPT"
EOF
} 