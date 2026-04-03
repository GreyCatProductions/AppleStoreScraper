import os
import random
import time
import requests
from scraper import scrapeUniversal
from shared.logger import get_logger, setup_logging
from dotenv import load_dotenv
from shared.objects import FailedTask, TaskResult
from googledrive import GoogleDriveClient

load_dotenv()
host = os.getenv("HOST")
port_raw = os.getenv("PORT")
server_ip = os.getenv("SERVER_IP")
google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

if not host or not port_raw or not server_ip:
    raise Exception("HOST or PORT or server_ip are missing in .env!")

if not google_drive_folder_id:
    raise Exception("GOOGLE_DRIVE_FOLDER_ID missing in .env!")

SERVER_URL = f"http://{server_ip}:{int(port_raw)}"

_DEFAULT_CONFIG = {
    "task_wait_interval": 60,
    "scrape_retries": 3,
    "scrape_retry_delay": 5,
    "scrape_retry_delay_variation": 2,
}

googleDriveClient = GoogleDriveClient(google_drive_folder_id)

setup_logging()
log = get_logger(__name__)

def fetch_config() -> dict:
    try:
        response = requests.get(f"{SERVER_URL}/config", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.warning(f"Could not fetch config from server, using defaults: {e}")
        return _DEFAULT_CONFIG

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
    cfg = fetch_config()
    TASK_WAIT_INTERVAL = cfg.get("task_wait_interval", _DEFAULT_CONFIG["task_wait_interval"])
    SCRAPE_RETRIES = cfg.get("scrape_retries", _DEFAULT_CONFIG["scrape_retries"])
    SCRAPE_RETRY_DELAY = cfg.get("scrape_retry_delay", _DEFAULT_CONFIG["scrape_retry_delay"])
    SCRAPE_RETRY_DELAY_VARIATION = cfg.get("scrape_retry_delay_variation", _DEFAULT_CONFIG["scrape_retry_delay_variation"])

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

        log.info(f"Scraping: {url}")
        result: TaskResult | None = None

        for attempt in range(1, SCRAPE_RETRIES + 1):
            try:
                result, html = scrapeUniversal(url)
                
                if not result or not result.success or not html:
                    raise Exception(f"Scrape failed to fetch html for {url}")

                count = len(result.foundUrls) if result.foundUrls else 0
                log.info(f"Successfully extracted data from {url}. Found {count} URLs. Trying to save html")
                
                ATTEMPTS = 10
                for uploadAttempt in range(1, ATTEMPTS + 1):
                    try:
                        googleDriveClient.upload_with_conversion(result.processed_url, html)
                        break #successful upload
                    except Exception as e:
                        sleep_time = min(2 ** uploadAttempt, 60)
                        log.warning(f"Failed to upload html for {url}, [Attempt {uploadAttempt}/{ATTEMPTS}] retrying in {sleep_time}")
                        time.sleep(sleep_time)
                        continue
                
                break #successful scrape and upload
            
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

        time.sleep(SCRAPE_RETRY_DELAY + random.uniform(-SCRAPE_RETRY_DELAY_VARIATION, SCRAPE_RETRY_DELAY_VARIATION))
        try:
            complete_task(result)
            log.info(f"Done: {url}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
