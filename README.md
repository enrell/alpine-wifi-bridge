# **Wi-Fi to Ethernet Sharing Script**

This script automates the setup of a Linux device (using Alpine Linux) to connect to a Wi-Fi network and share the internet connection through an Ethernet interface. It handles network configuration, IP forwarding and NAT setup.

## **Disclaimer**

This script is designed for personal use and may require adjustments for specific system configurations. Use at your own risk.

---

## **Features**
- Connects the system to a Wi-Fi network using `wpa_supplicant`.
- Configures a static IP on the Ethernet interface.
- Enables IP forwarding to allow internet sharing.
- Sets up NAT using `iptables` to route traffic from Ethernet to Wi-Fi.

---

## **Prerequisites**
- Alpine Linux.
- Internet access on the Wi-Fi network to share.
---

## **Setup**

### **1. Clone the Repository**
```bash
sudo apk update && sudo apk add git
git clone https://github.com/enrell/alpine-wifi-bridge.git
cd alpine-wifi-bridge
```

### **2. Make the Script Executable**
```bash
chmod +x script.sh
```

---

## **Usage**

### **1. Run the Script**
Run the script as root or with `sudo` to ensure it has the required permissions:
```bash
sudo ./script.sh
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

---

## **Troubleshooting**

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
     ```
   - Verify that IP forwarding is enabled:
     ```bash
     sysctl net.ipv4.ip_forward
     ```

---

## **Customization**

You can modify the following settings directly in the script:
- **Static IP for Ethernet**: Change the `10.42.0.1` address in the script.
- **Wi-Fi Configuration Path**: Default is `/etc/wpa_supplicant/wpa_supplicant.conf`.

---

## **Contributing**

Feel free to submit issues or pull requests to improve the script!

---

## **License**

This project is licensed under the [MIT License](LICENSE).
