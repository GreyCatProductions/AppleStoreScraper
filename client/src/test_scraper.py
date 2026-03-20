import glob
from bs4 import BeautifulSoup
from scraper import parse

HTML_FILE = glob.glob("../../*.html")[0]


if __name__ == "__main__":
    with open(HTML_FILE, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    result = parse(HTML_FILE, soup)
    if result:
        for k, v in result.items():
            print(f"{k}: {v}")
