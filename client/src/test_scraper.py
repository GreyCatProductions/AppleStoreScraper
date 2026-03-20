import glob
from pathlib import Path
from bs4 import BeautifulSoup
from pydantic import ValidationError
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from objects import TaskResult
from scraper import parse

HTML_FILE = glob.glob("../../*.html")[0]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        import requests
        from scraper import HEADERS
        url = sys.argv[1]
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
    else:
        url = HTML_FILE
        with open(HTML_FILE, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

    result = parse(url, soup)
    if not result:
        print("FAIL: parse() returned None")
        sys.exit(1)

    print("=== Parsed fields ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n=== TaskResult conversion ===")
    try:
        obj = TaskResult(**result)
        print("OK: all fields valid")
    except ValidationError as e:
        print("FAIL: validation errors:")
        for err in e.errors():
            print(f"  {err['loc']}: {err['msg']}")
