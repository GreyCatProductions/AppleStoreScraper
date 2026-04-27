from pydantic import BaseModel


class CreateServerRequest(BaseModel):
    amount: int
    zone: str
    
class Metadata(BaseModel):
    server_ip: str
    port: str
    google_drive_folder_id: str
    api_key: str
    google_credentials: dict