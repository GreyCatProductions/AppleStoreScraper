from fastapi import APIRouter
from dependencies import state

router = APIRouter(prefix="/queue")

@router.post("")
async def enqueue(body: list[str]):
    added = state.add_urls(body, True)
    return {"added": added}


@router.get("")
async def get_queue(offset: int = 0, limit: int = 100):
    urls = state.get_available_urls()
    return {"total": len(urls), "urls": urls[offset : offset + limit]}
