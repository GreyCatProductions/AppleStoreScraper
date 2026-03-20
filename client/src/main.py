import time
import requests
from scraper import scrape
from shared.logger import get_logger, setup_logging

SERVER_URL = "http://localhost:8000"
TASK_WAIT_INTERVAL = 60  
SCRAPE_RETRIES = 3
SCRAPE_RETRY_DELAY = 60


setup_logging()
log = get_logger(__name__)

def request_task() -> str | None:
    response = requests.get(f"{SERVER_URL}/task")
    response.raise_for_status()
    return response.json().get("url")


def complete_task(result: dict) -> None:
    response = requests.post(f"{SERVER_URL}/task/complete", json=result)
    response.raise_for_status()


def report_failed(url: str) -> None:
    response = requests.post(f"{SERVER_URL}/task/failed", json={"url": url})
    response.raise_for_status()


def run():
    log.info("Starting worker...")

    while True:
        try:
            url = request_task()
        except requests.ConnectionError:
            log.error("Cannot reach server, retrying...")
            time.sleep(TASK_WAIT_INTERVAL)
            continue
        except requests.Timeout:
            log.error("Server timed out on task request, retrying...")
            time.sleep(TASK_WAIT_INTERVAL)
            continue
        except requests.HTTPError as e:
            log.error(f"Server returned error on task request: {e}")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        if not url:
            log.info("No task received, waiting...")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        log.info(f"Scraping: {url}")
        result = None
        for attempt in range(1, SCRAPE_RETRIES + 1):
            try:
                result = scrape(url)
                break
            except Exception as e:
                log.warning(f"Scrape attempt {attempt}/{SCRAPE_RETRIES} failed for {url}: {e}")
                if attempt < SCRAPE_RETRIES:
                    time.sleep(SCRAPE_RETRY_DELAY)
        if result is None:
            log.error(f"All {SCRAPE_RETRIES} scrape attempts failed for {url}, reporting to server")
            try:
                report_failed(url)
            except Exception as e:
                log.error(f"Could not report failed URL to server: {e}")
            continue

        try:
            complete_task(result)
            log.info(f"Done: {result['title']}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
