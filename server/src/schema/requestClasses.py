from typing import List
from pydantic import BaseModel


class CreateServerRequest(BaseModel):
    ssh_keys: List[str]
    amount: int