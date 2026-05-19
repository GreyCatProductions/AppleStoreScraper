import random
import time
import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from scraper import scrapeUniversal
from shared.logger import get_logger, setup_logging
from shared.objects import DriveId, FailedTask, TaskResult
from googledrive import GoogleDriveClient
from smartConfig import smartConfig

setup_logging()
log = get_logger(__name__)

config = smartConfig()

def request_task() -> str | None:
    response = requests.get(f"{config.SERVER_URL}/task", headers=config.HEADERS)
    response.raise_for_status()
    return response.json().get("url")

def complete_task(result: TaskResult) -> None:
    response = requests.post(f"{config.SERVER_URL}/task/complete", json=result.model_dump(), headers=config.HEADERS)
    response.raise_for_status()

def send_heartbeat(url: str) -> None:
    try:
        obj = FailedTask(url=url)
        requests.post(f"{config.SERVER_URL}/task/heartbeat", json=obj.model_dump(), headers=config.HEADERS, timeout=5)
    except Exception as e:
        log.warning(f"Heartbeat failed for {url}: {e}")

def report_failed(url: str) -> None:
    obj = FailedTask(url=url)
    response = requests.post(f"{config.SERVER_URL}/task/failed", json=obj.model_dump(), headers=config.HEADERS)
    response.raise_for_status()
    
def report_full_drive(driveId: str) -> None:
    obj = DriveId(url=driveId)
    response = requests.post(f"{config.SERVER_URL}/drive/full", json=obj.model_dump(), headers=config.HEADERS)
    response.raise_for_status()

def try_upload_once(processed_url: str, html: str, drive_client: GoogleDriveClient) -> tuple[bool, GoogleDriveClient]:
    """Try one upload. On drive-full, report and return a fresh client. Raises on other errors."""
    try:
        drive_client.upload_with_conversion(processed_url, html)
        return True, drive_client
    except Exception as e:
        if "limit for this folder's number of children" in str(e):
            try:
                report_full_drive(config.values.google_drive_folder_id)
                log.warning("Reported full drive. Refetching config")
            except Exception as re:
                log.error(f"Failed to report full drive: {re}")
            config.refresh()
            return False, GoogleDriveClient(config.values.google_drive_folder_id)
        raise
    
def run():
    log.info("Starting worker...")
    googleDriveClient = GoogleDriveClient(config.values.google_drive_folder_id)
    last_config_fetch = time.time()

    while True:
        if time.time() - last_config_fetch >= 60:
            config.refresh()
            last_config_fetch = time.time()

        try:
            url = request_task()
        except requests.ConnectionError:
            log.error("Cannot reach server, retrying...")
            time.sleep(config.values.task_wait_interval)
            continue
        except requests.Timeout:
            log.error("Server timed out on task request, retrying...")
            time.sleep(config.values.task_wait_interval)
            continue
        except requests.HTTPError as e:
            log.error(f"Server returned error on task request: {e}")
            time.sleep(config.values.task_wait_interval)
            continue
        except Exception as e:
            log.error(f"Server returned unexpected error on task request: {e}")
            time.sleep(config.values.task_wait_interval)
            continue

        if not url:
            log.info(f"No tasks available, waiting {config.values.task_wait_interval}s...")
            time.sleep(config.values.task_wait_interval)
            continue

        log.info(f"Scraping: {url}")
        result: TaskResult | None = None
        uploaded = False

        for attempt in range(1, config.values.scrape_retries + 1):
            try:
                result, html = scrapeUniversal(url)

                if not result or not result.success or not html:
                    raise Exception(f"Scrape failed to fetch html for {url}")

                count = len(result.foundUrls) if result.foundUrls else 0
                log.info(f"Successfully extracted data from {url}. Found {count} URLs. Trying to save html to folder id {googleDriveClient.htmlFolderID}")

                #fast retries exp backoff
                ATTEMPTS = 10
                for uploadAttempt in range(1, ATTEMPTS + 1):
                    try:
                        uploaded, googleDriveClient = try_upload_once(result.processed_url, html, googleDriveClient)
                        if uploaded:
                            break
                    except Exception as e:
                        sleep_time = min(2 ** uploadAttempt, 60)
                        log.warning(f"Failed to upload html for {url}, [Attempt {uploadAttempt}/{ATTEMPTS}] retrying in {sleep_time}s: {e}")
                        time.sleep(sleep_time)
                        config.refresh()
                        googleDriveClient = GoogleDriveClient(config.values.google_drive_folder_id)

                #slow refresh until success
                while not uploaded:
                    log.warning(f"All upload attempts failed for {url}, waiting 10 minutes and retrying with refreshed config...")
                    TIME_TO_REFRESH = 600
                    interval = max(config.values.task_timeout // 2, 10)
                    elapsed = 0
                    while elapsed < TIME_TO_REFRESH:
                        chunk = min(interval, TIME_TO_REFRESH - elapsed)
                        time.sleep(chunk)
                        elapsed += chunk
                        send_heartbeat(url)

                    config.refresh()
                    googleDriveClient = GoogleDriveClient(config.values.google_drive_folder_id)
                    try:
                        uploaded, googleDriveClient = try_upload_once(result.processed_url, html, googleDriveClient)
                    except Exception as e:
                        log.warning(f"Retry upload still failed: {e}")

                break  # scrape + upload succeeded, don't re-scrape
                        
            except Exception as e:
                log.warning(f"Attempt {attempt}/{config.values.scrape_retries} failed for {url}: {e}")
                if attempt < config.values.scrape_retries:
                    time.sleep(config.values.scrape_retry_delay * attempt)

        if result is None:
            log.warning(f"All {config.values.scrape_retries} attempts failed for {url}. Reporting as failed")
            try:
                report_failed(url)
            except Exception as e:
                log.error(f"Could not report failed URL to server: {e}")
            continue

        time.sleep(config.values.scrape_retry_delay + random.uniform(-config.values.scrape_retry_delay_variation, config.values.scrape_retry_delay_variation))
        try:
            complete_task(result)
            log.info(f"Done: {url}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
