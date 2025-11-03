import datetime
from src.db import SensorData, clean_sensor_id
from typing import List


def normalize_sensor_data(data: dict) -> List[SensorData]:
    """
    Parse incoming JSON data into SensorData objects.

    Expected JSON format (single reading):
    {
        "timestamp": "2024-01-15T10:30:00",
        "sensor_id": "sensor_001",
        "zone": "Zone 2",
        "location": "Room A",
        "temperature": 24.34,
        "humidity": 67.5
    }

    Or array format:
    [
        { ... },
        { ... }
    ]
    """
    rows = []

    # Handle both single object and array of objects
    data_list = data if isinstance(data, list) else [data]

    for item in data_list:
        try:
            # Extract and validate required fields
            timestamp_str = item.get("timestamp")
            sensor_id = item.get("sensor_id")

            if not timestamp_str or not sensor_id:
                print(f"Skipping item: missing timestamp or sensor_id - {item}")
                continue

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                # Try alternative format
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            # Clean sensor ID
            sensor_id = clean_sensor_id(sensor_id)

            # Create SensorData object
            sensor_row = SensorData(
                timestamp=timestamp,
                sensor_id=sensor_id,
                zone=item.get("zone", ""),
                location=item.get("location", ""),
                temperature=float(item.get("temperature")) if item.get("temperature") else None,
                humidity=float(item.get("humidity")) if item.get("humidity") else None
            )

            rows.append(sensor_row)
            print(f"Parsed sensor data: {sensor_id} @ {timestamp}")

        except Exception as e:
            print(f"Error parsing sensor data item: {str(e)}")
            continue

    return rows
