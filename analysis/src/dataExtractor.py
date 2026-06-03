import csv
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from bs4 import BeautifulSoup
from client.src.extractor import extractAppData
from utils import extract_country_code, reconstruct_url

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../data/parsed.csv")

COLUMNS = [
    "url", 
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
        print("Usage: python dataExtractor.py <path_to_data_folder> [regex] [--limit N]")
        sys.exit(1)

    PATH_TO_DATA_FOLDER = sys.argv[1]
    args = sys.argv[2:]
    limit = None
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    regex = re.compile(args[0]) if args else None

    if not os.path.exists(PATH_TO_DATA_FOLDER):
        raise FileNotFoundError(f"Expected data to be in {PATH_TO_DATA_FOLDER}! Folder not found.")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    count = 0
    skipped = 0
    start = time.time()

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=",", extrasaction="ignore")
        writer.writeheader()

        for root, dirs, files in os.walk(PATH_TO_DATA_FOLDER):
            for file in files:
                if regex and not regex.search(file):
                    skipped += 1
                    continue
                path = os.path.join(root, file)
                url = reconstruct_url(file) or path

                with open(path, "r", encoding="utf-8") as fh:
                    html = fh.read()

                soup = BeautifulSoup(html, "html.parser")
                data = extractAppData(url, soup)
                if not data:
                    skipped += 1
                    continue

                writer.writerow({k: _serialize(data.get(k)) for k in COLUMNS})
                count += 1

                if count % 10000 == 0:
                    elapsed = time.time() - start
                    rate = count / elapsed
                    print(f"  {count:,} parsed | {skipped:,} skipped | {rate:.1f} files/s | {elapsed/3600:.1f}h elapsed", flush=True)

                if limit and count >= limit:
                    break
            if limit and count >= limit:
                break

    elapsed = time.time() - start
    print(f"Done: {count:,} apps -> {OUTPUT_PATH} ({elapsed/3600:.1f}h total)")
    
if __name__ == "__main__":
    main()