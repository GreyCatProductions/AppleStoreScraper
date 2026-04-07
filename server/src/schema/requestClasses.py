from enum import Enum
from typing import List
from pydantic import BaseModel


class Zone(str, Enum):
    us_central1_a = "us-central1-a"
    us_central1_b = "us-central1-b"
    us_east1_b = "us-east1-b"
    europe_west1_b = "europe-west1-b"
    northamerica_northeast2_b = "northamerica-northeast2-b"


class CreateServerRequest(BaseModel):
    amount: int
    zone: Zone
