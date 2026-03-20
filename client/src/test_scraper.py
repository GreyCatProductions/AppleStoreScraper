import sys
import glob
from pathlib import Path
from bs4 import BeautifulSoup
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from objects import TaskResult
from scraper import parse

HTML_FILE = glob.glob("../../*.html")[0]


if __name__ == "__main__":
    with open(HTML_FILE, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    result = parse(HTML_FILE, soup)
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
