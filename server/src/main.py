import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI, HTTPException
from schema.sharedState import SharedState
from schema.requestClasses import CreateServerRequest
from shared.objects import FailedTask, TaskResult
from hetzner import create_server, delete_server, list_servers

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")

app = FastAPI()
state = SharedState(csv_path=CSV_PATH)

@app.get("/task")
def get_task():
    url = state.pop_url()
    if url:
        return {"url": url}
    
    return {"Out of urls"}


@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.similar_apps:
        state.enqueue_new_urls(result.similar_apps)
    state.write_row(result.model_dump())
    return {"status": "ok"}


@app.post("/task/failed")
def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}


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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
