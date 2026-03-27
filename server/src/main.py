import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI, HTTPException
from schema.sharedState import SharedState
from schema.requestClasses import CreateServerRequest
from shared.objects import FailedTask, TaskResult
from hetzner import create_server, delete_server, list_servers
from shared.logger import setup_logging, get_logger

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")
HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "html")
INITIAL_LINKS = os.path.join(os.path.dirname(__file__), "..", "config/initialLinks")

setup_logging()
logger = get_logger(__name__)

app = FastAPI()
state = SharedState(csv_path=CSV_PATH, html_dir=HTML_DIR)
if os.path.exists(INITIAL_LINKS):
    with open(INITIAL_LINKS) as f:
        urls = [line.strip() for line in f if line.strip()]
        state.enqueue_urls(urls)
else:
    raise FileNotFoundError("Could not find file for loading initial urls! Expected at {INITIAL_LINKS}. Existing!")

@app.get("/task")
def get_task():
    url = state.pop_url()
    if url:
        return {"url": url}
    
    return {"url": None}


@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.foundUrls:
        state.enqueue_urls(result.foundUrls)
        
    if result.appData:
        state.write_row(result.appData.model_dump())
        
    if result.html:
        state.save_html(result.processed_url, result.html)
    return {"status": "ok"}


@app.post("/task/failed")
def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}


@app.post("/queue")
def enqueue(body: list[str]):
    added = state.enqueue_urls(body)
    return {"added": added}

@app.get("/queue")
def get_queue(offset: int = 0, limit: int = 100):
    urls = state.get_pending_urls()
    return {"total": len(urls), "urls": urls[offset:offset + limit]}

@app.get("/progress")
def stats():
    return {
        "pending": state.get_url_count(),
        "completed": len(state.get_completed_urls()),
        "failed": len(state.get_failed_urls())
    }

def _serialize_server(server):
    return {
        "id": server.id,
        "name": server.name,
        "status": server.status,
        "ipv4": server.public_net.ipv4.ip if server.public_net and server.public_net.ipv4 else None,
        "ipv6": server.public_net.ipv6.ip if server.public_net and server.public_net.ipv6 else None,
    }

@app.post("/servers")
async def spawn_server(body: CreateServerRequest):
    try:
        loop = asyncio.get_event_loop()
        
        async def spawn_one():
            server, root_password = await loop.run_in_executor(None, lambda: create_server(body.ssh_keys))
            return {**_serialize_server(server), "root_password": root_password}

        return await asyncio.gather(*[spawn_one() for _ in range(body.amount)])

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/servers/{server_id}")
def remove_server(server_id: int):
    try:
        delete_server(server_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/servers")
def list_all_servers():
    try: 
        servers = list_servers()
        return {"servers": [_serialize_server(s) for s in servers] if servers else []}
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