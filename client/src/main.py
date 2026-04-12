import random
import time
import requests
from scraper import scrapeUniversal
from shared.logger import get_logger, setup_logging
from shared.objects import FailedTask, TaskResult, WorkerConfig
from googledrive import GoogleDriveClient

setup_logging()
log = get_logger(__name__)

_METADATA_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/{key}"
_METADATA_HEADERS = {"Metadata-Flavor": "Google"}

def _get_metadata(key: str) -> str:
    response = requests.get(_METADATA_URL.format(key=key), headers=_METADATA_HEADERS, timeout=5)
    response.raise_for_status()
    return response.text

server_ip = _get_metadata("SERVER_IP")
port = _get_metadata("PORT")
api_key = _get_metadata("API_KEY")
SERVER_URL = f"http://{server_ip}:{port}"
_HEADERS = {"X-API-Key": api_key}

def fetch_config() -> WorkerConfig:
    try:
        response = requests.get(f"{SERVER_URL}/config", headers=_HEADERS, timeout=5)
        response.raise_for_status()
        log.info("Successfully fetched config")
        return WorkerConfig(**response.json())
    except Exception as e:
        log.warning(f"Could not fetch config from server, using defaults: {e}")
        return WorkerConfig(
            task_wait_interval=60,
            scrape_retries=3,
            scrape_retry_delay=5,
            scrape_retry_delay_variation=2,
            google_drive_folder_id=_get_metadata("GOOGLE_DRIVE_FOLDER_ID"),
        )

def request_task() -> str | None:
    response = requests.get(f"{SERVER_URL}/task", headers=_HEADERS)
    response.raise_for_status()
    return response.json().get("url")

def complete_task(result: TaskResult) -> None:
    response = requests.post(f"{SERVER_URL}/task/complete", json=result.model_dump(), headers=_HEADERS)
    response.raise_for_status()

def send_heartbeat(url: str) -> None:
    try:
        obj = FailedTask(url=url)
        requests.post(f"{SERVER_URL}/task/heartbeat", json=obj.model_dump(), headers=_HEADERS, timeout=5)
    except Exception as e:
        log.warning(f"Heartbeat failed for {url}: {e}")

def report_failed(url: str) -> None:
    obj = FailedTask(url=url)
    response = requests.post(f"{SERVER_URL}/task/failed", json=obj.model_dump(), headers=_HEADERS)
    response.raise_for_status()

def run():
    log.info("Starting worker...")
    cfg = fetch_config()
    googleDriveClient = GoogleDriveClient(cfg.google_drive_folder_id)
    last_config_fetch = time.time()

    while True:
        if time.time() - last_config_fetch >= 60:
            cfg = fetch_config()
            last_config_fetch = time.time()

        try:
            url = request_task()
        except requests.ConnectionError:
            log.error("Cannot reach server, retrying...")
            time.sleep(cfg.task_wait_interval)
            continue
        except requests.Timeout:
            log.error("Server timed out on task request, retrying...")
            time.sleep(cfg.task_wait_interval)
            continue
        except requests.HTTPError as e:
            log.error(f"Server returned error on task request: {e}")
            time.sleep(cfg.task_wait_interval)
            continue
        except Exception as e:
            log.error(f"Server returned unexpected error on task request: {e}")
            time.sleep(cfg.task_wait_interval)
            continue

        if not url:
            log.info(f"No tasks available, waiting {cfg.task_wait_interval}s...")
            time.sleep(cfg.task_wait_interval)
            continue

        log.info(f"Scraping: {url}")
        result: TaskResult | None = None
        uploaded = False

        for attempt in range(1, cfg.scrape_retries + 1):
            try:
                result, html = scrapeUniversal(url)

                if not result or not result.success or not html:
                    raise Exception(f"Scrape failed to fetch html for {url}")

                count = len(result.foundUrls) if result.foundUrls else 0
                log.info(f"Successfully extracted data from {url}. Found {count} URLs. Trying to save html to folder id {googleDriveClient.htmlFolderID}")

                ATTEMPTS = 10
                for uploadAttempt in range(1, ATTEMPTS + 1):
                    try:
                        googleDriveClient.upload_with_conversion(result.processed_url, html)
                        uploaded = True
                        break
                    except Exception as e:
                        sleep_time = min(2 ** uploadAttempt, 60)
                        fetch_config()
                        googleDriveClient = GoogleDriveClient(cfg.google_drive_folder_id)
                        log.warning(f"Failed to upload html for {url}, [Attempt {uploadAttempt}/{ATTEMPTS}] retrying in {sleep_time}s: {e}")
                        time.sleep(sleep_time)

                while not uploaded:
                    log.warning(f"All upload attempts failed for {url}, waiting 10 minutes and retrying with refreshed config...")
                    TIME_TO_REFRESH = 600
                    interval = max(cfg.task_timeout // 2, 10)
                    elapsed = 0
                    while elapsed < TIME_TO_REFRESH:
                        chunk = min(interval, TIME_TO_REFRESH - elapsed)
                        time.sleep(chunk)
                        elapsed += chunk
                        send_heartbeat(url)
                        
                    cfg = fetch_config()
                    googleDriveClient = GoogleDriveClient(cfg.google_drive_folder_id)
                    try:
                        googleDriveClient.upload_with_conversion(result.processed_url, html)
                        uploaded = True
                    except Exception as e:
                        log.warning(f"Retry upload still failed: {e}")
                        
            except Exception as e:
                log.warning(f"Attempt {attempt}/{cfg.scrape_retries} failed for {url}: {e}")
                if attempt < cfg.scrape_retries:
                    time.sleep(cfg.scrape_retry_delay * attempt)

        if result is None:
            log.warning(f"All {cfg.scrape_retries} attempts failed for {url}. Reporting as failed")
            try:
                report_failed(url)
            except Exception as e:
                log.error(f"Could not report failed URL to server: {e}")
            continue

        time.sleep(cfg.scrape_retry_delay + random.uniform(-cfg.scrape_retry_delay_variation, cfg.scrape_retry_delay_variation))
        try:
            complete_task(result)
            log.info(f"Done: {url}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
