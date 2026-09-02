"""
Cross-platform ZMQ IPC transport abstraction.

On Linux, ZMQ supports the `ipc://` transport using Unix domain sockets.
The `@` prefix uses the abstract socket namespace (Linux-only).

On Windows, ZMQ does NOT support the `ipc://` transport at all.
We fall back to `tcp://127.0.0.1:PORT` on Windows.

This module provides:
  - get_ipc_endpoint(name) -> str: Returns the appropriate transport endpoint
  - A dynamic port allocation scheme for Windows TCP fallback with retry logic
  - Socket option helpers for clean bind/close behavior

Port allocation strategy on Windows:
  - Well-known channels (data, heartbeat) use fixed base ports for discovery.
  - If a fixed port is already in use (e.g. stale socket from a crashed process),
    the system automatically retries on the next available port.
  - The actual bound port is recorded so clients can discover it.
"""
import sys
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Windows TCP fallback base ports for well-known IPC channels.
# These are starting points; if occupied, the next free port is used.
_WIN_PORT_MAP = {
    "xr_teleoperate_data": 60100,
    "xr_teleoperate_hb": 60101,
}

# Track dynamically assigned ports for unknown channel names
_dynamic_port_counter = 60200
_dynamic_port_map: dict[str, int] = {}

# Track actual bound ports (filled when a server binds)
_bound_port_map: dict[str, int] = {}


def _find_free_port(start: int, max_attempts: int = 50) -> int:
    """
    Find a free TCP port starting from `start`, trying up to `max_attempts` ports.

    Uses a real socket bind test (not ZMQ) to check availability.
    Returns the first free port, or start+max_attempts-1 if none found
    (the ZMQ bind will then fail with a clear error).
    """
    for offset in range(max_attempts):
        port = start + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    # Fallback: let the OS choose a random port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
    except OSError:
        return start  # last resort


def _get_windows_port(name: str) -> int:
    """Get the TCP port for a named IPC channel on Windows."""
    # Strip the @ prefix if present
    clean_name = name.lstrip("@")

    # If already bound, return the actual bound port
    if clean_name in _bound_port_map:
        return _bound_port_map[clean_name]

    if clean_name in _WIN_PORT_MAP:
        return _WIN_PORT_MAP[clean_name]

    # Dynamically assign a port for unknown channels
    global _dynamic_port_counter
    if clean_name not in _dynamic_port_map:
        _dynamic_port_map[clean_name] = _dynamic_port_counter
        _dynamic_port_counter += 1
    return _dynamic_port_map[clean_name]


def record_bound_port(name: str, port: int):
    """
    Record the actual port a server bound to (for dynamic port discovery).

    Call this after a successful ZMQ bind() so clients can discover the port.
    """
    clean_name = name.lstrip("@").replace("ipc://", "")
    _bound_port_map[clean_name] = port


def get_bound_port(name: str) -> Optional[int]:
    """
    Get the actual port a server bound to for the given channel name.

    Returns None if no server has bound yet.
    """
    clean_name = name.lstrip("@").replace("ipc://", "")
    return _bound_port_map.get(clean_name)


def get_ipc_endpoint(name: str) -> str:
    """
    Return the appropriate ZMQ endpoint for the given channel name.

    On Linux:   ipc://@<name>  (abstract Unix socket)
    On Windows: tcp://127.0.0.1:<port>  (TCP loopback)

    Args:
        name: Channel name without the ipc:// prefix (e.g. "xr_teleoperate_data")

    Returns:
        ZMQ endpoint string suitable for bind() or connect()
    """
    # Strip any existing prefix
    clean_name = name.replace("ipc://", "").lstrip("@")

    if sys.platform == "win32":
        port = _get_windows_port(clean_name)
        endpoint = f"tcp://127.0.0.1:{port}"
        logger.debug(f"IPC transport (Windows): {clean_name} -> {endpoint}")
        return endpoint
    else:
        endpoint = f"ipc://@{clean_name}"
        logger.debug(f"IPC transport (Linux): {clean_name} -> {endpoint}")
        return endpoint


def get_ipc_endpoint_with_retry(name: str, max_retries: int = 10) -> tuple:
    """
    Return a ZMQ endpoint for the given channel, retrying on port conflicts (Windows only).

    On Windows, if the base port is occupied, tries subsequent ports.
    Returns (endpoint_str, actual_port) so the caller can record the bound port.

    On Linux, returns (ipc://@<name>, 0) with no retry.

    Args:
        name: Channel name
        max_retries: Maximum number of port retries on Windows

    Returns:
        Tuple of (endpoint_string, port_number)
    """
    clean_name = name.replace("ipc://", "").lstrip("@")

    if sys.platform != "win32":
        return f"ipc://@{clean_name}", 0

    base_port = _get_windows_port(clean_name)
    for attempt in range(max_retries):
        port = base_port + attempt
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                endpoint = f"tcp://127.0.0.1:{port}"
                logger.debug(f"IPC transport (Windows): {clean_name} -> {endpoint} (attempt {attempt+1})")
                return endpoint, port
        except OSError:
            continue

    # All retries exhausted — let the OS pick a random port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    except OSError:
        port = base_port

    endpoint = f"tcp://127.0.0.1:{port}"
    logger.warning(f"IPC transport (Windows): {clean_name} -> {endpoint} (fallback to OS-assigned port)")
    return endpoint, port


def is_ipc_supported() -> bool:
    """Return True if the ZMQ ipc:// transport is supported on this platform."""
    return sys.platform != "win32"
