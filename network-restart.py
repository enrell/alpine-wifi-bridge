#!/usr/bin/env python3
import os
import time
import subprocess
import json
from itertools import cycle

# Configuration
CONFIG_FILE = "/etc/alpine-wifi-bridge/config"
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Targets for ping test to check connectivity
RETRY_INTERVAL = 5      # Interval between tests (in seconds) - 5s to avoid locks but be fast
MAX_RETRY = 3           # Maximum number of attempts before restarting the network
RESTART_CMD = "/etc/init.d/networking restart"  # Command to restart the network
POST_RESTART_DELAY = 2  # Delay after restarting the network (in seconds)
IPTABLES_CHECK_INTERVAL = 300  # Check iptables rules every 5 minutes
DEFAULT_GATEWAY = "192.168.0.1"  # Default gateway if not specified in config

# Infinite cycle of DNS servers for rotation
ping_targets_cycle = cycle(PING_TARGETS)

def load_config():
    """Load configuration from the config file if it exists."""
    config = {
        "WLAN_IFACE": None,
        "ETH_IFACE": None,
        "GATEWAY_IP": DEFAULT_GATEWAY
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Loading configuration from {CONFIG_FILE}")
            with open(CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            if key in config:
                                config[key] = value
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Loaded configuration: WLAN={config['WLAN_IFACE']}, ETH={config['ETH_IFACE']}, GATEWAY={config['GATEWAY_IP']}")
        else:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Config file not found. Will detect interfaces.")
    except Exception as e:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Error loading config: {e}")
    
    # If interfaces are not in config, detect them
    if not config["WLAN_IFACE"]:
        try:
            wlan_iface_cmd = "ip link | grep -E '^[0-9]+: wlan' | awk -F': ' '{print $2}' | head -n 1"
            config["WLAN_IFACE"] = subprocess.check_output(wlan_iface_cmd, shell=True).decode().strip()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Detected WLAN interface: {config['WLAN_IFACE']}")
        except:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Failed to detect WLAN interface")
    
    if not config["ETH_IFACE"]:
        try:
            eth_iface_cmd = "ip link | grep -E '^[0-9]+: eth' | awk -F': ' '{print $2}' | head -n 1"
            config["ETH_IFACE"] = subprocess.check_output(eth_iface_cmd, shell=True).decode().strip()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Detected ETH interface: {config['ETH_IFACE']}")
        except:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Failed to detect ETH interface")
    
    # If gateway is not in config, try to detect it
    if config["GATEWAY_IP"] == DEFAULT_GATEWAY:
        try:
            if config["WLAN_IFACE"]:
                gateway_cmd = f"ip route | grep 'default via' | grep '{config['WLAN_IFACE']}' | awk '{{print $3}}' | head -n 1"
                detected_gateway = subprocess.check_output(gateway_cmd, shell=True).decode().strip()
                if detected_gateway:
                    config["GATEWAY_IP"] = detected_gateway
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Detected gateway IP: {config['GATEWAY_IP']}")
        except:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Failed to detect gateway IP, using default: {config['GATEWAY_IP']}")
    
    return config

def is_connected(target):
    """Checks connectivity with a target using ping."""
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", target], stderr=subprocess.DEVNULL)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Connection OK with {target}.")
        return True
    except subprocess.CalledProcessError:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Failed to ping {target}.")
        return False

def restart_network():
    """Restarts the network service with an additional delay."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Restarting network...")
    
    # Load configuration
    config = load_config()
    
    # Check if the networking service exists
    if os.path.exists("/etc/init.d/networking"):
        os.system(RESTART_CMD)
    else:
        # Alternative method to restart networking
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Networking service not found. Using alternative method.")
        
        if config["WLAN_IFACE"]:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Restarting WLAN interface {config['WLAN_IFACE']}...")
            os.system(f"ip link set {config['WLAN_IFACE']} down")
            time.sleep(1)
            os.system(f"ip link set {config['WLAN_IFACE']} up")
            time.sleep(1)
            os.system(f"udhcpc -i {config['WLAN_IFACE']}")
            
            # Set default route with the correct gateway
            if config["GATEWAY_IP"]:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Setting default route via {config['GATEWAY_IP']}...")
                os.system(f"ip route replace default via {config['GATEWAY_IP']} dev {config['WLAN_IFACE']}")
    
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Waiting {POST_RESTART_DELAY} seconds for stabilization...")
    time.sleep(POST_RESTART_DELAY)
    
    # Ensure IP forwarding is enabled after network restart
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Ensuring IP forwarding is enabled...")
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

def check_and_fix_iptables():
    """Checks if the essential iptables rules are in place and fixes them if not."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Checking iptables rules...")
    
    # Get network interfaces from config
    config = load_config()
    wlan_iface = config["WLAN_IFACE"]
    eth_iface = config["ETH_IFACE"]
    
    if not wlan_iface or not eth_iface:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Could not find network interfaces. WLAN: {wlan_iface}, ETH: {eth_iface}")
        return
        
    try:
        # Check and fix basic NAT rule
        nat_rule_check = f"iptables -t nat -C POSTROUTING -o {wlan_iface} -j MASQUERADE"
        if os.system(nat_rule_check + " 2>/dev/null") != 0:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Fixing NAT rule...")
            os.system(f"iptables -t nat -A POSTROUTING -o {wlan_iface} -j MASQUERADE")
        
        # Check and fix forwarding rules
        forward_rules = [
            f"iptables -C FORWARD -i {eth_iface} -o {wlan_iface} -m state --state RELATED,ESTABLISHED -j ACCEPT",
            f"iptables -C FORWARD -i {wlan_iface} -o {eth_iface} -j ACCEPT",
            f"iptables -C FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT",
            f"iptables -C FORWARD -i {eth_iface} -j ACCEPT",
            f"iptables -C FORWARD -s 10.42.0.0/24 -d 10.42.0.0/24 -j ACCEPT",
            f"iptables -C FORWARD -p icmp -j ACCEPT"
        ]
        
        for i, rule_check in enumerate(forward_rules):
            if os.system(rule_check + " 2>/dev/null") != 0:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Fixing forwarding rule {i+1}...")
                # Convert check command to add command
                add_rule = rule_check.replace("-C ", "-A ")
                os.system(add_rule)
                
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: iptables rules have been checked and fixed if needed.")
        
    except Exception as e:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Error checking iptables: {e}")

def main():
    """Main function to monitor and fix connection issues."""
    fail_count = 0
    last_iptables_check = 0

    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Starting network monitoring...")
    
    # Load configuration
    config = load_config()
    
    # Initial check of iptables rules
    check_and_fix_iptables()
    last_iptables_check = time.time()
    
    while True:
        # Check if it's time to verify iptables rules
        current_time = time.time()
        if current_time - last_iptables_check >= IPTABLES_CHECK_INTERVAL:
            check_and_fix_iptables()
            last_iptables_check = current_time
            
        target = next(ping_targets_cycle)  # Switch to the next DNS server
        if is_connected(target):
            fail_count = 0  # Reset failure counter
        else:
            fail_count += 1
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Connection failed ({fail_count}/{MAX_RETRY}).")

        if fail_count >= MAX_RETRY:
            restart_network()
            # After network restart, check iptables rules
            check_and_fix_iptables()
            last_iptables_check = time.time()
            fail_count = 0  # Reset counter after restarting the network

        time.sleep(RETRY_INTERVAL)  # Interval between ping attempts

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: This script must be run as root. Use 'sudo'.")
        exit(1)
    
    main()
