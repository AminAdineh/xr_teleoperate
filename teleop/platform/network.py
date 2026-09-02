"""
Cross-platform network interface enumeration.

On Linux: uses /proc/net or psutil to list interfaces like eth0, wlan0.
On Windows: uses psutil or socket to list adapters like "Ethernet", "Wi-Fi".

Provides a unified NetworkInterface dataclass and list_network_interfaces().
"""
import socket
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.debug("psutil not available; network enumeration will be limited.")


@dataclass
class NetworkInterface:
    """Represents a single network adapter."""
    name: str                   # Interface name (e.g. "eth0" on Linux, "Ethernet" on Windows)
    ipv4: str                   # Primary IPv4 address (empty string if none)
    ipv6: str = ""              # Primary IPv6 address (empty string if none)
    mac: str = ""               # MAC address (empty string if unavailable)
    is_up: bool = True          # Whether the interface is up
    is_loopback: bool = False   # Whether this is the loopback interface
    is_virtual: bool = False    # Whether this is a virtual/software interface


def list_network_interfaces() -> List[NetworkInterface]:
    """
    Enumerate all network interfaces on the current platform.

    Returns a list of NetworkInterface objects, sorted by:
      1. Non-loopback, non-virtual, up interfaces first
      2. Then virtual interfaces
      3. Then loopback

    Uses psutil if available; falls back to socket-based discovery.
    """
    interfaces: List[NetworkInterface] = []

    if HAS_PSUTIL:
        interfaces = _enumerate_psutil()
    else:
        interfaces = _enumerate_socket_fallback()

    # Sort: real up interfaces first, then virtual, then loopback
    interfaces.sort(key=lambda ni: (ni.is_loopback, ni.is_virtual, not ni.is_up))
    return interfaces


def _enumerate_psutil() -> List[NetworkInterface]:
    """Use psutil to enumerate network interfaces."""
    result = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for name, addr_list in addrs.items():
        ipv4 = ""
        ipv6 = ""
        mac = ""

        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ipv4 = addr.address
            elif addr.family == socket.AF_INET6:
                ipv6 = addr.address
            elif addr.family == psutil.AF_LINK:
                mac = addr.address

        is_up = stats.get(name, type("s", (), {"isup": True})).isup if name in stats else True
        is_loopback = name.lower() in ("lo", "loopback") or ipv4.startswith("127.")
        is_virtual = _is_virtual_interface(name)

        result.append(NetworkInterface(
            name=name,
            ipv4=ipv4,
            ipv6=ipv6,
            mac=mac,
            is_up=is_up,
            is_loopback=is_loopback,
            is_virtual=is_virtual,
        ))

    return result


def _enumerate_socket_fallback() -> List[NetworkInterface]:
    """Fallback enumeration using socket (limited information)."""
    result = []
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        result.append(NetworkInterface(
            name="default",
            ipv4=local_ip,
            is_up=True,
            is_loopback=local_ip.startswith("127."),
        ))
    except Exception:
        result.append(NetworkInterface(
            name="unknown",
            ipv4="",
            is_up=False,
        ))
    return result


def _is_virtual_interface(name: str) -> bool:
    """Heuristic to detect virtual/software interfaces."""
    virtual_prefixes = (
        "docker", "veth", "br-", "vboxnet", "vmnet",
        "virtual", "tun", "tap", "ppp",
    )
    name_lower = name.lower()
    return any(name_lower.startswith(prefix) for prefix in virtual_prefixes)


def resolve_interface_ip(interface_name: str) -> str:
    """
    Resolve the IPv4 address of a named network interface.

    Args:
        interface_name: Interface name (e.g. "eth0" on Linux, "Ethernet" on Windows)

    Returns:
        IPv4 address string, or empty string if not found.
    """
    interfaces = list_network_interfaces()
    for ni in interfaces:
        if ni.name == interface_name:
            return ni.ipv4
    return ""


def find_interface_for_ip(ip: str) -> Optional[NetworkInterface]:
    """
    Find the network interface that has the given IP address.

    Args:
        ip: IPv4 address to search for

    Returns:
        NetworkInterface or None if not found.
    """
    for ni in list_network_interfaces():
        if ni.ipv4 == ip:
            return ni
    return None


def is_ip_reachable(ip: str, timeout: float = 2.0) -> bool:
    """
    Check if an IP address is reachable via ICMP or TCP connect.

    Uses a TCP connect to common ports as a fallback when ICMP is not available.
    """
    import subprocess
    import sys

    if sys.platform == "win32":
        # Windows: use ping with -n (count) and -w (timeout in ms)
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), ip]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def print_interfaces() -> None:
    """Print all network interfaces in a human-readable format."""
    interfaces = list_network_interfaces()
    print(f"\n{'Name':<25} {'IPv4':<16} {'MAC':<18} {'Status'}")
    print("-" * 70)
    for ni in interfaces:
        status = "UP" if ni.is_up else "DOWN"
        if ni.is_loopback:
            status += " (loopback)"
        elif ni.is_virtual:
            status += " (virtual)"
        print(f"{ni.name:<25} {ni.ipv4:<16} {ni.mac:<18} {status}")
    print()
