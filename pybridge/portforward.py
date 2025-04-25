"""
Port forwarding configuration for Alpine Wi-Fi Bridge
"""
import re
import subprocess
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
        warn_continue("Could not determine IP address of WLAN interface. Skipping port forwarding.")
        return
    
    wlan_ip = result.stdout.strip()
    log(f"Setting up traffic redirection from {wlan_ip} to {pc_ip}")
    
    # DNAT rule to redirect all traffic coming to the Alpine machine to the PC
    result = run_command(f"iptables -t nat -C PREROUTING -d {wlan_ip} -j DNAT --to-destination {pc_ip} 2>/dev/null", silent=True)
    if result.returncode != 0:
        result = run_command(f"iptables -t nat -A PREROUTING -d {wlan_ip} -j DNAT --to-destination {pc_ip}")
        if result.returncode != 0:
            warn_continue("Failed to set up DNAT rule for port forwarding.")
    
    # Allow forwarding of packets to the PC
    result = run_command(f"iptables -C FORWARD -d {pc_ip} -j ACCEPT 2>/dev/null", silent=True)
    if result.returncode != 0:
        result = run_command(f"iptables -A FORWARD -d {pc_ip} -j ACCEPT")
        if result.returncode != 0:
            warn_continue("Failed to allow forwarding to PC.")
    
    # Add masquerading rule if it doesn't exist already
    result = run_command(f"iptables -t nat -C POSTROUTING -o {wlan_iface} -j MASQUERADE 2>/dev/null", silent=True)
    if result.returncode != 0:
        result = run_command(f"iptables -t nat -A POSTROUTING -o {wlan_iface} -j MASQUERADE")
        if result.returncode != 0:
            warn_continue("Failed to set up masquerading for responses.")
    
    log(f"Port forwarding setup complete. Traffic to {wlan_ip} will be redirected to {pc_ip}")
    
    # Store the WLAN_IP in config for later use when removing rules
    config['WLAN_IP'] = wlan_ip


def remove_port_forwarding(config):
    """Remove port forwarding rules."""
    # Get the IP addresses
    wlan_ip = config.get('WLAN_IP', '')
    pc_ip = config.get('PC_IP', '')
    wlan_iface = config.get('WLAN_IFACE', '')
    
    # If WLAN_IP is not in config, try to detect it
    if not wlan_ip and wlan_iface:
        result = run_command(f"ip -4 addr show {wlan_iface} | grep -oP 'inet \\K[\\d.]+'", silent=True)
        if result.returncode == 0 and result.stdout:
            wlan_ip = result.stdout.strip()
    
    if not wlan_ip or not pc_ip:
        warn_continue("Could not determine IP addresses for removing port forwarding rules.")
        return
    
    log(f"Removing port forwarding from {wlan_ip} to {pc_ip}")
    
    # Remove DNAT rule
    run_command(f"iptables -t nat -D PREROUTING -d {wlan_ip} -j DNAT --to-destination {pc_ip} 2>/dev/null")
    
    # Remove forward rule
    run_command(f"iptables -D FORWARD -d {pc_ip} -j ACCEPT 2>/dev/null")
    
    log("Port forwarding rules removed.")