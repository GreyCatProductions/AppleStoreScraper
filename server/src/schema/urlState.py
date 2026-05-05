from dataclasses import dataclass, field
import threading
import csv
import os
import time
from typing import Dict, List

MAX_RETRIES_OF_URL = 5

@dataclass
class UrlTask:
    url: str
    retries: int = 0
    assigned_at: float | None = None

class UrlState:
    def __init__(self, csv_path: str, html_dir: str):
        self._lock = threading.Lock()
        self._available: Dict[str, UrlTask] = {}
        self._occupied: Dict[str, UrlTask] = {}
        self._processed: Dict[str, UrlTask] = {}
        self._terminated: Dict[str, UrlTask] = {}
        self._csv_path = csv_path
        self._csv_lock = threading.Lock()
        self._html_dir = html_dir
        self._csv_initialized = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        os.makedirs(html_dir, exist_ok=True)

    def _find_url(self, url: str) -> Dict[str, UrlTask] | None:
        for d in (self._available, self._occupied, self._processed, self._terminated):
            if url in d:
                return d
        return None

    def add_url(self, url: str, force: bool = False) -> bool:
        with self._lock:
            d = self._find_url(url)
            if not d:
                self._available[url] = UrlTask(url)
                return True
            elif force and d is not self._occupied:
                self._available[url] = d.pop(url)
                self._available[url].retries = 0
                return True
            return False

    def add_urls(self, urls: List[str], force: bool = False) -> int:
        success = 0
        with self._lock:
            for url in urls:
                d = self._find_url(url)
                if not d:
                    self._available[url] = UrlTask(url)
                    success += 1
                elif force and d is not self._occupied:
                    self._available[url] = d.pop(url)
                    self._available[url].retries = 0
                    success += 1
        return success

    def get_url(self) -> str | None:
        with self._lock:
            if not self._available:
                return None
            url, task = next(iter(self._available.items()))
            del self._available[url]
            task.assigned_at = time.time()
            self._occupied[url] = task
            return url

    def get_timed_out(self, timeout: float) -> list[str]:
        now = time.time()
        with self._lock:
            return [
                url
                for url, task in self._occupied.items()
                if task.assigned_at is not None and (now - task.assigned_at) >= timeout
            ]

    def reset_assigned_at(self, url: str) -> bool:
        with self._lock:
            task = self._occupied.get(url)
            if task is None:
                return False
            task.assigned_at = time.time()
            return True

    def requeue_url(self, url: str) -> bool:
        with self._lock:
            task = self._occupied.pop(url, None)
            if task is None:
                return False
            task.assigned_at = None
            self._available[url] = task
            return True

    def has_urls(self) -> bool:
        with self._lock:
            return bool(self._available or self._occupied)

    def save_html(self, url: str, html: str) -> None:
        filename = url.replace("https://", "").replace("/", "_") + ".html"
        path = os.path.join(self._html_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    def mark_failed(self, url: str) -> None:
        with self._lock:
            task = self._occupied.pop(url, None)
            if not task:
                return
            task.retries += 1
            if task.retries >= MAX_RETRIES_OF_URL:
                self._terminated[url] = task
            else:
                self._available[url] = task

    def mark_success(self, url: str) -> None:
        with self._lock:
            task = self._occupied.pop(url, None)
            if not task:
                return
            self._processed[url] = task

    def write_row(self, row: dict) -> None:
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
            return len(self._available) + len(self._occupied) + len(self._processed) + len(self._terminated)

    def get_available_urls(self) -> list[str]:
        with self._lock:
            return list(self._available.keys())

    def get_occupied_urls(self) -> list[str]:
        with self._lock:
            return list(self._occupied.keys())

    def get_processed_urls(self) -> list[str]:
        with self._lock:
            return list(self._processed.keys())

    def get_terminated_urls(self) -> list[str]:
        with self._lock:
            return list(self._terminated.keys())

    def load_from_checkpoint(self, available: list[str], occupied: list[str], processed: list[str], terminated: list[str]) -> dict:
        with self._lock:
            self._available.clear()
            self._occupied.clear()
            self._processed.clear()
            self._terminated.clear()
            for url in available:
                self._available[url] = UrlTask(url)
            for url in occupied:
                self._available[url] = UrlTask(url)
            for url in processed:
                self._processed[url] = UrlTask(url)
            for url in terminated:
                self._terminated[url] = UrlTask(url)
        return {
            "available": len(self._available),
            "processed": len(self._processed),
            "terminated": len(self._terminated),
        }

    def merge_from_checkpoint(self, available: list[str], occupied: list[str], processed: list[str], terminated: list[str]) -> dict:
        added = {"available": 0, "processed": 0, "terminated": 0}
        with self._lock:
            for url in available + occupied:
                if not self._find_url(url):
                    self._available[url] = UrlTask(url)
                    added["available"] += 1
            for url in processed:
                if not self._find_url(url):
                    self._processed[url] = UrlTask(url)
                    added["processed"] += 1
            for url in terminated:
                if not self._find_url(url):
                    self._terminated[url] = UrlTask(url)
                    added["terminated"] += 1
        return added
