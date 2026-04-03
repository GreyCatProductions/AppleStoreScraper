import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from schema.sharedState import SharedState
from schema.requestClasses import CreateServerRequest
from shared.objects import FailedTask, TaskResult, WorkerConfig
from shared.logger import setup_logging, get_logger
from googleCloud import create_instance_from_template, delete_instance, list_instances
from dotenv import load_dotenv
from google.cloud import compute_v1

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")
HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "html")
INITIAL_LINKS = os.path.join(os.path.dirname(__file__), "..", "config/initialLinks")

load_dotenv()

HOST = os.getenv("HOST")
port_raw = os.getenv("PORT")

assert HOST and port_raw

PORT = int(port_raw)
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TEMPLATE_NAME = os.getenv("GOOGLE_TEMPLATE_NAME")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SERVER_IP = os.getenv("SERVER_IP")
_raw_ssh_keys = os.getenv("SSH_KEYS", "")
SSH_KEYS = [k.strip() for k in _raw_ssh_keys.split(",") if k.strip()] or None

API_KEY = os.getenv("API_KEY")
assert API_KEY, "API_KEY missing from environment!"
assert GOOGLE_PROJECT_ID and GOOGLE_TEMPLATE_NAME and GOOGLE_DRIVE_FOLDER_ID and SERVER_IP

setup_logging()
logger = get_logger(__name__)
state = SharedState(csv_path=CSV_PATH, html_dir=HTML_DIR)

if os.path.exists(INITIAL_LINKS):
    with open(INITIAL_LINKS) as f:
        urls = [line.strip() for line in f if line.strip()]
        state.add_urls(urls)
else:
    raise FileNotFoundError(
        f"Could not find file for loading initial urls! Expected at {INITIAL_LINKS}. Exiting!"
    )

app = FastAPI()

_PUBLIC_PATHS = {"/docs"}

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

_config = WorkerConfig(
    task_wait_interval=60,
    scrape_retries=3,
    scrape_retry_delay=5,
    scrape_retry_delay_variation=2,
    google_drive_folder_id=GOOGLE_DRIVE_FOLDER_ID,
)


@app.get("/config")
async def get_config():
    return _config


@app.post("/config")
async def update_config(body: WorkerConfig):
    global _config
    _config = _config.model_copy(update=body.model_dump(exclude_unset=True))
    return _config


@app.get("/task")
async def get_task():
    url = state.get_url()
    return {"url": url}


@app.post("/task/complete")
async def complete_task(result: TaskResult):
    if result.foundUrls:
        state.add_urls(result.foundUrls)
    if result.success:
        state.mark_success(result.processed_url)
    else:
        state.mark_failed(result.processed_url)
    return {"status": "ok"}


@app.post("/task/failed")
async def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}


@app.post("/queue")
async def enqueue(body: list[str]):
    added = state.add_urls(body, True)
    return {"added": added}


@app.get("/queue")
async def get_queue(offset: int = 0, limit: int = 100):
    urls = state.get_available_urls()
    return {"total": len(urls), "urls": urls[offset : offset + limit]}


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
        "completed": len(state.get_processed_urls()),
        "terminated": len(state.get_terminated_urls()),
        "currently_occupied": len(state.get_occupied_urls()),
    }


def _serialize_worker(worker: compute_v1.Instance):
    ipv4 = None
    ipv6 = None
    if worker.network_interfaces:
        iface = worker.network_interfaces[0]
        if iface.access_configs:
            ipv4 = iface.access_configs[0].nat_i_p or None
        if iface.ipv6_access_configs:
            ipv6 = iface.ipv6_access_configs[0].external_ipv6 or None
    return {
        "id": worker.id,
        "name": worker.name,
        "status": worker.status,
        "ipv4": ipv4,
        "ipv6": ipv6,
    }


@app.post("/workers")
async def spawn_worker(body: CreateServerRequest):
    try:
        loop = asyncio.get_running_loop()

        async def spawn_one():
            worker = await loop.run_in_executor(
                None,
                lambda: create_instance_from_template(
                    project_id=GOOGLE_PROJECT_ID, # type: ignore
                    template_name=GOOGLE_TEMPLATE_NAME, # type: ignore
                    port=PORT,
                    ssh_keys=SSH_KEYS,
                    google_drive_folder_id=GOOGLE_DRIVE_FOLDER_ID, # type: ignore
                    server_ip=SERVER_IP, # type: ignore
                    api_key=API_KEY # type: ignore
                )
            )
            return {**_serialize_worker(worker)}

        return await asyncio.gather(*[spawn_one() for _ in range(body.amount)])

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/workers/{worker_name}")
async def remove_worker(worker_name: str):
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: delete_instance(GOOGLE_PROJECT_ID, worker_name))  # type: ignore
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/workers")
async def remove_all_workers():
    loop = asyncio.get_running_loop()
    workers = await loop.run_in_executor(None, lambda: list_instances(GOOGLE_PROJECT_ID))  # type: ignore
    if not workers:
        return {"deleted": []}

    deleted = []
    errors = []
    for worker in workers:
        try:
            if worker.id is None:
                continue
            await loop.run_in_executor(None, lambda w=worker: delete_instance(GOOGLE_PROJECT_ID, w.name))  # type: ignore
            deleted.append(worker.id)
        except Exception as e:
            errors.append({"id": worker.id, "error": str(e)})

    return {"deleted": deleted, "errors": errors}


@app.get("/workers")
async def list_all_workers():
    try:
        loop = asyncio.get_running_loop()
        workers = await loop.run_in_executor(None, lambda: list_instances(GOOGLE_PROJECT_ID))  # type: ignore
        return {"workers": [_serialize_worker(s) for s in workers] if workers else []}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT)
