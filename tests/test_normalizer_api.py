import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
from datetime import datetime


# Mock all external dependencies before importing the src
@pytest.fixture(autouse=True, scope='session')
def mock_dependencies():
    """Mock all external dependencies at session level"""
    with patch('src.db.init_db'), \
         patch('src.db.insert_sensor_rows'), \
         patch('src.db.insert_sensor_metadata'), \
         patch('src.db.delete_sensor'), \
         patch('src.db.get_all_sensor_metadata'):
        yield


@pytest.fixture
def client():
    """Create a test client for the FastAPI src"""
    from src.normalizer_api import app
    return TestClient(app)


@pytest.fixture
def mock_insert_rows():
    """Mock insert_sensor_rows"""
    with patch('src.routers.webhook.insert_sensor_rows') as mock:
        yield mock


@pytest.fixture
def mock_insert_metadata():
    """Mock insert_sensor_metadata"""
    with patch('src.routers.sensors.insert_sensor_metadata') as mock:
        yield mock


@pytest.fixture
def mock_delete_sensor():
    """Mock delete_sensor"""
    with patch('src.routers.sensors.delete_sensor') as mock:
        yield mock


@pytest.fixture
def mock_get_metadata():
    """Mock get_all_sensor_metadata"""
    with patch('src.routers.sensors.get_all_sensor_metadata') as mock:
        yield mock


@pytest.fixture
def mock_sensor_parser():
    """Mock SensorDataParser"""
    with patch('src.routers.webhook.SensorDataParser') as mock_parser_class:
        yield mock_parser_class


@pytest.fixture
def mock_sync_function():
    """Mock sync_firestore_to_timescale"""
    with patch('src.routers.history.sync_firestore_to_timescale') as mock_sync:
        yield mock_sync


@pytest.fixture
def mock_sync_status():
    """Mock sync_status"""
    with patch('src.routers.history.sync_status', {'state': None, 'error': None}) as mock_status:
        yield mock_status


@pytest.fixture
def sample_sensor_data():
    """Sample sensor data for testing"""
    return {
        "sensor_type": "temperature",
        "sensor_id": "sensor_001",
        "timestamp": "2024-01-01T12:00:00",
        "temperature": 22.5,
        "humidity": 65.0
    }


@pytest.fixture
def sample_sensor_metadata():
    """Sample sensor metadata for testing"""
    return {
        "sensor_id": "sensor_001",
        "latitude": 60.1699,
        "longitude": 24.9384,
        "sensor_type": "temperature"
    }


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test that health check returns OK"""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAddSensor:
    """Test add sensor endpoint"""

    def test_add_sensor_success(self, client, mock_insert_metadata, sample_sensor_metadata):
        """Test successfully adding a sensor"""
        mock_insert_metadata.return_value = None

        response = client.post("/api/sensors", json=sample_sensor_metadata)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Sensor added successfully"
        assert data["data"] == sample_sensor_metadata
        mock_insert_metadata.assert_called_once_with([sample_sensor_metadata])

    def test_add_sensor_missing_required_field(self, client):
        """Test adding sensor with missing required field"""
        incomplete_data = {
            "sensor_id": "sensor_001",
            "latitude": 60.1699,
            # Missing longitude and sensor_type
        }
        response = client.post("/api/sensors", json=incomplete_data)

        assert response.status_code == 422  # Pydantic validation error

    def test_add_sensor_invalid_data_type(self, client):
        """Test adding sensor with invalid data type"""
        invalid_data = {
            "sensor_id": "sensor_001",
            "latitude": "not_a_number",  # Should be float
            "longitude": 24.9384,
            "sensor_type": "temperature"
        }
        response = client.post("/api/sensors", json=invalid_data)

        assert response.status_code == 422  # Pydantic validation error

    def test_add_sensor_invalid_json(self, client):
        """Test adding sensor with invalid JSON"""
        response = client.post(
            "/api/sensors",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # FastAPI validation error

    def test_add_sensor_database_error(self, client, mock_insert_metadata, sample_sensor_metadata):
        """Test adding sensor when database fails"""
        mock_insert_metadata.side_effect = Exception("Database connection error")

        response = client.post("/api/sensors", json=sample_sensor_metadata)

        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Database connection error" in data["message"]


class TestFirestoreWebhook:
    """Test Firestore webhook endpoint"""

    def test_webhook_success(self, client, mock_insert_rows, mock_sensor_parser, sample_sensor_data):
        """Test successful webhook processing"""
        # Setup mock parser
        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [
            {"sensor_id": "sensor_001", "value": 22.5}
        ]
        mock_sensor_parser.return_value = mock_parser_instance

        # Mock file writing
        with patch('builtins.open', mock_open()):
            response = client.post("/api/webhook", json=sample_sensor_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "New data successfully inserted to the database"
        assert data["data"] == sample_sensor_data

        # Verify parser was called correctly
        mock_sensor_parser.assert_called_once_with("temperature")
        mock_parser_instance.process_raw_sensor_data.assert_called_once_with(sample_sensor_data)
        mock_insert_rows.assert_called_once()

    def test_webhook_missing_sensor_type(self, client):
        """Test webhook with missing required sensor_type field"""
        data = {"temperature": 22.5}  # Missing sensor_type

        response = client.post("/api/webhook", json=data)

        assert response.status_code == 422  # Pydantic validation error
        error_data = response.json()
        assert "detail" in error_data

    def test_webhook_invalid_json(self, client):
        """Test webhook with invalid JSON"""
        response = client.post(
            "/api/webhook",
            data="not json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_webhook_no_valid_sensor_data(self, client, mock_sensor_parser, sample_sensor_data):
        """Test webhook when parser returns no valid data"""
        # Setup mock parser to return empty list
        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = []
        mock_sensor_parser.return_value = mock_parser_instance

        response = client.post("/api/webhook", json=sample_sensor_data)

        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "didn't contain valid sensor data" in data["message"]

    def test_webhook_parser_exception(self, client, mock_sensor_parser, sample_sensor_data):
        """Test webhook when parser raises an exception"""
        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.side_effect = Exception("Parse error")
        mock_sensor_parser.return_value = mock_parser_instance

        response = client.post("/api/webhook", json=sample_sensor_data)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Parse error" in data["message"]

    def test_webhook_database_insertion_error(
        self,
        client,
        mock_insert_rows,
        mock_sensor_parser,
        sample_sensor_data
    ):
        """Test webhook when database insertion fails"""
        # Setup mock parser
        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
        mock_sensor_parser.return_value = mock_parser_instance

        # Make insert fail
        mock_insert_rows.side_effect = Exception("Database error")

        response = client.post("/api/webhook", json=sample_sensor_data)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Database error" in data["message"]

    def test_webhook_logs_data(self, client, mock_sensor_parser, sample_sensor_data):
        """Test that webhook logs data to file"""
        # Setup mock parser
        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
        mock_sensor_parser.return_value = mock_parser_instance

        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            response = client.post("/api/webhook", json=sample_sensor_data)

        assert response.status_code == 201

        # Verify file was opened for appending
        mock_file.assert_called_once_with("webhook_logs.txt", "a")

        # Verify something was written
        handle = mock_file()
        assert handle.write.called

    def test_webhook_with_list_data(self, client, mock_insert_rows, mock_sensor_parser):
        """Test webhook with list data (like your example)"""
        list_data = {
            "humidity": [65, 65, 65, 65, 65, 65, 65, 65],
            "sensor_id": "sensor_001",
            "sensor_type": "temperature",
            "temperature": [22.5, 22.5, 22.5, 22.5, 22.5, 22.5],
            "batch": 12
        }

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [
            {"sensor_id": "sensor_001", "metric_name": "humidity", "metric_value": 65},
            {"sensor_id": "sensor_001", "metric_name": "temperature", "metric_value": 22.5},
        ]
        mock_sensor_parser.return_value = mock_parser_instance

        with patch('builtins.open', mock_open()):
            response = client.post("/api/webhook", json=list_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"


class TestDeleteSensor:
    """Test delete sensor endpoint"""

    def test_delete_sensor_success(self, client, mock_delete_sensor):
        """Test successfully deleting a sensor"""
        mock_delete_sensor.return_value = 1  # 1 row deleted

        response = client.delete("/api/sensors/sensor_001")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sensor_001 deleted" in data["message"]
        mock_delete_sensor.assert_called_once_with("sensor_001")

    def test_delete_sensor_not_found(self, client, mock_delete_sensor):
        """Test deleting a sensor that doesn't exist"""
        mock_delete_sensor.return_value = 0  # No rows deleted

        response = client.delete("/api/sensors/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"]

    def test_delete_sensor_database_error(self, client, mock_delete_sensor):
        """Test deleting sensor when database fails"""
        mock_delete_sensor.side_effect = Exception("Database error")

        response = client.delete("/api/sensors/sensor_001")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Database error" in data["message"]


class TestSyncHistory:
    """Test history synchronization endpoints"""

    def test_sync_history_starts_background_task(self, client, mock_sync_function):
        """Test that sync history starts a background task"""
        response = client.post("/api/history")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "background" in data["message"].lower()

    def test_get_sync_status_success(self, client, mock_sync_status):
        """Test getting sync status when successful"""
        mock_sync_status['state'] = 'success'
        mock_sync_status['error'] = None

        response = client.get("/api/history/status")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "success"
        assert data["error"] is None

    def test_get_sync_status_failed(self, client, mock_sync_status):
        """Test getting sync status when failed"""
        mock_sync_status['state'] = 'failed'
        mock_sync_status['error'] = 'Connection timeout'

        response = client.get("/api/history/status")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "failed"
        assert data["error"] == "Connection timeout"

    def test_get_sync_status_running(self, client, mock_sync_status):
        """Test getting sync status when running"""
        mock_sync_status['state'] = 'running'
        mock_sync_status['error'] = None

        response = client.get("/api/history/status")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "running"


class TestGetSensorMetadata:
    """Test get sensor metadata endpoint"""

    def test_get_metadata_success(self, client, mock_get_metadata):
        """Test successfully retrieving sensor metadata"""
        sample_metadata = [
            {
                "sensor_id": "sensor_001",
                "sensor_type": "temperature",
                "latitude": 60.1699,
                "longitude": 24.9384
            },
            {
                "sensor_id": "sensor_002",
                "sensor_type": "humidity",
                "latitude": 60.2,
                "longitude": 24.9
            }
        ]
        mock_get_metadata.return_value = sample_metadata

        response = client.get("/api/sensors/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Sensor metadata retrieved successfully"
        assert data["data"] == sample_metadata
        mock_get_metadata.assert_called_once()

    def test_get_metadata_empty(self, client, mock_get_metadata):
        """Test retrieving metadata when no sensors exist"""
        mock_get_metadata.return_value = []

        response = client.get("/api/sensors/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"] == []

    def test_get_metadata_database_error(self, client, mock_get_metadata):
        """Test retrieving metadata when database fails"""
        mock_get_metadata.side_effect = Exception("Database connection error")

        response = client.get("/api/sensors/metadata")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Database connection error" in data["message"]


class TestCORSMiddleware:
    """Test CORS configuration"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestLogWebhook:
    """Test log_webhook helper function"""

    def test_log_webhook_writes_to_file(self):
        """Test that log_webhook writes formatted data to file"""
        from src.routers.webhook import log_webhook

        test_data = {"sensor_id": "test", "value": 123}

        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('src.routers.webhook.datetime') as mock_datetime:
                mock_datetime.datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
                log_webhook(test_data, 5)

        # Verify file operations
        mock_file.assert_called_once_with("webhook_logs.txt", "a")

        # Verify content was written
        handle = mock_file()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)

        assert "TIMESTAMP: 2024-01-01 12:00:00" in written_content
        assert "ROWS STORED: 5" in written_content
        assert '"sensor_id": "test"' in written_content
        assert '"value": 123' in written_content

    def test_log_webhook_handles_file_error(self):
        """Test that log_webhook handles file write errors gracefully"""
        from src.routers.webhook import log_webhook

        with patch('builtins.open', side_effect=IOError("Disk full")):
            # Should not raise exception
            log_webhook({"test": "data"}, 1)


class TestEndToEnd:
    """End-to-end integration tests"""

    def test_full_webhook_flow(
        self,
        client,
        mock_insert_rows,
        mock_sensor_parser,
        sample_sensor_data
    ):
        """Test complete webhook flow from request to database"""
        # Setup mocks
        mock_parser_instance = Mock()
        parsed_rows = [
            {"sensor_id": "sensor_001", "temperature": 22.5, "timestamp": "2024-01-01T12:00:00"}
        ]
        mock_parser_instance.process_raw_sensor_data.return_value = parsed_rows
        mock_sensor_parser.return_value = mock_parser_instance

        # Execute request
        with patch('builtins.open', mock_open()):
            response = client.post("/api/webhook", json=sample_sensor_data)

        # Verify complete flow
        assert response.status_code == 201
        mock_sensor_parser.assert_called_once_with("temperature")
        mock_parser_instance.process_raw_sensor_data.assert_called_once()
        mock_insert_rows.assert_called_once()

    def test_sensor_lifecycle(self, client, mock_insert_metadata, mock_get_metadata, mock_delete_sensor, sample_sensor_metadata):
        """Test adding, retrieving, and deleting a sensor"""
        # Add sensor
        mock_insert_metadata.return_value = None
        add_response = client.post("/api/sensors", json=sample_sensor_metadata)
        assert add_response.status_code == 201

        # Get metadata
        mock_get_metadata.return_value = [sample_sensor_metadata]
        get_response = client.get("/api/sensors/metadata")
        assert get_response.status_code == 200
        assert len(get_response.json()["data"]) == 1

        # Delete sensor
        mock_delete_sensor.return_value = 1
        delete_response = client.delete("/api/sensors/sensor_001")
        assert delete_response.status_code == 200


class TestErrorHandling:
    """Test various error scenarios"""

    def test_invalid_endpoint(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_webhook_extra_fields_allowed(self, client, mock_sensor_parser):
        """Test that webhook accepts extra fields due to extra='allow'"""
        data_with_extras = {
            "sensor_type": "temperature",
            "sensor_id": "sensor_001",
            "temperature": 22.5,
            "custom_field_1": "value1",
            "custom_field_2": 999,
            "nested": {"data": "allowed"}
        }

        mock_parser_instance = Mock()
        mock_parser_instance.process_raw_sensor_data.return_value = [{"sensor_id": "test"}]
        mock_sensor_parser.return_value = mock_parser_instance

        with patch('builtins.open', mock_open()):
            response = client.post("/api/webhook", json=data_with_extras)

        assert response.status_code == 201
        # Verify all fields were passed through
        call_args = mock_parser_instance.process_raw_sensor_data.call_args[0][0]
        assert call_args["custom_field_1"] == "value1"
        assert call_args["custom_field_2"] == 999
        assert call_args["nested"] == {"data": "allowed"}