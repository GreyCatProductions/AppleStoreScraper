import argparse
import csv
import itertools
import json
import os
import re
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from bs4 import BeautifulSoup
from client.src.parser import extractAppData
from utils import reconstruct_url

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


def _process_file(path: str) -> dict | None:
    url = reconstruct_url(os.path.basename(path)) or path
    try:
        with open(path, "r", encoding="utf-8") as fh:
            html = fh.read()
        soup = BeautifulSoup(html, "html.parser")
        return extractAppData(url, soup)
    except Exception as e:
        print(f"[warn] {path}: {type(e).__name__}: {e}", flush=True)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract app data from scraped HTML files into a CSV."
    )
    parser.add_argument("data_folder", help="Folder containing scraped HTML files")
    parser.add_argument("--regex", "-r", help="Only process files matching this pattern")
    parser.add_argument("--workers", "-w", type=int, default=None, help="Worker processes (default: cpu count)")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite output if it already exists")
    args = parser.parse_args()

    if not os.path.exists(args.data_folder):
        parser.error(f"Folder not found: {args.data_folder}")

    try:
        regex = re.compile(args.regex) if args.regex else None
    except re.error as e:
        parser.error(f"Invalid regex: {e}")

    if args.workers is not None and args.workers <= 0:
        parser.error("--workers must be a positive integer")

    if os.path.exists(OUTPUT_PATH) and not args.force:
        parser.error(f"Output already exists: {OUTPUT_PATH}  (use --force to overwrite)")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    count = 0
    failed = 0
    regex_skipped = 0
    start = time.time()

    def _iter_paths():
        nonlocal regex_skipped
        for root, _, files in os.walk(args.data_folder):
            for file in files:
                if regex and not regex.search(file):
                    regex_skipped += 1
                    continue
                yield os.path.join(root, file)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=",", extrasaction="ignore", quoting=csv.QUOTE_ALL)
        writer.writeheader()

        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            max_in_flight = (args.workers or os.cpu_count() or 4) * 4
            path_iter = _iter_paths()

            #initial queue
            pending = {
                executor.submit(_process_file, p)
                for p in itertools.islice(path_iter, max_in_flight)
            }

            while pending:
                done, remaining = wait(pending, return_when=FIRST_COMPLETED)
                pending = set(remaining)

                for fut in done:
                    nxt = next(path_iter, None)
                    if nxt is not None:
                        pending.add(executor.submit(_process_file, nxt))

                    data = fut.result()
                    if data:
                        writer.writerow({k: _serialize(data.get(k)) for k in COLUMNS})
                        count += 1
                    else:
                        failed += 1

                    total = count + failed
                    if total % 10000 == 0:
                        elapsed = time.time() - start
                        rate = total / elapsed if elapsed > 0 else 0.0
                        f.flush()
                        print(f"  {count:,} parsed | {failed:,} failed | {regex_skipped:,} regex-skipped | {rate:.1f} files/s | {elapsed/3600:.1f}h elapsed", flush=True)

    elapsed = time.time() - start
    print(f"Done: {count:,} apps -> {OUTPUT_PATH} ({elapsed/3600:.1f}h total)")


if __name__ == "__main__":
    main()
