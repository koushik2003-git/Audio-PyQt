
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_logger(name: str = "workshop"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    # File logger (optional)
    try:
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_dir / "workshop.log", maxBytes=1_000_000, backupCount=2)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except Exception:
        pass
    # don't add an extra console handler; assume app configured it
    return logger
