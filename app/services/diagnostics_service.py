"""
Diagnostics service — wraps tools.windows_diagnostics for the GUI.

Provides structured check results that the GUI can display.
"""
from __future__ import annotations

import importlib
import logging
import os
import platform
import socket
import sys
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    name: str
    status: str          # "pass", "warn", "fail", "skip"
    detail: str = ""
    fix: str = ""
    category: str = ""


class DiagnosticsService:
    """Runs system checks and returns structured results."""

    def run_system_check(self) -> list[CheckResult]:
        """Run all system checks (no robot required)."""
        results: list[CheckResult] = []
        cat = "System"

        # OS
        is_win = sys.platform == "win32"
        os_name = f"{platform.system()} {platform.release()}"
        if is_win:
            try:
                build = int(platform.version().split(".")[-1])
                win11 = build >= 22000
                results.append(CheckResult(
                    "Windows 11 (Build 22000+)", "pass" if win11 else "warn",
                    f"Build {build}",
                    "Windows 11 is recommended." if not win11 else "",
                    cat,
                ))
            except Exception:
                results.append(CheckResult("Windows version", "warn", platform.version(), "", cat))
        else:
            results.append(CheckResult(
                "Windows platform", "warn", os_name,
                "This GUI targets Windows 11; running on Linux for development.", cat,
            ))

        # Architecture
        arch = platform.architecture()[0]
        results.append(CheckResult(
            "64-bit architecture", "pass" if arch == "64bit" else "fail",
            arch, "64-bit is required for native libraries.", cat,
        ))

        # Python
        ver = sys.version_info
        results.append(CheckResult(
            "Python 3.10+", "pass" if ver >= (3, 10) else "fail",
            f"{ver.major}.{ver.minor}.{ver.micro}", "", cat,
        ))

        # CPU
        cpu_count = os.cpu_count() or 1
        results.append(CheckResult(
            "CPU cores (4+)", "pass" if cpu_count >= 4 else "warn",
            f"{cpu_count} cores", "", cat,
        ))

        # GPU
        try:
            import torch
            if torch.cuda.is_available():
                gpu = torch.cuda.get_device_name(0)
                results.append(CheckResult("CUDA GPU", "pass", gpu, "", cat))
            else:
                results.append(CheckResult("CUDA GPU", "warn", "No CUDA (CPU-only)", "", cat))
        except ImportError:
            results.append(CheckResult("PyTorch / GPU", "warn", "Not installed", "pip install torch", cat))

        # Network adapters
        try:
            from teleop.platform.network import list_network_interfaces
            ifaces = list_network_interfaces()
            real = [ni for ni in ifaces if ni.is_up and not ni.is_loopback and ni.ipv4]
            if real:
                results.append(CheckResult(
                    "Network adapters", "pass",
                    f"{len(real)} active adapter(s)", "", cat,
                ))
            else:
                results.append(CheckResult(
                    "Network adapters", "fail", "No active adapters",
                    "Connect an Ethernet adapter to the robot network.", cat,
                ))
        except Exception as exc:
            results.append(CheckResult("Network adapters", "fail", str(exc), "", cat))

        return results

    def run_dependency_check(self) -> list[CheckResult]:
        """Check all Python dependencies and native libraries."""
        results: list[CheckResult] = []
        cat = "Dependencies"

        deps = [
            ("NumPy", "numpy"),
            ("SciPy", "scipy"),
            ("CasADi", "casadi"),
            ("OpenCV", "cv2"),
            ("PyZMQ", "zmq"),
            ("PyYAML", "yaml"),
            ("PyTorch", "torch"),
            ("psutil", "psutil"),
            ("Pinocchio", "pinocchio"),
            ("NLopt", "nlopt"),
            ("logging_mp", "logging_mp"),
            ("sshkeyboard", "sshkeyboard"),
            ("pytransform3d", "pytransform3d"),
            ("trimesh", "trimesh"),
            ("anytree", "anytree"),
            ("lxml", "lxml"),
            ("PySide6", "PySide6"),
        ]

        for name, mod in deps:
            try:
                importlib.import_module(mod)
                results.append(CheckResult(name, "pass", "", "", cat))
            except ImportError:
                results.append(CheckResult(
                    name, "fail", "Not installed",
                    f"pip install {mod}  (or conda install {mod})", cat,
                ))

        # Submodules
        for name, mod, path in [
            ("televuer", "televuer", "teleop/televuer"),
            ("teleimager", "teleimager", "teleop/teleimager"),
            ("dex-retargeting", "dex_retargeting", "teleop/robot_control/dex-retargeting"),
        ]:
            try:
                importlib.import_module(mod)
                results.append(CheckResult(name, "pass", "", "", cat))
            except ImportError:
                results.append(CheckResult(
                    name, "fail", "Not installed",
                    f"cd {path} && pip install -e .", cat,
                ))

        # Unitree SDK
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize  # noqa
            results.append(CheckResult("unitree_sdk2_python", "pass", "", "", cat))
        except ImportError:
            results.append(CheckResult(
                "unitree_sdk2_python", "fail", "Not installed",
                "git clone https://github.com/unitreerobotics/unitree_sdk2_python.git && pip install -e .", cat,
            ))

        # CycloneDDS
        try:
            from cyclonedds import core  # noqa
            results.append(CheckResult("cyclonedds", "pass", "", "", cat))
        except ImportError:
            results.append(CheckResult("cyclonedds", "warn", "Not found", "pip install cyclonedds", cat))

        return results

    def run_connection_test(self, robot_ip: str, network_interface: str = None) -> list[CheckResult]:
        """Run a full connection test sequence."""
        results: list[CheckResult] = []
        cat = "Connection"

        # Windows
        results.append(CheckResult("Windows", "pass", platform.system(), "", cat))

        # Network adapter
        try:
            from teleop.platform.network import list_network_interfaces, resolve_interface_ip
            ifaces = list_network_interfaces()
            real = [ni for ni in ifaces if ni.is_up and not ni.is_loopback and ni.ipv4]
            if real:
                results.append(CheckResult("Network adapter", "pass",
                                           f"{len(real)} adapter(s)", "", cat))
            else:
                results.append(CheckResult("Network adapter", "fail", "No adapters", "", cat))
        except Exception as exc:
            results.append(CheckResult("Network adapter", "fail", str(exc), "", cat))

        # Robot IP format
        parts = robot_ip.split(".")
        ip_valid = len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
        results.append(CheckResult("Robot IP format", "pass" if ip_valid else "fail",
                                   robot_ip, "", cat))

        # Reachability
        if ip_valid:
            try:
                from teleop.platform.network import is_ip_reachable
                reachable = is_ip_reachable(robot_ip, timeout=2.0)
                results.append(CheckResult("Network reachability", "pass" if reachable else "fail",
                                           f"ping {robot_ip}",
                                           "Robot may be off or cable disconnected." if not reachable else "", cat))
            except Exception as exc:
                results.append(CheckResult("Network reachability", "fail", str(exc), "", cat))
        else:
            results.append(CheckResult("Network reachability", "skip", "Invalid IP", "", cat))

        # DDS
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            ChannelFactoryInitialize(0, networkInterface=network_interface)
            results.append(CheckResult("DDS initialization", "pass", "Domain 0", "", cat))
        except ImportError:
            results.append(CheckResult("DDS initialization", "skip", "SDK not installed", "", cat))
        except Exception as exc:
            results.append(CheckResult("DDS initialization", "fail", str(exc),
                                       "Check network interface and CycloneDDS.", cat))

        # Unitree SDK
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize  # noqa
            results.append(CheckResult("Unitree SDK", "pass", "", "", cat))
        except ImportError:
            results.append(CheckResult("Unitree SDK", "fail", "Not installed", "", cat))

        # Certificate
        try:
            from teleop.platform.paths import get_cert_paths
            from teleop.platform.certs import is_certificate_valid
            cert_path, key_path = get_cert_paths()
            if os.path.exists(cert_path) and os.path.exists(key_path):
                valid = is_certificate_valid(cert_path, key_path)
                results.append(CheckResult("Certificate", "pass" if valid else "warn",
                                           cert_path, "Regenerate certificate." if not valid else "", cat))
            else:
                results.append(CheckResult("Certificate", "fail", "Missing",
                                           "Generate certificate.", cat))
        except Exception as exc:
            results.append(CheckResult("Certificate", "warn", str(exc), "", cat))

        # HTTPS
        try:
            from teleop.platform.certs import get_lan_ip
            lan_ip = get_lan_ip()
            results.append(CheckResult("HTTPS endpoint", "pass",
                                       f"https://{lan_ip}:8012", "", cat))
        except Exception:
            results.append(CheckResult("HTTPS endpoint", "skip", "Cannot determine LAN IP", "", cat))

        # WebSocket / WebRTC — require televuer
        try:
            import televuer  # noqa
            results.append(CheckResult("WebRTC / XR", "pass", "televuer available", "", cat))
        except ImportError:
            results.append(CheckResult("WebRTC / XR", "skip", "televuer not installed", "", cat))

        return results
