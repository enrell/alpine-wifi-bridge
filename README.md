# **Wi-Fi to Ethernet Sharing - Python Implementation**

This project automates the setup of a Linux device (using Alpine Linux) to connect to a Wi-Fi network and share the internet connection through an Ethernet interface. It handles network configuration, IP forwarding and NAT setup.

**NEW**: Now available in both Shell script and Python implementations!

## **Disclaimer**

- This script is designed for my personal use and may require adjustments for specific system configurations. Use at your own risk.
- The goal is to automate sharing the internet from a notebook running Alpine Linux, completely loaded into RAM (no disk), to a computer via wired connection.
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
- Safe to run multiple times without breaking existing configurations
- Automatically backs up network settings before making changes
- Stores configuration in a file for consistent operation after updates
- Auto-detects gateway IP address or allows custom specification
- Uses Alpine Linux's native configuration methods
- Modular structure for easier configuration and maintenance
- Port forwarding support to make services on your PC accessible from the internet
- **NEW**: Available as a Python implementation with improved error handling
- **NEW**: Comprehensive test suite for the Python modules
- **NEW**: Better handling of special characters in Wi-Fi passwords
- **NEW**: Support for both iptables and nftables firewall systems

## **Prerequisites**
- Alpine Linux
- Python 3 (for Python implementation)
- Internet access
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

### **2. Choose Your Implementation**

#### **Shell Script Implementation**
Make the scripts executable:
```bash
chmod +x setup.sh script.sh scripts/*.sh
```

Run the setup:
```bash
./setup.sh
```

#### **Python Implementation**
Install Python and dependencies:
```bash
apk add python3 py3-pip
pip install -r requirements.txt
```

Make the Python scripts executable:
```bash
chmod +x setup.py script.py network-restart.py
```

Run the setup:
```bash
./setup.py setup
```

### **3. Provide Wi-Fi Credentials**
If the script doesn't find an existing Wi-Fi configuration, it will prompt you to enter:
- **SSID**: The name of the Wi-Fi network.
- **Password**: The Wi-Fi password.

### **4. Gateway IP Configuration**
The program will:
- Automatically detect your gateway IP address from the network configuration
- If detection fails, it will ask if you want to specify a custom gateway IP
- You can enter your router's IP address (typically something like 192.168.1.1 or 10.0.0.1)

### **5. Internet Sharing**
The program will:
- Connect to the Wi-Fi network
- Set up a static IP on the Ethernet interface (`10.42.0.1` by default)
- Enable NAT and IP forwarding
- Configure comprehensive iptables rules that allow unrestricted network traffic

## **Port Forwarding Feature**

The project includes the ability to forward all traffic from your Alpine machine to your PC. This is useful when you want to run services on your PC and make them accessible from the outside network.

### **How to Enable Port Forwarding**

1. Edit the configuration file:
   ```bash
   nano config/settings.conf
   ```

2. Change the following settings:
   ```
   # Port forwarding configuration
   # Set to "true" to enable forwarding all traffic from Alpine to PC
   ENABLE_PORT_FORWARDING="true"
   
   # IP address of the PC to forward traffic to
   # Example: PC_IP="10.42.0.100"
   PC_IP="10.42.0.100"  # Replace with your PC's actual IP address
   ```

3. Run the setup script (either implementation):
   ```bash
   # Shell script
   ./setup.sh
   
   # Python
   ./setup.py setup
   ```

### **How It Works**

- All traffic sent to your Alpine machine's Wi-Fi IP address will be redirected to your PC
- This makes services running on your PC (e.g., web servers, game servers) accessible from the outside network
- You'll access these services using the Alpine machine's IP address (the one on the Wi-Fi network)

## **Python Implementation**

The new Python implementation offers several advantages:

### **Benefits**
- Better error handling and more robust operation
- Improved code organization with a modular package structure
- Better handling of special characters in passwords and commands
- Automatic detection of the firewall system (iptables or nftables)
- Comprehensive test suite for quality assurance
- Consistent configuration across implementation methods

### **Python Package Structure**
- `pybridge/`: Main Python package
  - `__init__.py`: Package initialization
  - `utils.py`: Common utility functions
  - `config.py`: Configuration management
  - `backup.py`: Backup and restore operations
  - `network.py`: Network interface detection and setup
  - `firewall.py`: Firewall and NAT configuration
  - `portforward.py`: Port forwarding functionality

### **Running Tests**

The Python implementation includes comprehensive unit tests. To run the tests:

```bash
# Install test dependencies
pip install pytest

# Run the tests
python run_tests.py
```

## **Customizing Settings**

To customize the behavior, edit the `config/settings.conf` file:

```bash
# Edit the configuration file
nano config/settings.conf
```

Available settings:
- Network interfaces (auto-detected by default)
- Gateway IP (auto-detected by default)
- Static IP for Ethernet interface
- Wi-Fi configuration path
- Paths for configuration storage
- Iptables rules storage
- Port forwarding configuration

## **Network Monitoring**

The network monitoring script automatically keeps your connection stable:

```bash
# Install Python if needed
apk add python3

# Start the monitoring script
python3 network-restart.py
```

## **Restoring Original Settings**

If you need to revert to your original network settings:

```bash
# Shell script
./setup.sh --restore

# Python
./setup.py restore
```

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
     iptables -L FORWARD
     ```
   - Verify that IP forwarding is enabled:
     ```bash
     sysctl net.ipv4.ip_forward
     ```
   - Restart the network monitor to automatically check and fix missing rules:
     ```bash
     python network-restart.py
     ```

4. **Gateway IP Issues**
   - Check your gateway IP:
     ```bash
     ip route | grep default
     ```
   - If incorrect, edit the configuration file and re-run setup.

5. **Port Forwarding Not Working**
   - Verify forwarding is enabled in the configuration
   - Check that your PC's IP is correct
   - Ensure your PC's firewall allows incoming connections

6. **Python Implementation Issues**
   - Check for Python dependency issues:
     ```bash
     pip install -r requirements.txt
     ```
   - Run the tests to verify the code is working properly:
     ```bash
     python run_tests.py
     ```

---

## **Contributing**

Feel free to submit issues or pull requests!

---

## **License**

This project is licensed under the [MIT License](LICENSE).
