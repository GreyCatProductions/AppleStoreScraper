import urllib
import urllib.request

VALIDATION_URL = "https://www.apple.com"
VALIDATION_TIMEOUT = 10


def isUrlReachable(url: str) -> bool:
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": url, "https": url})
        )
        response = opener.open(VALIDATION_URL, timeout=VALIDATION_TIMEOUT)
        return response.status == 200
    except Exception:
        return False