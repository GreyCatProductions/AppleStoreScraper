import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import requests
from bs4 import BeautifulSoup

from parser import extractAppData, extractAppRefs, extractChartRefs, extractMoreByDevRefs, extractRoomRefs
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

def scrapeUniversal(url: str) -> TaskResult:
    soup = _fetch_soup(url)
    raw = extractAppData(url, soup) or {}
    app_data = AppData(**raw) if raw else None
    found_urls = list(set(extractAppRefs(soup) + extractRoomRefs(soup) + extractMoreByDevRefs(soup) + extractChartRefs(soup)))
    return TaskResult(processed_url=url, appData=app_data, html=str(soup), foundUrls=found_urls)