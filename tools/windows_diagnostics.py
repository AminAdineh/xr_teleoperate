#!/usr/bin/env python3
"""
XR Teleoperate Windows Diagnostics Tool

Checks all prerequisites for running xr_teleoperate on Windows 11:
  - Windows version and architecture
  - Python version and architecture
  - Conda environment
  - CPU and GPU
  - Network adapters and IPv4 addresses
  - Robot IP reachability
  - Required ports
  - DDS availability (unitree_sdk2_python)
  - Pinocchio import
  - OpenCV import
  - ZMQ import
  - WebRTC dependencies
  - Certificate files
  - Firewall rules

Usage:
    python tools/windows_diagnostics.py
    python tools/windows_diagnostics.py --robot-ip 192.168.123.164
"""
import sys
import os
import platform
import socket
import subprocess
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class Diagnostics:
    def __init__(self, robot_ip: str = "192.168.123.164"):
        self.robot_ip = robot_ip
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def check(self, name: str, condition: bool, detail: str = "", fix: str = ""):
        if condition:
            print(f"[OK]   {name}" + (f" - {detail}" if detail else ""))
            self.passed += 1
        else:
            print(f"[FAIL] {name}" + (f" - {detail}" if detail else ""))
            if fix:
                print(f"       FIX: {fix}")
            self.failed += 1

    def warn(self, name: str, detail: str = "", fix: str = ""):
        print(f"[WARN] {name}" + (f" - {detail}" if detail else ""))
        if fix:
            print(f"       FIX: {fix}")
        self.warnings += 1

    def section(self, title: str):
        print(f"\n--- {title} ---")

    def run(self):
        self.check_os()
        self.check_python()
        self.check_conda()
        self.check_cpu()
        self.check_gpu()
        self.check_network()
        self.check_robot_reachability()
        self.check_dependencies()
        self.check_certificates()
        self.check_firewall()
        self.summary()

    def check_os(self):
        self.section("Operating System")
        is_win = sys.platform == "win32"
        self.check("Windows platform", is_win,
                   f"{platform.system()} {platform.version()}" if is_win else f"{platform.system()} {platform.release()}",
                   "This project is designed for Windows 11. On Linux, use the original upstream code.")

        if is_win:
            build = int(platform.version().split('.')[-1])
            self.check("Windows 11 (Build 22000+)", build >= 22000,
                       f"Build {build}",
                       "Windows 11 is recommended. Windows 10 may work but is not officially supported.")

        arch = platform.architecture()[0]
        self.check("64-bit Python", arch == "64bit", f"Python is {arch}",
                   "Install 64-bit Python (conda create -n xr_teleoperate python=3.10)")

    def check_python(self):
        self.section("Python")
        ver = sys.version_info
        self.check("Python 3.10+", ver >= (3, 10), f"Python {ver.major}.{ver.minor}.{ver.micro}")
        self.check("Python 3.12 or lower", ver < (3, 13), f"Python {ver.major}.{ver.minor}",
                   "Python 3.13+ is not yet tested. Use Python 3.10.")

    def check_conda(self):
        self.section("Conda")
        conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
        if conda_env:
            self.check("Conda environment active", True, f"Environment: {conda_env}")
        else:
            self.warn("Conda environment", "No conda environment detected",
                       "Activate with: conda activate xr_teleoperate")

    def check_cpu(self):
        self.section("CPU")
        cpu_count = os.cpu_count() or 1
        self.check("CPU cores", cpu_count >= 4, f"{cpu_count} cores",
                   "At least 4 CPU cores are recommended for real-time control.")

    def check_gpu(self):
        self.section("GPU")
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                self.check("CUDA GPU", True, f"{gpu_name}")
            else:
                self.warn("CUDA GPU", "No CUDA GPU detected (CPU-only mode)",
                          "A CUDA GPU is recommended for simulation but not required for teleoperation.")
        except ImportError:
            self.warn("PyTorch", "Not installed",
                      "pip install torch")

    def check_network(self):
        self.section("Network Adapters")
        try:
            from teleop.platform.network import list_network_interfaces
            interfaces = list_network_interfaces()
            real_ifaces = [ni for ni in interfaces if not ni.is_loopback and ni.is_up and ni.ipv4]

            if real_ifaces:
                for ni in real_ifaces:
                    self.check(f"Adapter: {ni.name}", True, f"IPv4: {ni.ipv4}")
            else:
                self.warn("Network adapters", "No active non-loopback adapters with IPv4 found",
                          "Connect an Ethernet adapter to the robot network.")

            # Check for robot-network adapter (192.168.123.x)
            robot_adapter = [ni for ni in real_ifaces if ni.ipv4.startswith("192.168.123.")]
            if robot_adapter:
                self.check("Robot network adapter", True,
                           f"{robot_adapter[0].name} ({robot_adapter[0].ipv4})")
            else:
                self.warn("Robot network adapter",
                          "No adapter on 192.168.123.x subnet",
                          f"Set your adapter IP to 192.168.123.x to reach the robot at {self.robot_ip}")
        except ImportError:
            self.warn("Network enumeration", "psutil not installed",
                      "pip install psutil")

    def check_robot_reachability(self):
        self.section(f"Robot Reachability ({self.robot_ip})")
        try:
            from teleop.platform.network import is_ip_reachable
            reachable = is_ip_reachable(self.robot_ip, timeout=2.0)
            self.check(f"Robot IP {self.robot_ip} reachable", reachable,
                       "" if reachable else "No response to ping",
                       f"Check Ethernet connection and that the robot is powered on at {self.robot_ip}")
        except Exception as e:
            self.warn("Robot reachability", f"Check failed: {e}")

    def check_dependencies(self):
        self.section("Python Dependencies")

        deps = [
            ("NumPy", "numpy"),
            ("SciPy", "scipy"),
            ("OpenCV", "cv2"),
            ("PyZMQ", "zmq"),
            ("PyYAML", "yaml"),
            ("CasADi", "casadi"),
            ("Pinocchio", "pinocchio"),
            ("PyTorch", "torch"),
            ("Meshcat", "meshcat"),
            ("Rerun SDK", "rerun"),
            ("psutil", "psutil"),
            ("sshkeyboard", "sshkeyboard"),
            ("logging_mp", "logging_mp"),
            ("Vuer", "vuer"),
            ("pytransform3d", "pytransform3d"),
            ("trimesh", "trimesh"),
            ("anytree", "anytree"),
            ("lxml", "lxml"),
            ("NLopt", "nlopt"),
        ]

        for name, module in deps:
            try:
                __import__(module)
                self.check(name, True)
            except ImportError:
                self.check(name, False, fix=f"pip install {module}")

        # Unitree SDK
        self.section("Unitree SDK")
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            self.check("unitree_sdk2_python", True)
        except ImportError:
            self.check("unitree_sdk2_python", False,
                       fix="git clone https://github.com/unitreerobotics/unitree_sdk2_python.git && cd unitree_sdk2_python && pip install -e .")

        # DDS initialization test
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            ChannelFactoryInitialize(0)
            self.check("DDS initialization", True)
        except Exception as e:
            self.warn("DDS initialization", f"Failed: {e}",
                      "Ensure CycloneDDS is properly installed and a network interface is available.")
        try:
            from cyclonedds import core as dds_core
            self.check("cyclonedds Python bindings", True)
        except ImportError:
            self.warn("cyclonedds Python bindings", "Not found",
                      "Install via: pip install cyclonedds")

        # Submodules
        self.section("Submodules")
        for name, module in [
            ("televuer", "televuer"),
            ("teleimager", "teleimager"),
            ("dex_retargeting", "dex_retargeting"),
        ]:
            try:
                __import__(module)
                self.check(name, True)
            except ImportError:
                self.check(name, False,
                           fix=f"cd teleop/{'televuer' if module == 'televuer' else 'teleimager' if module == 'teleimager' else 'robot_control/dex-retargeting'} && pip install -e .")

    def check_certificates(self):
        self.section("SSL Certificates")
        try:
            from teleop.platform.paths import get_cert_paths, get_cert_dir
            cert_path, key_path = get_cert_paths()
            cert_exists = os.path.exists(cert_path)
            key_exists = os.path.exists(key_path)
            self.check("Certificate file", cert_exists, cert_path if cert_exists else f"Missing: {cert_path}",
                       f"Run scripts/install_windows.ps1 or generate manually in {get_cert_dir()}")
            self.check("Key file", key_exists, key_path if key_exists else f"Missing: {key_path}",
                       f"Run scripts/install_windows.ps1 or generate manually in {get_cert_dir()}")
        except Exception as e:
            self.warn("Certificate check", f"Failed: {e}")

    def check_firewall(self):
        self.section("Windows Defender Firewall")
        if sys.platform != "win32":
            self.warn("Firewall check", "Skipped (not Windows)")
            return

        try:
            from teleop.platform.firewall import check_firewall_rules, is_admin
            admin = is_admin()
            self.check("Administrator privileges", admin,
                       "" if admin else "Not running as admin",
                       "Run diagnostics as admin for firewall rule creation")

            rules = check_firewall_rules()
            for port, exists in rules.items():
                self.check(f"Firewall rule for port {port}", exists,
                           "" if exists else "No rule found",
                           f"Run: scripts/setup_windows.ps1 (as Administrator)")
        except Exception as e:
            self.warn("Firewall check", f"Failed: {e}")

    def summary(self):
        print(f"\n{'=' * 60}")
        print(f"  Diagnostics Summary: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")
        print(f"{'=' * 60}")

        if self.failed == 0 and self.warnings == 0:
            print("\n  System is ready for teleoperation.\n")
            return 0
        elif self.failed == 0:
            print("\n  System is ready with warnings. Review [WARN] items above.\n")
            return 0
        else:
            print(f"\n  {self.failed} issue(s) must be resolved before teleoperation.\n")
            return 1


def main():
    parser = argparse.ArgumentParser(description="XR Teleoperate Windows Diagnostics")
    parser.add_argument("--robot-ip", type=str, default="192.168.123.164",
                        help="Robot IP address to check reachability (default: 192.168.123.164)")
    args = parser.parse_args()

    print("=" * 60)
    print("  XR Teleoperate Windows Diagnostics")
    print("=" * 60)

    diag = Diagnostics(robot_ip=args.robot_ip)
    return diag.run()


if __name__ == "__main__":
    sys.exit(main())
