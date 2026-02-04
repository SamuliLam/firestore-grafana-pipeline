from fastapi import APIRouter, status, Depends
from src.models.schemas import SensorMetadataInput, ApiResponse
from src.db import insert_sensor_metadata, delete_sensor, get_all_sensor_metadata
from src.auth import auth0
from src.utils.api_response import make_response

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("",
             responses={
                 201: {
                     "description": "Sensor added successfully",
                     "model": ApiResponse
                 },
                 400: {
                     "description": "Bad request - invalid sensor data",
                     "model": ApiResponse
                 },
                 422: {
                     "description": "Validation error"
                 }
             },
             status_code=status.HTTP_201_CREATED
             )

async def add_sensor(sensor_data: SensorMetadataInput, auth_result: dict = Depends(auth0.require_auth())):
    """Add a new sensor to the metadata registry"""
    try:
        data = sensor_data.model_dump()
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


@router.delete("/{sensor_id}",
               responses={
                   200: {
                       "description": "Sensor deleted successfully",
                       "model": ApiResponse
                   },
                   404: {
                       "description": "Sensor not found",
                       "model": ApiResponse
                   },
                   500: {
                       "description": "Internal server error",
                       "model": ApiResponse
                   }
               }
               )
async def delete_sensor_endpoint(sensor_id: str,  auth_result: dict = Depends(auth0.require_auth())):
    """Delete a sensor from the metadata registry"""
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


@router.get("/metadata", dependencies=[Depends(auth0.require_auth())],
            responses={
                200: {
                    "description": "Sensor metadata retrieved successfully",
                    "model": ApiResponse
                },
                500: {
                    "description": "Internal server error",
                    "model": ApiResponse
                }
            }
            )
async def get_sensor_metadata_endpoint():
    """Retrieve metadata for all registered sensors"""
    try:
        metadata = get_all_sensor_metadata()
    except Exception as e:
        return make_response(
            status="error",
            message=str(e),
            status_code=500
        )

    return make_response(
        status="success",
        message="Sensor metadata retrieved successfully",
        data=metadata,
        status_code=200
    )
