import datetime
import logging
from typing import List
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

SENSOR_READINGS_INFO_FIELDS = ("sensor_id", "timestamp", "sensor_type",
                               "location", "zone", "battery_voltage", "Battery")

LIST_VALUE_INTERVAL_MINUTES = 5


class SensorParser:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    def parse_firestore_document(self, raw_data: dict):

        first_value = next(iter(raw_data.values()))
        is_nested_dict = isinstance(first_value, dict)

        if is_nested_dict:
            sensor_id = next(iter(raw_data))
            data = first_value
        else:
            sensor_id = None
            data = raw_data

        return self.normalize_sensor_data(data, sensor_id)

    def normalize_sensor_data(self, data: dict, sensor_id: str) -> List[dict]:
        """
        Parse incoming JSON data into SensorData objects in EAV format.

        Expected JSON format (single reading):
        {
            "timestamp": "2024-01-15T10:30:00",
            "sensor_id": "sensor_001",
            "zone": "Zone 2",
            "location": "Room A",
            "temperature": 24.34,
            "humidity": 67.5
        }
        """
        rows = []

        # Handle both single object and array of objects
        sensor_data_as_list = data if isinstance(data, list) else [data]

        for sensor_reading in sensor_data_as_list:
            metrics = {k: v for k, v in sensor_reading.items() if k not in SENSOR_READINGS_INFO_FIELDS}
            rows.extend(self.parse_sensor_item(sensor_reading, metrics, sensor_id))

        return rows

    def parse_sensor_item(self, item: dict, metrics: dict, sensor_id: str) -> List[dict]:
        sensor_type = item.get("sensor_type", self.collection_name)
        s_id = sensor_id or item.get("sensor_id")

        base_time = SensorParser.parse_timestamp(item.get("timestamp"))

        rows = []
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, list):
                rows.extend(
                    self.parse_list_metric(metric_name, metric_value, s_id, sensor_type, base_time)
                )
            else:
                row = self.create_sensor_row(metric_name, metric_value, s_id, sensor_type, base_time)
                if row:
                    rows.append(row)

        if rows:
            print(f"Parsed {len(rows)} metrics for sensor {s_id} starting {base_time}")
        return rows

    @staticmethod
    def parse_timestamp(f_timestamp) -> datetime.datetime:
        if not f_timestamp:
            return datetime.datetime.now(datetime.timezone.utc)

        if isinstance(f_timestamp, DatetimeWithNanoseconds):
            return f_timestamp.replace(tzinfo=None)

        if isinstance(f_timestamp, str):
            try:
                return datetime.datetime.fromisoformat(f_timestamp)
            except ValueError:
                pass

        return datetime.datetime.now(datetime.timezone.utc)

    @staticmethod
    def parse_list_metric(
            metric_name: str,
            metric_values: list,
            sensor_id: str,
            sensor_type: str,
            base_time: datetime.datetime
    ) -> List[dict]:
        rows = []
        for i, val in enumerate(metric_values):
            ts = base_time + datetime.timedelta(minutes=LIST_VALUE_INTERVAL_MINUTES * i)
            row = SensorParser.create_sensor_row(metric_name, val, sensor_id, sensor_type, ts)
            if row:
                rows.append(row)
        return rows

    @staticmethod
    def create_sensor_row(
            metric_name: str,
            metric_value,
            sensor_id: str,
            sensor_type: str,
            timestamp: datetime.datetime
    ) -> dict | None:
        try:
            value = round(float(metric_value), 2)
        except (TypeError, ValueError):
            logging.warning("Invalid metric value", extra={"metric": metric_name, "value": metric_value})
            return None

        return {
            "timestamp": timestamp,
            "sensor_id": sensor_id,
            "metric_name": metric_name,
            "metric_value": value,
            "source": sensor_type,
        }
