"""
Tests for the utilities module
"""
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pybridge.utils import log, warn_continue, error_exit, run_command, command_exists


class TestUtils(unittest.TestCase):
    """Test cases for utility functions"""

    @patch('builtins.print')
    def test_log(self, mock_print):
        """Test log function"""
        message = "Test log message"
        log(message)
        mock_print.assert_called_once_with(f"[INFO] {message}")

    @patch('builtins.print')
    def test_warn_continue(self, mock_print):
        """Test warn_continue function"""
        message = "Test warning message"
        warn_continue(message)
        mock_print.assert_called_once_with(f"[WARNING] {message} - Skipping this step.")

    @patch('builtins.print')
    @patch('sys.exit')
    def test_error_exit(self, mock_exit, mock_print):
        """Test error_exit function"""
        message = "Test error message"
        error_exit(message)
        mock_print.assert_called_once_with(f"[ERROR] {message}")
        mock_exit.assert_called_once_with(1)

    @patch('subprocess.run')
    def test_run_command(self, mock_run):
        """Test run_command function"""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Call the function
        command = "echo test"
        result = run_command(command)

        # Verify
        mock_run.assert_called_once()
        self.assertEqual(result, mock_result)

    @patch('shutil.which')
    def test_command_exists(self, mock_which):
        """Test command_exists function"""
        # Test command exists
        mock_which.return_value = '/bin/ls'
        self.assertTrue(command_exists('ls'))

        # Test command does not exist
        mock_which.return_value = None
        self.assertFalse(command_exists('nonexistentcommand'))


if __name__ == '__main__':
    unittest.main()