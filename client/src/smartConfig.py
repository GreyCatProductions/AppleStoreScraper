import requests
from shared.objects import WorkerConfig
from shared.logger import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)

_METADATA_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/{key}"
_METADATA_HEADERS = {"Metadata-Flavor": "Google"}

class smartConfig:
    def __init__(self):
        server_ip = self._get_metadata("SERVER_IP")
        port = self._get_metadata("PORT")
        api_key = self._get_metadata("API_KEY")
        self.SERVER_URL = f"http://{server_ip}:{port}"
        self.HEADERS = {"X-API-Key": api_key}
        self.refresh()
    
    def refresh(self) -> int:
        try:
            response = requests.get(f"{self.SERVER_URL}/config", headers=self.HEADERS, timeout=5)
            response.raise_for_status()
            self.values = WorkerConfig(**response.json())
            return 0
        except Exception as e:
            log.warning(f"Could not fetch config from server, using defaults: {e}")
            self.values = WorkerConfig(
                task_wait_interval=60,
                scrape_retries=3,
                scrape_retry_delay=5,
                scrape_retry_delay_variation=2,
                google_drive_folder_id=self._get_metadata("GOOGLE_DRIVE_FOLDER_ID"),
            )
            return 1
            
    def _get_metadata(self, key: str) -> str:
        response = requests.get(_METADATA_URL.format(key=key), headers=_METADATA_HEADERS, timeout=5)
        response.raise_for_status()
        return response.text
