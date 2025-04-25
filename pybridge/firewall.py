"""
Firewall and NAT configuration for Alpine Wi-Fi Bridge
"""
import os
from .utils import log, warn_continue, run_command, command_exists


def detect_firewall_system():
    """Detect which firewall system to use (nftables or iptables)."""
    # Check if nftables is the primary firewall system
    if command_exists("nft") and not os.path.exists("/proc/net/ip_tables_names"):
        log("Detected nftables as primary firewall system.")
        return "nftables"
    else:
        log("Using iptables for firewall configuration.")
        return "iptables"


def setup_firewall(config):
    """Setup NAT and firewall rules."""
    if not config.get('ETH_IFACE'):
        log("Skipping NAT configuration as no Ethernet interface is available.")
        return
    
    # Detect which firewall system to use
    firewall_type = detect_firewall_system()
    
    if firewall_type == "nftables":
        setup_nftables_firewall(config)
    else:
        setup_iptables_firewall(config)


def setup_nftables_firewall(config):
    """Configure NAT and firewall using nftables."""
    log("Setting up NAT with nftables...")
    
    # Check if nft is available
    if not command_exists("nft"):
        log("nft command not found. Falling back to iptables...")
        setup_iptables_firewall(config)
        return
    
    # Create a basic nftables configuration file
    nft_file = "/etc/nftables/alpine-wifi-bridge.nft"
    os.makedirs(os.path.dirname(nft_file), exist_ok=True)
    
    wlan_iface = config['WLAN_IFACE']
    eth_iface = config['ETH_IFACE']
    eth_static_ip = config['ETH_STATIC_IP']
    eth_subnet = config['ETH_SUBNET']
    
    subnet = f"{eth_static_ip.rsplit('.', 1)[0]}.0/{eth_subnet}"
    
    with open(nft_file, 'w') as f:
        f.write("#!/usr/sbin/nft -f\n\n")
        f.write("flush ruleset\n\n")
        
        # NAT table
        f.write("table ip nat {\n")
        f.write("    chain prerouting {\n")
        f.write("        type nat hook prerouting priority -100; policy accept;\n")
        f.write("    }\n")
        f.write("    \n")
        f.write("    chain postrouting {\n")
        f.write("        type nat hook postrouting priority 100; policy accept;\n")
        f.write(f"        oifname \"{wlan_iface}\" masquerade\n")
        f.write("    }\n")
        f.write("}\n\n")
        
        # Filter table
        f.write("table ip filter {\n")
        f.write("    chain input {\n")
        f.write("        type filter hook input priority 0; policy accept;\n")
        f.write(f"        iifname \"{eth_iface}\" accept\n")
        f.write("        icmp type echo-request accept\n")
        f.write("    }\n")
        f.write("    \n")
        f.write("    chain forward {\n")
        f.write("        type filter hook forward priority 0; policy accept;\n")
        f.write(f"        iifname \"{eth_iface}\" oifname \"{wlan_iface}\" ct state related,established accept\n")
        f.write(f"        iifname \"{wlan_iface}\" oifname \"{eth_iface}\" accept\n")
        f.write("        ct state related,established accept\n")
        f.write(f"        iifname \"{eth_iface}\" accept\n")
        f.write(f"        ip saddr {subnet} ip daddr {subnet} accept\n")
        f.write("        icmp type echo-request accept\n")
        f.write("    }\n")
        f.write("    \n")
        f.write("    chain output {\n")
        f.write("        type filter hook output priority 0; policy accept;\n")
        f.write(f"        oifname \"{wlan_iface}\" accept\n")
        f.write("        icmp type echo-request accept\n")
        f.write("    }\n")
        f.write("}\n")
    
    # Apply the nftables rules
    log("Applying nftables rules...")
    result = run_command(f"nft -f {nft_file}")
    if result.returncode != 0:
        warn_continue("Failed to apply nftables rules. Falling back to iptables...")
        setup_iptables_firewall(config)
        return
    
    # Make sure nftables service is enabled
    if os.path.exists("/etc/init.d/nftables"):
        run_command("rc-update add nftables default 2>/dev/null")
    
    # Create a script to load nftables rules at boot
    nft_script = "/etc/local.d/nftables.start"
    os.makedirs(os.path.dirname(nft_script), exist_ok=True)
    
    with open(nft_script, 'w') as f:
        f.write("#!/bin/sh\n")
        f.write("# Load nftables rules\n")
        f.write(f"/usr/sbin/nft -f {nft_file}\n")
        f.write("exit 0\n")
    
    # Make the script executable
    os.chmod(nft_script, 0o755)


def setup_iptables_firewall(config):
    """Configure NAT and firewall using iptables."""
    log("Setting up NAT with iptables...")
    
    wlan_iface = config['WLAN_IFACE']
    eth_iface = config['ETH_IFACE']
    eth_static_ip = config['ETH_STATIC_IP']
    eth_subnet = config['ETH_SUBNET']
    
    # Basic NAT configuration - check before adding
    result = run_command(f"iptables -t nat -C POSTROUTING -o {wlan_iface} -j MASQUERADE 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -t nat -A POSTROUTING -o {wlan_iface} -j MASQUERADE")
    
    result = run_command(f"iptables -C FORWARD -i {eth_iface} -o {wlan_iface} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A FORWARD -i {eth_iface} -o {wlan_iface} -m state --state RELATED,ESTABLISHED -j ACCEPT")
    
    result = run_command(f"iptables -C FORWARD -i {wlan_iface} -o {eth_iface} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A FORWARD -i {wlan_iface} -o {eth_iface} -j ACCEPT")
    
    # Enhanced rules to allow all traffic to pass freely - check before adding
    log("Setting up enhanced rules for unrestricted network communication...")
    
    # Allow all established connections
    result = run_command("iptables -C FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command("iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT")
    
    # Allow all outgoing connections
    result = run_command(f"iptables -C FORWARD -i {eth_iface} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A FORWARD -i {eth_iface} -j ACCEPT")
    
    # Allow all traffic between devices in the local network
    subnet = f"{eth_static_ip.rsplit('.', 1)[0]}.0/{eth_subnet}"
    result = run_command(f"iptables -C FORWARD -s {subnet} -d {subnet} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A FORWARD -s {subnet} -d {subnet} -j ACCEPT")
    
    # Allow all traffic to the notebook (bridging device)
    result = run_command(f"iptables -C INPUT -i {eth_iface} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A INPUT -i {eth_iface} -j ACCEPT")
    
    # Allow traffic from the notebook to any destination
    result = run_command(f"iptables -C OUTPUT -o {wlan_iface} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command(f"iptables -A OUTPUT -o {wlan_iface} -j ACCEPT")
    
    # Allow ICMP (ping) traffic in all directions
    result = run_command("iptables -C INPUT -p icmp -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command("iptables -A INPUT -p icmp -j ACCEPT")
    
    result = run_command("iptables -C OUTPUT -p icmp -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command("iptables -A OUTPUT -p icmp -j ACCEPT")
    
    result = run_command("iptables -C FORWARD -p icmp -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        run_command("iptables -A FORWARD -p icmp -j ACCEPT")


def save_firewall_rules(config):
    """Save firewall rules to make them persistent after reboot."""
    # If we're using nftables, rules are already saved in the setup_nftables_firewall function
    if detect_firewall_system() == "nftables":
        log("nftables rules already saved during setup.")
        return
    
    log("Saving iptables rules...")
    
    iptables_rules = config['IPTABLES_RULES']
    iptables_script = config['IPTABLES_SCRIPT']
    
    if os.path.exists("/etc/init.d/iptables"):
        run_command("/etc/init.d/iptables save")
    else:
        # Alternative method to save iptables rules for Alpine Linux
        os.makedirs(os.path.dirname(iptables_rules), exist_ok=True)
        run_command(f"iptables-save > {iptables_rules}")
        
        # Create a local.d script to load iptables rules at boot (Alpine Linux approach)
        os.makedirs(os.path.dirname(iptables_script), exist_ok=True)
        
        with open(iptables_script, 'w') as f:
            f.write("#!/bin/sh\n")
            f.write("# Load iptables rules\n")
            f.write(f"/sbin/iptables-restore < {iptables_rules}\n")
            f.write("exit 0\n")
        
        os.chmod(iptables_script, 0o755)
        
        # Ensure local service is enabled
        run_command("rc-update add local default 2>/dev/null")