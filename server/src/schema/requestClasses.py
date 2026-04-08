from pydantic import BaseModel


class CreateServerRequest(BaseModel):
    amount: int
    zone: str