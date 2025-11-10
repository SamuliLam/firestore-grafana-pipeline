import datetime
from typing import List
from src.db import SensorData, clean_sensor_id

def normalize_sensor_data(data: dict, sensor_id=None) -> List[SensorData]:
from google.api_core.datetime_helpers import DatetimeWithNanoseconds


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
        try:
            # Extract and validate required fields
            f_timestamp = item.get("timestamp")

            if not sensor_id:
                sensor_id = item.get("sensor_id")

            if not f_timestamp or not sensor_id:
                print(f"Skipping item: missing timestamp or sensor id - {item}")
                continue
            
            # Parse timestamp
            if isinstance(f_timestamp, DatetimeWithNanoseconds):
                timestamp = f_timestamp.replace(tzinfo=None)
            else:
                timestamp = datetime.datetime.now(datetime.UTC)

            # Clean sensor ID
            sensor_id = clean_sensor_id(sensor_id)

            # Create SensorData object
            sensor_row = SensorData(
                timestamp=timestamp,
                sensor_id=sensor_id,
                zone=item.get("zone", ""),
                location=item.get("location", ""),
                temperature=round(float(item.get("temperature")), 2) if item.get("temperature") else None,
                humidity=round(float(item.get("humidity")), 2) if item.get("humidity") else None
            )

            rows.append(sensor_row)
            print(f"Parsed sensor data: {sensor_id} @ {timestamp}")
        
        except Exception as e:
            print(f"Error parsing sensor data item: {str(e)}")
            continue
    
    return rows
