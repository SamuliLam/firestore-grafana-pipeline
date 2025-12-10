"""
Pytest configuration file that sets up mocks before module imports.
Place this file in the tests/ directory.
"""
import sys
import os
from unittest.mock import MagicMock
import pytest


# Set environment variables FIRST, before any imports
os.environ['GCP_PROJECT_ID'] = 'test-project-id'
os.environ['FIRESTORE_COLLECTIONS'] = 'viherpysakki,ymparistomoduuli,suvilahti_uusi,suvilahti,urban'

# Mock only Google Cloud Firestore to prevent authentication errors
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.firestore'] = MagicMock()


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Ensure environment variables are set for each test"""
    os.environ['GCP_PROJECT_ID'] = 'test-project-id'
    os.environ['FIRESTORE_COLLECTIONS'] = 'viherpysakki,ymparistomoduuli,suvilahti_uusi,suvilahti,urban'
    yield


@pytest.fixture(autouse=True)
def reset_firestore_client():
    """Reset the global CLIENT variable between tests"""
    import src.history_to_timescale as hist_module
    hist_module.CLIENT = None
    yield
    hist_module.CLIENT = None