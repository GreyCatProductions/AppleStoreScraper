import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

class _ConsoleColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[90m",
        "INFO": "\033[94m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, "")
        record.levelname = f"{color}{levelname}{self.RESET}" if color else levelname
        try:
            return super().format(record)
        finally:
            record.levelname = levelname


def setup_logging(
    log_file: str = "logs/app.log",
    level: int = logging.INFO,
    max_bytes: int = 5_000_000,
    backup_count: int = 10,
) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return

    base_dir = Path(__file__).resolve().parents[1]
    log_path = base_dir / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(_ConsoleColorFormatter(fmt, datefmt=datefmt))

    fh = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root.addHandler(ch)
    root.addHandler(fh)


def setup_request_logging(
    log_file: str = "logs/requests.log",
    max_bytes: int = 10_000_000,
    backup_count: int = 10,
) -> None:
    logger = logging.getLogger("all_requests")
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  

    base_dir = Path(__file__).resolve().parents[1]
    log_path = base_dir / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s [%(threadName)s]: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    fh = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    logger.addHandler(fh)


def get_request_logger() -> logging.Logger:
    return logging.getLogger("all_requests")


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or __name__)