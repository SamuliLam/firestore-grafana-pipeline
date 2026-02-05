from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class SensorMetadataInput(BaseModel):
    """Input model for creating/updating sensor metadata"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensor_id": "sensor_001",
                "description": "Outdoor temperature sensor",
                "latitude": 60.1699,
                "longitude": 24.9384,
                "sensor_type": "viherpysakki"
            }
        }
    )

    sensor_id: str = Field(..., description="Unique identifier for the sensor")
    description: Optional[str] = Field(None, description="Description of the sensor")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    sensor_type: str = Field(..., description="Type of sensor")


class WebhookData(BaseModel):
    """Flexible model for incoming webhook sensor data"""
    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for flexible sensor data
        json_schema_extra={
            "example": {
                "sensor_type": "viherpysakki",
                "sensor_id": "sensor_001",
                "timestamp": "2025-12-12T10:30:00",
                "temperature": 22.5,
                "humidity": 65.0
            }
        }
    )

    sensor_type: str = Field(..., description="Type of sensor")
