"""
Dynamic, centralized logger with YAML config.
Supports live reloading of all logging parameters (level, file, rotation).
"""

import os
import yaml
import time
import logging
import threading
from logging.handlers import RotatingFileHandler

_logger_initialized = False
_logger_lock = threading.Lock()
_config_path = None
_config_last_modified = 0


# ============================================================
# Helpers
# ============================================================

def _resolve_path(path: str) -> str:
    """Resolve a path relative to this file."""
    if not os.path.isabs(path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(base_dir, path))
    return path


def _load_config() -> dict:
    """Load YAML logging configuration."""
    global _config_path
    with open(_config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    cfg = data.get("logging", {})
    return {
        "level": cfg.get("level", "INFO").upper(),
        "file": cfg.get("file", "logs/app.log"),
        "max_bytes": int(cfg.get("max_bytes", 5 * 1024 * 1024)),
        "backup_count": int(cfg.get("backup_count", 5)),
    }


def _create_handler(cfg: dict) -> RotatingFileHandler:
    """Create a new rotating file handler from the config."""
    log_file = _resolve_path(cfg["file"])
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    handler = RotatingFileHandler(
        log_file,
        mode="a",  # append mode
        maxBytes=cfg["max_bytes"],
        backupCount=cfg["backup_count"],
        encoding="utf-8",
    )
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "%(filename)s:%(lineno)d | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    return handler


def _apply_new_config(logger, new_cfg):
    """Rebuild logger configuration dynamically."""
    level = getattr(logging, new_cfg["level"], logging.INFO)
    logger.setLevel(level)

    # Remove old file handlers and add new one
    for h in logger.handlers[:]:
        if isinstance(h, RotatingFileHandler):
            logger.removeHandler(h)

    new_handler = _create_handler(new_cfg)
    logger.addHandler(new_handler)

    # Update console handler level too
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setLevel(level)

    logger.info(
        f"[LOGGER] Reloaded config: level={new_cfg['level']}, file={new_cfg['file']}, "
        f"max_bytes={new_cfg['max_bytes']}, backup_count={new_cfg['backup_count']}"
    )


def _watch_config(logger):
    """Monitor YAML file and reload configuration dynamically."""
    global _config_last_modified
    while True:
        try:
            mtime = os.path.getmtime(_config_path)
            if mtime != _config_last_modified:
                _config_last_modified = mtime
                new_cfg = _load_config()
                _apply_new_config(logger, new_cfg)
        except Exception as e:
            logger.error(f"[LOGGER] Config watcher error: {e}")
        time.sleep(5)  # check every 5 seconds


# ============================================================
# Initialization
# ============================================================

def setup_logger(config_path: str) -> logging.Logger:
    """Initialize logger and start watching for config changes."""
    global _logger_initialized, _config_path, _config_last_modified
    if _logger_initialized:
        return logging.getLogger()

    with _logger_lock:
        if _logger_initialized:
            return logging.getLogger()

        _config_path = _resolve_path(config_path)
        if not os.path.exists(_config_path):
            raise FileNotFoundError(f"[LOGGER] Config file not found: {_config_path}")

        cfg = _load_config()
        _config_last_modified = os.path.getmtime(_config_path)

        # ---- Setup logger ----
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, cfg["level"], logging.INFO))

        # Formatter
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        # File handler
        file_handler = _create_handler(cfg)
        file_handler.setLevel(getattr(logging, cfg["level"], logging.INFO))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt)
        console_handler.setLevel(getattr(logging, cfg["level"], logging.INFO))

        # Clear any old handlers and attach new ones
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Start watcher thread
        watcher = threading.Thread(target=_watch_config, args=(logger,), daemon=True)
        watcher.start()

        logger.info(f"[LOGGER] Initialized using {_config_path}")
        logger.info(f"[LOGGER] Writing logs to {cfg['file']}")
        logger.info(f"[LOGGER] Watching for live config updates every 5s")

        _logger_initialized = True
        return logger


def get_logger(config_path: str = "./config.yaml") -> logging.Logger:
    """Return a shared logger instance (initialize if needed)."""
    global _logger_initialized
    if not _logger_initialized:
        setup_logger(config_path)
    return logging.getLogger()
