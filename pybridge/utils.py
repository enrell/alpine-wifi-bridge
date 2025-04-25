"""
Utility functions for Alpine Wi-Fi Bridge
"""
import os
import sys
import subprocess
import shutil


def log(message):
    """Print a formatted log message."""
    print(f"[INFO] {message}")


def warn_continue(message):
    """Print a warning message but continue execution."""
    print(f"[WARNING] {message} - Skipping this step.")


def error_exit(message):
    """Print an error message and exit."""
    print(f"[ERROR] {message}")
    sys.exit(1)


def ensure_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        error_exit("This script must be run as root. Use 'sudo'.")


def run_command(command, shell=True, check=False, silent=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            stdout=subprocess.PIPE if silent else None,
            stderr=subprocess.PIPE if silent else None,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            warn_continue(f"Command failed: {command}")
        return e


def command_exists(command):
    """Check if a command exists."""
    return shutil.which(command) is not None


def display_banner():
    """Display the application banner."""
    print("==================================================")
    print("      Alpine Wi-Fi to Ethernet Bridge Setup       ")
    print("==================================================")
    print("")