from fastapi import APIRouter
from shared.objects import FailedTask, TaskResult
from dependencies import state

router = APIRouter(prefix="/task")

@router.get("")
async def get_task():
    url = state.get_url()
    return {"url": url}


@router.post("/heartbeat")
async def task_heartbeat(body: FailedTask):
    state.reset_assigned_at(body.url)
    return {"status": "ok"}


@router.post("/complete")
async def complete_task(result: TaskResult):
    if result.foundUrls:
        state.add_urls(result.foundUrls)
    if result.success:
        state.mark_success(result.processed_url)
    else:
        state.mark_failed(result.processed_url)
    return {"status": "ok"}


@router.post("/failed")
async def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}
