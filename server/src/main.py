import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from shared.logger import get_logger
from googleCloud import start_stopped_instances
from routers.checkpoint import _write_checkpoint
from dependencies import API_KEY, HOST, PORT, state, GOOGLE_PROJECT_ID
from routers import tasks, queue, config as config_router, checkpoint, workers, metadata, drive
import dependencies


_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = get_logger(__name__)

async def _checkpoint_loop():
    while True:
        await asyncio.sleep(12*3600)
        try:
            path = _write_checkpoint()
            logger.info(f"Auto-checkpoint saved to {path}")
        except Exception as e:
            logger.error(f"Auto-checkpoint failed: {e}")

async def _timeout_loop():
    while True:
        await asyncio.sleep(10)
        try:
            if dependencies.config.task_timeout is None:
                continue
            candidates = state.get_timed_out(dependencies.config.task_timeout)
            for url in candidates:
                state.requeue_url(url)
                logger.info(f"Requeued {url}. Timed out")
        except Exception as e:
            logger.error(f"Error in timeout loop: {e}")
            
async def _restart_loop():
    while True:
        await asyncio.sleep(300)
        try:
            loop = asyncio.get_running_loop()
            started = await loop.run_in_executor(
                None, lambda: start_stopped_instances(GOOGLE_PROJECT_ID)  # type: ignore
            )
            if started:
                logger.info(f"Restarted stopped workers: {started}")
        except Exception as e:
            logger.error(f"Error in restart loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    t1 = asyncio.create_task(_timeout_loop())
    t2 = asyncio.create_task(_restart_loop())
    t3 = asyncio.create_task(_checkpoint_loop())
    yield
    t1.cancel()
    t2.cancel()
    t3.cancel()

app = FastAPI(dependencies=[Security(_api_key_scheme)], lifespan=lifespan)

_PUBLIC_PATHS = {"/docs", "/openapi.json", "/redoc"}

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

@app.get("/state")
async def get_state(offset: int = 0, limit: int = 1000):
    return {
        "available": state.get_available_urls()[offset:offset+limit],
        "occupied": state.get_occupied_urls()[offset:offset+limit],
        "processed": state.get_processed_urls()[offset:offset+limit],
        "terminated": state.get_terminated_urls()[offset:offset+limit],
        "total": state.get_url_count(),
    }

@app.get("/progress")
async def stats():
    return {
        "total": state.get_url_count(),
        "available": len(state.get_available_urls()),
        "completed": len(state.get_processed_urls()),
        "terminated": len(state.get_terminated_urls()),
        "currently_occupied": len(state.get_occupied_urls()),
    }

app.include_router(tasks.router)
app.include_router(queue.router)
app.include_router(config_router.router)
app.include_router(checkpoint.router)
app.include_router(workers.router)
app.include_router(metadata.router)
app.include_router(drive.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT)
