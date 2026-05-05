import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.objects import DriveId

class googleDrive:
    def __init__(self):
        self._lock = threading.Lock()
        self._available: list[DriveId] = []
        self._full: list[DriveId] = []

    def add(self, driveId: DriveId) -> bool:
        with self._lock:
            if driveId in self._available or driveId in self._full:
                return False
            self._available.append(driveId)
            return True

    def mark_full(self, driveId: DriveId) -> bool:
        with self._lock:
            if driveId not in self._available:
                return False
            self._available.remove(driveId)
            self._full.append(driveId)
            return True
        
    def next_available(self) -> DriveId | None:
        with self._lock:
            return self._available[0] if self._available else None

    def count_available(self) -> int:
        with self._lock:
            return len(self._available)

