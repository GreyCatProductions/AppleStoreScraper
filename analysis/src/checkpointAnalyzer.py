import json
import re
import sys
from collections import Counter


def analyze(path: str):
    with open(path, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)

    queues = ["available", "occupied", "processed", "terminated"]
    country_pattern = re.compile(r"https://apps\.apple\.com/([a-z]{2})/app/")

    total = 0
    country_counts: Counter = Counter()

    for queue in queues:
        urls = checkpoint.get(queue, [])
        count = len(urls)
        total += count
        print(f"  {queue}: {count}")
        for url in urls:
            match = country_pattern.search(url)
            if match:
                country_counts[match.group(1)] += 1

    print(f"\nTotal entries: {total}")
    print(f"\nBy country ({len(country_counts)} countries):")
    for country, count in sorted(country_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total else 0
        print(f"  {country}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyzeCheckpoint.py <path_to_checkpoint.json>")
        sys.exit(1)
    analyze(sys.argv[1])
