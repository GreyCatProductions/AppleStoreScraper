import asyncio
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter
from dependencies import GOOGLE_PROJECT_ID
from schema.requestClasses import Metadata
from googleCloud import get_project_metadata, set_project_metadata


router = APIRouter(prefix="/metadata")


@router.get("")
async def get_metadata():
    loop = asyncio.get_event_loop()
    keys = ["SERVER_IP", "PORT", "GOOGLE_DRIVE_FOLDER_ID", "API_KEY"]
    results = {}
    for key in keys:
        results[key] = await loop.run_in_executor(None, get_project_metadata, GOOGLE_PROJECT_ID, key)  # type: ignore
    return results


@router.post("")
async def set_metadata(body: Metadata):
    loop = asyncio.get_event_loop()
    mapping = {
        "SERVER_IP": body.server_ip,
        "PORT": body.port,
        "API_KEY": body.api_key,
        "GOOGLE_CREDENTIALS": json.dumps(body.google_credentials),
    }
    await loop.run_in_executor(None, set_project_metadata, GOOGLE_PROJECT_ID, mapping) # type: ignore
    return {"updated": list(mapping.keys())}