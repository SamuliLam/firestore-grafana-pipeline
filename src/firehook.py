from fastapi import FastAPI, Request
from datetime import datetime
import json
from typing import Optional, List
from sensor_data import (
    SensorData, 
    insert_sensor_rows, 
    clean_sensor_id,
    get_db_engine,
    Base,
    create_hypertable
)

app = FastAPI(title="Sensor Data Webhook Logger")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/webhook")
async def firestore_webhook(request: Request):
    """
    Receive sensor data and store it in TimescaleDB
    """
    try:
        # Get the raw body as JSON
        body = await request.body()
        body_str = body.decode('utf-8')
        
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON"}
        
        # Parse incoming data into SensorData objects
        sensor_rows = parse_sensor_data(data)
        
        if not sensor_rows:
            return {"status": "error", "message": "No valid sensor data found"}
        
        # Insert into database
        insert_sensor_rows(sensor_rows)
        
        # Log to file
        log_webhook(data, len(sensor_rows))
        
        return {
            "status": "success",
            "rows_inserted": len(sensor_rows),
            "message": f"Successfully stored {len(sensor_rows)} sensor readings"
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}


def parse_sensor_data(data: dict) -> List[SensorData]:
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


def log_webhook(data: dict, rows_count: int):
    """Log webhook requests to a file for debugging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"""
{'='*80}
TIMESTAMP: {timestamp}
ROWS STORED: {rows_count}
{'='*80}
DATA:
{json.dumps(data, indent=2)}
{'='*80}

"""
    
    try:
        with open("webhook_logs.txt", "a") as f:
            f.write(log_message)
        print(log_message)
    except Exception as e:
        print(f"Failed to write log: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    subprocess.Popen(['ngrok', 'http', '8000'])
    time.sleep(2)