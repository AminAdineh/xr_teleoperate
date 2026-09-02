"""
Cross-platform ZMQ IPC transport abstraction.

On Linux, ZMQ supports the `ipc://` transport using Unix domain sockets.
The `@` prefix uses the abstract socket namespace (Linux-only).

On Windows, ZMQ does NOT support the `ipc://` transport at all.
We fall back to `tcp://127.0.0.1:PORT` on Windows.

This module provides:
  - get_ipc_endpoint(name) -> str: Returns the appropriate transport endpoint
  - A fixed port allocation scheme for Windows TCP fallback
"""
import sys
import logging

logger = logging.getLogger(__name__)

# Windows TCP fallback ports for IPC channels
# These are fixed so server and client can agree without a discovery mechanism.
_WIN_PORT_MAP = {
    "xr_teleoperate_data": 60100,
    "xr_teleoperate_hb": 60101,
}

# Track dynamically assigned ports for unknown channel names
_dynamic_port_counter = 60200
_dynamic_port_map = {}


def _get_windows_port(name: str) -> int:
    """Get the TCP port for a named IPC channel on Windows."""
    # Strip the @ prefix if present
    clean_name = name.lstrip("@")

    if clean_name in _WIN_PORT_MAP:
        return _WIN_PORT_MAP[clean_name]

    # Dynamically assign a port for unknown channels
    global _dynamic_port_counter
    if clean_name not in _dynamic_port_map:
        _dynamic_port_map[clean_name] = _dynamic_port_counter
        _dynamic_port_counter += 1
    return _dynamic_port_map[clean_name]


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


def is_ipc_supported() -> bool:
    """Return True if the ZMQ ipc:// transport is supported on this platform."""
    return sys.platform != "win32"
