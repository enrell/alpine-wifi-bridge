"""
Tests for the port forwarding module
"""
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.portforward import setup_port_forwarding, remove_port_forwarding


class TestPortForward(unittest.TestCase):
    """Test cases for port forwarding functions"""

    @patch('pybridge.portforward.run_command')
    def test_setup_port_forwarding_disabled(self, mock_run):
        """Test port forwarding when disabled in config"""
        config = {
            'ENABLE_PORT_FORWARDING': 'false'
        }
        
        # Call the function
        setup_port_forwarding(config)
        
        # Verify no commands were run
        mock_run.assert_not_called()

    @patch('pybridge.portforward.run_command')
    def test_setup_port_forwarding_no_pc_ip(self, mock_run):
        """Test port forwarding when PC_IP is not set"""
        config = {
            'ENABLE_PORT_FORWARDING': 'true',
            'PC_IP': ''
        }
        
        # Call the function
        setup_port_forwarding(config)
        
        # Verify no commands were run
        mock_run.assert_not_called()

    @patch('pybridge.portforward.run_command')
    def test_setup_port_forwarding_success(self, mock_run):
        """Test port forwarding setup success"""
        config = {
            'ENABLE_PORT_FORWARDING': 'true',
            'PC_IP': '10.42.0.100',
            'WLAN_IFACE': 'wlan0'
        }
        
        # Mock getting the WLAN IP
        mock_ip_result = MagicMock()
        mock_ip_result.returncode = 0
        mock_ip_result.stdout = "192.168.1.5"
        
        # Mock rule checks (rules don't exist)
        mock_rule_check = MagicMock()
        mock_rule_check.returncode = 1
        
        # Mock rule additions (success)
        mock_rule_add = MagicMock()
        mock_rule_add.returncode = 0
        
        mock_run.side_effect = [mock_ip_result, mock_rule_check, mock_rule_add, mock_rule_check, mock_rule_add, mock_rule_check, mock_rule_add]
        
        # Call the function
        setup_port_forwarding(config)
        
        # Verify WLAN IP was determined
        mock_run.assert_any_call(f"ip -4 addr show {config['WLAN_IFACE']} | grep -oP 'inet \\K[\\d.]+'", silent=True)
        
        # Verify DNAT rule was added
        mock_run.assert_any_call(f"iptables -t nat -A PREROUTING -d 192.168.1.5 -j DNAT --to-destination {config['PC_IP']}")
        
        # Verify forward rule was added
        mock_run.assert_any_call(f"iptables -A FORWARD -d {config['PC_IP']} -j ACCEPT")
        
        # Verify WLAN IP was stored in config
        self.assertEqual(config['WLAN_IP'], "192.168.1.5")

    @patch('pybridge.portforward.run_command')
    def test_remove_port_forwarding(self, mock_run):
        """Test removing port forwarding rules"""
        config = {
            'WLAN_IP': '192.168.1.5',
            'PC_IP': '10.42.0.100'
        }
        
        # Call the function
        remove_port_forwarding(config)
        
        # Verify DNAT rule was removed
        mock_run.assert_any_call(f"iptables -t nat -D PREROUTING -d {config['WLAN_IP']} -j DNAT --to-destination {config['PC_IP']} 2>/dev/null")
        
        # Verify forward rule was removed
        mock_run.assert_any_call(f"iptables -D FORWARD -d {config['PC_IP']} -j ACCEPT 2>/dev/null")

    @patch('pybridge.portforward.run_command')
    def test_remove_port_forwarding_auto_detect_ip(self, mock_run):
        """Test removing port forwarding when WLAN_IP is not in config"""
        config = {
            'PC_IP': '10.42.0.100',
            'WLAN_IFACE': 'wlan0'
        }
        
        # Mock getting the WLAN IP
        mock_ip_result = MagicMock()
        mock_ip_result.returncode = 0
        mock_ip_result.stdout = "192.168.1.5"
        mock_run.return_value = mock_ip_result
        
        # Call the function
        remove_port_forwarding(config)
        
        # Verify WLAN IP was determined
        mock_run.assert_any_call(f"ip -4 addr show {config['WLAN_IFACE']} | grep -oP 'inet \\K[\\d.]+'", silent=True)
        
        # Verify DNAT rule was removed
        mock_run.assert_any_call(f"iptables -t nat -D PREROUTING -d 192.168.1.5 -j DNAT --to-destination {config['PC_IP']} 2>/dev/null")


if __name__ == '__main__':
    unittest.main()