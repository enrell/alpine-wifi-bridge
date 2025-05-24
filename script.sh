# Install packages if necessary
if ! apk info | grep -q iptables; then
    apk add iptables wpa_supplicant iw || { exit 1; }
else
    echo "Packages already installed, skipping."
fi

# Bring up wlan0 interface if necessary
if ! ip link show wlan0 | grep -q 'state UP'; then
    ip link set wlan0 up || { exit 1; }
else
    echo "wlan0 is already up, skipping."
fi

printf "Enter your Wi-Fi SSID: "
read -r WIFI_SSID
printf "Enter your Wi-Fi password: "
read -r WIFI_PASSWORD

# Generate wpa_supplicant.conf if it does not exist
if [ ! -f /tmp/wpa_supplicant.conf ]; then
    wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" > "/tmp/wpa_supplicant.conf" || { exit 1; }
else
    echo "/tmp/wpa_supplicant.conf already exists, skipping."
fi

# Start wpa_supplicant if not running
if ! pgrep -f 'wpa_supplicant.*wlan0' > /dev/null; then
    wpa_supplicant -B -i wlan0 -c "/tmp/wpa_supplicant.conf" || { exit 1; }
    sleep 5
else
    echo "wpa_supplicant is already running, skipping."
fi

udhcp -i wlan0 || { exit 1; }
sleep 2

# Pause for cable swap
read -p "Swap the network cable now and press Enter, y or Y to continue: " resposta
if [ -n "$resposta" ] && [ "$resposta" != "y" ] && [ "$resposta" != "Y" ]; then
    echo "Exiting..."
    exit 0
fi

ip addr add 10.42.0.1/24 dev eth0 || { exit 1; }
ip link set eth0 up || { exit 1; }

sysctl -w net.ipv4.ip_forward=1 || { exit 1; }

iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE || { exit 1; }
iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT || { exit 1; }
iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT || { exit 1; }

iptables -t nat -A PREROUTING -i wlan0 -j DNAT --to-destination 10.42.0.100 || { exit 1; }

echo "Finished"
