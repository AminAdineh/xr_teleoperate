"""
Cross-platform firewall instructions and helpers.

On Linux: ufw commands
On Windows: netsh advfirewall commands (requires admin privileges)
"""
import os
import sys
import logging
import subprocess
from typing import List

logger = logging.getLogger(__name__)

# Ports used by xr_teleoperate
REQUIRED_PORTS = [
    (8012, "tcp", "Televuer HTTPS/WebRTC signaling"),
    (60000, "tcp", "Teleimager camera config request"),
    (60100, "tcp", "IPC data channel (Windows fallback)"),
    (60101, "tcp", "IPC heartbeat channel (Windows fallback)"),
    (7400, "udp", "DDS multicast discovery"),
    (7401, "udp", "DDS unicast range start"),
]


def get_firewall_instructions() -> List[str]:
    """
    Return platform-specific firewall commands to allow required ports.

    Returns a list of command strings that can be run in a terminal.
    """
    if sys.platform == "win32":
        return _get_windows_firewall_commands()
    else:
        return _get_linux_firewall_commands()


def _get_windows_firewall_commands() -> List[str]:
    """Return Windows Defender Firewall commands (requires admin)."""
    commands = []
    for port, proto, desc in REQUIRED_PORTS:
        commands.append(
            f'netsh advfirewall firewall add rule name="xr_teleoperate {desc}" '
            f'dir=in action=allow protocol={proto.upper()} localport={port}'
        )
    return commands


def _get_linux_firewall_commands() -> List[str]:
    """Return ufw firewall commands."""
    commands = []
    for port, proto, desc in REQUIRED_PORTS:
        commands.append(f"sudo ufw allow {port}/{proto}")
    return commands


def check_firewall_rules() -> dict:
    """
    Check if firewall rules exist for the required ports.

    Returns a dict mapping port numbers to bool (True if rule exists).
    """
    result = {}
    if sys.platform == "win32":
        try:
            output = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
                capture_output=True, text=True, timeout=10
            )
            text = output.stdout.lower()
            for port, _, _ in REQUIRED_PORTS:
                result[port] = str(port) in text
        except Exception:
            for port, _, _ in REQUIRED_PORTS:
                result[port] = False
    else:
        # On Linux, just check if ufw is available
        for port, _, _ in REQUIRED_PORTS:
            result[port] = False
    return result


def is_admin() -> bool:
    """Check if the current process has admin/root privileges."""
    if sys.platform == "win32":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def print_firewall_instructions():
    """Print firewall setup instructions for the current platform."""
    if sys.platform == "win32":
        print("\n=== Windows Defender Firewall Setup ===")
        print("Run the following commands in an elevated PowerShell prompt:")
        print("(Right-click PowerShell -> Run as Administrator)\n")
        for cmd in get_firewall_instructions():
            print(f"  {cmd}")
        print()
    else:
        print("\n=== Linux Firewall (ufw) Setup ===")
        print("Run the following commands:\n")
        for cmd in get_firewall_instructions():
            print(f"  {cmd}")
        print()
