from fastapi import FastAPI, Request
import json
from src.db import insert_sensor_rows, init_db
from src.utils import normalize_sensor_data
from contextlib import asynccontextmanager
import datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    yield
    print("Application shutting down")


app = FastAPI(title="Normalizer-API", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/webhook")
async def firestore_webhook(request: Request):
    try:
        body = await request.body()
        body_str = body.decode('utf-8')

        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

        print("Received webhook")
        print(json.dumps(data, indent=2))

        sensor_rows = normalize_sensor_data(data)

        if not sensor_rows:
            return {"status": "error", "message": "No valid sensor data found"}

        # Insert into database
        insert_sensor_rows(sensor_rows)

        log_webhook(data, len(sensor_rows))

        return {
            "status": "success",
            "rows_inserted": len(sensor_rows),
            "message": f"Successfully stored {len(sensor_rows)} sensor readings"
        }

    except Exception as e:
        print(f"Webhook erre: {e}")
        return {"error": str(e)}


def log_webhook(data: dict, rows_count: int):
    """Log webhook requests to a file for debugging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
