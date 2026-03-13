from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict


class SensorMetadataInput(BaseModel):
    """Input model for creating/updating sensor metadata and configuration"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensor_id": "C6:31:F5:...",
                "description": "Outdoor temperature sensor",
                "latitude": 60.1699,
                "longitude": 24.9384,
                "project_id": "myyrmaki-test",
                "ts_field": "ts",
                "mapping": {
                    "t": "temperature",
                    "h": "humidity",
                    "p": "pressure"
                }
            }
        }
    )

    sensor_id: str = Field(..., description="Unique identifier (MAC) for the sensor")
    description: Optional[str] = Field(None, description="Description of the sensor")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    project_id: str = Field(..., description="What project the sensor belongs to")

    ts_field: str = Field(default="ts", description="The key name for the timestamp in raw data")
    mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping raw data keys to clean measurement names"
    )


class WebhookData(BaseModel):
    """Flexible model for incoming webhook sensor data"""
    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for flexible sensor data
        json_schema_extra={
            "example": {
                "project_id": "myyrmäki_katupuu",
                "sensor_id": "sensor_001",
                "timestamp": "2025-12-12T10:30:00",
                "temperature": 22.5,
                "humidity": 65.0
            }
        }
    )

    project_id: str = Field(..., description="What project the sensor belongs to")
