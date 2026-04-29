import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from bs4 import BeautifulSoup
from client.src.parser import extractAppData
from utils import extract_country_code, reconstruct_url

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../data/parsed.csv")

COLUMNS = [
    "url", "country_code",
    "app_name", "developer_name", "category", "price", "description",
    "review_count", "review_average",
    "review_one", "review_two", "review_three", "review_four", "review_five",
    "versions", "size", "languages",
    "age", "age_reasons",
    "privacy_linked", "privacy_unlinked", "privacy_tracked", "privacy_not_collected",
    "version_history", "in_app_purchases", "privacy_policy_link", "similar_apps",
]


def _serialize(value) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_data_folder>")
        sys.exit(1)

    PATH_TO_DATA_FOLDER = sys.argv[1]

    if not os.path.exists(PATH_TO_DATA_FOLDER):
        raise FileNotFoundError(f"Expected data to be in {PATH_TO_DATA_FOLDER}! Folder not found.")

    count = 0
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=",", extrasaction="ignore")
        writer.writeheader()

        for root, dirs, files in os.walk(PATH_TO_DATA_FOLDER):
            for file in files:
                path = os.path.join(root, file)
                url = reconstruct_url(file) or path
                country_code = extract_country_code(url)
                
                with open(path, "r", encoding="utf-8") as fh:
                    html = fh.read()

                soup = BeautifulSoup(html, "html.parser")
                data = extractAppData(url, soup)
                if not data:
                    continue
                
                data["country_code"] = country_code
                writer.writerow({k: _serialize(data.get(k)) for k in COLUMNS})
                count += 1

    print(f"Parsed {count} apps -> {OUTPUT_PATH}")
    
if __name__ == "__main__":
    main()