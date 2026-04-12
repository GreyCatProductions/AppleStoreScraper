import sys
import json
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bs4 import BeautifulSoup
from parser import extractAppData

if len(sys.argv) < 2:
    print("Usage: python parse_file.py <path_to_html_file>")
    sys.exit(1)

path = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else path

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
result = extractAppData(url, soup)

print(json.dumps(result, indent=2, ensure_ascii=False))
