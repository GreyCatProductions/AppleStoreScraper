import threading
import time
import urllib.request


class ProxyState:
    AVAILABLE = "available"
    PAUSED = "paused"


class ProxyEntry:
    def __init__(self, url: str, pause_duration: float = 60.0):
        self.url = url
        self.state = ProxyState.AVAILABLE
        self.pause_duration = pause_duration
        self._resume_at: float = 0.0

    def pause(self):
        self.state = ProxyState.PAUSED
        self._resume_at = time.monotonic() + self.pause_duration

    def check_resume(self):
        if self.state == ProxyState.PAUSED and time.monotonic() >= self._resume_at:
            self.state = ProxyState.AVAILABLE


VALIDATION_URL = "https://www.apple.com"
VALIDATION_TIMEOUT = 10


def _is_valid_proxy(url: str) -> bool:
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": url, "https": url})
        )
        response = opener.open(VALIDATION_URL, timeout=VALIDATION_TIMEOUT)
        return response.status == 200
    except Exception:
        return False


class ProxyManager:
    def __init__(self, proxies: list[str], pause_duration: float = 60.0):
        self._lock = threading.Lock()
        valid = [url for url in proxies if _is_valid_proxy(url)]
        print(f"[ProxyManager] {len(valid)}/{len(proxies)} proxies passed validation")
        self._proxies = [ProxyEntry(url, pause_duration) for url in valid]

    def get_proxy(self) -> str | None:
        with self._lock:
            for entry in self._proxies:
                entry.check_resume()
                if entry.state == ProxyState.AVAILABLE:
                    return entry.url
            return None

    def report_blocked(self, proxy_url: str) -> None:
        with self._lock:
            for entry in self._proxies:
                if entry.url == proxy_url:
                    entry.pause()
                    break

    def available_count(self) -> int:
        with self._lock:
            for entry in self._proxies:
                entry.check_resume()
            return sum(1 for e in self._proxies if e.state == ProxyState.AVAILABLE)
