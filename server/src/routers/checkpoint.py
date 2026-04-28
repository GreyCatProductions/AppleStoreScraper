from datetime import datetime
import json
import os
from fastapi import APIRouter, HTTPException
from shared.logger import get_logger
from dependencies import CHECKPOINTS_DIR, state

router = APIRouter(prefix="/checkpoint")
logger = get_logger(__name__)

def _write_checkpoint() -> str:
    checkpoint = {
        "available": state.get_available_urls(),
        "occupied": state.get_occupied_urls(),
        "processed": state.get_processed_urls(),
        "terminated": state.get_terminated_urls(),
    }
    filename = datetime.utcnow().strftime("checkpoint_%Y%m%d_%H%M%S.json")
    path = os.path.join(CHECKPOINTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f)
    return path

@router.get("")
async def list_checkpoints():
    files = sorted(os.listdir(CHECKPOINTS_DIR), reverse=True)
    return {"checkpoints": files}


@router.post("")
async def save_checkpoint():
    path = _write_checkpoint()
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