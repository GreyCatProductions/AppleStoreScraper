from typing import List
from pydantic import BaseModel

class AppData(BaseModel):
    url: str | None
    app_name: str| None
    developer_name: str| None
    category: str| None
    price: str| None
    description: str | None
    review_count: int | None
    review_average: float | None
    review_one: int | None
    review_two: int | None
    review_three: int | None
    review_four: int | None
    review_five: int | None
    versions: str | None
    size: int | None
    languages: str | None
    age: str | None
    age_reasons: List[str]| None
    privacy_linked: List[str]| None
    privacy_unlinked: List[str]| None
    privacy_tracked: List[str]| None
    privacy_not_collected: str| None
    version_history: List[dict]| None
    in_app_purchases: str | None
    privacy_policy_link: str| None
    similar_apps: List[str]| None

class TaskResult(BaseModel):
    processed_url: str
    success: bool
    foundUrls: List[str] | None
    
class FailedTask(BaseModel):
    url: str

class WorkerConfig(BaseModel):
    task_wait_interval: int = 60
    scrape_retries: int = 3
    scrape_retry_delay: int = 5
    scrape_retry_delay_variation: int = 2
    google_drive_folder_id: str
    task_timeout: int = 300
    
class DriveId(BaseModel):
    url: str