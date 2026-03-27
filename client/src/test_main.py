import sys
import os
import pprint
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scraper import scrapeApp, scrapeGrouping, scrapeCharts, scrapeRoom, scrapeDeveloperApps
from shared.logger import setup_logging

setup_logging()

TEST_URLS = [
    "https://apps.apple.com/us/app/hbo-max-filme-und-serien/id1666653815",
    "https://apps.apple.com/us/iphone/room/1439382985",
    "https://apps.apple.com/us/developer/peak-games/id476160947",
    "https://apps.apple.com/us/iphone/grouping/25164",
    "https://apps.apple.com/us/iphone/charts/7001?chart=top-free",
]

def scrape(url: str) -> dict:
    if "/iphone/room/" in url:
        return scrapeRoom(url).model_dump()
    elif "/developer/" in url:
        return scrapeDeveloperApps(url).model_dump()
    elif "/iphone/grouping/" in url:
        return scrapeGrouping(url).model_dump()
    elif "/iphone/charts/" in url:
        return scrapeCharts(url).model_dump()
    else:
        return scrapeApp(url).model_dump()

if __name__ == "__main__":
    urls = sys.argv[1:] or TEST_URLS
    for url in urls:
        print(f"\n--- {url} ---")
        try:
            result = scrape(url)
            html = result.pop("html", None)
            pprint.pprint(result)
            print(f"html length: {len(html) if html else 0}")
        except Exception as e:
            print(f"FAIL: {e}")
