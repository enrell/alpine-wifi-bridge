"""
Tests for the firewall module
"""
import unittest
import os
import sys
from unittest.mock import patch, mock_open, MagicMock

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.firewall import detect_firewall_system, setup_firewall, setup_iptables_firewall, save_firewall_rules


class TestFirewall(unittest.TestCase):
    """Test cases for firewall functions"""

    @patch('os.path.exists')
    @patch('pybridge.firewall.command_exists')
    def test_detect_firewall_system_nft(self, mock_command_exists, mock_exists):
        """Test detecting nftables as firewall system"""
        # Mock nft exists and ip_tables_names doesn't
        mock_command_exists.return_value = True
        mock_exists.return_value = False
        
        result = detect_firewall_system()
        self.assertEqual(result, "nftables")

    @patch('os.path.exists')
    @patch('pybridge.firewall.command_exists')
    def test_detect_firewall_system_iptables(self, mock_command_exists, mock_exists):
        """Test detecting iptables as firewall system"""
        # Mock ip_tables_names exists
        mock_exists.return_value = True
        
        result = detect_firewall_system()
        self.assertEqual(result, "iptables")

    @patch('pybridge.firewall.detect_firewall_system')
    @patch('pybridge.firewall.setup_nftables_firewall')
    @patch('pybridge.firewall.setup_iptables_firewall')
    def test_setup_firewall_nft(self, mock_setup_iptables, mock_setup_nftables, mock_detect):
        """Test firewall setup with nftables"""
        # Config with interfaces
        config = {
            'WLAN_IFACE': 'wlan0',
            'ETH_IFACE': 'eth0'
        }
        
        # Mock detection of nftables
        mock_detect.return_value = "nftables"
        
        # Call the function
        setup_firewall(config)
        
        # Verify nftables setup was called
        mock_setup_nftables.assert_called_once_with(config)
        
        # Verify iptables setup was not called
        mock_setup_iptables.assert_not_called()

    @patch('pybridge.firewall.detect_firewall_system')
    @patch('pybridge.firewall.setup_nftables_firewall')
    @patch('pybridge.firewall.setup_iptables_firewall')
    def test_setup_firewall_iptables(self, mock_setup_iptables, mock_setup_nftables, mock_detect):
        """Test firewall setup with iptables"""
        # Config with interfaces
        config = {
            'WLAN_IFACE': 'wlan0',
            'ETH_IFACE': 'eth0'
        }
        
        # Mock detection of iptables
        mock_detect.return_value = "iptables"
        
        # Call the function
        setup_firewall(config)
        
        # Verify iptables setup was called
        mock_setup_iptables.assert_called_once_with(config)
        
        # Verify nftables setup was not called
        mock_setup_nftables.assert_not_called()

    @patch('pybridge.firewall.run_command')
    def test_setup_iptables_firewall(self, mock_run):
        """Test setting up iptables firewall"""
        # Config with interfaces
        config = {
            'WLAN_IFACE': 'wlan0',
            'ETH_IFACE': 'eth0',
            'ETH_STATIC_IP': '10.42.0.1',
            'ETH_SUBNET': '24'
        }
        
        # Mock all rules not existing yet
        mock_rule_check = MagicMock()
        mock_rule_check.returncode = 1
        
        # Mock rule addition success
        mock_rule_add = MagicMock()
        mock_rule_add.returncode = 0
        
        mock_run.side_effect = [mock_rule_check] * 10 + [mock_rule_add] * 10
        
        # Call the function
        setup_iptables_firewall(config)
        
        # Verify basic NAT rule was added
        mock_run.assert_any_call(f"iptables -t nat -A POSTROUTING -o {config['WLAN_IFACE']} -j MASQUERADE")
        
        # Verify forward rule was added
        mock_run.assert_any_call(f"iptables -A FORWARD -i {config['ETH_IFACE']} -o {config['WLAN_IFACE']} -m state --state RELATED,ESTABLISHED -j ACCEPT")

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('os.chmod')
    @patch('pybridge.firewall.detect_firewall_system')
    @patch('pybridge.firewall.run_command')
    def test_save_firewall_rules(self, mock_run, mock_detect, mock_chmod, mock_exists, mock_makedirs):
        """Test saving firewall rules"""
        # Mock config
        config = {
            'IPTABLES_RULES': '/etc/iptables/rules.v4',
            'IPTABLES_SCRIPT': '/etc/local.d/iptables.start'
        }
        
        # Mock iptables detection
        mock_detect.return_value = "iptables"
        
        # Mock that /etc/init.d/iptables doesn't exist
        mock_exists.return_value = False
        
        # Call the function
        save_firewall_rules(config)
        
        # Verify directories were created
        mock_makedirs.assert_any_call(os.path.dirname(config['IPTABLES_RULES']), exist_ok=True)
        
        # Verify rules were saved
        mock_run.assert_any_call(f"iptables-save > {config['IPTABLES_RULES']}")
        
        # Verify local service was enabled
        mock_run.assert_any_call("rc-update add local default 2>/dev/null")
        
        # Verify script was made executable
        mock_chmod.assert_called_once()


if __name__ == '__main__':
    unittest.main()