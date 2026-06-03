import argparse
import os
import sys
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "googleCredentials.json")
_SCOPES = ["https://www.googleapis.com/auth/drive"]


def deduplicate(drive_id: str, yes: bool = False):
    creds = service_account.Credentials.from_service_account_file(_CREDENTIALS_PATH, scopes=_SCOPES)
    service = build("drive", "v3", credentials=creds)

    seen: set[str] = set()
    to_delete: list[dict] = []
    total_files = 0
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                driveId=drive_id,
                corpora="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                pageToken=page_token,
            )
            .execute()
        )

        files: List[Dict] = response.get("files", [])
        total_files += len(files)
        print(f"Fetched {len(files)} files of which {len(set(f['name'] for f in files))} are unique by name")

        for file in files:
            if file["name"] in seen:
                to_delete.append(file)
            else:
                seen.add(file["name"])

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    if not to_delete:
        print("No duplicates found.")
        return
    
    for file in to_delete:
        print(f"  {file['name']} ({file['id']})")

    print(f"\nFound {total_files} files with {len(to_delete)} duplicate(s) to delete.")
    if not yes:
        while True:
            answer = input("\nDelete all of the above? [y/N] ").strip().lower()
            if answer == "n":
                print("Aborted.")
                return
            if answer == "y":
                break

    for file in to_delete:
        service.files().delete(fileId=file["id"], supportsAllDrives=True).execute()
        print(f"Deleted: {file['name']} ({file['id']})")

    print(f"\nDone. Deleted {len(to_delete)} file(s).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("drive_id")
    parser.add_argument("-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    print(f"Eliminating duplicates in shared drive: {args.drive_id}\n")
    deduplicate(args.drive_id, yes=args.y)

if __name__ == "__main__":
    main()
