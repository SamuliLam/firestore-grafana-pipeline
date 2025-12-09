"""
Pytest configuration file that sets up mocks before module imports.
Place this file in the tests/ directory.
"""
import sys
from unittest.mock import Mock, MagicMock
import pytest


# Mock Google Cloud Firestore before any imports
sys.modules['google.cloud.firestore'] = MagicMock()

# Mock the Firestore client class
mock_firestore = MagicMock()
sys.modules['google.cloud.firestore'].Client = Mock(return_value=Mock())




@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests"""
    yield
    # Cleanup can go here if needed