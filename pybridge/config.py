"""
Configuration handling for Alpine Wi-Fi Bridge
"""
import os
import shutil
from datetime import datetime
from configparser import ConfigParser
from .utils import log, warn_continue, error_exit


def load_config(config_path):
    """
    Load configuration from file.
    Returns a dictionary with configuration values.
    """
    log(f"Loading configuration from {config_path}")
    
    config = {
        'WLAN_IFACE': '',
        'ETH_IFACE': '',
        'GATEWAY_IP': '',
        'ETH_STATIC_IP': '10.42.0.1',
        'ETH_SUBNET': '24',
        'WPA_CONF': '/etc/wpa_supplicant/wpa_supplicant.conf',
        'CONFIG_DIR': '/etc/alpine-wifi-bridge',
        'BACKUP_DIR': '/etc/alpine-wifi-bridge/backup',
        'IPTABLES_RULES': '/etc/iptables/rules.v4',
        'IPTABLES_SCRIPT': '/etc/local.d/iptables.start',
        'ENABLE_PORT_FORWARDING': 'true',
        'PC_IP': ''
    }
    
    # Check if config_path is a shell-style config or an INI file
    if os.path.exists(config_path):
        if config_path.endswith('.conf'):
            # Shell-style config (key=value)
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            if key in config:
                                config[key] = value
        else:
            # Try as INI file
            try:
                parser = ConfigParser()
                parser.read(config_path)
                if 'alpine-wifi-bridge' in parser:
                    section = parser['alpine-wifi-bridge']
                    for key in config:
                        if key.lower() in section:
                            config[key] = section[key.lower()]
            except Exception as e:
                warn_continue(f"Failed to parse config file as INI: {e}")
    else:
        warn_continue(f"Configuration file not found: {config_path}")
    
    return config


def save_runtime_config(config, filepath):
    """Save runtime configuration to a file."""
    log(f"Saving configuration to {filepath}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(f"# Alpine Wi-Fi Bridge Configuration\n")
        f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for key, value in config.items():
            f.write(f"{key}=\"{value}\"\n")