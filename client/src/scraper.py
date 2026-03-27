import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import requests
from bs4 import BeautifulSoup

from parser import extractAppData, extractAppRefs, extractMoreByDevRefs, extractRoomRefs
from shared.objects import AppData, TaskResult

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.7",
    "Origin": "https://apps.apple.com",
    "Referer": "https://apps.apple.com/",
    "Sec-Ch-Ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Brave";v="146"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Gpc": "1",
}

TIMEOUT = 15


def _fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    return soup

# For urls like https://apps.apple.com/us/app/nyt-games-wordle-crossword/id307569751
def scrapeApp(url: str) -> TaskResult:
    soup = _fetch_soup(url)
    found_urls = list(set(extractAppRefs(soup) + extractRoomRefs(soup) + extractMoreByDevRefs(soup)))
    raw = extractAppData(url, soup) or {}
    app_data = AppData(**raw) if raw else None
    return TaskResult(processed_url=url, appData=app_data, html=str(soup), foundUrls=found_urls)


# For urls like https://apps.apple.com/us/iphone/room/1439382985
def scrapeRoom(url: str) -> TaskResult:
    soup = _fetch_soup(url)
    found_urls = list(set(extractAppRefs(soup)))
    return TaskResult(processed_url=url, appData=None, html=None, foundUrls=found_urls)


# For urls like https://apps.apple.com/us/developer/peak-games/id476160947
def scrapeDeveloperApps(url: str) -> TaskResult:
    soup = _fetch_soup(url)
    found_urls = list(set(extractAppRefs(soup)))
    return TaskResult(processed_url=url, appData=None, html=None, foundUrls=found_urls)

#For urls like https://apps.apple.com/us/iphone/grouping/25164
def scrapeGrouping(url: str) -> TaskResult:
    soup = _fetch_soup(url)
    found_urls = list(set(extractAppRefs(soup) + extractRoomRefs(soup) + extractMoreByDevRefs(soup)))
    return TaskResult(processed_url=url, appData=None, html=None, foundUrls=found_urls)