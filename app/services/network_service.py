"""
Network service — wraps teleop.platform.network for the GUI.

Provides adapter enumeration, auto-selection, and reachability checks.
"""
from __future__ import annotations

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)


class NetworkService:
    """Thin wrapper around the platform network module."""

    def list_interfaces(self):
        """Return a list of NetworkInterface objects from the platform layer."""
        from teleop.platform.network import list_network_interfaces
        return list_network_interfaces()

    def get_recommended(self):
        """Return the recommended interface (robot-network 192.168.123.x preferred)."""
        interfaces = self.list_interfaces()
        real = [ni for ni in interfaces
                if ni.is_up and not ni.is_loopback and ni.ipv4]
        # Prefer 192.168.123.x
        for ni in real:
            if ni.ipv4.startswith("192.168.123."):
                return ni
        # Then non-virtual
        for ni in real:
            if not ni.is_virtual:
                return ni
        # Then any
        if real:
            return real[0]
        return None

    def auto_select(self) -> Optional[str]:
        """Auto-select the best interface and return its name."""
        ni = self.get_recommended()
        return ni.name if ni else None

    def resolve_ip(self, interface_name: str) -> str:
        """Return the IPv4 of the named interface, or '' if not found."""
        from teleop.platform.network import resolve_interface_ip
        return resolve_interface_ip(interface_name)

    def is_reachable(self, ip: str, timeout: float = 2.0) -> bool:
        """Check if an IP is reachable via ICMP ping."""
        from teleop.platform.network import is_ip_reachable
        return is_ip_reachable(ip, timeout)

    def get_lan_ip(self) -> str:
        """Return the primary LAN IP of this machine."""
        try:
            from teleop.platform.certs import get_lan_ip
            return get_lan_ip()
        except Exception:
            return "127.0.0.1"

    def get_all_lan_ips(self) -> list[str]:
        """Return all non-loopback IPv4 addresses."""
        try:
            from teleop.platform.certs import get_all_lan_ips
            return get_all_lan_ips()
        except Exception:
            return []
