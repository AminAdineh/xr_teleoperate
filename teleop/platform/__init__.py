"""
Platform abstraction layer for xr_teleoperate.

Provides cross-platform utilities for:
  - Network interface enumeration
  - Certificate / config path resolution
  - ZMQ IPC transport selection
  - Cross-platform process spawning (Process on Linux, Thread on Windows)
  - CPU affinity management
  - Firewall instructions

Usage:
    from teleop.platform import is_windows, is_linux, get_network_interfaces, ...
"""
import sys
import platform

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"

PLATFORM_NAME = "windows" if IS_WINDOWS else ("linux" if IS_LINUX else "macos")


def is_windows() -> bool:
    """Return True if running on Windows."""
    return IS_WINDOWS


def is_linux() -> bool:
    """Return True if running on Linux."""
    return IS_LINUX


def is_macos() -> bool:
    """Return True if running on macOS."""
    return IS_MACOS


def get_platform_name() -> str:
    """Return a lowercase platform name: 'windows', 'linux', or 'macos'."""
    return PLATFORM_NAME


def get_python_arch() -> str:
    """Return '64bit' or '32bit' for the current Python interpreter."""
    return platform.architecture()[0]


def get_os_version() -> str:
    """Return a human-readable OS version string."""
    if IS_WINDOWS:
        return platform.version()
    elif IS_LINUX:
        return platform.uname().release
    else:
        return platform.version()


# Re-export commonly used functions for convenience
def get_network_interfaces():
    """List network interfaces (lazy import to avoid psutil dependency at import time)."""
    from teleop.platform.network import list_network_interfaces
    return list_network_interfaces()


def get_ipc_endpoint(name: str) -> str:
    """Get the ZMQ IPC endpoint for a channel (lazy import)."""
    from teleop.platform.ipc_transport import get_ipc_endpoint as _get
    return _get(name)
