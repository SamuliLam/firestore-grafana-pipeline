from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_auth_claims, require_admin
from src.models.schemas import SensorMetadataInput
from src.db import insert_sensor_metadata, delete_sensor_metadata, get_all_sensor_metadata
from src.sensor_config import update_sensor_config as update_sensor_config_fs, \
    get_unconfigured_sensor_ids_from_firestore, trigger_backfill, get_sensor_config, delete_sensor_config

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_or_update_sensor(
        sensor_data: dict,
        _=Depends(require_admin),
):
    sensor_id = sensor_data.get("sensor_id")
    if not sensor_id:
        raise HTTPException(status_code=400, detail="sensor_id is required")

    try:
        sql_data = {
            "sensor_id": sensor_id,
            "project_id": sensor_data.get("project_id"),
            "description": sensor_data.get("description"),
            "latitude": sensor_data.get("latitude"),
            "longitude": sensor_data.get("longitude"),
        }
        insert_sensor_metadata([sql_data])

        fs_config = {
            "project_id": sensor_data.get("project_id"),
            "mapping": sensor_data.get("mapping", {}),
            "ts_field": sensor_data.get("ts_field", "ts")
        }
        update_sensor_config_fs(sensor_id, fs_config)

        moved_count = trigger_backfill(sensor_id, fs_config)

        return {
            "status": "success",
            "message": f"Sensor saved and {moved_count} historical readings processed.",
            "data": sql_data,
        }
    except Exception as e:
        print(f"Error processing sensor {sensor_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during sensor processing")


@router.delete("/{sensor_id}")
async def delete_sensor_endpoint(
        sensor_id: str,
        _=Depends(require_admin),
):
    try:
        sql_deleted = delete_sensor_metadata(sensor_id)

        fs_deleted = delete_sensor_config(sensor_id)

        if sql_deleted == 0 and not fs_deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Sensor {sensor_id} not found in metadata or config",
            )

    except Exception as e:
        print(f"Error during deletion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete sensor: {str(e)}",
        )

    return {
        "status": "success",
        "message": f"Sensor {sensor_id} deleted successfully",
        "details": {
            "sql": "deleted" if sql_deleted > 0 else "not_found",
            "firestore": "deleted" if fs_deleted else "not_found"
        }
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


@router.get("/unknown")
async def get_unknown_sensors(_=Depends(require_admin)):
    unknown_ids = get_unconfigured_sensor_ids_from_firestore()
    return {"status": "success", "data": unknown_ids}


@router.get("/{sensor_id}/config")
async def get_sensor_config_endpoint(sensor_id: str, _=Depends(get_auth_claims)):
    config = get_sensor_config(sensor_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"status": "success", "data": config}
