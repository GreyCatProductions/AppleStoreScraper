import threading
import csv
import os


class SharedState:
    CSV_FIELDS = ["url", "title", "price", "rating", "reviews"]

    def __init__(self, csv_path: str):
        self._lock = threading.Lock()
        self._urls: set[str] = set()
        self._completed_urls: set[str] = set()
        self._failed_urls: set[str] = set()
        self._csv_path = csv_path
        self._csv_lock = threading.Lock()
        
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_FIELDS)

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

    def mark_failed(self, url: str) -> None:
        with self._lock:
            self._failed_urls.add(url)

    def write_row(self, row: dict) -> None:
        with self._lock:
            self._completed_urls.add(row["url"])
        with self._csv_lock:
            with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
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
