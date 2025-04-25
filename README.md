# Alpine Wi-Fi Bridge

A Python application that turns your Alpine Linux device into a Wi-Fi to Ethernet bridge. It automatically configures your network interfaces, sets up NAT, and enables internet sharing.

## **Disclaimer**

- This script is designed for my personal use and may require adjustments for specific system configurations. Use at your own risk.
- The goal is to automate sharing the internet from a notebook running Alpine Linux, completely loaded into RAM (no disk), to a computer via wired connection.
- Here's my use case: the router is in the living room and my PC is in the bedroom. I didn't want to run a cable from the living room to the bedroom because it would be too much work. So I thought, "Why not load a minimal system (Alpine Linux) onto a laptop that I no longer use via PXE and share the Wi-Fi connection with the PC?" And that's exactly what I did.

## Prerequisites

- Alpine Linux
- Python 3.6+
- Basic networking packages (installed automatically)

## Quick Start

```bash
# Clone the repository
apk update && apk add git
git clone https://github.com/enrell/alpine-wifi-bridge.git
cd alpine-wifi-bridge

# Install dependencies

echo "http://dl-cdn.alpinelinux.org/alpine/latest-stable/community" >> /etc/apk/repositories
apk add python3 py3-pip
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt

# Run the setup
python setup.py setup

## Configuration

Edit `config/settings.conf` to customize the behavior:

```bash
# Port forwarding configuration
PC_IP="10.42.0.100"  # Your PC's IP address on the Ethernet network
```

The application auto-detects network interfaces and gateway IP, but you can also configure them manually in the settings file.

## Restore Original Settings

If you need to revert to your original network settings:

```bash
python setup.py restore
```

## Troubleshooting

- **Wi-Fi Not Connecting**: Check SSID/password and wpa_supplicant (`ps aux | grep wpa_supplicant`)
- **No Ethernet Interface**: Verify with `ip link show` 
- **No Internet Sharing**: Check iptables rules and IP forwarding
- **Port Forwarding Issues**: Verify PC IP address and firewall settings

## License

This project is licensed under the [MIT License](LICENSE).
