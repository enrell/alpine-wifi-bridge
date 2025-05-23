---

# Alpine Live Boot Network Configuration Script

This script automates the process of setting up network connectivity on an Alpine Linux live boot environment. It configures Wi-Fi, enables internet sharing (NAT) from the Wi-Fi interface to an Ethernet interface, and sets up port forwarding for all traffic to a specific target PC on the wired network.

---

## Features

* **Automated Wi-Fi Connection:** Prompts for SSID and password to connect to your wireless network.
* **Internet Sharing (NAT):** Configures your Alpine notebook to share its Wi-Fi internet connection with a wired device.
* **All-Port Port Forwarding:** Redirects all incoming traffic from your Wi-Fi network to a specified target PC on the wired network.
* **Temporary Configuration:** Ideal for Alpine live boot where network settings are not persistent.
* **Error Handling:** Includes basic checks to notify you if a step fails.

---

## Prerequisites

* A notebook running **Alpine Linux in live boot mode**.
* Two network interfaces: one for Wi-Fi (e.g., `wlan0`) and one for Ethernet (e.g., `eth0`).
* A physical Ethernet cable connecting your Alpine notebook to the target PC.
* The target PC should be configured to accept an IP address in the `10.42.0.0/24` range (either statically or via DHCP if you manually configure a DHCP server on the Alpine notebook, though this script doesn't include a DHCP server).
* **Basic understanding of network interfaces and IP addresses.**

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

---

## Script Breakdown

The script performs the following actions in sequence:

1.  **Installs Necessary Tools:** `iptables`, `wpa_supplicant`, and `iw`.
2.  **Activates Wi-Fi Interface:** Brings up your specified Wi-Fi interface.
3.  **Configures Wi-Fi Connection:** Prompts for Wi-Fi SSID and password, then uses `wpa_passphrase` and `wpa_supplicant` to connect to your wireless network.
4.  **Obtains Wi-Fi IP:** Uses `udhcpc` to get an IP address for your Wi-Fi interface from your main router.
5.  **Configures Ethernet Interface:** Assigns a static IP (`10.42.0.1`) to your Ethernet interface and brings it up.
6.  **Enables IP Forwarding:** Allows your notebook to route traffic between its network interfaces.
7.  **Sets up NAT Rules:** Configures `iptables` to perform Network Address Translation (NAT), enabling devices on your wired network (`10.42.0.0/24`) to access the internet via your Wi-Fi connection.
8.  **Configures All-Port Forwarding (DNAT):** Redirects all incoming traffic from your Wi-Fi interface to the specified `TARGET_PC_IP` on the wired network.

---

## Important Considerations

* **Temporary Configuration:** All changes made by this script are temporary and will be lost upon rebooting your Alpine live system.
* **Security Warning (All-Port Forwarding):** The script sets up port forwarding for *all* protocols and ports to your target PC. This is generally **not recommended for production environments** as it exposes all services on your target PC to your main Wi-Fi network. **Ensure your target PC has its own robust firewall** configured to allow only necessary connections.
* **Target PC IP:** Ensure the `TARGET_PC_IP` variable in the script matches the actual static IP you've set on your wired target PC (e.g., `10.42.0.100`).
* **Error Handling:** While basic error handling is included, real-world network issues can be complex. If the script fails, carefully read the error messages.

---
