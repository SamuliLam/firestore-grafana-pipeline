from fastapi import APIRouter, status, Depends, HTTPException
import json
import datetime

from src.dependencies import get_auth_claims
from src.models.schemas import WebhookData
from src.db import insert_sensor_rows
from src.SensorDataParser import SensorDataParser

router = APIRouter(tags=["webhook"])


@router.post("/api/webhook", status_code=status.HTTP_201_CREATED)
async def firestore_webhook(
    webhook_data: WebhookData,
    _=Depends(get_auth_claims),
):
    data = webhook_data.model_dump()

    parser = SensorDataParser(data.get("sensor_type"))
    sensor_rows = parser.process_raw_sensor_data(data)

    if not sensor_rows:
        raise HTTPException(
            status_code=400,
            detail="Message didn't contain valid sensor data",
        )

    try:
        insert_sensor_rows(sensor_rows)
        log_webhook(data, len(sensor_rows))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to insert sensor data",
        )

    return {
        "status": "success",
        "message": "New data successfully inserted to the database",
        "data": data,
    }


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
