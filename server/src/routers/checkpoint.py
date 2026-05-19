from datetime import datetime
import json
import os
import shutil
from fastapi import APIRouter, HTTPException
from shared.logger import get_logger
from dependencies import CHECKPOINTS_DIR, state

router = APIRouter(prefix="/checkpoint")
logger = get_logger(__name__)

def _free_space_for(needed: int) -> None:
    files = sorted(f for f in os.listdir(CHECKPOINTS_DIR) if f.endswith(".json"))
    while shutil.disk_usage(CHECKPOINTS_DIR).free < needed:
        if not files:
            raise OSError(f"Disk full and no checkpoints left to delete (need {needed} bytes)")
        oldest = files.pop(0)
        logger.warning(f"Disk full, deleting oldest checkpoint to make space: {oldest}")
        os.remove(os.path.join(CHECKPOINTS_DIR, oldest))

def _write_checkpoint() -> str:
    checkpoint = {
        "available": state.get_available_urls(),
        "occupied": state.get_occupied_urls(),
        "processed": state.get_processed_urls(),
        "terminated": state.get_terminated_urls(),
    }
    data = json.dumps(checkpoint)
    _free_space_for(len(data.encode("utf-8")))

    filename = datetime.utcnow().strftime("checkpoint_%Y%m%d_%H%M%S.json")
    path = os.path.join(CHECKPOINTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    return path

@router.get("")
async def list_checkpoints():
    files = sorted(os.listdir(CHECKPOINTS_DIR), reverse=True)
    return {"checkpoints": files}


@router.post("")
async def save_checkpoint():
    try:
        path = _write_checkpoint()
    except OSError as e:
        logger.error(f"Failed to write checkpoint: {e}")
        raise HTTPException(status_code=507, detail=str(e))
    total = state.get_url_count()
    logger.info(f"Manual checkpoint saved to {path} ({total} URLs)")
    return {"saved": total, "path": path}

@router.post("/load/{filename}")
async def load_checkpoint(filename: str, overwrite: bool = False):
    path = os.path.join(CHECKPOINTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No checkpoint file found: {filename}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if overwrite:
        state.load_from_checkpoint(
            available=data.get("available", []),
            occupied=data.get("occupied", []),
            processed=data.get("processed", []),
            terminated=data.get("terminated", [])
        )
        logger.info(f"Checkpoint loaded (overwrite) from {path}")
        return {"path": path}
    else:
        counts = state.merge_from_checkpoint(
            available=data.get("available", []),
            occupied=data.get("occupied", []),
            processed=data.get("processed", []),
            terminated=data.get("terminated", []),
        )
        total = sum(counts.values())
        logger.info(f"Checkpoint merged from {path} (+{total} URLs)")
        return {"added": counts, "path": path}