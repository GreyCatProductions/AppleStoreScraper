import csv
import json
import os
from argparse import ArgumentParser
from collections import Counter


def _is_empty(value: str) -> bool:
    if not value or value.strip() in ("", "null", "None"):
        return True
    try:
        parsed = json.loads(value)
        return parsed in (None, [], {})
    except (json.JSONDecodeError, ValueError):
        return False


def main():
    parser = ArgumentParser(description="Print summary statistics for a parsed CSV.")
    parser.add_argument("file", help="CSV file to check")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        parser.error(f"File not found: {args.file}")

    total = 0
    null_counts: Counter = Counter()
    columns: list[str] = []

    errors = 0
    with open(args.file, encoding="utf-8", newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])

        for row in reader:
            try:
                total += 1
                for col in columns:
                    if _is_empty(row.get(col, "") or ""):
                        null_counts[col] += 1
            except Exception:
                errors += 1

    if total == 0:
        print("File is empty.")
        return

    print(f"\nFile  : {args.file}")
    print(f"Rows  : {total:,}")
    if errors:
        print(f"Errors: {errors:,} rows skipped due to parse errors")
    print()

    col_w = max(len(c) for c in columns)
    print(f"{'Column':<{col_w}}   {'Non-null':>10}   {'Null':>10}   {'Fill %':>7}")
    print("-" * (col_w + 36))

    for col in columns:
        nulls = null_counts[col]
        filled = total - nulls
        pct = filled / total * 100
        print(f"{col:<{col_w}}   {filled:>10,}   {nulls:>10,}   {pct:>6.1f}%")

    print()


if __name__ == "__main__":
    main()
