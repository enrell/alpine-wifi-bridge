---

# Alpine Live Boot Network Configuration Script

This script automates the process of setting up network connectivity on an Alpine Linux live boot environment. It configures Wi-Fi, enables internet sharing (NAT) from the Wi-Fi interface to an Ethernet interface, and sets up port forwarding for all traffic to a specific target PC on the wired network.

---

## Setup and Usage

1.  **Update and Install Git:**
    First, ensure your package list is updated and install Git.

    ```bash
    apk update && apk add git
    ```

2.  **Set System Date and Time (Important for Git and SSL):**
    If your system date/time is incorrect, Git clones might fail due to SSL certificate issues. Replace `YYYY-MM-DD HH-MM-SS` with the current date and time.

    ```bash
    date -s "YYYY-MM-DD HH-MM-SS"
    # Example: date -s "2025-05-23 08-22-00"
    ```

3.  **Clone the Repository:**
    Clone this repository to get the script.

    ```bash
    git clone https://github.com/enrell/alpine-wifi-bridge
    ```

4.  **Navigate to the Script Directory:**

    ```bash
    cd alpine-wifi-bridge
    ```

5.  **Make it Executable:**
    Give the script execution permissions.

    ```bash
    chmod +x setup_network.sh
    ```

6.  **Customize Configuration Variables (Optional but Recommended):**
    Open the `setup_network.sh` file and adjust the following variables at the top to match your environment:

    ```bash
    WIFI_IFACE="wlan0"      # Your Wi-Fi interface name
    ETHERNET_IFACE="eth0"   # Your Ethernet interface name
    NOTEBOOK_IP_ETH="10.42.0.1" # The IP your notebook will use on the wired network
    TARGET_PC_IP="10.42.0.100"  # The IP of the PC connected via Ethernet
    ```

7.  **Run the Script:**
    Execute the script with `sudo`.

    ```bash
    sudo ./setup_network.sh
    ```

    The script will then prompt you to enter your Wi-Fi SSID and password.
