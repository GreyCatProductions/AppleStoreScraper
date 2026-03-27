import os
from schema.sharedState import SharedState

CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), "categories")


class Crawler:
    def __init__(self, state: SharedState):
        self._state = state
        self.fillFromList()

    def fillFromList(self):
        with open(CATEGORIES_FILE) as f:
            urls = [line.strip() for line in f if line.strip()]
        self._state.enqueue_urls(urls)
