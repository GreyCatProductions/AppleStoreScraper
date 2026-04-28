from fastapi import APIRouter
from shared.objects import WorkerConfig
import dependencies

router = APIRouter(prefix="/config")

@router.get("")
async def get_config():
    return dependencies.config


@router.post("")
async def update_config(body: WorkerConfig):
    dependencies.config = dependencies.config.model_copy(update=body.model_dump(exclude_unset=True))
    return dependencies.config