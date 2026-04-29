import json
import re
import sys
from collections import Counter


URL_RE = re.compile(r'"(https://apps\.apple\.com/[^"]+)"')
QUEUE_RE = re.compile(r'"(available|occupied|processed|terminated)"\s*:\s*\[([^\]]*)', re.DOTALL)
COUNTRY_RE = re.compile(r"https://apps\.apple\.com/([a-z]{2})/app/")


def _load_checkpoint(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    return json.loads(raw)

def analyze(path: str):
    checkpoint = _load_checkpoint(path)

    queues = ["available", "occupied", "processed", "terminated"]

    total = 0
    country_counts: Counter = Counter()

    for queue in queues:
        urls = checkpoint.get(queue, [])
        count = len(urls)
        total += count
        print(f"  {queue}: {count}")
        for url in urls:
            match = COUNTRY_RE.search(url)
            if match:
                country_counts[match.group(1)] += 1

    print(f"\nTotal entries: {total}")
    print(f"\nBy country ({len(country_counts)} countries):")
    for country, count in sorted(country_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total else 0
        print(f"  {country}: {count} ({pct:.1f}%)")


def compare(path_a: str, path_b: str):
    a = _load_checkpoint(path_a)
    b = _load_checkpoint(path_b)

    queues = ["available", "occupied", "processed", "terminated"]

    total_a, total_b = 0, 0
    country_a: Counter = Counter()
    country_b: Counter = Counter()

    print(f"{'Queue':<14} {'A':>8} {'B':>8} {'Δ':>8}")
    print("-" * 42)

    for queue in queues:
        urls_a = set(a.get(queue, []))
        urls_b = set(b.get(queue, []))
        ca, cb = len(urls_a), len(urls_b)
        total_a += ca
        total_b += cb
        for url in urls_a:
            m = COUNTRY_RE.search(url)
            if m:
                country_a[m.group(1)] += 1
        for url in urls_b:
            m = COUNTRY_RE.search(url)
            if m:
                country_b[m.group(1)] += 1
        delta = cb - ca
        sign = "+" if delta > 0 else ""
        print(f"  {queue:<12} {ca:>8} {cb:>8} {sign}{delta:>7}")

    delta_total = total_b - total_a
    sign = "+" if delta_total > 0 else ""
    print("-" * 42)
    print(f"  {'TOTAL':<12} {total_a:>8} {total_b:>8} {sign}{delta_total:>7}")

    all_countries = sorted(set(country_a) | set(country_b))
    if all_countries:
        print(f"\nBy country ({len(all_countries)} countries):")
        print(f"  {'Country':<8} {'A':>8} {'B':>8} {'Δ':>8}")
        print("  " + "-" * 36)
        for country in sorted(all_countries, key=lambda c: -(country_b[c] - country_a[c])):
            ca, cb = country_a[country], country_b[country]
            delta = cb - ca
            sign = "+" if delta > 0 else ""
            print(f"  {country:<8} {ca:>8} {cb:>8} {sign}{delta:>7}")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        analyze(sys.argv[1])
    elif len(sys.argv) == 3:
        compare(sys.argv[1], sys.argv[2])
    else:
        print("Usage:")
        print("  python analyzeCheckpoint.py <checkpoint.json>")
        print("  python analyzeCheckpoint.py <checkpoint_a.json> <checkpoint_b.json>")
        sys.exit(1)
