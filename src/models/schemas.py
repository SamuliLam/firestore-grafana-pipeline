from pydantic import BaseModel, Field
from typing import Any, Optional


class ApiResponse(BaseModel):
    """Standard API response format"""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {}
            }
        }


class SensorMetadataInput(BaseModel):
    """Input model for creating/updating sensor metadata"""
    sensor_id: str = Field(..., description="Unique identifier for the sensor")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    sensor_type: str = Field(..., description="Type of sensor")

    class Config:
        json_schema_extra = {
            "example": {
                "sensor_id": "sensor_001",
                "latitude": 60.1699,
                "longitude": 24.9384,
                "sensor_type": "viherpysakki"
            }
        }


class WebhookData(BaseModel):
    """Flexible model for incoming webhook sensor data"""
    sensor_type: str = Field(..., description="Type of sensor")

    class Config:
        extra = "allow"  # Allow additional fields for flexible sensor data
        json_schema_extra = {
            "example": {
                "sensor_type": "viherpysakki",
                "sensor_id": "sensor_001",
                "timestamp": "2025-12-12T10:30:00",
                "temperature": 22.5,
                "humidity": 65.0
            }
        }