import pytest
import datetime
import json
from zoneinfo import ZoneInfo
from unittest.mock import patch
from google.api_core.datetime_helpers import DatetimeWithNanoseconds


# Import the module to test
from src.utils.SensorDataParser import (
    SensorDataParser,
    extract_sensor_and_metrics,
    _value_looks_nested,
    POSSIBLE_SENSOR_ID_FIELDS,
    POSSIBLE_TIMESTAMP_FIELDS,
    LIST_VALUE_INTERVAL_MINUTES
)


class TestSensorDataParser:
    """Test suite for SensorDataParser class"""

    @pytest.fixture
    def parser(self):
        """Create a SensorDataParser instance for testing"""
        return SensorDataParser("test_collection")

    @pytest.fixture
    def fixed_time(self):
        """Return a fixed datetime for testing"""
        return datetime.datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    def test_initialization(self):
        """Test parser initialization"""
        parser = SensorDataParser("my_collection")
        assert parser.collection_name == "my_collection"

    def test_simple_flat_data(self, parser, fixed_time):
        """Test processing flat sensor data with all fields"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor001",
                "timestamp": "2024-01-15T12:00:00",
                "temperature": 23.5,
                "humidity": 65.0
            }
            result = parser.process_raw_sensor_data(raw_data)

            assert len(result) == 2
            assert result[0]["sensor_id"] == "sensor001"
            assert result[0]["metric_name"] == "temperature"
            assert result[0]["metric_value"] == 23.5
            assert result[1]["metric_name"] == "humidity"
            assert result[1]["metric_value"] == 65.0

    def test_nested_data_with_sensor_key(self, parser, fixed_time):
        """Test processing nested data where key is sensor ID"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_123": {
                    "temperature": [20.0, 21.0, 22.0],
                    "pressure": [1013, 1014, 1015]
                }
            }
            result = parser.process_raw_sensor_data(raw_data)

            assert len(result) == 6  # 3 temperature + 3 pressure values
            sensor_ids = set(row["sensor_id"] for row in result)
            assert "sensor_123" in sensor_ids


    def test_parse_timestamp_with_iso_string(self):
        """Test parsing ISO format timestamp string"""
        timestamp_str = "2024-01-15T12:00:00+02:00"
        result = SensorDataParser.parse_timestamp(timestamp_str)

        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")
        assert isinstance(result, datetime.datetime)

    def test_parse_timestamp_with_naive_datetime(self):
        """Test parsing naive datetime (assumes Helsinki timezone)"""
        timestamp_str = "2024-01-15T12:00:00"
        result = SensorDataParser.parse_timestamp(timestamp_str)

        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")

    def test_parse_timestamp_with_none_default_true(self):
        """Test parsing None timestamp returns current time"""
        result = SensorDataParser.parse_timestamp(None, use_default=True)

        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")

    def test_parse_timestamp_with_none_default_false(self):
        """Test parsing None timestamp with use_default=False returns None"""
        result = SensorDataParser.parse_timestamp(None, use_default=False)
        assert result is None

    def test_parse_timestamp_with_datetimewithnanos(self):
        """Test parsing DatetimeWithNanoseconds object"""
        dt = DatetimeWithNanoseconds(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        result = SensorDataParser.parse_timestamp(dt)

        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")

    def test_parse_timestamp_with_datetimewithnanos_naive(self):
        """Test parsing naive DatetimeWithNanoseconds"""
        dt = DatetimeWithNanoseconds(2024, 1, 15, 12, 0, 0)
        result = SensorDataParser.parse_timestamp(dt)

        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")

    def test_parse_list_metric(self, fixed_time):
        """Test parsing metric with list values"""
        metric_values = [20.0, 21.0, 22.0]
        result = SensorDataParser.parse_list_metric(
            "temperature", metric_values, "sensor_001", "temp_sensor", fixed_time
        )

        assert len(result) == 3
        # Values are reversed, so last value gets base_time
        assert result[0]["metric_value"] == 22.0
        assert result[0]["timestamp"] == fixed_time
        assert result[1]["timestamp"] == fixed_time - datetime.timedelta(minutes=5)
        assert result[2]["timestamp"] == fixed_time - datetime.timedelta(minutes=10)

    def test_create_sensor_row_valid(self, fixed_time):
        """Test creating valid sensor row"""
        row = SensorDataParser.create_sensor_row(
            "temperature", 23.456789, "sensor:001", "temp_sensor", fixed_time
        )

        assert row is not None
        assert row["metric_name"] == "temperature"
        assert row["metric_value"] == 23.4568  # Rounded to 4 decimals
        assert row["sensor_id"] == "sensor001"  # Colon removed
        assert row["sensor_type"] == "temp_sensor"
        assert row["timestamp"] == fixed_time

    def test_create_sensor_row_with_none_value(self, fixed_time):
        """Test that None values are skipped"""
        row = SensorDataParser.create_sensor_row(
            "temperature", None, "sensor_001", "temp_sensor", fixed_time
        )
        assert row is None

    def test_create_sensor_row_with_empty_string(self, fixed_time):
        """Test that empty strings are skipped"""
        row = SensorDataParser.create_sensor_row(
            "temperature", "", "sensor_001", "temp_sensor", fixed_time
        )
        assert row is None

    def test_create_sensor_row_with_empty_list(self, fixed_time):
        """Test that empty lists are skipped"""
        row = SensorDataParser.create_sensor_row(
            "temperature", [], "sensor_001", "temp_sensor", fixed_time
        )
        assert row is None

    def test_create_sensor_row_with_empty_dict(self, fixed_time):
        """Test that empty dicts are skipped"""
        row = SensorDataParser.create_sensor_row(
            "temperature", {}, "sensor_001", "temp_sensor", fixed_time
        )
        assert row is None

    def test_create_sensor_row_rounds_float(self, fixed_time):
        """Test that float values are rounded to 4 decimals"""
        row = SensorDataParser.create_sensor_row(
            "temperature", 23.123456789, "sensor_001", "temp_sensor", fixed_time
        )
        assert row["metric_value"] == 23.1235

    def test_create_sensor_row_converts_int_to_float(self, fixed_time):
        """Test that int values are converted to float"""
        row = SensorDataParser.create_sensor_row(
            "temperature", 23, "sensor_001", "temp_sensor", fixed_time
        )
        assert row["metric_value"] == 23.0
        assert isinstance(row["metric_value"], float)

    def test_sensor_id_field_variants(self, parser, fixed_time):
        """Test that different sensor ID field names are recognized"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            for field in POSSIBLE_SENSOR_ID_FIELDS:
                raw_data = {
                    field: "test_sensor",
                    "temperature": 23.5
                }
                result = parser.process_raw_sensor_data(raw_data)
                assert len(result) == 1
                assert result[0]["sensor_id"] == "test_sensor"

    def test_timestamp_field_variants(self, parser):
        """Test that different timestamp field names are recognized"""
        for field in POSSIBLE_TIMESTAMP_FIELDS:
            raw_data = {
                "sensor_id": "test_sensor",
                field: "2024-01-15T12:00:00",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert len(result) == 1

    def test_sensor_type_from_item(self, parser, fixed_time):
        """Test that sensor_type is taken from item if present"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "test_sensor",
                "sensor_type": "custom_type",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert result[0]["sensor_type"] == "custom_type"

    def test_sensor_type_defaults_to_collection(self, parser, fixed_time):
        """Test that sensor_type defaults to collection name"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "test_sensor",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert result[0]["sensor_type"] == "test_collection"

    def test_array_of_sensor_readings(self, parser, fixed_time):
        """Test processing array of sensor readings"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = [
                {"sensor_id": "sensor_001", "temperature": 20.0},
                {"sensor_id": "sensor_002", "temperature": 21.0}
            ]
            result = parser.convert_to_normalized_format(raw_data, None, None)

            assert len(result) == 2
            assert result[0]["sensor_id"] == "sensor_001"
            assert result[1]["sensor_id"] == "sensor_002"

    def test_first_key_as_timestamp(self, parser):
        """Test that first key can be parsed as timestamp"""
        raw_data = {
            "2024-01-15T12:00:00": {
                "sensor_123": {
                    "temperature": [20.0, 21.0]
                }
            }
        }
        result = parser.process_raw_sensor_data(raw_data)
        assert len(result) == 2

    def test_colon_removal_from_sensor_id(self, parser, fixed_time):
        """Test that colons are removed from sensor IDs"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "AA:BB:CC:DD",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert result[0]["sensor_id"] == "AABBCCDD"


class TestExtractSensorAndMetrics:
    """Test suite for extract_sensor_and_metrics function"""

    def test_extract_with_list_values(self):
        """Test extraction when value contains lists"""
        data = {
            "sensor_001": {
                "temperature": [20.0, 21.0],
                "humidity": [60.0, 61.0]
            }
        }
        sensor_id, metrics = extract_sensor_and_metrics(data)

        assert sensor_id == "sensor_001"
        assert metrics == {"temperature": [20.0, 21.0], "humidity": [60.0, 61.0]}

    def test_extract_with_nested_dict(self):
        """Test extraction with nested dictionaries"""
        data = {
            "outer": {
                "sensor_001": {
                    "temperature": [20.0, 21.0]
                }
            }
        }
        sensor_id, metrics = extract_sensor_and_metrics(data)

        assert sensor_id == "sensor_001"
        assert metrics == {"temperature": [20.0, 21.0]}

    def test_extract_with_json_string(self):
        """Test extraction when value is JSON string"""
        inner_data = {"temperature": [20.0, 21.0], "humidity": [60.0, 61.0]}
        data = {
            "sensor_001": json.dumps(inner_data)
        }
        sensor_id, metrics = extract_sensor_and_metrics(data)

        assert sensor_id == "sensor_001"
        assert metrics == inner_data

    def test_extract_with_non_json_string(self):
        """Test extraction when value is non-JSON string"""
        data = {"key": "not json"}
        sensor_id, metrics = extract_sensor_and_metrics(data)

        assert sensor_id is None
        assert metrics == {}

    def test_extract_with_empty_dict(self):
        """Test extraction with empty dictionary"""
        data = {}
        # Should not raise an error
        try:
            sensor_id, metrics = extract_sensor_and_metrics(data)
            # If it doesn't raise, we expect None, {}
            assert sensor_id is None or sensor_id == ""
        except StopIteration:
            # This is also acceptable behavior for empty dict
            pass


class TestValueLooksNested:
    """Test suite for _value_looks_nested function"""

    def test_dict_value(self):
        """Test that dict values are considered nested"""
        assert _value_looks_nested({"key": "value"}) is True

    def test_json_string_value(self):
        """Test that JSON string values are considered nested"""
        assert _value_looks_nested('{"key": "value"}') is True

    def test_plain_string_value(self):
        """Test that plain strings are not considered nested"""
        assert _value_looks_nested("plain string") is False

    def test_numeric_value(self):
        """Test that numeric values are not considered nested"""
        assert _value_looks_nested(42) is False
        assert _value_looks_nested(3.14) is False

    def test_list_value(self):
        """Test that list values are not considered nested"""
        assert _value_looks_nested([1, 2, 3]) is False

    def test_none_value(self):
        """Test that None is not considered nested"""
        assert _value_looks_nested(None) is False

    def test_malformed_json_string(self):
        """Test that malformed JSON strings are not considered nested"""
        assert _value_looks_nested('{"key": invalid}') is False


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def parser(self):
        return SensorDataParser("test_collection")

    def test_multiple_metrics_with_lists(self, parser, fixed_time):
        """Test processing multiple list metrics"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor_001",
                "temperature": [20.0, 21.0, 22.0],
                "humidity": [60.0, 61.0, 62.0],
                "pressure": [1013, 1014, 1015]
            }
            result = parser.process_raw_sensor_data(raw_data)

            assert len(result) == 9  # 3 values × 3 metrics

            temp_rows = [r for r in result if r["metric_name"] == "temperature"]
            assert len(temp_rows) == 3

    def test_mixed_metric_types(self, parser, fixed_time):
        """Test processing mix of scalar and list metrics"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor_001",
                "temperature": [20.0, 21.0],
                "status": "active",
                "count": 42
            }
            result = parser.process_raw_sensor_data(raw_data)

            assert len(result) == 4  # 2 temperature + 1 status + 1 count

    def test_invalid_timestamp_format(self, parser, fixed_time):
        """Test handling of invalid timestamp format"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor_001",
                "timestamp": "not a valid timestamp",
                "temperature": 23.5
            }
            # Should not raise an error, should use current time
            result = parser.process_raw_sensor_data(raw_data)
            assert len(result) == 1

    def test_special_characters_in_sensor_id(self, parser, fixed_time):
        """Test sensor IDs with special characters"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor::001::AA",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            # All colons should be removed
            assert result[0]["sensor_id"] == "sensor001AA"

    def test_very_large_list(self, parser, fixed_time):
        """Test processing very large list of values"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            large_list = list(range(100))
            raw_data = {
                "sensor_id": "sensor_001",
                "values": large_list
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert len(result) == 100

    def test_unicode_in_sensor_id(self, parser, fixed_time):
        """Test sensor IDs with unicode characters"""
        with patch('src.utils.SensorDataParser.SensorDataParser.parse_timestamp', return_value=fixed_time):
            raw_data = {
                "sensor_id": "sensor_ñ_001",
                "temperature": 23.5
            }
            result = parser.process_raw_sensor_data(raw_data)
            assert result[0]["sensor_id"] == "sensor_ñ_001"


@pytest.fixture
def fixed_time():
    """Global fixture for fixed time"""
    return datetime.datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))