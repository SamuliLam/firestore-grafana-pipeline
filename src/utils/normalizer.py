import datetime
from typing import List
from src.db import SensorData, clean_sensor_id

def normalize_sensor_data(data: dict, sensor_id=None) -> List[SensorData]:
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
                print(f"Skipping item: missing timestamp or sensor_id - {item}")
                continue
            
            # Parse timestamp
            if isinstance(f_timestamp, str):
                try:
                    timestamp = datetime.datetime.fromisoformat(f_timestamp)
                except (ValueError, TypeError):
                    timestamp = datetime.datetime.now()
            else:
                timestamp = datetime.datetime.now()
            
            # Clean sensor ID
            sensor_id = clean_sensor_id(sensor_id)
            
            # Define metrics to extract
            metrics = {
                "temperature": item.get("temperature"),
                "humidity": item.get("humidity"),
                "zone": item.get("zone"),
                "location": item.get("location"),
            }
            
            # Create one SensorData row per metric
            for metric_name, metric_value in metrics.items():
                if metric_value is not None:
                    # Convert numeric values to float, keep strings as is
                    if isinstance(metric_value, (int, float)):
                        metric_value = round(float(metric_value), 2)
                    else:
                        metric_value = str(metric_value)
                    
                    sensor_row = SensorData(
                        timestamp=timestamp,
                        sensor_id=sensor_id,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        source="viherpysäkki"
                    )
                    rows.append(sensor_row)
            
            print(f"Parsed sensor data: {sensor_id} @ {timestamp}")
        
        except Exception as e:
            print(f"Error parsing sensor data item: {str(e)}")
            continue
    
    return rows
