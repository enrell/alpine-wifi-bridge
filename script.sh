#!/bin/sh

# --- Configuration Variables ---
# Replace 'wlan0' with your actual Wi-Fi interface if different
WIFI_IFACE="wlan0"
# Replace 'eth0' with your actual Ethernet interface if different
ETHERNET_IFACE="eth0"
# IP of your notebook on the wired network
NOTEBOOK_IP_ETH="10.42.0.1"
# IP of the PC that will receive the connection
TARGET_PC_IP="10.42.0.100"

# --- Start Configuration ---

echo "--- Installing necessary tools (iptables, wpa_supplicant, iw) ---"
apk add iptables wpa_supplicant iw || { echo "Failed to install packages. Check initial connection or repositories."; exit 1; }

echo "--- Activating Wi-Fi interface ($WIFI_IFACE) ---"
ip link set "$WIFI_IFACE" up || { echo "Failed to activate $WIFI_IFACE. Check interface name."; exit 1; }

echo "--- Configuring Wi-Fi connection ---"
printf "Enter your Wi-Fi SSID: "
read -r WIFI_SSID
printf "Enter your Wi-Fi password: "
read -r WIFI_PASSWORD

# Generate wpa_supplicant configuration file
wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" > "/tmp/wpa_supplicant.conf" || { echo "Failed to generate wpa_supplicant.conf"; exit 1; }

# Start wpa_supplicant in the background
echo "Connecting to Wi-Fi..."
wpa_supplicant -B -i "$WIFI_IFACE" -c "/tmp/wpa_supplicant.conf" || { echo "Failed to start wpa_supplicant. Check SSID/password."; exit 1; }
sleep 5 # Give wpa_supplicant some time to establish the connection

echo "--- Obtaining IP address for $WIFI_IFACE via DHCP ---"
udhcpc -i "$WIFI_IFACE" || { echo "Failed to obtain IP for $WIFI_IFACE. Check Wi-Fi network."; exit 1; }
sleep 2 # Give some time for the IP to be assigned

echo "--- Configuring Ethernet interface ($ETHERNET_IFACE) ---"
ip addr add "$NOTEBOOK_IP_ETH/24" dev "$ETHERNET_IFACE" || { echo "Failed to configure static IP on $ETHERNET_IFACE."; exit 1; }
ip link set "$ETHERNET_IFACE" up || { echo "Failed to activate $ETHERNET_IFACE. Check interface name."; exit 1; }

echo "--- Enabling IP routing (IP Forwarding) ---"
sysctl -w net.ipv4.ip_forward=1 || { echo "Failed to enable IP forwarding."; exit 1; }

echo "--- Configuring NAT rules (Internet Sharing) ---"
# Clear POSTROUTING and FORWARD rules to prevent duplicates, but keep others if they exist
iptables -t nat -F POSTROUTING
iptables -F FORWARD

iptables -t nat -A POSTROUTING -o "$WIFI_IFACE" -j MASQUERADE || { echo "MASQUERADE rule failed."; exit 1; }
iptables -A FORWARD -i "$ETHERNET_IFACE" -o "$WIFI_IFACE" -j ACCEPT || { echo "FORWARD eth0->wlan0 rule failed."; exit 1; }
iptables -A FORWARD -i "$WIFI_IFACE" -o "$ETHERNET_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT || { echo "FORWARD wlan0->eth0 rule failed."; exit 1; }

echo "--- Configuring Port Forwarding (DNAT) to the PC ($TARGET_PC_IP) ---"
# Clear PREROUTING rules to prevent duplicates
iptables -t nat -F PREROUTING

iptables -t nat -A PREROUTING -i "$WIFI_IFACE" -j DNAT --to-destination "$TARGET_PC_IP" || { echo "DNAT rule failed."; exit 1; }

echo "--- Network configuration complete! ---"
echo "Your notebook is sharing internet and forwarding traffic to $TARGET_PC_IP."
echo "Check the connection on your PC and mobile phone."
