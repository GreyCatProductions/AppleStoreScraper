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
    data = json.loads(script.string)

    app_name = _get(data, "name")
    developer = _get(data, "author", "name")
    category = _get(data, "applicationCategory")
    price = f"{_get(data, 'offers', 'price')} {_get(data, 'offers', 'priceCurrency')}"
    review_average = _get(data, "aggregateRating", "ratingValue")
    review_count = _get(data, "aggregateRating", "reviewCount")
    description = _get(data, "description")

    bars = soup.select("[data-testid^='star-row-']")
    ratings: List[int] = [0] * 5
    try:
        total = int(review_count) if review_count else 0
    except (ValueError, TypeError):
        total = 0
    for bar in bars:
        try:
            stars = int(str(bar.get("data-testid", "")).split("-")[-1])
            m = re.search(r"(\d+)%", str(bar.get("style", "")))
            if m and 1 <= stars <= 5:
                pct = int(m.group(1))
                ratings[stars - 1] = round(pct / 100 * total)
        except (ValueError, IndexError):
            pass
    
    try:
        size_text = _findDt(soup, "size", "größe").find_next("dd").get_text(strip=True)  # type: ignore
        size = sizeToBytes(size_text)
    except AttributeError:
        size = None

    try:
        dd = _findDt(soup, "languages", "sprachen").find_next("dd")  # type: ignore
        li = dd.find("li")
        raw = (li or dd).get_text(strip=True)
        languages: List[str] = [l.strip() for l in raw.split(",") if l.strip()]
    except AttributeError:
        languages = []

    try:
        items = _findDt(soup, "in\u2011app purchases", "in-app-käufe").find_next("details").select("ul li")  # type: ignore
        in_app_purchases = "|".join(b.get_text("\n", strip=True) for b in items) or None
    except AttributeError:
        in_app_purchases = None

    try:
        age_restriction = (
            _findDt(soup, "age classification", "altersfreigabe")
            .find_next(
                lambda n: n.name in ("div", "span")
                and n.get_text(strip=True)
                and "Altersfreigabe" not in n.get_text()
                and "Age Classification" not in n.get_text()
            )
            .get_text(strip=True)
        )
    except AttributeError:
        age_restriction = None

    try:
        age_details = _findDt(soup, "age classification", "altersfreigabe").find_next("details")  # type: ignore
        age_restriction_reasons = []
        for li in age_details.select("ul li"):
            if li.find(class_="text-encapsulation") or li.find(class_="button-wrapper") or li.find(class_="spacer"):
                continue
            for br in li.find_all("br"):
                br.replace_with("\n")
            lines = [l.strip() for l in li.get_text().splitlines() if l.strip()]
            age_restriction_reasons.extend(lines)
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

    privacy_section = soup.find(id="privacyHeader")

    def _privacy_items(key: str) -> list[str]:
        try:
            container = privacy_section.find(
                "div", attrs={"aria-label": lambda v: v and v.strip() in PRIVACY_LABELS[key]}
            )
            if not container:
                print(f"[extractor] WARNING: privacy label '{key}' not found in {url}")
                return []
            items = container.select("ul.privacy-data-types li") or container.select("ul li")
            return list(dict.fromkeys(li.get_text(" ", strip=True) for li in items if li.get_text(strip=True)))
        except AttributeError:
            return []

    linked = _privacy_items("linked")
    unlinked = _privacy_items("unlinked")
    tracked = _privacy_items("tracked")
    not_collected = bool(
        privacy_section.find("h3", string=lambda s: s and s.strip() in PRIVACY_LABELS["not_collected"])
    )


    found_urls = extractAppRefs(soup=soup)
    
    version_history = []
    try:
        script = next(
            el for el in soup.find_all("script")
            if el.string and "versionHistory" in el.string
        )
        text = str(script.string)
        m = re.search(r'\{"data":\[', text)
        if m:
            blob = json.loads(text[m.start():])
            def _find_version_page(obj):
                if isinstance(obj, dict):
                    if obj.get("page") == "versionHistory":
                        return obj
                    for v in obj.values():
                        r = _find_version_page(v)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for i in obj:
                        r = _find_version_page(i)
                        if r:
                            return r
            vp = _find_version_page(blob)
            if vp:
                for item in vp.get("pageData", {}).get("shelves", [{}])[0].get("items", []):
                    version = item.get("primarySubtitle")
                    date = item.get("secondarySubtitle")
                    notes = item.get("text")
                    if version:
                        version_history.append({"version": version, "date": date, "notes": notes})
    except StopIteration:
        pass
    
    try:
        privacy_policy_link = next(
            str(a["href"])
            for a in soup.find_all("a", href=True)
            if ("privacy" in a.get_text(strip=True).lower() or "datenschutz" in a.get_text(strip=True).lower())
            and "apple.com" not in str(a["href"])
            and not str(a["href"]).startswith("#")
        )
    except StopIteration:
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
        #"versions": versions,
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
