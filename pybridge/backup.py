"""
Backup and restore functionality for Alpine Wi-Fi Bridge
"""
import os
from .utils import log, warn_continue, run_command


def backup_network_config(config):
    """Create backup of current network configuration."""
    log("Creating backup of network configuration...")
    
    # Create backup directory if it doesn't exist
    os.makedirs(config['BACKUP_DIR'], exist_ok=True)
    
    # Check if backup already exists
    if not os.path.exists(f"{config['BACKUP_DIR']}/network_config.bak"):
        log("Backing up current network configuration...")
        
        # Backup IP forwarding state
        try:
            with open("/proc/sys/net/ipv4/ip_forward", "r") as src:
                with open(f"{config['BACKUP_DIR']}/ip_forward.bak", "w") as dst:
                    dst.write(src.read())
        except Exception as e:
            warn_continue(f"Failed to backup IP forwarding state: {e}")
        
        # Backup iptables rules
        run_command(f"iptables-save > {config['BACKUP_DIR']}/iptables.bak")
        
        # Backup interface configurations
        run_command(f"ip addr show > {config['BACKUP_DIR']}/ip_addr.bak")
        run_command(f"ip route show > {config['BACKUP_DIR']}/ip_route.bak")
        
        # Mark backup as complete
        with open(f"{config['BACKUP_DIR']}/network_config.bak", "w") as f:
            f.write(f"Backup completed\n")
        
        log("Network configuration backup completed.")
    else:
        log("Network configuration backup already exists. Skipping backup.")


def restore_settings(config):
    """Restore network settings to original state."""
    log("Restoring network settings to the original state...")

    # Disable IP forwarding
    log("Disabling IP forwarding...")
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("0\n")
    except Exception as e:
        warn_continue(f"Failed to disable IP forwarding: {e}")
    
    # Remove IP forwarding rule in sysctl.conf if exists
    if os.path.exists("/etc/sysctl.conf"):
        with open("/etc/sysctl.conf", "r") as f:
            lines = f.readlines()
        
        with open("/etc/sysctl.conf", "w") as f:
            for line in lines:
                if "net.ipv4.ip_forward=1" not in line:
                    f.write(line)
    
    # Get interface and subnet information
    wlan_iface = config.get('WLAN_IFACE', '')
    eth_iface = config.get('ETH_IFACE', '')
    eth_static_ip = config.get('ETH_STATIC_IP', '10.42.0.1')
    eth_subnet = config.get('ETH_SUBNET', '24')
    gateway_ip = config.get('GATEWAY_IP', '')

    # Remove NAT and forwarding iptables rules
    log("Removing iptables rules...")
    
    # Basic NAT rules
    if wlan_iface:
        run_command(f"iptables -t nat -D POSTROUTING -o {wlan_iface} -j MASQUERADE 2>/dev/null")
    
    if eth_iface and wlan_iface:
        run_command(f"iptables -D FORWARD -i {eth_iface} -o {wlan_iface} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null")
        run_command(f"iptables -D FORWARD -i {wlan_iface} -o {eth_iface} -j ACCEPT 2>/dev/null")
    
    # Enhanced rules
    log("Removing enhanced iptables rules...")
    run_command(f"iptables -D FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null")
    
    if eth_iface:
        run_command(f"iptables -D FORWARD -i {eth_iface} -j ACCEPT 2>/dev/null")
        subnet_prefix = eth_static_ip.rsplit('.', 1)[0] + ".0"
        run_command(f"iptables -D FORWARD -s {subnet_prefix}/{eth_subnet} -d {subnet_prefix}/{eth_subnet} -j ACCEPT 2>/dev/null")
        run_command(f"iptables -D INPUT -i {eth_iface} -j ACCEPT 2>/dev/null")
    
    if wlan_iface:
        run_command(f"iptables -D OUTPUT -o {wlan_iface} -j ACCEPT 2>/dev/null")
    
    # Remove ICMP rules
    run_command(f"iptables -D INPUT -p icmp -j ACCEPT 2>/dev/null")
    run_command(f"iptables -D OUTPUT -p icmp -j ACCEPT 2>/dev/null")
    run_command(f"iptables -D FORWARD -p icmp -j ACCEPT 2>/dev/null")

    # Remove static IP from Ethernet interface
    if eth_iface:
        log(f"Removing static IP from Ethernet interface ({eth_iface})...")
        run_command(f"ip addr flush dev {eth_iface}")

    # Remove default route for Wi-Fi
    if wlan_iface and gateway_ip:
        run_command(f"ip route del default via {gateway_ip} dev {wlan_iface} 2>/dev/null")

    # Stop wpa_supplicant
    log("Stopping wpa_supplicant service...")
    run_command("pkill wpa_supplicant")

    # Down network interfaces
    if wlan_iface:
        run_command(f"ip link set {wlan_iface} down")
    
    if eth_iface:
        run_command(f"ip link set {eth_iface} down")

    # Restore from backup if available
    backup_path = f"{config['BACKUP_DIR']}/iptables.bak"
    if os.path.exists(backup_path):
        log("Restoring iptables rules from backup...")
        run_command(f"iptables-restore < {backup_path}")

    log("Network settings restored successfully.")