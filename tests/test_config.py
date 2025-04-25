"""
Tests for the configuration module
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, mock_open

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.config import load_config, save_runtime_config


class TestConfig(unittest.TestCase):
    """Test cases for configuration functions"""

    def test_load_config_missing_file(self):
        """Test loading config when file doesn't exist"""
        with patch('os.path.exists', return_value=False):
            config = load_config('/nonexistent/path')
            # Should return default config
            self.assertEqual(config['ETH_STATIC_IP'], '10.42.0.1')
            self.assertEqual(config['ETH_SUBNET'], '24')

    def test_load_config_shell_style(self):
        """Test loading shell-style config file"""
        # Create a mock file content
        mock_file_content = """
        # Comment
        WLAN_IFACE="wlan0"
        ETH_IFACE="eth0"
        GATEWAY_IP="192.168.1.1"
        """
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            config = load_config('/mock/config.conf')
            self.assertEqual(config['WLAN_IFACE'], 'wlan0')
            self.assertEqual(config['ETH_IFACE'], 'eth0')
            self.assertEqual(config['GATEWAY_IP'], '192.168.1.1')

    def test_save_runtime_config(self):
        """Test saving runtime configuration"""
        config = {
            'WLAN_IFACE': 'wlan0',
            'ETH_IFACE': 'eth0',
            'GATEWAY_IP': '192.168.1.1'
        }
        
        # Use a real temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            with patch('os.makedirs'):
                save_runtime_config(config, temp_path)
            
            # Read the file back to check content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check if the file contains our config values
            self.assertIn('WLAN_IFACE="wlan0"', content)
            self.assertIn('ETH_IFACE="eth0"', content)
            self.assertIn('GATEWAY_IP="192.168.1.1"', content)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()