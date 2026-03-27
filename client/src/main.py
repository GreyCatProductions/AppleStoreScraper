import os
import time
import requests
from scraper import scrapeUniversal
from shared.logger import get_logger, setup_logging
from dotenv import load_dotenv
from shared.objects import FailedTask, TaskResult

load_dotenv()
host = os.getenv("HOST")
port_raw = os.getenv("PORT")
server_ip = os.getenv("SERVER_IP")

if not host or not port_raw or not server_ip:
    raise Exception("HOST or PORT or server_ip are missing in .env!")

SERVER_URL = f"http://{server_ip}:{int(port_raw)}"
TASK_WAIT_INTERVAL = 60
SCRAPE_RETRIES = 3
SCRAPE_RETRY_DELAY = 5 


setup_logging()
log = get_logger(__name__)

def request_task() -> str | None:
    response = requests.get(f"{SERVER_URL}/task")
    response.raise_for_status()
    return response.json().get("url")


def complete_task(result: TaskResult) -> None:
    response = requests.post(f"{SERVER_URL}/task/complete", json=result.model_dump())
    response.raise_for_status()

def report_failed(url: str) -> None:
    obj = FailedTask(url=url)
    response = requests.post(f"{SERVER_URL}/task/failed", json=obj.model_dump())
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
        except Exception as e:
            log.error(f"Server returned unexpected error on task request: {e}")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        if not url:
            log.info(f"No tasks available, waiting {TASK_WAIT_INTERVAL}s...")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        log.info(f"Scraping: {url} of type")
        result: TaskResult | None = None

        for attempt in range(1, SCRAPE_RETRIES + 1):
            try:
                result = scrapeUniversal(url)

                count = len(result.foundUrls) if result.foundUrls else 0
                log.debug(f"Successfully extracted data from {url}. Found {count} URLs")
                break
            except Exception as e:
                log.warning(f"Attempt {attempt}/{SCRAPE_RETRIES} failed for {url}: {e}")
                if attempt < SCRAPE_RETRIES:
                    time.sleep(SCRAPE_RETRY_DELAY * attempt)  # exponential backoff

        if result is None:
            log.warning(f"All {SCRAPE_RETRIES} attempts failed for {url}. Reporting as failed")
            try:
                report_failed(url)
            except Exception as e:
                log.error(f"Could not report failed URL to server: {e}")
            continue

        time.sleep(SCRAPE_RETRY_DELAY)
        try:
            complete_task(result)
            log.info(f"Done: {url}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
