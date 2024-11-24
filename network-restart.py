#!/usr/bin/env python3
import os
import time
import subprocess
from itertools import cycle

# Configurations
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Targets for ping test to check connectivity
RETRY_INTERVAL = 5      # Interval between tests (in seconds) - 5s to avoid locks but be fast
MAX_RETRY = 3           # Maximum number of attempts before restarting the network
RESTART_CMD = "/etc/init.d/networking restart"  # Command to restart the network
POST_RESTART_DELAY = 2  # Delay after restarting the network (in seconds)

# Infinite cycle of DNS servers for rotation
ping_targets_cycle = cycle(PING_TARGETS)

def is_connected(target):
    """Checks connectivity with a target using ping."""
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", target], stderr=subprocess.DEVNULL)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Connection OK with {target}.")
        return True
    except subprocess.CalledProcessError:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Failed to ping {target}.")
        return False

def restart_network():
    """Restarts the network service with an additional delay."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Restarting network...")
    os.system(RESTART_CMD)
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Waiting {POST_RESTART_DELAY} seconds for stabilization...")
    time.sleep(POST_RESTART_DELAY)

def main():
    """Main function to monitor and fix connection issues."""
    fail_count = 0

    print("Monitoring internet connection...")
    while True:
        target = next(ping_targets_cycle)  # Switch to the next DNS server
        if is_connected(target):
            fail_count = 0  # Reset failure counter
        else:
            fail_count += 1
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Connection failed ({fail_count}/{MAX_RETRY}).")

        if fail_count >= MAX_RETRY:
            restart_network()
            fail_count = 0  # Reset counter after restarting the network

        time.sleep(RETRY_INTERVAL)  # Interval between ping attempts

if __name__ == "__main__":
    main()
