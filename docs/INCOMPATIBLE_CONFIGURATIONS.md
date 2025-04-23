# Incompatible Configurations

This document outlines configurations and environments where the Alpine Wi-Fi Bridge script may not work as expected. Understanding these limitations can help you troubleshoot issues or determine if this solution is appropriate for your specific setup.

## 1. Non-Standard Network Interface Names

**Configuration Issue:** Using systems with network interfaces that don't follow the standard naming pattern.

**Why It Won't Work:** The script auto-detects interfaces using these commands:
```bash
WLAN_IFACE=$(ip link | grep -E "^[0-9]+: wlan" | awk -F': ' '{print $2}' | head -n 1)
ETH_IFACE=$(ip link | grep -E "^[0-9]+: eth" | awk -F': ' '{print $2}' | head -n 1)
```

This only works for interfaces named like "wlan0" or "eth0". Modern Linux distributions often use predictable network interface names like "wlp3s0" or "enp2s0" (following systemd naming conventions), which would not be detected by this script.

**Solution:** Manually specify your interface names in the `config/settings.conf` file:
```
WLAN_IFACE="wlp3s0"  # Replace with your actual Wi-Fi interface name
ETH_IFACE="enp2s0"   # Replace with your actual Ethernet interface name
```

## 2. Port Forwarding with Missing PC_IP

**Configuration Issue:** In the default configuration, port forwarding is enabled but PC_IP is empty:
```
ENABLE_PORT_FORWARDING="true"
PC_IP=""
```

**Why It Won't Work:** The port forwarding script checks if PC_IP is set and skips port forwarding if it's empty:
```bash
if [ -z "$PC_IP" ]; then
    log "PC_IP is not set in configuration. Skipping port forwarding."
    return
fi
```
Users would expect port forwarding to work since it's enabled, but it will silently fail.

**Solution:** Either disable port forwarding by setting `ENABLE_PORT_FORWARDING="false"` or specify a valid PC_IP address.

## 3. Incorrect Default Gateway

**Configuration Issue:** If gateway auto-detection fails, it defaults to 192.168.0.1.

**Why It Won't Work:** Many home networks use different gateway IPs like 192.168.1.1 or 10.0.0.1. If auto-detection fails and the user doesn't manually set the correct gateway, routing will fail and internet sharing won't work.

**Solution:** Manually specify your gateway IP in the configuration file:
```
GATEWAY_IP="192.168.1.1"  # Replace with your actual gateway IP
```

## 4. Systems Without Ethernet Interface

**Configuration Issue:** Running the script on a system without an Ethernet interface.

**Why It Won't Work:** While the script does handle this case with warnings, the core functionality (bridging Wi-Fi to Ethernet) cannot work without an Ethernet interface. The script will set up Wi-Fi but won't be able to share the connection.

**Solution:** This script requires a system with both Wi-Fi and Ethernet interfaces. Consider using a USB Ethernet adapter if your system lacks a built-in Ethernet port.

## 5. Concurrent Network Management Tools

**Configuration Issue:** Running the script on systems with NetworkManager, systemd-networkd, or other network management tools.

**Why It Won't Work:** The script directly configures network interfaces and routing without checking for or disabling other network management tools. This can lead to conflicts where other tools might override the script's configurations or restart interfaces.

**Solution:** Disable other network management tools before running this script:
```bash
# For systems with NetworkManager
rc-service networkmanager stop
rc-update del networkmanager

# For systems with systemd-networkd
rc-service systemd-networkd stop
rc-update del systemd-networkd
```

## 6. Alpine Linux Version Compatibility

**Configuration Issue:** Running on older Alpine Linux versions.

**Why It Won't Work:** The README specifies installing Python 3.12:
```
apk update && apk add python3~3.12
```
Older Alpine versions might not have this version available. Additionally, the script uses Alpine-specific paths and commands that might differ between versions.

**Solution:** For older Alpine versions, modify the Python installation command:
```bash
# For Alpine 3.15 or earlier
apk update && apk add python3
```

## 7. Non-iptables Firewall Systems

**Configuration Issue:** Running on systems that use nftables instead of iptables.

**Why It Won't Work:** The script relies heavily on iptables commands for NAT and firewall rules. Newer Linux distributions might use nftables as the default firewall, where these commands would fail or have no effect.

**Solution:** Install and enable iptables compatibility layer:
```bash
apk add iptables-nft
```

## 8. Wi-Fi Passwords with Special Characters

**Configuration Issue:** Using Wi-Fi networks with passwords containing special characters.

**Why It Won't Work:** The script reads the password using `read -s PASSWORD` and passes it directly to `wpa_passphrase`. If the password contains special shell characters (like $, `, ", etc.), it might be interpreted incorrectly by the shell.

**Solution:** Manually create the wpa_supplicant.conf file before running the script:
```bash
mkdir -p /etc/wpa_supplicant
wpa_passphrase "YourSSID" "Your@Complex#Password" > /etc/wpa_supplicant/wpa_supplicant.conf
```

## 9. Missing Required Directories

**Configuration Issue:** Running on a minimal Alpine system without required directories.

**Why It Won't Work:** The script assumes certain directories exist or can be created:
```bash
mkdir -p "$(dirname "$WPA_CONF")" || error_exit "Failed to create wpa_supplicant directory."
```
If the parent directories don't exist or can't be created due to permissions, the script will fail.

**Solution:** Ensure your Alpine installation has the standard directory structure or manually create required directories before running the script.

## 10. Network Restart Method Incompatibility

**Configuration Issue:** The script tries to restart networking using:
```bash
/etc/init.d/networking restart
```

**Why It Won't Work:** Alpine Linux uses OpenRC as its init system, and the networking service might be named differently or managed differently. If this command fails, network connectivity might not be properly restored after failures.

**Solution:** The script includes a fallback method for restarting interfaces directly, but you may need to modify the script if your system uses a different network service name.

## 11. Persistence Across Reboots

**Configuration Issue:** The script creates startup files but doesn't verify if they're properly loaded on boot.

**Why It Won't Work:** The script attempts to make configurations persistent by creating startup scripts and enabling services:
```bash
rc-update add local default 2>/dev/null || warn_continue "Failed to enable local service for startup scripts."
```
If this fails silently, the configuration won't persist after a reboot, but the user won't be clearly notified.

**Solution:** After running the script, manually verify that the local service is enabled:
```bash
rc-update show | grep local
```
If it's not listed, manually enable it:
```bash
rc-update add local default
```

## 12. Running Without Root Privileges

**Configuration Issue:** Running the script without root privileges.

**Why It Won't Work:** The script requires root privileges to configure network interfaces, set up iptables rules, and modify system files. While it does check for root privileges at the start, if a user tries to run it without sudo or as a non-root user, it will fail immediately.

**Solution:** Always run the script with root privileges:
```bash
sudo ./setup.sh
```
Or as the root user:
```bash
su -
./setup.sh
```