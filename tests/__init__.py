"""
Test suite for the AI Agent application.

This package contains all test files for services and utilities.
"""

import pytest
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

# Setup test constants
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')