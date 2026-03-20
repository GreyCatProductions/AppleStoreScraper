import json
import re
import requests
from bs4 import BeautifulSoup

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


def _find_dt(soup: BeautifulSoup, *labels: str):
    return soup.find("dt", string=lambda s: s and s.strip().lower() in labels)  # type: ignore


def _get(data, *keys):
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        return None


def sizeToBytes(txt: str) -> int:
    s = txt.replace("\xa0", " ").replace(",", ".").strip()

    s = s.replace(" K B", " KB").replace(" M B", " MB").replace(" G B", " GB")
    s = s.replace("KB", " KB").replace("MB", " MB").replace("GB", " GB")

    parts = s.split()
    if not parts:
        return 0
    num = parts[0]
    unit = parts[1].upper() if len(parts) > 1 else "B"

    v = float(num)
    mult = {"B": 1, "KB": 1_000, "MB": 1_000_000, "GB": 1_000_000_000}
    return int(v * mult.get(unit, 1))


def parse(url: str, soup: BeautifulSoup) -> dict | None:
    script = soup.find("script", id="software-application", type="application/ld+json")
    if not script or not script.string:
        return None
    data = json.loads(script.string)

    app_name = _get(data, "name")
    developer = _get(data, "author", "name")
    category = _get(data, "applicationCategory")
    price = f"{_get(data, 'offers', 'price')} {_get(data, 'offers', 'priceCurrency')}"
    review_average = _get(data, "aggregateRating", "ratingValue")
    review_count = _get(data, "aggregateRating", "reviewCount")
    description = _get(data, "description")

    ratings: list[int | None] = [None] * 5
    for el in soup.select("[class*=numbers__star-graph__row]"):
        try:
            m = re.match(r"(\d) star, (\d+)%", str(el.get("aria-label", "")))
            if m:
                stars, percent = int(m.group(1)), int(m.group(2))
                if 1 <= stars <= 5:
                    ratings[stars - 1] = percent
        except (ValueError, IndexError):
            pass

    try:
        languages = _find_dt(soup, "languages", "sprachen").find_next("details").select_one("ul li .styled-text").get_text(strip=True)  # type: ignore
    except AttributeError:
        languages = None

    try:
        size_text = _find_dt(soup, "size", "größe").find_next("ul").select_one("li .styled-text").get_text(strip=True)  # type: ignore
        size = sizeToBytes(size_text)
    except AttributeError:
        size = None

    try:
        blocks = _find_dt(soup, "kompatibilität", "compatibility").find_next("details").select("ul li .styled-text")  # type: ignore
        versions = "|".join(b.get_text("\n", strip=True) for b in blocks) or None
    except AttributeError:
        versions = None

    try:
        items = _find_dt(soup, "in\u2011app purchases", "in-app-käufe").find_next("details").select("ul li")  # type: ignore
        in_app_purchases = "|".join(b.get_text("\n", strip=True) for b in items) or None
    except AttributeError:
        in_app_purchases = None

    try:
        age_restriction = (
            _find_dt(soup, "age rating", "altersfreigabe")
            .find_next(
                lambda n: n.name in ("div", "span")
                and n.get_text(strip=True)
                and "Altersfreigabe" not in n.get_text()
                and "Age Rating" not in n.get_text()
            )
            .get_text(strip=True)
        )
    except AttributeError:
        age_restriction = None

    try:
        age_restriction_reasons = _find_dt(
            soup, "age rating", "altersfreigabe"
        ).find_next("details")
        age_restriction_reasons = [
            li.get_text(" ", strip=True)
            for li in age_restriction_reasons.select("ul li")
        ]
    except AttributeError:
        age_restriction_reasons = None

    PRIVACY_LABELS = {
        "linked": ("Data Linked to You", "Mit dir verknüpfte Daten"),
        "unlinked": ("Data Not Linked to You", "Nicht mit dir verknüpfte Daten"),
        "tracked": (
            "Data Used to Track You",
            "Daten, die zum Tracking deiner Person verwendet werden",
        ),
        "not_collected": ("Data Not Collected", "Keine Daten erfasst"),
    }

    def _privacy_items(key: str) -> list[str]:
        try:
            ul = soup.find_all("h2", string=lambda s: s and s.strip() in PRIVACY_LABELS[key])[1].find_next("ul")  # type: ignore
            return [li.get_text(" ", strip=True) for li in ul.select("li")]
        except (AttributeError, IndexError):
            return []

    linked = _privacy_items("linked")
    unlinked = _privacy_items("unlinked")
    tracked = _privacy_items("tracked")
    not_collected = bool(soup.find("h2", string=lambda s: s and s.strip() in PRIVACY_LABELS["not_collected"]))  # type: ignore

    found_urls = [
        href
        for a in soup.find_all("a", href=True)
        if re.match(
            r"https://apps\.apple\.com/[a-z]{2}/app/.+/id\d+$", href := str(a["href"])
        )
    ]
    
    lis = soup.select('dialog ul li')
    VERSION_RE = re.compile(r"\b(?:Version\s*)?(\d+\.\d+(?:\.\d+)?)\b")
    version_history = []
    for li in lis:
        heading = li.find(["h3", "h4", "h5"])
        time = li.find("time")
        notes = li.find("p")
        m = VERSION_RE.search((heading.get_text(" ", strip=True) if heading else ""))
        if m and time:
            version_history.append({
                "version": m.group(1),
                "date": time.get("datetime") or time.get_text(strip=True),
                "notes": notes.get_text(" ", strip=True) if notes else None
            })
    
    try:
        privacy_policy_link = \
        soup.find("a", string=lambda s: s and ("datenschutz" in s.lower() or "privacy policy" in s.lower()))["href"] # type: ignore
    except (AttributeError, TypeError):
        privacy_policy_link = "None"

    return {
        "url": url,
        "app_name": app_name,
        "developer_name": developer,
        "category": category,
        "price": price,
        "description": description,
        "similar_apps": found_urls,
        "review_count": review_count,
        "review_average": review_average,
        "review_one": ratings[0],
        "review_two": ratings[1],
        "review_three": ratings[2],
        "review_four": ratings[3],
        "review_five": ratings[4],
        "versions": versions,
        "size": size,
        "languages": languages,
        "age": age_restriction,
        "age_reasons": age_restriction_reasons or [],
        "privacy_linked": linked,
        "privacy_unlinked": unlinked,
        "privacy_tracked": tracked,
        "privacy_not_collected": str(not_collected),
        "version_history": version_history,
        "in_app_purchases": in_app_purchases,
        "privacy_policy_link": privacy_policy_link,
    }


def scrape(url: str) -> dict | None:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    return parse(url, soup)
