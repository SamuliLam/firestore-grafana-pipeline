from fastapi import APIRouter, BackgroundTasks, status, Depends
from src.auth import auth0
from src.models.schemas import ApiResponse
from src.history_to_timescale import sync_firestore_to_timescale
from src.utils.api_response import make_response
from src.utils.sync_status import sync_status

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("", dependencies=[Depends(auth0.require_auth())],
    responses={
        202: {
            "description": "History sync started in background",
            "model": ApiResponse
        }
    },
    status_code=status.HTTP_202_ACCEPTED
)
async def sync_history(background_tasks: BackgroundTasks):
    """Start background synchronization of historical Firestore data"""
    background_tasks.add_task(sync_firestore_to_timescale)
    return make_response(
        status="accepted",
        message="History synchronization started in background",
        status_code=202
    )


@router.get("/status")
async def get_history_sync_status():
    """Get the current status of history synchronization"""
    return {
        "state": sync_status["state"],
        "error": sync_status["error"]
    }