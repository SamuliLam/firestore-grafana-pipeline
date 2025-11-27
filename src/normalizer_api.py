from fastapi import FastAPI, Request, status
import json
from src.db import insert_sensor_rows, init_db, SensorData, insert_sensor_metadata, delete_sensor
from src.utils.SensorDataParser import SensorDataParser
from src.utils.api_response import make_response
from contextlib import asynccontextmanager
import datetime
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    yield
    print("Application shutting down")


app = FastAPI(title="Normalizer-API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/sensors")
async def add_sensor(request: Request):
    try:
        data = await request.json()
        insert_sensor_metadata([data])
    except Exception as e:
        print("Error:", e)
        return make_response(
            status="error",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return make_response(
        status="success",
        message="Sensor added successfully",
        data=data,
        status_code=status.HTTP_201_CREATED
    )



@app.post("/webhook")
async def firestore_webhook(request: Request):

    try:
        data = await request.json()
    except json.JSONDecodeError as e:
        return make_response(
            status="error",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        parser = SensorDataParser(data.get("sensor_type"))
        sensor_reading_rows = parser.parse_sensor_data(data)

        if not sensor_reading_rows:
            return make_response(
                status="error",
                message="Message didn't contain valid sensor data",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Insert into database
        insert_sensor_rows(SensorData, sensor_reading_rows)

        log_webhook(data, len(sensor_reading_rows))

    except Exception as e:
        print(f"Webhook error: {e}")
        return make_response(
            status="error",
            message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return make_response(
        status="success",
        message="New data successfully inserted to the database",
        data=data,
        status_code=201
    )

@app.delete("/api/sensors/{sensor_id}")
async def api_delete_sensor(sensor_id: str):
    try:
        deleted = delete_sensor(sensor_id)

        if deleted == 0:
            return make_response(
                status="error",
                message=f"Sensor {sensor_id} not found",
                status_code=404
            )

        return make_response(
            status="success",
            message=f"Sensor {sensor_id} deleted",
            status_code=200
        )

    except Exception as e:
        return make_response(
            status="error",
            message=str(e),
            status_code=500
        )



def log_webhook(data: dict, rows_count: int):
    """Log webhook requests to a file for debugging."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"""
{'=' * 80}
TIMESTAMP: {timestamp}
ROWS STORED: {rows_count}
{'=' * 80}
DATA:
{json.dumps(data, indent=2)}
{'=' * 80}
"""
    try:
        with open("webhook_logs.txt", "a") as f:
            f.write(log_message)
        print(log_message)
    except Exception as e:
        print(f"Failed to write log: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import subprocess
    import time

    print("Starting FastAPI server...")
    server_process = subprocess.Popen([
        'uvicorn', 'normalizer_api:app', '--host', '0.0.0.0', '--port', '8000', '--reload'
    ])
    time.sleep(2)
    if server_process.poll() is not None:
        print("ERROR: FastAPI server failed to start!")
        exit(1)
    print("FastAPI server started!")
    try:
        # Keep the server running
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_process.terminate()
        server_process.wait()
        print("Shutdown complete")
