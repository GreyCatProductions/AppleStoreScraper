import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = _text(soup.select_one("h1.product-header__title"))
    price = _text(soup.select_one("[class*='price']"))
    rating = _text(soup.select_one("[class*='rating']"))
    reviews = _text(soup.select_one("[class*='review-count']"))

    return {
        "url": url,
        "title": title,
        "price": price,
        "rating": rating,
        "reviews": reviews,
    }


def _text(element) -> str:
    return element.get_text(strip=True) if element else ""
