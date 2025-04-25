#!/usr/bin/env python3
"""
Wrapper script for backward compatibility with the shell script version
This simply calls the setup.py script with all arguments
"""
import sys
import subprocess
from pybridge.utils import display_banner

if __name__ == "__main__":
    # Display the banner for backward compatibility with the shell script
    display_banner()
    
    # Pass all arguments to setup.py
    cmd = ["python3", "setup.py"] + sys.argv[1:]
    subprocess.run(cmd)