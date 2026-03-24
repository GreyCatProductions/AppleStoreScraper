from typing import List
from pydantic import BaseModel


class CreateServerRequest(BaseModel):
    name: str
    ssh_keys: List[str]