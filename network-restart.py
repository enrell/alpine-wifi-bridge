#!/usr/bin/env python3
import os
import time
import subprocess
from itertools import cycle

# Configurations
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Targets for ping test to check connectivity
RETRY_INTERVAL = 5      # Interval between tests (in seconds) - 5s to avoid locks but be fast
MAX_RETRY = 3           # Maximum number of attempts before restarting the network
RESTART_CMD = "/etc/init.d/networking restart"  # Command to restart the network
POST_RESTART_DELAY = 2  # Delay after restarting the network (in seconds)
IPTABLES_CHECK_INTERVAL = 300  # Check iptables rules every 5 minutes

# Infinite cycle of DNS servers for rotation
ping_targets_cycle = cycle(PING_TARGETS)

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
    os.system(RESTART_CMD)
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Waiting {POST_RESTART_DELAY} seconds for stabilization...")
    time.sleep(POST_RESTART_DELAY)
    
    # Ensure IP forwarding is enabled after network restart
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Ensuring IP forwarding is enabled...")
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

def check_and_fix_iptables():
    """Checks if the essential iptables rules are in place and fixes them if not."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Checking iptables rules...")
    
    # Get network interfaces
    try:
        # Find Wi-Fi interface
        wlan_iface_cmd = "ip link | grep -E '^[0-9]+: wlan' | awk -F': ' '{print $2}' | head -n 1"
        wlan_iface = subprocess.check_output(wlan_iface_cmd, shell=True).decode().strip()
        
        # Find Ethernet interface
        eth_iface_cmd = "ip link | grep -E '^[0-9]+: eth' | awk -F': ' '{print $2}' | head -n 1"
        eth_iface = subprocess.check_output(eth_iface_cmd, shell=True).decode().strip()
        
        if not wlan_iface or not eth_iface:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Could not find network interfaces. WLAN: {wlan_iface}, ETH: {eth_iface}")
            return
            
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
    main()
