import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from io import BytesIO
import re
from shared.logger import get_logger

logger = get_logger(__name__)

_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "googleCredentials.json")
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveClient:
    def __init__(self, htmlFolderID: str):
        creds = service_account.Credentials.from_service_account_file(_CREDENTIALS_PATH, scopes=_SCOPES)
        self.service = build("drive", "v3", credentials=creds)
        self.htmlFolderID = htmlFolderID

    def upload_with_conversion(self, name: str, content: str) -> str:
        name = re.sub(r'[^\w\-.]', '_', name)[:200]
        file_metadata = {
            "name": name,
            "parents": [self.htmlFolderID]
        }
        media = MediaIoBaseUpload(BytesIO(content.encode("utf-8")), mimetype="text/html", resumable=True)
        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True)
            .execute()
        )
        file_id = file.get("id")
        logger.info(f'File with ID: "{file_id}" and Name: "{name}" has been uploaded.')
        return file_id