import threading
import csv
import os


class SharedState:
    CSV_FIELDS = ["url", "title", "price", "rating", "reviews"]

    def __init__(self, csv_path: str):
        self._lock = threading.Lock()
        self._urls: list[str] = []
        self._csv_path = csv_path
        self._csv_lock = threading.Lock()

        # Initialize CSV
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_FIELDS)

    def add_url(self, url: str) -> None:
        with self._lock:
            self._urls.append(url)

    def add_urls(self, urls: list[str]) -> None:
        with self._lock:
            self._urls.extend(urls)

    def pop_url(self) -> str | None:
        with self._lock:
            return self._urls.pop(0) if self._urls else None

    def has_urls(self) -> bool:
        with self._lock:
            return len(self._urls) > 0

    def url_count(self) -> int:
        with self._lock:
            return len(self._urls)
        
    def write_row(self, row: dict) -> None:
        with self._csv_lock:
            with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                writer.writerow(row)
