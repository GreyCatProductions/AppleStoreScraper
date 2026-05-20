import os
from dotenv import load_dotenv
from shared.logger import setup_logging, get_logger
from shared.objects import WorkerConfig
from schema.urlState import UrlState 
from googleDrive import googleDrive

if not load_dotenv():
    raise EnvironmentError("Could not load .env!")

#Paths
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")
HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "html")
CHECKPOINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
INITIAL_LINKS = os.path.join(os.path.dirname(__file__), "..", "config/initialLinks")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

#Env
HOST = os.getenv("HOST")
port_raw = os.getenv("PORT")
assert HOST and port_raw
HOST = str(HOST)
PORT = int(port_raw)

GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_TEMPLATE_NAME = os.getenv("GOOGLE_TEMPLATE_NAME")
SERVER_IP = os.getenv("SERVER_IP")
_raw_ssh_keys = os.getenv("SSH_KEYS", "")
SSH_KEYS = [k.strip() for k in _raw_ssh_keys.split(",") if k.strip()] or None
API_KEY = os.getenv("API_KEY")

assert API_KEY, "API_KEY missing from environment!"
assert GOOGLE_PROJECT_ID and GOOGLE_TEMPLATE_NAME and SERVER_IP


setup_logging()
logger = get_logger(__name__)


#shared singletons
state = UrlState(csv_path=CSV_PATH, html_dir=HTML_DIR)

checkpoints = sorted(
    (f for f in os.listdir(CHECKPOINTS_DIR) if f.endswith(".json")),
    reverse=True,
)
if checkpoints:
    import json
    checkpoint_path = os.path.join(CHECKPOINTS_DIR, checkpoints[0])
    with open(checkpoint_path) as f:
        data = json.load(f)
    state.load_from_checkpoint(
        available=data.get("available", []),
        occupied=data.get("occupied", []),
        processed=data.get("processed", []),
        terminated=data.get("terminated", []),
    )
    logger.info(f"Restored state from checkpoint: {checkpoints[0]}")
elif os.path.exists(INITIAL_LINKS):
    with open(INITIAL_LINKS) as f:
        urls = [line.strip() for line in f if line.strip()]
        state.add_urls(urls)
    logger.info(f"Loaded {len(urls)} initial URLs from {INITIAL_LINKS}")
else:
    raise FileNotFoundError(
        f"Could not find file for loading initial urls! Expected at {INITIAL_LINKS}. Exiting!"
    )
    
config = WorkerConfig(
    task_wait_interval=60,
    scrape_retries=3,
    scrape_retry_delay=5,
    scrape_retry_delay_variation=2,
    google_drive_folder_id="",
    task_timeout=300
)

drive = googleDrive()