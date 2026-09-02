"""
Tests for cross-platform network interface enumeration.

Tests are hardware-independent: they verify the API works correctly
without requiring a specific network configuration.
"""
import sys
import socket
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestNetworkInterface:
    def test_list_interfaces_returns_list(self):
        from teleop.platform.network import list_network_interfaces
        interfaces = list_network_interfaces()
        assert isinstance(interfaces, list)

    def test_interface_has_required_fields(self):
        from teleop.platform.network import list_network_interfaces, NetworkInterface
        interfaces = list_network_interfaces()
        if interfaces:
            ni = interfaces[0]
            assert hasattr(ni, 'name')
            assert hasattr(ni, 'ipv4')
            assert hasattr(ni, 'is_up')
            assert hasattr(ni, 'is_loopback')

    def test_loopback_exists(self):
        from teleop.platform.network import list_network_interfaces
        interfaces = list_network_interfaces()
        # At least one interface should exist (loopback or real)
        assert len(interfaces) >= 1

    def test_resolve_interface_ip_returns_string(self):
        from teleop.platform.network import resolve_interface_ip
        result = resolve_interface_ip("nonexistent_interface_12345")
        assert isinstance(result, str)
        assert result == ""  # Should return empty for nonexistent interface

    def test_find_interface_for_ip_returns_none_for_invalid(self):
        from teleop.platform.network import find_interface_for_ip
        result = find_interface_for_ip("0.0.0.0")
        # 0.0.0.0 is not a valid interface IP
        assert result is None

    def test_is_ip_reachable_returns_bool(self):
        from teleop.platform.network import is_ip_reachable
        # Test with loopback (should always be reachable)
        result = is_ip_reachable("127.0.0.1", timeout=1.0)
        assert isinstance(result, bool)

    def test_is_ip_reachable_invalid_ip(self):
        from teleop.platform.network import is_ip_reachable
        # 192.0.2.1 is a documentation IP (RFC 5737), should not be reachable
        result = is_ip_reachable("192.0.2.1", timeout=1.0)
        assert result is False

    def test_print_interfaces_does_not_crash(self):
        from teleop.platform.network import print_interfaces
        # Should not raise
        print_interfaces()
