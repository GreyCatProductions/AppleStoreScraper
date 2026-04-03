import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from googledrive import GoogleDriveClient

FOLDER_ID = input("Enter Shared Drive folder ID: ").strip()

client = GoogleDriveClient(FOLDER_ID)
file_id = client.upload_with_conversion("test_upload", "<html><body>hello</body></html>")

if file_id:
    print(f"Success! File ID: {file_id}")
else:
    print("Upload failed.")
