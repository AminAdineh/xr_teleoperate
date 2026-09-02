"""
Cross-platform path resolution for certificates and configuration.

On Linux:   ~/.config/xr_teleoperate/
On Windows: %APPDATA%/xr_teleoperate/
On macOS:   ~/Library/Application Support/xr_teleoperate/
"""
import os
import sys
from pathlib import Path


def get_config_dir() -> Path:
    """
    Return the platform-appropriate configuration directory.

    Linux:   ~/.config/xr_teleoperate/
    Windows: %APPDATA%/xr_teleoperate/
    macOS:   ~/Library/Application Support/xr_teleoperate/
    """
    if sys.platform == "win32":
        # %APPDATA% on Windows (e.g. C:/Users/<user>/AppData/Roaming)
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "xr_teleoperate"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "xr_teleoperate"
    else:
        # Linux/Unix: ~/.config/xr_teleoperate/
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "xr_teleoperate"
        return Path.home() / ".config" / "xr_teleoperate"


def get_cert_dir() -> Path:
    """Return the directory where SSL certificates should be stored."""
    return get_config_dir()


def get_cert_paths() -> tuple:
    """
    Return (cert_path, key_path) for SSL certificates.

    Resolution order:
      1. Environment variables XR_TELEOP_CERT / XR_TELEOP_KEY
      2. Config directory: get_cert_dir() / cert.pem, key.pem
      3. Package root fallback (televuer submodule directory)

    Returns:
        Tuple of (cert_path_str, key_path_str)
    """
    env_cert = os.environ.get("XR_TELEOP_CERT")
    env_key = os.environ.get("XR_TELEOP_KEY")

    if env_cert and env_key:
        return env_cert, env_key

    cert_dir = get_cert_dir()
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)

    # Fallback: try package root (televuer submodule)
    # This is resolved relative to this file
    package_root = Path(__file__).resolve().parent.parent.parent
    fallback_cert = package_root / "teleop" / "televuer" / "cert.pem"
    fallback_key = package_root / "teleop" / "televuer" / "key.pem"

    if fallback_cert.exists() and fallback_key.exists():
        return str(fallback_cert), str(fallback_key)

    # Return the config dir paths even if they don't exist yet
    # (the caller will handle the missing files)
    return str(cert_path), str(key_path)


def ensure_config_dir() -> Path:
    """Create the config directory if it doesn't exist and return it."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """
    Return the platform-appropriate data directory for recordings.

    Linux:   ./teleop/data/ (current working directory, same as upstream)
    Windows: ./teleop/data/ (current working directory, same as upstream)
    """
    # Keep the same relative path behavior as the upstream project
    return Path("teleop") / "data"
