"""
Logging service — structured, rotating log files for the desktop app.

Separates GUI logs, application logs, and (via IPC heartbeat) robot-control logs.
Uses Python's standard logging with RotatingFileHandler.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Log categories
LOG_CATEGORIES = ["gui", "app", "robot", "dds", "xr"]

# In-memory ring buffer for the live logs screen
_BUFFER_SIZE = 2000


class _RingBufferHandler(logging.Handler):
    """Stores log records in a deque for the live logs view."""

    def __init__(self, capacity=_BUFFER_SIZE):
        super().__init__()
        self._records: deque[dict] = deque(maxlen=capacity)

    def emit(self, record):
        try:
            self._records.append({
                "timestamp": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "category": getattr(record, "category", "app"),
                "message": record.getMessage(),
            })
        except Exception:
            pass

    def get_records(self, category: str = None, level: str = None) -> list[dict]:
        result = list(self._records)
        if category and category != "all":
            result = [r for r in result if r["category"] == category]
        if level and level != "ALL":
            result = [r for r in result if r["level"] == level]
        return result

    def clear(self):
        self._records.clear()


class LoggingService:
    """Manages all application logging."""

    def __init__(self, log_dir: Optional[Path] = None):
        self._log_dir = log_dir or self._default_log_dir()
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._ring_handler = _RingBufferHandler()
        self._loggers: dict[str, logging.Logger] = {}
        self._setup()

    def _default_log_dir(self) -> Path:
        import sys
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        elif sys.platform == "darwin":
            base = str(Path.home() / "Library" / "Logs")
        else:
            base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        return Path(base) / "UnitreeXRTeleoperate" / "logs"

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def _setup(self):
        """Create per-category loggers with rotating file handlers."""
        for cat in LOG_CATEGORIES:
            log = logging.getLogger(f"unitree_teleop.{cat}")
            log.setLevel(logging.DEBUG)
            # Avoid duplicate handlers on re-init
            if log.handlers:
                continue
            # File handler (rotating, 5 MB x 5 files)
            fh = RotatingFileHandler(
                self._log_dir / f"{cat}.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            log.addHandler(fh)
            # Ring buffer handler
            log.addHandler(self._ring_handler)
            self._loggers[cat] = log

        # Also capture root logging for the ring buffer
        root = logging.getLogger()
        if not any(isinstance(h, _RingBufferHandler) for h in root.handlers):
            root.addHandler(self._ring_handler)
            root.setLevel(logging.INFO)

    def get_logger(self, category: str = "app") -> logging.Logger:
        return self._loggers.get(category, logging.getLogger(f"unitree_teleop.{category}"))

    def get_records(self, category: str = "all", level: str = "ALL") -> list[dict]:
        return self._ring_handler.get_records(category, level)

    def clear_buffer(self):
        self._ring_handler.clear()

    def save_to_file(self, path: str, category: str = "all", level: str = "ALL") -> int:
        """Save current log buffer to a file.  Returns number of lines written."""
        records = self.get_records(category, level)
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(f"{r['timestamp']} {r['level']} {r['category']}: {r['message']}\n")
        return len(records)
