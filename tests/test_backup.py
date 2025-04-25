"""
Tests for the backup module
"""
import unittest
import os
import sys
from unittest.mock import patch, mock_open

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.backup import backup_network_config, restore_settings


class TestBackup(unittest.TestCase):
    """Test cases for backup functions"""

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('pybridge.backup.run_command')
    def test_backup_network_config_new(self, mock_run, mock_exists, mock_makedirs):
        """Test creating a new backup"""
        # Mock that backup doesn't exist yet
        mock_exists.return_value = False
        
        # Set up config
        config = {
            'BACKUP_DIR': '/mock/backup'
        }
        
        # Mock open
        m = mock_open()
        with patch('builtins.open', m):
            backup_network_config(config)
        
        # Verify backup directory was created
        mock_makedirs.assert_called_with(config['BACKUP_DIR'], exist_ok=True)
        
        # Verify files were written
        m.assert_called()
        
        # Verify commands were run
        self.assertTrue(mock_run.called)
        
    @patch('os.path.exists')
    @patch('pybridge.backup.run_command')
    def test_backup_network_config_existing(self, mock_run, mock_exists):
        """Test skipping backup when one already exists"""
        # Mock that backup already exists
        mock_exists.return_value = True
        
        # Set up config
        config = {
            'BACKUP_DIR': '/mock/backup'
        }
        
        # Mock open
        m = mock_open()
        with patch('builtins.open', m):
            backup_network_config(config)
        
        # Verify no files were written (open wasn't called for writing)
        m.assert_not_called()
        
        # Verify no commands were run
        mock_run.assert_not_called()

    @patch('pybridge.backup.run_command')
    def test_restore_settings(self, mock_run):
        """Test restore settings functionality"""
        # Set up config
        config = {
            'WLAN_IFACE': 'wlan0',
            'ETH_IFACE': 'eth0',
            'ETH_STATIC_IP': '10.42.0.1',
            'ETH_SUBNET': '24',
            'GATEWAY_IP': '192.168.1.1',
            'BACKUP_DIR': '/mock/backup'
        }
        
        # Mock existence of sysctl.conf
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='net.ipv4.ip_forward=1\n')):
            restore_settings(config)
        
        # Verify commands were run
        self.assertTrue(mock_run.called)
        
        # Check specific calls for disabling IP forwarding
        mock_run.assert_any_call("pkill wpa_supplicant")


if __name__ == '__main__':
    unittest.main()