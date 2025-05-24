# Alpine Live Boot Network Configuration Script

This script automates the process of setting up network connectivity on an Alpine Linux live boot environment. It configures Wi-Fi, enables internet sharing (NAT) from the Wi-Fi interface to an Ethernet interface, and sets up port forwarding for all traffic to a specific target PC on the wired network.

> **Warning:** This script is intended for personal use. Review and verify the script before continuing.

> **I'm not responsible if you break your network config!**

## Setup and Usage

1. **Update and Install Git:**
    First, ensure your package list is updated and install Git.

    ```bash
    apk update && apk add git
    ```

2. **Set System Date and Time (Important for Git and SSL):**
    If your system date/time is incorrect, Git clones might fail due to SSL certificate issues. Replace `YYYY-MM-DD HH-MM-SS` with the current date and time.

    ```bash
    date -s "YYYY-MM-DD HH-MM-SS"
    # Example: date -s "2025-05-23 08-22-00"
    ```

3. **Clone the Repository:**
    Clone this repository to get the script.

    ```bash
    git clone https://github.com/enrell/alpine-wifi-bridge
    ```

4. **Navigate to the Script Directory:**

    ```bash
    cd alpine-wifi-bridge
    ```

5. **Make it Executable:**
    Give the script execution permissions.

    ```bash
    chmod +x script.sh
    ```

6. **Run the Script:**
    Execute the script with `sudo`.

    ```bash
    sudo ./script.sh
    ```

The script will then prompt you to enter your Wi-Fi SSID and password.

**Done**
