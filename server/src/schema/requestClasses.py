from typing import List
from pydantic import BaseModel


class CreateServerRequest(BaseModel):
    amount: int