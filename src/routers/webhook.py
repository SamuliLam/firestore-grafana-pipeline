from fastapi import APIRouter, status, Depends
from src.auth import auth0
import json
import datetime
from src.models.schemas import WebhookData, ApiResponse
from src.db import insert_sensor_rows, SensorData
from src.SensorDataParser import SensorDataParser
from src.utils.api_response import make_response

router = APIRouter(tags=["webhook"])


@router.post("/api/webhook", dependencies=[Depends(auth0.require_auth())],
             responses={
                 201: {
                     "description": "Data successfully inserted",
                     "model": ApiResponse
                 },
                 400: {
                     "description": "Bad request - invalid or missing sensor data",
                     "model": ApiResponse
                 },
                 422: {
                     "description": "Validation error"
                 },
                 500: {
                     "description": "Internal server error",
                     "model": ApiResponse
                 }
             },
             status_code=status.HTTP_201_CREATED
             )
async def firestore_webhook(webhook_data: WebhookData):
    """Receive and process sensor data from external sources"""
    try:
        data = webhook_data.model_dump()

        parser = SensorDataParser(data.get("sensor_type"))
        sensor_reading_rows = parser.process_raw_sensor_data(data)

        if not sensor_reading_rows:
            return make_response(
                status="error",
                message="Message didn't contain valid sensor data",
                status_code=status.HTTP_400_BAD_REQUEST
            )

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
