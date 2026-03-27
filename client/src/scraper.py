import json
import re
from typing import List
import requests
from bs4 import BeautifulSoup

from client.src.parser import extractAppData, extractAppRefs, extractMoreByDevRefs, extractRoomRefs

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
def scrapeApp(url: str) -> dict:
    soup = _fetch_soup(url)
    found_urls = list(set(extractAppRefs(soup) + extractRoomRefs(soup) + extractMoreByDevRefs(soup)))
    return {**(extractAppData(url, soup) or {}), "found_urls": found_urls, "html": str(soup)}


# For urls like https://apps.apple.com/us/iphone/room/1439382985
def scrapeRoom(url: str) -> dict:
    soup = _fetch_soup(url)
    return {"found_urls": list(set(extractAppRefs(soup))), "html": str(soup)}


# For urls like https://apps.apple.com/us/developer/peak-games/id476160947
def scrapeDeveloperApps(url: str) -> dict:
    soup = _fetch_soup(url)
    return {"found_urls": list(set(extractAppRefs(soup))), "html": str(soup)}