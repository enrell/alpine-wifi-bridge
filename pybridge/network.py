"""
Network configuration for Alpine Wi-Fi Bridge
"""
import os
import tempfile
from .utils import log, warn_continue, error_exit, run_command, command_exists


def install_packages():
    """Install required packages."""
    log("Installing required packages...")
    
    # Update package repositories
    result = run_command("apk update")
    if result.returncode != 0:
        error_exit("Failed to update package lists.")
    
    # Get Alpine version
    alpine_version = "unknown"
    if os.path.exists("/etc/alpine-release"):
        with open("/etc/alpine-release", "r") as f:
            alpine_version = f.read().strip()
    
    log(f"Detected Alpine Linux version: {alpine_version}")
    
    # Install base networking packages
    log("Installing base networking packages...")
    result = run_command("apk add --no-cache wireless-tools wpa_supplicant")
    if result.returncode != 0:
        error_exit("Failed to install wireless packages.")
    
    # Check if we need iptables or iptables-nft
    if command_exists("nft"):
        log("nftables detected, installing iptables-nft for compatibility...")
        result = run_command("apk add --no-cache iptables-nft")
        if result.returncode != 0:
            log("Failed to install iptables-nft, falling back to standard iptables...")
            result = run_command("apk add --no-cache iptables")
            if result.returncode != 0:
                error_exit("Failed to install iptables packages.")
    else:
        log("Installing standard iptables...")
        result = run_command("apk add --no-cache iptables")
        if result.returncode != 0:
            error_exit("Failed to install iptables packages.")
    
    # Create required directories
    for directory in ["/etc/wpa_supplicant", "/etc/iptables", "/etc/local.d"]:
        os.makedirs(directory, exist_ok=True)


def detect_interfaces(config):
    """Detect and configure network interfaces."""
    # Detect WLAN interface if not specified
    if not config.get('WLAN_IFACE'):
        log("Detecting Wi-Fi interface...")
        
        # First try traditional naming (wlan0)
        result = run_command("ip link | grep -E '^[0-9]+: wlan' | awk -F': ' '{print $2}' | head -n 1", silent=True)
        wlan_iface = result.stdout.strip() if result.returncode == 0 else ""
        
        # If not found, try to detect by wireless capability
        if not wlan_iface:
            for iface in os.listdir("/sys/class/net"):
                if (os.path.exists(f"/sys/class/net/{iface}/wireless") or 
                    os.path.exists(f"/sys/class/net/{iface}/phy80211")):
                    wlan_iface = iface
                    log(f"Found wireless interface using capability detection: {wlan_iface}")
                    break
        
        # If still not found, error out
        if not wlan_iface:
            error_exit("No Wi-Fi interface found. Ensure your device has a Wi-Fi adapter.")
        
        config['WLAN_IFACE'] = wlan_iface
    
    log(f"Using Wi-Fi interface: {config['WLAN_IFACE']}")
    
    # Detect Ethernet interface if not specified
    if not config.get('ETH_IFACE'):
        log("Detecting Ethernet interface...")
        
        # First try traditional naming (eth0)
        result = run_command("ip link | grep -E '^[0-9]+: eth' | awk -F': ' '{print $2}' | head -n 1", silent=True)
        eth_iface = result.stdout.strip() if result.returncode == 0 else ""
        
        # If not found, try to detect by type and exclude the wireless interface
        if not eth_iface:
            for iface in os.listdir("/sys/class/net"):
                # Skip loopback and wireless interfaces
                if (iface != "lo" and 
                    iface != config['WLAN_IFACE'] and
                    not os.path.exists(f"/sys/class/net/{iface}/wireless") and
                    not os.path.exists(f"/sys/class/net/{iface}/phy80211") and
                    os.path.exists(f"/sys/class/net/{iface}/device")):
                    eth_iface = iface
                    log(f"Found Ethernet interface using capability detection: {eth_iface}")
                    break
        
        if not eth_iface:
            warn_continue("No Ethernet interface found. Skipping Ethernet configuration.")
        else:
            config['ETH_IFACE'] = eth_iface
            log(f"Using Ethernet interface: {config['ETH_IFACE']}")
    else:
        log(f"Using configured Ethernet interface: {config['ETH_IFACE']}")


def detect_gateway_ip(config):
    """Detect and configure gateway IP address."""
    if config.get('GATEWAY_IP'):
        log(f"Using configured gateway IP: {config['GATEWAY_IP']}")
        return
    
    log("Detecting gateway IP address...")
    
    # Try to get the gateway IP from the routing table
    result = run_command(
        f"ip route | grep 'default via' | grep '{config['WLAN_IFACE']}' | awk '{{print $3}}' | head -n 1", 
        silent=True
    )
    detected_gw = result.stdout.strip() if result.returncode == 0 else ""
    
    if detected_gw:
        log(f"Detected gateway IP: {detected_gw}")
        config['GATEWAY_IP'] = detected_gw
    else:
        log("Could not auto-detect gateway IP. Using default: 192.168.0.1")
        config['GATEWAY_IP'] = "192.168.0.1"
        
        # Ask user if they want to specify a different gateway
        response = input("Do you want to specify a different gateway IP? (y/n): ").strip().lower()
        if response == 'y':
            custom_gateway = input("Enter the gateway IP address: ").strip()
            if custom_gateway:
                config['GATEWAY_IP'] = custom_gateway
                log(f"Using custom gateway IP: {config['GATEWAY_IP']}")


def setup_wifi(config):
    """Configure Wi-Fi connection."""
    log("Setting up Wi-Fi connection...")
    
    wpa_conf = config['WPA_CONF']
    
    # Configure Wi-Fi if no configuration exists
    if not os.path.exists(wpa_conf):
        log("Wi-Fi configuration not found. Creating a new one...")
        
        ssid = input("Enter the SSID of the Wi-Fi network: ").strip()
        password = input("Enter the password for the Wi-Fi network: ")
        
        if not ssid:
            error_exit("SSID cannot be empty.")
        if not password:
            error_exit("Password cannot be empty.")
        
        # Create wpa_supplicant directory if it doesn't exist
        os.makedirs(os.path.dirname(wpa_conf), exist_ok=True)
        
        # Handle special characters in passwords by using a temporary file
        log("Generating wpa_supplicant configuration...")
        
        # Create a temporary file for the password
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(password)
        
        try:
            # Use wpa_passphrase with the password file
            result = run_command(f"wpa_passphrase '{ssid}' \"$(cat {temp_path})\" > {wpa_conf} 2>/dev/null")
            
            # Secure delete the temporary file
            os.unlink(temp_path)
            
            # Check if the configuration was created successfully
            if not os.path.exists(wpa_conf) or os.path.getsize(wpa_conf) == 0:
                log("Failed to generate configuration with wpa_passphrase. Creating manual configuration...")
                
                # Create a basic configuration manually
                with open(wpa_conf, 'w') as f:
                    f.write("ctrl_interface=/var/run/wpa_supplicant\n")
                    f.write("update_config=1\n\n")
                    f.write("network={\n")
                    f.write(f"    ssid=\"{ssid}\"\n")
                    f.write(f"    psk=\"{password}\"\n")
                    f.write("    key_mgmt=WPA-PSK\n")
                    f.write("}\n")
                
                log("Manual Wi-Fi configuration created.")
            else:
                log(f"Wi-Fi configuration saved to {wpa_conf}.")
        except Exception as e:
            error_exit(f"Failed to create Wi-Fi configuration: {e}")
    else:
        log(f"Using existing Wi-Fi configuration at {wpa_conf}.")

    # Check if wpa_supplicant is already running
    result = run_command("pgrep -x wpa_supplicant", silent=True)
    if result.returncode != 0:
        log(f"Connecting to Wi-Fi using {config['WLAN_IFACE']}...")
        result = run_command(f"wpa_supplicant -B -i {config['WLAN_IFACE']} -c {wpa_conf}")
        if result.returncode != 0:
            error_exit("Failed to start wpa_supplicant. Check your Wi-Fi configuration.")
    else:
        log("wpa_supplicant is already running. Skipping Wi-Fi connection setup.")

    # Check if interface already has an IP address
    result = run_command(f"ip addr show {config['WLAN_IFACE']} | grep 'inet '", silent=True)
    if result.returncode != 0:
        log(f"Requesting IP for {config['WLAN_IFACE']} via DHCP...")
        result = run_command(f"udhcpc -i {config['WLAN_IFACE']} -t 10 -T 2")
        if result.returncode != 0:
            error_exit(f"Failed to obtain an IP address for {config['WLAN_IFACE']}.")
    else:
        log(f"{config['WLAN_IFACE']} already has an IP address. Skipping DHCP request.")
    
    # Verify connectivity
    log("Verifying network connectivity...")
    result = run_command("ping -c 1 -W 5 8.8.8.8", silent=True)
    if result.returncode == 0:
        log("Network connectivity confirmed.")
    else:
        warn_continue("Could not verify internet connectivity. The Wi-Fi connection may not be working properly.")


def setup_ethernet(config):
    """Configure Ethernet interface with static IP."""
    if not config.get('ETH_IFACE'):
        warn_continue("No Ethernet interface found. Skipping Ethernet configuration.")
        return
    
    log("Setting up Ethernet interface...")
    
    eth_iface = config['ETH_IFACE']
    eth_static_ip = config['ETH_STATIC_IP']
    eth_subnet = config['ETH_SUBNET']
    
    # Check if the interface already has the static IP
    result = run_command(f"ip addr show {eth_iface} | grep '{eth_static_ip}/{eth_subnet}'", silent=True)
    if result.returncode != 0:
        log(f"Setting up static IP for {eth_iface}...")
        run_command(f"ip addr flush dev {eth_iface}")
        result = run_command(f"ip addr add {eth_static_ip}/{eth_subnet} dev {eth_iface}")
        if result.returncode != 0:
            warn_continue(f"Failed to set IP for {eth_iface}.")
    else:
        log(f"{eth_iface} already has the correct static IP. Skipping IP configuration.")
    
    # Ensure the interface is up
    result = run_command(f"ip link show {eth_iface} | grep 'state UP'", silent=True)
    if result.returncode != 0:
        result = run_command(f"ip link set {eth_iface} up")
        if result.returncode != 0:
            warn_continue(f"Failed to bring up {eth_iface}.")
    else:
        log(f"{eth_iface} is already up. Skipping interface activation.")


def setup_routing(config):
    """Configure routing and IP forwarding."""
    log("Setting up routing...")
    
    wlan_iface = config['WLAN_IFACE']
    gateway_ip = config['GATEWAY_IP']
    
    # Set default route if not already set
    result = run_command(f"ip route | grep 'default via .* dev {wlan_iface}'", silent=True)
    if result.returncode != 0:
        log(f"Adding default route via {gateway_ip} on {wlan_iface}...")
        result = run_command(f"ip route replace default via {gateway_ip} dev {wlan_iface}")
        if result.returncode != 0:
            warn_continue("Failed to set default route.")
    else:
        log(f"Default route via {wlan_iface} already exists. Skipping route configuration.")

    # Enable IP forwarding if not already enabled
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
            ip_forward = f.read().strip()
        
        if ip_forward != "1":
            log("Enabling IP forwarding...")
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("1\n")
        else:
            log("IP forwarding is already enabled. Skipping.")
    except Exception as e:
        warn_continue(f"Failed to enable IP forwarding: {e}")

    # Make IP forwarding persistent if not already configured
    if os.path.exists("/etc/sysctl.conf"):
        with open("/etc/sysctl.conf", "r") as f:
            sysctl_content = f.read()
        
        if "net.ipv4.ip_forward=1" not in sysctl_content:
            log("Making IP forwarding persistent...")
            with open("/etc/sysctl.conf", "a") as f:
                f.write("\n# Added by Alpine Wi-Fi Bridge\n")
                f.write("net.ipv4.ip_forward=1\n")
        else:
            log("Persistent IP forwarding is already configured. Skipping.")