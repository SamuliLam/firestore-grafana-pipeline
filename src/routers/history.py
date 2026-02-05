from fastapi import APIRouter, BackgroundTasks, status, Depends
from src.dependencies import get_auth_claims
from src.history_to_timescale import sync_firestore_to_timescale
from src.utils.sync_status import sync_status


router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def sync_history(
    background_tasks: BackgroundTasks,
    _=Depends(get_auth_claims),
):
    background_tasks.add_task(sync_firestore_to_timescale)
    return {
        "status": "accepted",
        "message": "History synchronization started in background",
    }


@router.get("/status")
async def get_history_sync_status(_=Depends(get_auth_claims)):
    return {
        "state": sync_status["state"],
        "error": sync_status["error"],
    }
