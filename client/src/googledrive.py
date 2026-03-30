import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "..", "googleCredentials.json")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveClient:
    def __init__(self, hmtlFolderID: str):
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=creds)
        self.htmlFolderID = self.htmlFolderID

    def upload_with_conversion(self, name: str, ) -> int | None:
        try:
            file_metadata = {
                "name": name,
                "parents": [self.htmlFolderID]
            }
            media = MediaFileUpload("test.csv", mimetype="text/csv", resumable=True)

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            print(f'File with ID: "{file.get("id")}" has been uploaded.')

        except HttpError as error:
            print(f"An error occurred: {error}")
            file = None

        return file.get("id") if file else None