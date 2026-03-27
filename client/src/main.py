import json
import os
import time
import requests
from scraper import scrapeApp, scrapeRoom, scrapeDeveloperApps
from shared.logger import get_logger, setup_logging
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("HOST")
port_raw = os.getenv("PORT")
server_ip = os.getenv("SERVER_IP")

if not host or not port_raw or not server_ip:
    raise Exception("HOST or PORT or server_ip are missing in .env!")

SERVER_URL = f"http://{server_ip}:{int(port_raw)}"
TASK_WAIT_INTERVAL = 60  
SCRAPE_RETRIES = 3
SCRAPE_RETRY_DELAY = 60


setup_logging()
log = get_logger(__name__)

def request_task() -> str | None:
    response = requests.get(f"{SERVER_URL}/task")
    response.raise_for_status()
    return response.json().get("url")


def complete_task(result: dict, site: str) -> None:
    response = requests.post(f"{SERVER_URL}/task/complete", json={**result, "html": site})
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
        except Exception as e:
            log.error(f"Server returned unexpected error on task request: {e}")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        if not url:
            log.info(f"No tasks available, waiting {TASK_WAIT_INTERVAL}s...")
            time.sleep(TASK_WAIT_INTERVAL)
            continue

        if "/iphone/room/" in url:
            url_type = "room"
        elif "/developer/" in url:
            url_type = "developer"
        elif "/app/" in url:
            url_type = "app"
        else:
            url_type = "unknown"

        log.info(f"[{url_type}] Scraping: {url}")
        result = None
        html = None
        for attempt in range(1, SCRAPE_RETRIES + 1):
            try:
                if url_type == "room":
                    result = scrapeRoom(url)
                elif url_type == "developer":
                    result = scrapeDeveloperApps(url)
                else:
                    result = scrapeApp(url)
                html = result.pop("html")
                if not html:
                    raise Exception("empty html")
                log.debug(f"Found {len(result.get('found_urls', []))} new URLs from {url}")
                break
            except Exception as e:
                log.warning(f"Attempt {attempt}/{SCRAPE_RETRIES} failed for {url}: {e}")
                if attempt < SCRAPE_RETRIES:
                    time.sleep(SCRAPE_RETRY_DELAY)

        if result is None:
            log.error(f"All {SCRAPE_RETRIES} attempts failed for {url}, marking as failed")
            try:
                report_failed(url)
            except Exception as e:
                log.error(f"Could not report failed URL to server: {e}")
            continue

        try:
            complete_task(result, html)  # type: ignore
            log.info(f"[{url_type}] Done: {url}")
        except requests.ConnectionError:
            log.error(f"Cannot reach server to submit result for {url}")
        except requests.HTTPError as e:
            log.error(f"Server rejected result for {url}: {e}")


if __name__ == "__main__":
    run()
