#!/usr/bin/env python3
"""
Network monitoring script for Alpine Wi-Fi Bridge

This script monitors network connectivity and automatically restarts
the network if there are connectivity issues. It also periodically checks
and reinstates iptables rules.
"""
import os
import sys
import time
import subprocess
from itertools import cycle

# Import from our package if available
try:
    from pybridge.utils import log, warn_continue, ensure_root, run_command
    from pybridge.config import load_config
    from pybridge.firewall import setup_iptables_firewall
except ImportError:
    # Fallback for standalone operation
    def log(message):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}")

    def warn_continue(message):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: [WARNING] {message}")

    def ensure_root():
        if os.geteuid() != 0:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: This script must be run as root. Use 'sudo'.")
            sys.exit(1)

    def run_command(command, shell=True, check=False, silent=False):
        try:
            result = subprocess.run(
                command,
                shell=shell,
                check=check,
                stdout=subprocess.PIPE if silent else None,
                stderr=subprocess.PIPE if silent else None,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                warn_continue(f"Command failed: {command}")
            return e

# Configuration
CONFIG_FILE = "/etc/alpine-wifi-bridge/config"
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Targets for ping test
RETRY_INTERVAL = 5      # Interval between tests (seconds)
MAX_RETRY = 3           # Maximum attempts before restarting
RESTART_CMD = "/etc/init.d/networking restart"  # Network restart command
POST_RESTART_DELAY = 2  # Delay after restart (seconds)
IPTABLES_CHECK_INTERVAL = 300  # Check iptables every 5 minutes
DEFAULT_GATEWAY = "192.168.0.1"  # Default gateway if not specified
DEFAULT_ETH_SUBNET = "24"  # Default subnet mask for Ethernet

# Infinite cycle of ping targets for rotation
ping_targets_cycle = cycle(PING_TARGETS)


def load_configuration():
    """Load configuration from the config file or detect interfaces."""
    config = {
        "WLAN_IFACE": None,
        "ETH_IFACE": None,
        "GATEWAY_IP": DEFAULT_GATEWAY,
        "ETH_STATIC_IP": "10.42.0.1",
        "ETH_SUBNET": DEFAULT_ETH_SUBNET,
        "IPTABLES_RULES": "/etc/iptables/rules.v4"
    }
    
    try:
        if "pybridge.config" in sys.modules:
            # Use the pybridge config loader if available
            config.update(load_config(CONFIG_FILE))
        elif os.path.exists(CONFIG_FILE):
            log(f"Loading configuration from {CONFIG_FILE}")
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
            log(f"Loaded configuration: WLAN={config['WLAN_IFACE']}, ETH={config['ETH_IFACE']}, GATEWAY={config['GATEWAY_IP']}")
        else:
            log(f"Config file not found. Will detect interfaces.")
    except Exception as e:
        log(f"Error loading config: {e}")
    
    # If interfaces are not in config, detect them
    if not config["WLAN_IFACE"]:
        try:
            result = run_command("ip link | grep -E '^[0-9]+: wlan' | awk -F': ' '{print $2}' | head -n 1", silent=True)
            if result.returncode == 0:
                config["WLAN_IFACE"] = result.stdout.strip()
                log(f"Detected WLAN interface: {config['WLAN_IFACE']}")
            else:
                # Try to detect by wireless capability
                for iface in os.listdir("/sys/class/net"):
                    if (os.path.exists(f"/sys/class/net/{iface}/wireless") or 
                        os.path.exists(f"/sys/class/net/{iface}/phy80211")):
                        config["WLAN_IFACE"] = iface
                        log(f"Found wireless interface using capability detection: {config['WLAN_IFACE']}")
                        break
        except Exception:
            log(f"Failed to detect WLAN interface")
    
    if not config["ETH_IFACE"]:
        try:
            result = run_command("ip link | grep -E '^[0-9]+: eth' | awk -F': ' '{print $2}' | head -n 1", silent=True)
            if result.returncode == 0:
                config["ETH_IFACE"] = result.stdout.strip()
                log(f"Detected ETH interface: {config['ETH_IFACE']}")
            else:
                # Try to detect by excluding wireless and loopback
                for iface in os.listdir("/sys/class/net"):
                    if (iface != "lo" and 
                        iface != config["WLAN_IFACE"] and
                        not os.path.exists(f"/sys/class/net/{iface}/wireless") and
                        not os.path.exists(f"/sys/class/net/{iface}/phy80211") and
                        os.path.exists(f"/sys/class/net/{iface}/device")):
                        config["ETH_IFACE"] = iface
                        log(f"Found Ethernet interface using capability detection: {config['ETH_IFACE']}")
                        break
        except Exception:
            log(f"Failed to detect ETH interface")
    
    # If gateway is not in config, try to detect it
    if config["GATEWAY_IP"] == DEFAULT_GATEWAY:
        try:
            if config["WLAN_IFACE"]:
                result = run_command(
                    f"ip route | grep 'default via' | grep '{config['WLAN_IFACE']}' | awk '{{print $3}}' | head -n 1", 
                    silent=True
                )
                if result.returncode == 0:
                    detected_gateway = result.stdout.strip()
                    if detected_gateway:
                        config["GATEWAY_IP"] = detected_gateway
                        log(f"Detected gateway IP: {config['GATEWAY_IP']}")
        except Exception:
            log(f"Failed to detect gateway IP, using default: {config['GATEWAY_IP']}")
    
    return config


def is_connected(target):
    """Check connectivity using ping."""
    try:
        result = run_command(f"ping -c 1 -W 1 {target}", silent=True)
        if result.returncode == 0:
            log(f"Connection OK with {target}.")
            return True
        else:
            log(f"Failed to ping {target}.")
            return False
    except Exception as e:
        log(f"Error checking connection: {e}")
        return False


def restart_network():
    """Restart the network interfaces."""
    log("Restarting network...")
    
    # Load configuration
    config = load_configuration()
    
    # Check if the networking service exists
    if os.path.exists("/etc/init.d/networking"):
        run_command(RESTART_CMD)
    else:
        # Alternative method to restart networking
        log("Networking service not found. Using alternative method.")
        
        wlan_iface = config["WLAN_IFACE"]
        if wlan_iface:
            log(f"Restarting WLAN interface {wlan_iface}...")
            run_command(f"ip link set {wlan_iface} down")
            time.sleep(1)
            run_command(f"ip link set {wlan_iface} up")
            time.sleep(1)
            run_command(f"udhcpc -i {wlan_iface}")
            
            # Set default route with the correct gateway
            gateway_ip = config["GATEWAY_IP"]
            if gateway_ip:
                log(f"Setting default route via {gateway_ip}...")
                run_command(f"ip route replace default via {gateway_ip} dev {wlan_iface}")
    
    log(f"Waiting {POST_RESTART_DELAY} seconds for network stabilization...")
    time.sleep(POST_RESTART_DELAY)
    
    # Ensure IP forwarding is enabled after network restart
    log("Ensuring IP forwarding is enabled...")
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("1\n")
    except Exception as e:
        log(f"Error enabling IP forwarding: {e}")


def check_and_fix_iptables(config):
    """Check if essential iptables rules are in place and fix them if not."""
    log("Checking iptables rules...")
    
    wlan_iface = config["WLAN_IFACE"]
    eth_iface = config["ETH_IFACE"]
    
    if not wlan_iface or not eth_iface:
        log(f"Could not find network interfaces. WLAN: {wlan_iface}, ETH: {eth_iface}")
        return
    
    eth_static_ip = config["ETH_STATIC_IP"]
    eth_subnet = config["ETH_SUBNET"]
    subnet = f"{eth_static_ip.rsplit('.', 1)[0]}.0/{eth_subnet}"
    
    try:
        # Check and fix basic NAT rule
        result = run_command(f"iptables -t nat -C POSTROUTING -o {wlan_iface} -j MASQUERADE", silent=True)
        if result.returncode != 0:
            log("Fixing NAT rule...")
            run_command(f"iptables -t nat -A POSTROUTING -o {wlan_iface} -j MASQUERADE")
        
        # Check and fix forwarding rules
        forward_rules = [
            f"iptables -C FORWARD -i {eth_iface} -o {wlan_iface} -m state --state RELATED,ESTABLISHED -j ACCEPT",
            f"iptables -C FORWARD -i {wlan_iface} -o {eth_iface} -j ACCEPT",
            f"iptables -C FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT",
            f"iptables -C FORWARD -i {eth_iface} -j ACCEPT",
            f"iptables -C FORWARD -s {subnet} -d {subnet} -j ACCEPT",
            f"iptables -C FORWARD -p icmp -j ACCEPT"
        ]
        
        for i, rule_check in enumerate(forward_rules):
            result = run_command(f"{rule_check}", silent=True)
            if result.returncode != 0:
                log(f"Fixing forwarding rule {i+1}...")
                # Convert check command to add command
                add_rule = rule_check.replace("-C ", "-A ")
                run_command(add_rule)
        
        # Save iptables rules if they were modified
        iptables_rules = config["IPTABLES_RULES"]
        if iptables_rules:
            log("Saving iptables rules...")
            os.makedirs(os.path.dirname(iptables_rules), exist_ok=True)
            run_command(f"iptables-save > {iptables_rules}")
        
        log("iptables rules have been checked and fixed if needed.")
        
    except Exception as e:
        log(f"Error checking iptables: {e}")


def main():
    """Main monitoring function."""
    fail_count = 0
    last_iptables_check = 0

    log("Starting network monitoring...")
    
    # Load configuration
    config = load_configuration()
    
    # Initial check of iptables rules
    check_and_fix_iptables(config)
    last_iptables_check = time.time()
    
    while True:
        # Check if it's time to verify iptables rules
        current_time = time.time()
        if current_time - last_iptables_check >= IPTABLES_CHECK_INTERVAL:
            check_and_fix_iptables(config)
            last_iptables_check = current_time
            
        target = next(ping_targets_cycle)  # Rotate ping targets
        if is_connected(target):
            fail_count = 0  # Reset failure counter
        else:
            fail_count += 1
            log(f"Connection failed ({fail_count}/{MAX_RETRY}).")

        if fail_count >= MAX_RETRY:
            restart_network()
            # After network restart, check iptables rules
            check_and_fix_iptables(config)
            last_iptables_check = time.time()
            fail_count = 0  # Reset counter after restart

        time.sleep(RETRY_INTERVAL)  # Interval between ping attempts


if __name__ == "__main__":
    # Check if running as root
    ensure_root()
    
    main()
