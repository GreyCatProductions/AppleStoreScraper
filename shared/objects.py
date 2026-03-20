from pydantic import BaseModel

class TaskResult(BaseModel):
    url: str
    title: str
    price: str
    rating: str
    reviews: str

class FailedTask(BaseModel):
    url: str