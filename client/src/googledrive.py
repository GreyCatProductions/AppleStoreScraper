import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import re
from shared.logger import get_logger

logger = get_logger(__name__)

class GoogleDriveClient:
    def __init__(self, htmlFolderID: str):
        self.service = build("drive", "v3")
        self.htmlFolderID = htmlFolderID

    def upload_with_conversion(self, name: str, content: str) -> int | None:
        name = re.sub(r'[^\w\-.]', '_', name)[:200]
        try:
            file_metadata = {
                "name": name,
                "parents": [self.htmlFolderID]
            }
            media = MediaIoBaseUpload(BytesIO(content.encode("utf-8")), mimetype="text/html", resumable=True)

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            logger.info(f'File with ID: "{file.get("id")}" and Name: "{name}" has been uploaded.')

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            file = None

        return file.get("id") if file else None