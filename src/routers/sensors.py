from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_auth_claims, require_admin
from src.models.schemas import SensorMetadataInput
from src.db import insert_sensor_metadata, delete_sensor, get_all_sensor_metadata

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_sensor(
    sensor_data: SensorMetadataInput,
    _=Depends(require_admin),
):
    data = sensor_data.model_dump()

    try:
        insert_sensor_metadata([data])
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to insert sensor metadata",
        )

    return {
        "status": "success",
        "message": "Sensor added successfully",
        "data": data,
    }


@router.delete("/{sensor_id}")
async def delete_sensor_endpoint(
    sensor_id: str,
    _=Depends(require_admin),
):
    try:
        deleted = delete_sensor(sensor_id)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete sensor",
        )

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Sensor {sensor_id} not found",
        )

    return {
        "status": "success",
        "message": f"Sensor {sensor_id} deleted",
    }


@router.get("/metadata")
async def get_sensor_metadata_endpoint(
    _=Depends(get_auth_claims),
):
    try:
        metadata = get_all_sensor_metadata()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve sensor metadata",
        )

    return {
        "status": "success",
        "message": "Sensor metadata retrieved successfully",
        "data": metadata,
    }