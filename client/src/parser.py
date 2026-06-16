import json
import re
from typing import List

from bs4 import BeautifulSoup


def _findDt(soup: BeautifulSoup, *labels: str):
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

def extractAppRefs(soup: BeautifulSoup) -> List[str]:
    return [
        href
        for a in soup.find_all("a", href=True)
        if re.match(
            r"https://apps\.apple\.com/[a-z]{2}/app/.+/id\d+$", href := str(a["href"])
        )
    ]

def extractRoomRefs(soup: BeautifulSoup) -> List[str]:
    return [
        href
        for a in soup.find_all("a", href=True)
        if re.match(
            r"https://apps\.apple\.com/[a-z]{2}/iphone/room/\d+", href := str(a["href"])
        )
    ]

def extractMoreByDevRefs(soup: BeautifulSoup) -> List[str]:
    return [
        href
        for a in soup.find_all("a", href=True)
        if re.match(
            r"https://apps\.apple\.com/[a-z]{2}/developer/[^/\"'\s]+/room/id\d+", href := str(a["href"])
        )
    ]

def extractChartRefs(soup: BeautifulSoup) -> List[str]:
    return [
        href
        for a in soup.find_all("a", href=True)
        if re.match(
            r"https://apps\.apple\.com/[a-z]{2}/iphone/charts/[^/\"'\s]+", href := str(a["href"])
        )
    ]

def extractAppData(url: str, soup: BeautifulSoup) -> dict | None:
    script = soup.find("script", id="software-application", type="application/ld+json")
    if not script or not script.string:
        return None
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return None

    app_name = _get(data, "name")
    developer = _get(data, "author", "name")
    category = _get(data, "applicationCategory")
    _price, _currency = _get(data, "offers", "price"), _get(data, "offers", "priceCurrency")
    price = f"{_price} {_currency}" if _price is not None and _currency is not None else None
    review_average = _get(data, "aggregateRating", "ratingValue")
    review_count = _get(data, "aggregateRating", "reviewCount")
    description = _get(data, "description")

    ratings: list[int] = [0] * 5
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
        languages = _findDt(soup, "languages", "sprachen").find_next("dd").select_one("li").get_text(strip=True)  # type: ignore
    except AttributeError:
        languages = None

    try:
        size_text = _findDt(soup, "size", "größe").find_next("ul").select_one("li").get_text(strip=True)  # type: ignore
        size = sizeToBytes(size_text)
    except (AttributeError, ValueError):
        size = None

    try:
        blocks = [b for b in _findDt(soup, "kompatibilität", "compatibility").find_next("details").select("ul li") if b.get_text(strip=True)]  # type: ignore
        versions = "|".join(b.get_text(" ", strip=True) for b in blocks) or None
    except AttributeError:
        versions = None

    try:
        items = _findDt(soup, "in-app purchases", "in-app-käufe").find_next("details").select("ul li")  # type: ignore
        in_app_purchases = "|".join(b.get_text(" ", strip=True) for b in items) or None
    except AttributeError:
        in_app_purchases = None

    try:
        age_restriction = (
            _findDt(soup, "age rating", "altersfreigabe")
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
        age_restriction_reasons = _findDt(
            soup, "age rating", "altersfreigabe"
        ).find_next("details")
        age_restriction_reasons = [
            li.get_text(" ", strip=True)
            for li in age_restriction_reasons.select("ul li")
            if li.get_text(strip=True) != "" and "Learn More" not in li.get_text()
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

    # privacy headings are h3; linked/unlinked use li.purpose-category, tracked uses plain ul li
    def _privacy_items(key: str) -> list[str]:
        try:
            h3 = soup.find("h3", string=lambda s: s and s.strip() in PRIVACY_LABELS[key])  # type: ignore
            if not h3:
                return []
            container = h3.find_parent("div")
            items = container.select("li.purpose-category") or container.select("ul li")  # type: ignore
            return [li.get_text(" ", strip=True) for li in items if li.get_text(strip=True)]
        except AttributeError:
            return []

    linked = _privacy_items("linked")
    unlinked = _privacy_items("unlinked")
    tracked = _privacy_items("tracked")
    not_collected = bool(soup.find("h3", string=lambda s: s and s.strip() in PRIVACY_LABELS["not_collected"]))  # type: ignore

    found_urls = extractAppRefs(soup=soup)

    lis = soup.select('dialog ul li')
    VERSION_RE = re.compile(r"\b(?:Version\s*)?(\d+\.\d+(?:\.\d+)?)\b")
    version_history = []
    for li in lis:
        metadata = li.select_one("div.metadata")
        time_el = li.find("time")
        notes = li.find("p")
        if not metadata or not time_el:
            continue
        version_span = metadata.find("span")
        if not version_span:
            continue
        m = VERSION_RE.search(version_span.get_text(strip=True))
        if m:
            version_history.append({
                "version": m.group(1),
                "date": time_el.get("datetime") or time_el.get_text(strip=True),
                "notes": notes.get_text(" ", strip=True) if notes else None
            })

    try:
        privacy_policy_link = \
        soup.find("a", string=lambda s: s and ("datenschutz" in s.lower() or "privacy policy" in s.lower()))["href"] # type: ignore
    except (AttributeError, TypeError):
        privacy_policy_link = None

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
