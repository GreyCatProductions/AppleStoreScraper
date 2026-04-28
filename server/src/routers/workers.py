import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException
from google.cloud import compute_v1
from dependencies import GOOGLE_PROJECT_ID, SSH_KEYS, GOOGLE_TEMPLATE_NAME
from schema.requestClasses import CreateServerRequest
from googleCloud import create_instance_from_template, delete_instance, list_instances

router = APIRouter(prefix="/workers")

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

@router.post("")
async def spawn_worker(body: CreateServerRequest):
    try:
        loop = asyncio.get_running_loop()

        async def spawn_one():
            worker = await loop.run_in_executor(
                None,
                lambda: create_instance_from_template(
                    project_id=GOOGLE_PROJECT_ID, # type: ignore
                    template_name=GOOGLE_TEMPLATE_NAME, # type: ignore
                    ssh_keys=SSH_KEYS,
                    zone=body.zone,
                )
            )
            return {**_serialize_worker(worker)}

        return await asyncio.gather(*[spawn_one() for _ in range(body.amount)])

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.delete("")
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

@router.delete("/{worker_name}")
async def remove_worker(worker_name: str):
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: delete_instance(GOOGLE_PROJECT_ID, worker_name)) # type: ignore
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("")
async def list_all_workers():
    try:
        loop = asyncio.get_running_loop()
        workers = await loop.run_in_executor(None, lambda: list_instances(GOOGLE_PROJECT_ID))  # type: ignore
        return {"workers": [_serialize_worker(s) for s in workers] if workers else []}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
