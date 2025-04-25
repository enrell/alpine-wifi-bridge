"""
Tests for the network module
"""
import unittest
import os
import sys
import io
from unittest.mock import patch, mock_open, MagicMock, call

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.network import (
    install_packages, detect_interfaces, detect_gateway_ip,
    setup_wifi, setup_ethernet, setup_routing
)


class TestNetwork(unittest.TestCase):
    """Test cases for network module functions"""

    @patch('pybridge.network.command_exists')
    @patch('pybridge.network.run_command')
    @patch('os.makedirs')
    def test_install_packages(self, mock_makedirs, mock_run, mock_command_exists):
        """Test package installation"""
        # Mock run_command to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Mock nft command exists
        mock_command_exists.return_value = True
        
        # Call the function
        install_packages()
        
        # Verify apk update was called
        mock_run.assert_any_call("apk update")
        
        # Verify packages were installed
        mock_run.assert_any_call("apk add --no-cache wireless-tools wpa_supplicant")
        
        # Verify directories were created
        mock_makedirs.assert_any_call("/etc/wpa_supplicant", exist_ok=True)

    @patch('pybridge.network.run_command')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_detect_interfaces(self, mock_listdir, mock_exists, mock_run):
        """Test interface detection"""
        config = {}
        
        # Mock run_command to find wlan0
        mock_wlan_result = MagicMock()
        mock_wlan_result.returncode = 0
        mock_wlan_result.stdout = "wlan0"
        
        # Mock run_command to find eth0
        mock_eth_result = MagicMock()
        mock_eth_result.returncode = 0
        mock_eth_result.stdout = "eth0"
        
        mock_run.side_effect = [mock_wlan_result, mock_eth_result]
        
        # Call the function
        detect_interfaces(config)
        
        # Verify interfaces were detected
        self.assertEqual(config['WLAN_IFACE'], 'wlan0')
        self.assertEqual(config['ETH_IFACE'], 'eth0')

    @patch('builtins.input')
    @patch('pybridge.network.run_command')
    def test_detect_gateway_ip_from_route(self, mock_run, mock_input):
        """Test gateway IP detection from route table"""
        config = {'WLAN_IFACE': 'wlan0'}
        
        # Mock run_command to find gateway IP
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "192.168.1.1"
        mock_run.return_value = mock_result
        
        # Call the function
        detect_gateway_ip(config)
        
        # Verify gateway was detected
        self.assertEqual(config['GATEWAY_IP'], '192.168.1.1')

    @patch('builtins.input')
    @patch('pybridge.network.run_command')
    def test_detect_gateway_ip_default(self, mock_run, mock_input):
        """Test gateway IP detection using default"""
        config = {'WLAN_IFACE': 'wlan0'}
        
        # Mock run_command to fail finding gateway IP
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        # Mock user input to not specify custom gateway
        mock_input.return_value = 'n'
        
        # Call the function
        detect_gateway_ip(config)
        
        # Verify default gateway is used
        self.assertEqual(config['GATEWAY_IP'], '192.168.0.1')

    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.input')
    @patch('os.path.exists')
    @patch('pybridge.network.run_command')
    @patch('os.makedirs')
    @patch('os.unlink')
    def test_setup_wifi_new_config(self, mock_unlink, mock_makedirs, mock_run, 
                              mock_exists, mock_input, mock_tempfile):
        """Test Wi-Fi setup with new configuration"""
        config = {
            'WLAN_IFACE': 'wlan0',
            'WPA_CONF': '/etc/wpa_supplicant/wpa_supplicant.conf'
        }
        
        # Mock config file doesn't exist
        mock_exists.return_value = False
        
        # Mock user inputs
        mock_input.side_effect = ['MySSID', 'MyPassword']
        
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/mock_temp_file'
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        # Mock wpa_supplicant creation success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Call the function
        setup_wifi(config)
        
        # Verify wpa_passphrase was called
        mock_run.assert_any_call(f"wpa_passphrase 'MySSID' \"$(cat {mock_temp.name})\" > {config['WPA_CONF']} 2>/dev/null")
        
        # Verify wpa_supplicant was started
        mock_run.assert_any_call(f"wpa_supplicant -B -i {config['WLAN_IFACE']} -c {config['WPA_CONF']}")

    @patch('pybridge.network.run_command')
    def test_setup_ethernet(self, mock_run):
        """Test ethernet interface setup"""
        config = {
            'ETH_IFACE': 'eth0',
            'ETH_STATIC_IP': '10.42.0.1',
            'ETH_SUBNET': '24'
        }
        
        # Mock interface doesn't have IP set
        mock_ip_check = MagicMock()
        mock_ip_check.returncode = 1
        
        # Mock interface not up
        mock_link_check = MagicMock()
        mock_link_check.returncode = 1
        
        # Mock setting IP success
        mock_ip_set = MagicMock()
        mock_ip_set.returncode = 0
        
        # Mock interface up success
        mock_link_up = MagicMock()
        mock_link_up.returncode = 0
        
        mock_run.side_effect = [mock_ip_check, mock_ip_set, mock_link_check, mock_link_up]
        
        # Call the function
        setup_ethernet(config)
        
        # Verify IP was set
        mock_run.assert_any_call(f"ip addr add {config['ETH_STATIC_IP']}/{config['ETH_SUBNET']} dev {config['ETH_IFACE']}")
        
        # Verify interface was brought up
        mock_run.assert_any_call(f"ip link set {config['ETH_IFACE']} up")

    @patch('pybridge.network.run_command')
    def test_setup_routing(self, mock_run):
        """Test routing setup"""
        config = {
            'WLAN_IFACE': 'wlan0',
            'GATEWAY_IP': '192.168.1.1'
        }
        
        # Mock default route doesn't exist
        mock_route_check = MagicMock()
        mock_route_check.returncode = 1
        
        # Mock set route success
        mock_route_set = MagicMock()
        mock_route_set.returncode = 0
        
        mock_run.side_effect = [mock_route_check, mock_route_set]
        
        # Mock reading ip_forward = 0
        m = mock_open(read_data='0')
        
        # Need to mock open for both reading and writing
        with patch('builtins.open', m):
            # Mock sysctl.conf exists but doesn't have ip_forward
            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data='some other content\n')):
                setup_routing(config)
        
        # Verify default route was set
        mock_run.assert_any_call(f"ip route replace default via {config['GATEWAY_IP']} dev {config['WLAN_IFACE']}")


if __name__ == '__main__':
    unittest.main()