"""
Port forwarding configuration for Alpine Wi-Fi Bridge
"""
from .utils import log, warn_continue, run_command


def setup_port_forwarding(config):
    """Setup port forwarding from Alpine (WLAN) to PC (ETH)."""
    log("Setting up port forwarding...")
    
    # Check if port forwarding is enabled in config
    if config.get('ENABLE_PORT_FORWARDING', 'false').lower() != 'true':
        log("Port forwarding is disabled in configuration. Skipping.")
        return
    
    # Check if we have necessary parameters
    pc_ip = config.get('PC_IP', '')
    if not pc_ip:
        log("PC_IP is not set in configuration. Skipping port forwarding.")
        return
    
    wlan_iface = config.get('WLAN_IFACE', '')
    if not wlan_iface:
        warn_continue("WLAN interface is not defined. Skipping port forwarding.")
        return
    
    # Get the IP address of the WLAN interface
    result = run_command(f"ip -4 addr show {wlan_iface} | grep -oP 'inet \\K[\\d.]+'", silent=True)
    if result.returncode != 0 or not result.stdout:
        warn_continue("Could not get WLAN IP address. Skipping port forwarding.")
        return
    
    wlan_ip = result.stdout.strip()
    log(f"Setting up port forwarding from {wlan_ip} to {pc_ip}")
    
    # Enable IP forwarding
    run_command("echo 1 > /proc/sys/net/ipv4/ip_forward")
    
    # Add PREROUTING rule to forward all incoming traffic to PC
    run_command(f"iptables -t nat -A PREROUTING -i {wlan_iface} -j DNAT --to-destination {pc_ip}")
    
    # Add POSTROUTING rule for masquerading
    eth_iface = config.get('ETH_IFACE', '')
    if eth_iface:
        run_command(f"iptables -t nat -A POSTROUTING -o {eth_iface} -j MASQUERADE")
    
    log("Port forwarding setup complete")


def remove_port_forwarding(config):
    """Remove port forwarding rules."""
    wlan_iface = config.get('WLAN_IFACE', '')
    pc_ip = config.get('PC_IP', '')
    eth_iface = config.get('ETH_IFACE', '')
    
    if wlan_iface and pc_ip:
        run_command(f"iptables -t nat -D PREROUTING -i {wlan_iface} -j DNAT --to-destination {pc_ip}")
    
    if eth_iface:
        run_command(f"iptables -t nat -D POSTROUTING -o {eth_iface} -j MASQUERADE")
    
    log("Port forwarding rules removed")