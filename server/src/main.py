import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI, HTTPException
from schema.sharedState import SharedState
from schema.requestClasses import CreateServerRequest
from shared.objects import FailedTask, TaskResult
from shared.logger import setup_logging, get_logger
from googleCloud import create_instance_from_template, delete_instance, list_instances
from dotenv import load_dotenv
from google.cloud import compute_v1

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")
HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "html")
INITIAL_LINKS = os.path.join(os.path.dirname(__file__), "..", "config/initialLinks")

load_dotenv()

GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TEMPLATE_NAME = os.getenv("GOOGLE_TEMPLATE_NAME")
_raw_ssh_keys = os.getenv("SSH_KEYS", "")
SSH_KEYS = [k.strip() for k in _raw_ssh_keys.split(",") if k.strip()] or None
SSH_USERNAME = os.getenv("SSH_USERNAME")

if not GOOGLE_PROJECT_ID or not GOOGLE_TEMPLATE_NAME:
    raise EnvironmentError(
        f"Could not find GOOGLE_PROJECT_ID or GOOGLE_TEMPLATE_NAME in .env!"
    )

setup_logging()
logger = get_logger(__name__)
state = SharedState(csv_path=CSV_PATH, html_dir=HTML_DIR)

if os.path.exists(INITIAL_LINKS):
    with open(INITIAL_LINKS) as f:
        urls = [line.strip() for line in f if line.strip()]
        state.add_urls(urls)
else:
    raise FileNotFoundError(
        f"Could not find file for loading initial urls! Expected at {INITIAL_LINKS}. Existing!"
    )

app = FastAPI()

_config = {
    "task_wait_interval": 60,
    "scrape_retries": 3,
    "scrape_retry_delay": 5,
    "scrape_retry_delay_variation": 2,
}


@app.get("/config")
def get_config():
    return _config


@app.post("/config")
def update_config(body: dict):
    for key in _config:
        if key in body:
            _config[key] = body[key]

    return _config

@app.get("/task")
def get_task():
    url = state.get_url()
    if url:
        return {"url": url}

    return {"url": None}


@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.foundUrls:
        state.add_urls(result.foundUrls)

    if result.success:
        state.mark_success(result.processed_url)
    else:
        state.mark_failed(result.processed_url)

    return {"status": "ok"}


@app.post("/task/failed")
def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}


@app.post("/queue")
def enqueue(body: list[str]):
    added = state.add_urls(body, True)
    return {"added": added}


@app.get("/queue")
def get_queue(offset: int = 0, limit: int = 100):
    urls = state.get_available_urls()
    return {"total": len(urls), "urls": urls[offset : offset + limit]}


@app.get("/progress")
def stats():
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
                    GOOGLE_PROJECT_ID, # type: ignore
                    GOOGLE_TEMPLATE_NAME, # type: ignore
                    ssh_keys=SSH_KEYS,
                ),
            )
            return {**_serialize_worker(worker)}

        return await asyncio.gather(*[spawn_one() for _ in range(body.amount)])

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/workers/{worker_id}")
def remove_worker(worker_id: str):
    try:
        delete_instance(GOOGLE_PROJECT_ID, worker_id) # type: ignore
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/workers")
def remove_all_workers():
    workers = list_instances(GOOGLE_PROJECT_ID) # type: ignore
    if not workers:
        return {"deleted": []}

    deleted = []
    errors = []
    for worker in workers:
        try:
            if worker.id is None:
                continue
            delete_instance(GOOGLE_PROJECT_ID, worker.name) # type: ignore
            deleted.append(worker.id)
        except Exception as e:
            errors.append({"id": worker.id, "error": str(e)})

    return {"deleted": deleted, "errors": errors}


@app.get("/workers")
def list_all_workers():
    try:
        workers = list_instances(GOOGLE_PROJECT_ID) # type: ignore
        return {"workers": [_serialize_worker(s) for s in workers] if workers else []}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST")
    port_raw = os.getenv("PORT")

    if not host or not port_raw:
        raise Exception("HOST or PORT are missing in .env!")

    port = int(port_raw)
    uvicorn.run("main:app", host=host, port=port)
