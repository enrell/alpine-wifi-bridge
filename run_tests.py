#!/usr/bin/env python3
"""
Test runner for Alpine Wi-Fi Bridge
Run this script to execute all tests in the tests directory
"""
import unittest
import sys

if __name__ == "__main__":
    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover('tests')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return non-zero exit code if tests failed, for CI integration
    sys.exit(0 if result.wasSuccessful() else 1)