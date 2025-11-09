import datetime
from src.db import SensorData, clean_sensor_id
from typing import List

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
            if isinstance(f_timestamp, DatetimeWithNanoseconds):
                timestamp = f_timestamp.replace(tzinfo=None)
            else:
                timestamp = datetime.datetime.now(datetime.UTC)
            
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
                    # Convert numeric values
                    if isinstance(metric_value, (int, float)):
                        metric_value = round(float(metric_value), 2)
                    
                    sensor_row = SensorData(
                        timestamp=timestamp,
                        sensor_id=sensor_id,
                        metric_name=metric_name,
                        metric_value=metric_value if isinstance(metric_value, (int, float)) else float('nan'),
                        source="viherpysäkki"  # or extract from item if available
                    )
                    rows.append(sensor_row)
            
            print(f"Parsed sensor data: {sensor_id} @ {timestamp}")
        
        except Exception as e:
            print(f"Error parsing sensor data item: {str(e)}")
            continue
    
    return rows
