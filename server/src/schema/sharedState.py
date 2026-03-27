from dataclasses import dataclass
from enum import Enum
import threading
import csv
import os
from typing import Dict, List

class CompletionState(Enum):
    AVAILABLE = "available" #available and not processed
    OCCUPIED = "occupied" #currently getting processed
    PROCESSED = "processed" #processed successfully
    TERMINATED = "terminated" #failed so often it is terminated

MAX_RETRIES_OF_URL = 5 
@dataclass
class UrlTask:
    url: str
    retries: int = 0
    state: CompletionState = CompletionState.AVAILABLE

class SharedState:
    def __init__(self, csv_path: str, html_dir: str):
        self._lock = threading.Lock()
        self._tasks: Dict[str, UrlTask] = {}
        self._csv_path = csv_path
        self._csv_lock = threading.Lock()
        self._html_dir = html_dir
        self._csv_initialized = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        os.makedirs(html_dir, exist_ok=True)

    def add_url(self, url: str, force: bool) -> None:
        with self._lock:
            task = self._tasks.get(url)

            if not task or (task.state is not CompletionState.OCCUPIED and force):
                self._tasks[url] = UrlTask(url)
    
    def add_urls(self, urls: List[str], force: bool = False) -> int:
        success = 0
        with self._lock:
            for url in urls:
                task = self._tasks.get(url)

                if not task or (task.state is not CompletionState.OCCUPIED and force):
                    self._tasks[url] = UrlTask(url)
                    success += 1
        return success
            
    def get_url(self) -> str | None:
        with self._lock:
            for url, task in self._tasks.items():
                if task.state is CompletionState.AVAILABLE:
                    task.state = CompletionState.OCCUPIED
                    return url
            return None

    def has_urls(self) -> bool:
        with self._lock:
            return len(self._tasks) > 0

    def save_html(self, url: str, html: str) -> None:
        filename = url.replace("https://", "").replace("/", "_") + ".html"
        path = os.path.join(self._html_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    def mark_failed(self, url: str) -> None:
        with self._lock:
            task = self._tasks.get(url)
            if not task:
                return 
            
            task.state = CompletionState.AVAILABLE
            task.retries += 1
            
            if task.retries >= MAX_RETRIES_OF_URL:
                task.state = CompletionState.TERMINATED

    def mark_success(self, url: str) -> None:
        with self._lock:
            task = self._tasks.get(url)
            if not task:
                return 
            
            task.state = CompletionState.PROCESSED

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
            return len(self._tasks)

    def get_urls(self, state: CompletionState) -> list[str]:
        with self._lock:
            return [t.url for t in self._tasks.values() if t.state == state]

