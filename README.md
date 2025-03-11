# **Wi-Fi to Ethernet Sharing Script**

This script automates the setup of a Linux device (using Alpine Linux) to connect to a Wi-Fi network and share the internet connection through an Ethernet interface. It handles network configuration, IP forwarding and NAT setup.

## **Disclaimer**

- This script is designed for my personal use and may require adjustments for specific system configurations. Use at your own risk.
- The goal of the scripts is to automate sharing the internet from a notebook running Alpine Linux, completely loaded into RAM (no disk), to a computer via wired connection.
- Here's my use case: the router is in the living room and my PC is in the bedroom. The router is modern enough to provide the full speed of my internet plan even over Wi-Fi, with almost zero latency and fluctuation. I didn't want to run a cable from the living room to the bedroom because it would be too much work. So I thought, "Why not load a minimal system (Alpine Linux) onto a laptop that I no longer use via PXE and share the Wi-Fi connection with the PC?" And that's exactly what I did. Don't judge me, my old notebook consumes less energy than my router.

## **Features**
- Connects the system to a Wi-Fi network using `wpa_supplicant`.
- Configures a static IP on the Ethernet interface.
- Enables IP forwarding to allow internet sharing.
- Sets up comprehensive NAT and firewall rules using `iptables` to enable unrestricted traffic flow in all directions:
  - Between devices on the internal network
  - From internal devices to external networks
  - From the notebook to any destination
  - ICMP (ping) traffic in all directions
- Includes a robust network monitoring script that automatically:
  - Checks internet connectivity at regular intervals
  - Restores network connectivity when issues are detected
  - Periodically verifies and reinstates iptables rules if they're missing

## **Prerequisites**
- Alpine Linux.
- Internet access.
---

## **Setup**

### **1. Clone the Repository**
Check System Date and Time
SSL certificates are sensitive to the system date and time. If the date or time zone is incorrect, certificate validation may fail.
````
date
````
If the time is wrong, fix it
````
date -s "YYYY-MM-DD HH:MM:SS"
````

```bash
apk update && apk add git
git clone https://github.com/enrell/alpine-wifi-bridge.git
cd alpine-wifi-bridge
```

### **2. Make the Script Executable**
```bash
chmod +x script.sh
```

## **Usage**

### **1. Run the Script**
Run the script as root or with `sudo` to ensure it has the required permissions:
```bash
./script.sh
```

### **2. Provide Wi-Fi Credentials**
If the script doesn't find an existing Wi-Fi configuration, it will prompt you to enter:
- **SSID**: The name of the Wi-Fi network.
- **Password**: The Wi-Fi password.

### **3. Internet Sharing**
The script will:
- Connect to the Wi-Fi network.
- Set up a static IP on the Ethernet interface (`10.42.0.1` by default).
- Enable NAT and IP forwarding.
- Configure comprehensive iptables rules that allow unrestricted network traffic:
  - All traffic between connected devices
  - All traffic to and from the internet
  - All traffic to and from the notebook
  - ICMP traffic for ping and network diagnostics

# **Troubleshooting**

1. **Wi-Fi Not Connecting**
   - Ensure the Wi-Fi SSID and password are correct.
   - Check that the `wpa_supplicant` service is running:  
     ```bash
     ps aux | grep wpa_supplicant
     ```

2. **No Ethernet Interface**
   - Verify the Ethernet interface is detected:
     ```bash
     ip link show
     ```
   - If unavailable, check hardware or use a USB Ethernet adapter.

3. **Internet Not Shared**
   - Ensure `iptables` rules are set correctly:
     ```bash
     iptables -t nat -L
     iptables -L FORWARD
     iptables -L INPUT
     iptables -L OUTPUT
     ```
   - Verify that IP forwarding is enabled:
     ```bash
     sysctl net.ipv4.ip_forward
     ```
   - Make sure that all required rules are present. You can restart the network monitor to automatically check and fix missing rules:
     ```bash
     python network-restart.py
     ```

# Network monitor
The network_restart.py script is designed to automatically monitor your network connection and quickly restart the network interface if the connection drops. It aims to minimize interruptions, with a particular focus on activities where low downtime is critical.

The script works by:
   - Monitoring the network to ensure that it remains connected.
   - Automatically reconnecting to the network if the connection is lost.
   - Reinforcing connectivity by running necessary commands when the network fails.
   - Periodically checking that all required iptables rules are in place and fixing any missing rules.
   - Ensuring IP forwarding is enabled after any network restarts.

## Install python and run:
Install:
````
apk update && apk add python3~3.12
````
Run:
````
python network-restart.py
````

# Revert the settings to their original state
By running the script with the --restore flag, you can revert the settings to their original state.
````
./script.sh --restore
````

---

## **Customization**

You can modify the following settings directly in the script:
- **Static IP for Ethernet**: Change the `10.42.0.1` address in the script.
- **Wi-Fi Configuration Path**: Default is `/etc/wpa_supplicant/wpa_supplicant.conf`.

---

## **Contributing**

Feel free to submit issues or pull requests!

---

## **License**

This project is licensed under the [MIT License](LICENSE).
