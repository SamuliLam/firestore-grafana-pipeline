import datetime
from typing import List
from src.db import SensorData
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

SENSOR_READINGS_INFO_FIELDS = ("sensor_id", "timestamp", "sensor_type",
                               "location", "zone", "battery_voltage", "Battery")


def normalize_sensor_data(data: dict, sensor_id) -> List[SensorData]:
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
    data_list = data if isinstance(data, list) else [data]

    for item in data_list:
        metrics = {k: v for k, v in item.items() if k not in SENSOR_READINGS_INFO_FIELDS}

        # Extract and validate required fields
        f_timestamp = item.get("timestamp")
        sensor_type = item.get("sensor_type")
        s_id = sensor_id or item.get("sensor_id")

        # if not f_timestamp or not s_id:
        #     print(f"Skipping item: missing timestamp or sensor id - {item}")
        #     continue

        # Parse timestamp
        if not f_timestamp:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        elif isinstance(f_timestamp, DatetimeWithNanoseconds):
            timestamp = f_timestamp.replace(tzinfo=None)
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc)

        try:
            for metric_name, metric_value in metrics.items():

                try:
                    value = round(float(metric_value), 2)
                except (TypeError, ValueError):
                    print(f"Invalid metric value for {metric_name}: {metric_value}")
                    continue

                sensor_row = SensorData(
                    timestamp=timestamp,
                    sensor_id=s_id,
                    metric_name=metric_name,
                    metric_value=value,
                    source=sensor_type
                )
                rows.append(sensor_row)
                print(f"Parsed sensor data: {s_id} @ {timestamp}")
        except Exception as e:
            print(f"Error parsing sensor data item: {str(e)}")
            continue

    return rows
