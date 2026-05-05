from fastapi import APIRouter, HTTPException
import dependencies
from shared.logger import get_logger
from shared.objects import DriveId

router = APIRouter(prefix="/drive")

@router.post("")
async def report_full_drive(driveId: DriveId):
    marked = dependencies.drive.mark_full(driveId)
    if not marked:
        raise HTTPException(status_code=404, detail=f"Drive {driveId} not in available list")

    next_drive = dependencies.drive.next_available()
    if next_drive:
        dependencies.config = dependencies.config.model_copy(update={"google_drive_folder_id": next_drive})

    return {
        "marked_full": driveId,
        "new_active_drive": dependencies.config.google_drive_folder_id,
        "remaining": dependencies.drive.count_available(),
    }
    
@router.post("")
async def add_shared_drive(driveIds: list[DriveId]):
    
    success = 0
    for driveId in driveIds:
        if dependencies.drive.add(driveId):
            success += 1
        
    return {"added": success}
