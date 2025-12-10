import pytest
import os
from unittest.mock import Mock, patch, call, MagicMock
from datetime import datetime


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client for sync tests"""
    with patch('src.history_to_timescale.get_firestore_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_db_functions():
    """Mock database functions"""
    with patch('src.history_to_timescale.get_oldest_collection_timestamp_from_db') as mock_get_oldest, \
         patch('src.history_to_timescale.insert_sensor_rows') as mock_insert:
        yield {
            'get_oldest': mock_get_oldest,
            'insert': mock_insert
        }


@pytest.fixture
def mock_sensor_parser():
    """Mock SensorDataParser"""
    with patch('src.history_to_timescale.SensorDataParser') as mock_parser_class:
        yield mock_parser_class


@pytest.fixture
def mock_sync_status():
    """Mock sync_status"""
    with patch('src.history_to_timescale.sync_status', {'state': None, 'error': None}) as mock_status:
        yield mock_status


@pytest.fixture
def sample_firestore_doc():
    """Create a sample Firestore document"""
    doc = Mock()
    doc.id = "test_doc_123"
    doc.to_dict.return_value = {
        "timestamp": datetime(2024, 1, 1, 12, 0, 0),
        "temperature": 22.5,
        "humidity": 65.0
    }
    return doc


class TestGetFirestoreClient:
    """Test get_firestore_client function"""

    def test_client_initialization_success(self):
        """Test successful Firestore client initialization"""
        import src.history_to_timescale as hist_module

        # Reset CLIENT to None
        hist_module.CLIENT = None

        with patch('src.history_to_timescale.firestore.Client') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_class.return_value = mock_client_instance

            client = hist_module.get_firestore_client()

            assert client == mock_client_instance
            mock_client_class.assert_called_once_with(project='test-project-id')


    def test_client_initialization_failure(self):
        """Test Firestore client initialization failure"""
        import src.history_to_timescale as hist_module

        # Reset CLIENT to None
        hist_module.CLIENT = None

        with patch('src.history_to_timescale.firestore.Client') as mock_client_class:
            mock_client_class.side_effect = Exception("Authentication failed")

            client = hist_module.get_firestore_client()

            assert client is None


    def test_client_reuses_existing_instance(self):
        """Test that client is only created once (singleton pattern)"""
        import src.history_to_timescale as hist_module

        # Set up existing client
        existing_client = Mock()
        hist_module.CLIENT = existing_client

        with patch('src.history_to_timescale.firestore.Client') as mock_client_class:
            client = hist_module.get_firestore_client()

            # Should return existing client without creating a new one
            assert client == existing_client
            mock_client_class.assert_not_called()


class TestSyncFirestoreToTimescale:

    def test_sync_with_no_oldest_timestamp(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status,
        sample_firestore_doc
    ):
        """Test sync when no oldest timestamp exists in database"""
        from src.history_to_timescale import sync_firestore_to_timescale, COLLECTIONS

        # Setup
        mock_db_functions['get_oldest'].return_value = None

        mock_collection = Mock()
        mock_collection.stream.return_value = [sample_firestore_doc]
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [
            {"sensor_id": "test", "value": 22.5}
        ]
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'success'
        assert mock_sync_status['error'] is None
        assert mock_db_functions['get_oldest'].call_count == len(COLLECTIONS)
        assert mock_firestore_client.collection.call_count == len(COLLECTIONS)
        assert mock_parser_instance.process_raw_sensor_data.called
        assert mock_db_functions['insert'].called


    def test_sync_with_oldest_timestamp(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status,
        sample_firestore_doc
    ):
        """Test sync when oldest timestamp exists in database"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup
        oldest_ts = datetime(2024, 1, 15, 10, 0, 0)
        mock_db_functions['get_oldest'].return_value = oldest_ts

        mock_collection = Mock()
        mock_where = Mock()
        mock_where.stream.return_value = [sample_firestore_doc]
        mock_collection.where.return_value = mock_where
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [
            {"sensor_id": "test", "value": 22.5}
        ]
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'success'
        mock_collection.where.assert_called_with("timestamp", "<", oldest_ts)


    def test_sync_with_no_parsed_rows(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status,
        sample_firestore_doc
    ):
        """Test sync when parser returns no rows"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup
        mock_db_functions['get_oldest'].return_value = None

        mock_collection = Mock()
        mock_collection.stream.return_value = [sample_firestore_doc]
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = []  # No rows
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'success'
        assert not mock_db_functions['insert'].called


    def test_sync_with_multiple_documents(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status
    ):
        """Test sync with multiple documents"""
        from src.history_to_timescale import sync_firestore_to_timescale, COLLECTIONS

        # Setup
        mock_db_functions['get_oldest'].return_value = None

        doc1 = Mock()
        doc1.id = "doc_1"
        doc1.to_dict.return_value = {"timestamp": datetime(2024, 1, 1), "temp": 20}

        doc2 = Mock()
        doc2.id = "doc_2"
        doc2.to_dict.return_value = {"timestamp": datetime(2024, 1, 2), "temp": 21}

        mock_collection = Mock()
        mock_collection.stream.return_value = [doc1, doc2]
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'success'
        # Should be called twice per collection (2 docs * 5 collections = 10)
        assert mock_parser_instance.process_raw_sensor_data.call_count == 2 * len(COLLECTIONS)
        assert mock_db_functions['insert'].call_count == 2 * len(COLLECTIONS)


    def test_sync_handles_exception_in_parsing(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status,
        sample_firestore_doc
    ):
        """Test sync handles exceptions during parsing"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup
        mock_db_functions['get_oldest'].return_value = None

        mock_collection = Mock()
        mock_collection.stream.return_value = [sample_firestore_doc]
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.side_effect = Exception("Parse error")
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'failed'
        assert mock_sync_status['error'] == "Parse error"
        assert not mock_db_functions['insert'].called


    def test_sync_handles_firestore_exception(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status
    ):
        """Test sync handles Firestore connection exceptions"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup
        mock_db_functions['get_oldest'].return_value = None
        mock_firestore_client.collection.side_effect = Exception("Firestore connection error")

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'failed'
        assert mock_sync_status['error'] == "Firestore connection error"


    def test_sync_handles_database_exception(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status,
        sample_firestore_doc
    ):
        """Test sync handles database insertion exceptions"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup
        mock_db_functions['get_oldest'].return_value = None
        mock_db_functions['insert'].side_effect = Exception("Database insert error")

        mock_collection = Mock()
        mock_collection.stream.return_value = [sample_firestore_doc]
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'failed'
        assert mock_sync_status['error'] == "Database insert error"


    def test_sync_handles_client_initialization_failure(
        self,
        mock_db_functions,
        mock_sync_status
    ):
        """Test sync when Firestore client cannot be initialized"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup - make get_firestore_client return None
        with patch('src.history_to_timescale.get_firestore_client') as mock_get_client:
            mock_get_client.return_value = None

            # Execute
            sync_firestore_to_timescale()

            # Assert
            assert mock_sync_status['state'] == 'failed'
            assert mock_sync_status['error'] == "Firestore client not initialized (check credentials)"
            assert not mock_db_functions['get_oldest'].called


    def test_sync_processes_all_collections(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status
    ):
        """Test that sync processes all defined collections"""
        from src.history_to_timescale import sync_firestore_to_timescale, COLLECTIONS

        # Setup
        mock_db_functions['get_oldest'].return_value = None

        mock_collection = Mock()
        mock_collection.stream.return_value = []
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert
        assert mock_sync_status['state'] == 'success'
        # Check that collection was called for each collection name
        assert mock_firestore_client.collection.call_count == len(COLLECTIONS)
        # Verify each collection name was used
        collection_calls = [call_args[0][0] for call_args in mock_firestore_client.collection.call_args_list]
        assert collection_calls == list(COLLECTIONS)


    def test_sync_status_reset_on_new_run(
        self,
        mock_firestore_client,
        mock_db_functions,
        mock_sensor_parser,
        mock_sync_status
    ):
        """Test that sync_status is properly reset at the start"""
        from src.history_to_timescale import sync_firestore_to_timescale

        # Setup - set initial error state
        mock_sync_status['state'] = 'failed'
        mock_sync_status['error'] = 'Previous error'

        mock_db_functions['get_oldest'].return_value = None

        mock_collection = Mock()
        mock_collection.stream.return_value = []
        mock_firestore_client.collection.return_value = mock_collection

        mock_parser_instance = Mock()
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute
        sync_firestore_to_timescale()

        # Assert - should be reset at start then set to success
        assert mock_sync_status['state'] == 'success'
        assert mock_sync_status['error'] is None


def test_each_collection_individually(
    mock_firestore_client,
    mock_db_functions,
    mock_sensor_parser,
    mock_sync_status,
    sample_firestore_doc
):
    """Test to verify each collection is processed correctly"""
    from src.history_to_timescale import sync_firestore_to_timescale, COLLECTIONS

    # Setup
    mock_db_functions['get_oldest'].return_value = None

    processed_collections = []

    def collection_side_effect(name):
        processed_collections.append(name)
        mock_collection = Mock()
        mock_collection.stream.return_value = [sample_firestore_doc]
        return mock_collection

    mock_firestore_client.collection.side_effect = collection_side_effect

    mock_parser_instance = Mock()
    mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
    mock_sensor_parser.return_value = mock_parser_instance

    # Execute
    sync_firestore_to_timescale()

    # Assert
    assert len(processed_collections) == len(COLLECTIONS)
    for collection_name in COLLECTIONS:
        assert collection_name in processed_collections
    assert mock_sync_status['state'] == 'success'


class TestEnvironmentVariables:
    """Test environment variable configuration"""

    def test_collections_loaded_from_env(self):
        """Test that COLLECTIONS is loaded from environment variable"""
        from src.history_to_timescale import COLLECTIONS

        expected_collections = ['viherpysakki', 'ymparistomoduuli', 'suvilahti_uusi', 'suvilahti', 'urban']
        assert list(COLLECTIONS) == expected_collections


    def test_gcp_project_id_from_env(self):
        """Test that GCP_PROJECT_ID is loaded from environment"""
        from src.history_to_timescale import project_id

        assert project_id == 'test-project-id'