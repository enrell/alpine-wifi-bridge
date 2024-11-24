#!/usr/bin/env python3
import os
import time
import subprocess

# Configurations
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Targets for ping test to check connectivity
RETRY_INTERVAL = 1       # Interval between tests (in seconds)
MAX_RETRY = 5            # Maximum number of attempts before restarting the network
RESTART_CMD = "/etc/init.d/networking restart"  # Command to restart the network
POST_RESTART_DELAY = 2   # Delay after restarting the network (in seconds)

def is_connected(targets):
    """Checks connectivity with multiple targets using ping."""
    for target in targets:
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
        if is_connected(PING_TARGETS):
            fail_count = 0  # Reset failure counter
        else:
            fail_count += 1
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Connection failed ({fail_count}/{MAX_RETRY}).")

        if fail_count >= MAX_RETRY:
            restart_network()
            fail_count = 0  # Reset counter after restarting the network

        time.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    main()
