"""
Configuration service — load, save, validate, and repair application config.

Config is stored as YAML under the platform-appropriate application-data
directory (reusing teleop.platform.paths).

On Windows:  %APPDATA%\\UnitreeXRTeleoperate\\config.yaml
On Linux:    ~/.config/UnitreeXRTeleoperate/config.yaml
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

import yaml

from app.models import AppConfig

logger = logging.getLogger(__name__)

# App name used for the config directory (distinct from the upstream
# "xr_teleoperate" dir so the GUI app does not clobber CLI config).
_APP_DIR_NAME = "UnitreeXRTeleoperate"
_CONFIG_FILE = "config.yaml"
_CONFIG_BACKUP = "config.yaml.bak"


def _config_dir() -> Path:
    """Return the platform-appropriate config directory for the GUI app."""
    import sys, os
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / _APP_DIR_NAME


class ConfigService:
    """Manages persistent application configuration."""

    def __init__(self):
        self._dir: Path = _config_dir()
        self._path: Path = self._dir / _CONFIG_FILE
        self._backup: Path = self._dir / _CONFIG_BACKUP
        self._config: AppConfig = AppConfig()

    # -- properties --------------------------------------------------------

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def config_dir(self) -> Path:
        return self._dir

    @property
    def config_path(self) -> Path:
        return self._path

    # -- load / save ------------------------------------------------------

    def load(self) -> AppConfig:
        """Load config from disk.  Returns defaults if file is missing."""
        self._dir.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            logger.info("No config file found; using defaults.")
            self._config = AppConfig()
            self.save()
            return self._config
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if data is None:
                raise ValueError("Config file is empty")
            self._config = AppConfig.from_dict(data)
            logger.info("Config loaded from %s", self._path)
        except Exception as exc:
            logger.warning("Config load failed (%s); attempting repair", exc)
            self._config = self._repair()
        return self._config

    def save(self) -> None:
        """Persist the current config to disk."""
        self._dir.mkdir(parents=True, exist_ok=True)
        # Back up existing file before overwriting
        if self._path.exists():
            try:
                shutil.copy2(self._path, self._backup)
            except Exception:
                pass
        data = self._config.to_dict()
        self._path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False),
                              encoding="utf-8")
        logger.info("Config saved to %s", self._path)

    def reset(self) -> AppConfig:
        """Reset to factory defaults."""
        self._config = AppConfig()
        self.save()
        return self._config

    def is_corrupted(self) -> bool:
        """Check whether the on-disk config can be parsed."""
        if not self._path.exists():
            return False
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if data is None:
                return True
            AppConfig.from_dict(data)
            return False
        except Exception:
            return True

    def repair(self) -> AppConfig:
        """Attempt to repair a corrupted config (restore from backup or reset)."""
        self._config = self._repair()
        self.save()
        return self._config

    def _repair(self) -> AppConfig:
        if self._backup.exists():
            try:
                data = yaml.safe_load(self._backup.read_text(encoding="utf-8"))
                if data:
                    logger.info("Restored config from backup")
                    return AppConfig.from_dict(data)
            except Exception:
                pass
        logger.info("Config reset to defaults (repair)")
        return AppConfig()

    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty = valid)."""
        errors: list[str] = []
        c = self._config
        # Robot IP
        ip = c.robot.ip.strip()
        if not ip:
            errors.append("Robot IP is empty")
        else:
            parts = ip.split(".")
            if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                errors.append(f"Robot IP '{ip}' is not a valid IPv4 address")
        # End-effector validity
        from app.models.app_state import valid_end_effectors
        valid_ees = {e.value for e in valid_end_effectors(c.robot.model)}
        if c.robot.end_effector.value not in valid_ees:
            errors.append(
                f"End effector '{c.robot.end_effector.display_name}' is not "
                f"valid for robot '{c.robot.model.display_name}'"
            )
        # XR port
        if not (1 <= c.xr.port <= 65535):
            errors.append(f"XR port {c.xr.port} is out of range (1-65535)")
        # Frequency
        if c.robot.frequency <= 0 or c.robot.frequency > 200:
            errors.append(f"Control frequency {c.robot.frequency} is out of range")
        return errors
