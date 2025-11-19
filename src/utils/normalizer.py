import datetime
from typing import List
from src.db import SensorData
from google.api_core.datetime_helpers import DatetimeWithNanoseconds

SENSOR_READINGS_INFO_FIELDS = ("sensor_id", "timestamp", "sensor_type",
                               "location", "zone", "battery_voltage", "Battery")

LIST_VALUE_INTERVAL_MINUTES = 5


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
        rows.extend(parse_sensor_item(item, metrics, sensor_id))

    return rows


def parse_sensor_item(item: dict, metrics: dict, sensor_id: str) -> List[SensorData]:
    sensor_type = item.get("sensor_type")
    s_id = sensor_id or item.get("sensor_id")

    base_time = parse_timestamp(item.get("timestamp"))

    rows = []
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, list):
            rows.extend(
                parse_list_metric(metric_name, metric_value, s_id, sensor_type, base_time)
            )
        else:
            row = create_sensor_row(metric_name, metric_value, s_id, sensor_type, base_time)
            if row:
                rows.append(row)

    if rows:
        print(f"Parsed {len(rows)} metrics for sensor {s_id} starting {base_time}")
    return rows


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


def parse_list_metric(
        metric_name: str,
        metric_values: list,
        sensor_id: str,
        sensor_type: str,
        base_time: datetime.datetime
) -> List[SensorData]:
    rows = []
    for i, val in enumerate(metric_values):
        ts = base_time - datetime.timedelta(minutes=LIST_VALUE_INTERVAL_MINUTES * i)
        row = create_sensor_row(metric_name, val, sensor_id, sensor_type, ts)
        if row:
            rows.append(row)
    return rows


def create_sensor_row(
        metric_name: str,
        metric_value,
        sensor_id: str,
        sensor_type: str,
        timestamp: datetime.datetime
) -> SensorData | None:
    try:
        value = round(float(metric_value), 2)
    except (TypeError, ValueError):
        print(f"Invalid metric value for {metric_name}: {metric_value}")
        return None

    return SensorData(
        timestamp=timestamp,
        sensor_id=sensor_id,
        metric_name=metric_name,
        metric_value=value,
        source=sensor_type
    )
