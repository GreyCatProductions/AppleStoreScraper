import threading
import csv
import os


class SharedState:
    def __init__(self, csv_path: str, html_dir: str):
        self._lock = threading.Lock()
        self._urls: set[str] = set()
        self._completed_urls: set[str] = set()
        self._failed_urls: set[str] = set()
        self._csv_path = csv_path
        self._csv_lock = threading.Lock()
        self._html_dir = html_dir
        self._csv_initialized = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        os.makedirs(html_dir, exist_ok=True)

    def add_url(self, url: str) -> None:
        with self._lock:
            self._urls.add(url)
            
    def pop_url(self) -> str | None:
        with self._lock:
            return self._urls.pop() if self._urls else None

    def has_urls(self) -> bool:
        with self._lock:
            return len(self._urls) > 0
        
    def enqueue_urls(self, urls: list[str]) -> int:
        with self._lock:
            seen = self._urls | self._completed_urls | self._failed_urls
            new = [u for u in urls if u not in seen]
            self._urls.update(new)
            return len(new)

    def save_html(self, url: str, html: str) -> None:
        filename = url.replace("https://", "").replace("/", "_") + ".html"
        path = os.path.join(self._html_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    def mark_failed(self, url: str) -> None:
        with self._lock:
            self._failed_urls.add(url)

    def write_row(self, row: dict) -> None:
        with self._lock:
            self._completed_urls.add(row.get("url", ""))
        with self._csv_lock:
            fields = list(row.keys())
            write_header = not self._csv_initialized
            with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                if write_header:
                    writer.writeheader()
                    self._csv_initialized = True
                writer.writerow(row)

    def get_url_count(self) -> int:
        with self._lock:
            return len(self._urls)

    def get_failed_urls(self) -> list[str]:
        with self._lock:
            return list(self._failed_urls)
        
    def get_completed_urls(self) -> list[str]:
        with self._lock:
            return list(self._completed_urls)
