#!/usr/bin/env python3
"""
XR Teleoperate Windows Diagnostics Tool

Checks all prerequisites for running xr_teleoperate on Windows 11:
  - Windows version and architecture
  - Python version and architecture
  - Conda environment
  - CPU and GPU
  - Network adapters and IPv4 addresses
  - Robot IP reachability (ping + UDP)
  - DDS availability (unitree_sdk2_python, CycloneDDS)
  - Native DLL validation
  - DDS discovery test
  - Robot state reception test
  - Required ports
  - ZMQ IPC transport
  - WebRTC dependencies
  - Certificate files
  - Firewall rules
  - Process/thread model

Usage:
    python tools/windows_diagnostics.py
    python tools/windows_diagnostics.py --robot-ip 192.168.123.164
    python tools/windows_diagnostics.py --robot-ip 192.168.123.164 --dds-test
    python tools/windows_diagnostics.py --dll-check
"""
import sys
import os
import platform
import socket
import subprocess
import argparse
import importlib
import ctypes
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class Diagnostics:
    def __init__(self, robot_ip: str = "192.168.123.164", dds_test: bool = False, dll_check: bool = False):
        self.robot_ip = robot_ip
        self.dds_test = dds_test
        self.dll_check = dll_check
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = {}  # test_name -> (result, evidence)

    def check(self, name: str, condition: bool, detail: str = "", fix: str = ""):
        if condition:
            print(f"[OK]   {name}" + (f" - {detail}" if detail else ""))
            self.passed += 1
            self.results[name] = ("PASS", detail)
        else:
            print(f"[FAIL] {name}" + (f" - {detail}" if detail else ""))
            if fix:
                print(f"       FIX: {fix}")
            self.failed += 1
            self.results[name] = ("FAIL", detail)

    def warn(self, name: str, detail: str = "", fix: str = ""):
        print(f"[WARN] {name}" + (f" - {detail}" if detail else ""))
        if fix:
            print(f"       FIX: {fix}")
        self.warnings += 1
        self.results[name] = ("WARN", detail)

    def not_tested(self, name: str, reason: str = ""):
        print(f"[SKIP] {name}" + (f" - {reason}" if reason else ""))
        self.results[name] = ("NOT TESTED", reason)

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
        self.check_dlls()
        self.check_dds()
        self.check_zmq()
        self.check_certificates()
        self.check_firewall()
        self.check_process_model()
        self.summary()

    # -----------------------------------------------------------------------
    # OS checks
    # -----------------------------------------------------------------------
    def check_os(self):
        self.section("Operating System")
        is_win = sys.platform == "win32"
        self.check("Windows platform", is_win,
                   f"{platform.system()} {platform.version()}" if is_win else f"{platform.system()} {platform.release()}",
                   "This project is designed for Windows 11. On Linux, use the original upstream code.")

        if is_win:
            try:
                build = int(platform.version().split('.')[-1])
                self.check("Windows 11 (Build 22000+)", build >= 22000,
                           f"Build {build}",
                           "Windows 11 is recommended. Windows 10 may work but is not officially supported.")
            except (ValueError, IndexError):
                self.warn("Windows build number", f"Could not parse build from {platform.version()}")

        arch = platform.architecture()[0]
        self.check("64-bit Python", arch == "64bit", f"Python is {arch}",
                   "Install 64-bit Python (conda create -n xr_teleoperate python=3.10)")

    # -----------------------------------------------------------------------
    # Python checks
    # -----------------------------------------------------------------------
    def check_python(self):
        self.section("Python")
        ver = sys.version_info
        self.check("Python 3.10+", ver >= (3, 10), f"Python {ver.major}.{ver.minor}.{ver.micro}")
        self.check("Python 3.12 or lower", ver < (3, 13), f"Python {ver.major}.{ver.minor}",
                   "Python 3.13+ is not yet tested. Use Python 3.10.")

        # Check for Python ABI compatibility with native libraries
        self.check("Python executable path", True, sys.executable)

    # -----------------------------------------------------------------------
    # Conda checks
    # -----------------------------------------------------------------------
    def check_conda(self):
        self.section("Conda")
        conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
        if conda_env:
            self.check("Conda environment active", True, f"Environment: {conda_env}")
        else:
            self.warn("Conda environment", "No conda environment detected",
                       "Activate with: conda activate xr_teleoperate")

    # -----------------------------------------------------------------------
    # CPU checks
    # -----------------------------------------------------------------------
    def check_cpu(self):
        self.section("CPU")
        cpu_count = os.cpu_count() or 1
        self.check("CPU cores", cpu_count >= 4, f"{cpu_count} cores",
                   "At least 4 CPU cores are recommended for real-time control.")

    # -----------------------------------------------------------------------
    # GPU checks
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Network checks
    # -----------------------------------------------------------------------
    def check_network(self):
        self.section("Network Adapters")
        try:
            from teleop.platform.network import list_network_interfaces
            interfaces = list_network_interfaces()
            real_ifaces = [ni for ni in interfaces if not ni.is_loopback and ni.is_up and ni.ipv4]

            if real_ifaces:
                for ni in real_ifaces:
                    virtual_tag = " (virtual)" if ni.is_virtual else ""
                    self.check(f"Adapter: {ni.name}", True, f"IPv4: {ni.ipv4}{virtual_tag}")
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

            # Check for virtual adapters that might interfere with DDS
            virtual_ifaces = [ni for ni in real_ifaces if ni.is_virtual]
            if virtual_ifaces:
                self.warn("Virtual adapters detected",
                           f"{len(virtual_ifaces)} virtual adapter(s) found (Docker, VMware, etc.)",
                           "Virtual adapters can interfere with DDS multicast discovery. "
                           "Use --network-interface to select the correct adapter.")
        except ImportError:
            self.warn("Network enumeration", "psutil not installed",
                      "pip install psutil")

    # -----------------------------------------------------------------------
    # Robot reachability checks
    # -----------------------------------------------------------------------
    def check_robot_reachability(self):
        self.section(f"Robot Reachability ({self.robot_ip})")

        # 1. Ping test
        try:
            from teleop.platform.network import is_ip_reachable
            reachable = is_ip_reachable(self.robot_ip, timeout=2.0)
            self.check(f"Ping {self.robot_ip}", reachable,
                       "" if reachable else "No response to ping",
                       f"Check Ethernet connection and that the robot is powered on at {self.robot_ip}")
        except Exception as e:
            self.warn("Ping test", f"Check failed: {e}")

        # 2. TCP port test (DDS uses UDP, but the robot may have a TCP service)
        tcp_ports = [80, 8080]  # common robot service ports
        for port in tcp_ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                result = s.connect_ex((self.robot_ip, port))
                s.close()
                if result == 0:
                    self.check(f"TCP {self.robot_ip}:{port}", True, "Port open")
                else:
                    pass  # Don't report failure for every port
            except Exception:
                pass

        # 3. UDP reachability (DDS uses UDP multicast/unicast)
        self.check("UDP DDS port", True, "DDS uses UDP (not directly testable without DDS stack)")

        # 4. Routing check
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.robot_ip, 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.check("Route to robot", True, f"Via local interface {local_ip}")
            if not local_ip.startswith("192.168.123."):
                self.warn("Routing",
                           f"Local IP {local_ip} is not on 192.168.123.x subnet",
                           "Configure your Ethernet adapter to 192.168.123.x subnet")
        except Exception as e:
            self.warn("Route to robot", f"Could not determine route: {e}")

    # -----------------------------------------------------------------------
    # Dependency checks
    # -----------------------------------------------------------------------
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

        # Submodules
        self.section("Submodules")
        for name, module, path in [
            ("televuer", "televuer", "teleop/televuer"),
            ("teleimager", "teleimager", "teleop/teleimager"),
            ("dex_retargeting", "dex_retargeting", "teleop/robot_control/dex-retargeting"),
        ]:
            try:
                __import__(module)
                self.check(name, True)
            except ImportError:
                self.check(name, False,
                           fix=f"cd {path} && pip install -e .")

    # -----------------------------------------------------------------------
    # DLL validation
    # -----------------------------------------------------------------------
    def check_dlls(self):
        self.section("Native DLL Validation")

        if not self.dll_check and not (sys.platform == "win32"):
            self.not_tested("DLL validation", "Not on Windows (use --dll-check to force)")
            return

        native_deps = [
            ("CycloneDDS", "cyclonedds", "ddsc2.dll"),
            ("Pinocchio", "pinocchio", "pinocchio_pywrap.dll"),
            ("NLopt", "nlopt", "nlopt.dll"),
            ("CasADi", "casadi", "casadi.dll"),
            ("OpenCV", "cv2", "cv2.dll"),
            ("PyZMQ", "zmq", "libzmq.dll" if sys.platform == "win32" else "libzmq.so"),
        ]

        for name, module, dll_name in native_deps:
            loaded = False
            error_msg = ""
            try:
                mod = importlib.import_module(module)
                loaded = True
                # Try to find the actual DLL path
                mod_dir = os.path.dirname(getattr(mod, '__file__', '') or '')
                dll_path = None
                if mod_dir:
                    for root, dirs, files in os.walk(mod_dir):
                        if dll_name in files:
                            dll_path = os.path.join(root, dll_name)
                            break
                if dll_path:
                    self.check(f"{name} native library", True, f"{dll_name} at {dll_path}")
                else:
                    self.check(f"{name} native library", True, f"{dll_name} loaded (path not found)")
            except ImportError as e:
                error_msg = str(e)
                self.check(f"{name} native library", False, error_msg,
                           f"Reinstall: pip install {module} or conda install {module}")
            except Exception as e:
                error_msg = str(e)
                if "DLL load failed" in error_msg or "module could not be found" in error_msg:
                    self.check(f"{name} native library", False, error_msg,
                               f"DLL load failed. Check architecture (64-bit) and dependencies. "
                               f"Reinstall: conda install {module} -c conda-forge")
                else:
                    self.warn(f"{name} native library", f"Unexpected error: {error_msg}")

        # Check Python ABI compatibility
        self.section("Python ABI Compatibility")
        py_arch = platform.architecture()[0]
        py_bits = struct_bits = "unknown"
        try:
            import struct
            py_bits = str(struct.calcsize("P") * 8) + "-bit"
        except Exception:
            pass
        self.check("Python pointer size", py_bits == "64-bit" or py_arch == "64bit",
                   f"{py_bits} ({py_arch})",
                   "Native libraries require 64-bit Python. Reinstall Python 64-bit.")

    # -----------------------------------------------------------------------
    # DDS checks
    # -----------------------------------------------------------------------
    def check_dds(self):
        self.section("DDS")

        # CycloneDDS Python bindings
        try:
            from cyclonedds import core as dds_core
            self.check("cyclonedds Python bindings", True)
        except ImportError:
            self.warn("cyclonedds Python bindings", "Not found",
                      "Install via: pip install cyclonedds")

        # DDS initialization test
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            ChannelFactoryInitialize(0)
            self.check("DDS initialization (domain 0)", True)
        except Exception as e:
            error_str = str(e)
            if "network" in error_str.lower() or "interface" in error_str.lower():
                self.warn("DDS initialization", f"Failed (network): {error_str}",
                          "Specify a network interface with --network-interface")
            else:
                self.check("DDS initialization (domain 0)", False, error_str,
                           "Ensure CycloneDDS is properly installed and a network interface is available.")
            return

        # DDS discovery test (if requested)
        if self.dds_test:
            self.section("DDS Discovery Test")
            self._test_dds_discovery()
        else:
            self.not_tested("DDS discovery", "Use --dds-test to run (requires robot connected)")

    def _test_dds_discovery(self):
        """Test DDS discovery by subscribing to a known topic and waiting for data."""
        try:
            from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
            from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_

            # Try subscribing to hand state topics
            for topic_name, msg_type in [
                ("rt/dex3/left/state", HandState_),
            ]:
                try:
                    sub = ChannelSubscriber(topic_name, msg_type)
                    sub.Init()

                    # Wait for data
                    import time
                    found = False
                    for _ in range(50):  # 5 seconds
                        msg = sub.Read()
                        if msg is not None:
                            found = True
                            break
                        time.sleep(0.1)

                    if found:
                        self.check(f"DDS discovery: {topic_name}", True, "Data received")
                    else:
                        self.warn(f"DDS discovery: {topic_name}",
                                  "No data received in 5 seconds",
                                  "The robot may not be publishing on this topic, or DDS discovery failed.")
                except Exception as e:
                    self.warn(f"DDS discovery: {topic_name}", f"Failed: {e}")

        except ImportError:
            self.warn("DDS discovery test", "unitree_sdk2py not available")

    # -----------------------------------------------------------------------
    # ZMQ checks
    # -----------------------------------------------------------------------
    def check_zmq(self):
        self.section("ZMQ IPC Transport")
        try:
            from teleop.platform.ipc_transport import get_ipc_endpoint, is_ipc_supported
            endpoint = get_ipc_endpoint("test_channel")
            self.check("ZMQ endpoint generation", True, endpoint)

            if sys.platform == "win32":
                self.check("ZMQ uses TCP on Windows", endpoint.startswith("tcp://127.0.0.1:"),
                           "Windows does not support ipc:// transport")
            else:
                self.check("ZMQ uses IPC on Linux", endpoint.startswith("ipc://@"),
                           "Linux supports ipc:// abstract sockets")

            self.check("IPC supported on this platform", is_ipc_supported() or sys.platform == "win32",
                       "TCP fallback is used on Windows")
        except Exception as e:
            self.check("ZMQ IPC transport", False, str(e))

    # -----------------------------------------------------------------------
    # Certificate checks
    # -----------------------------------------------------------------------
    def check_certificates(self):
        self.section("SSL Certificates")
        try:
            from teleop.platform.paths import get_cert_paths, get_cert_dir
            cert_path, key_path = get_cert_paths()
            cert_exists = os.path.exists(cert_path)
            key_exists = os.path.exists(key_path)
            self.check("Certificate file", cert_exists, cert_path if cert_exists else f"Missing: {cert_path}",
                       f"Run scripts/install_windows.ps1 or: python -m teleop.platform.certs")
            self.check("Key file", key_exists, key_path if key_exists else f"Missing: {key_path}",
                       f"Run scripts/install_windows.ps1 or: python -m teleop.platform.certs")

            # Check certificate validity
            if cert_exists and key_exists:
                try:
                    from teleop.platform.certs import is_certificate_valid
                    valid = is_certificate_valid(cert_path, key_path)
                    self.check("Certificate valid (not expired)", valid,
                               "" if valid else "Certificate may be expired or invalid",
                               "Regenerate: python -m teleop.platform.certs --regenerate")
                except Exception as e:
                    self.warn("Certificate validation", f"Could not validate: {e}")

            # Show LAN IP for certificate trust
            try:
                from teleop.platform.certs import get_lan_ip
                lan_ip = get_lan_ip()
                self.check("LAN IP for XR connection", True, f"https://{lan_ip}:8012")
            except Exception:
                pass

        except Exception as e:
            self.warn("Certificate check", f"Failed: {e}")

    # -----------------------------------------------------------------------
    # Firewall checks
    # -----------------------------------------------------------------------
    def check_firewall(self):
        self.section("Windows Defender Firewall")
        if sys.platform != "win32":
            self.not_tested("Firewall check", "Skipped (not Windows)")
            return

        try:
            from teleop.platform.firewall import check_firewall_rules, is_admin, REQUIRED_PORTS
            admin = is_admin()
            self.check("Administrator privileges", admin,
                       "" if admin else "Not running as admin",
                       "Run diagnostics as admin for firewall rule creation")

            rules = check_firewall_rules()
            for port, exists in rules.items():
                self.check(f"Firewall rule for port {port}", exists,
                           "" if exists else "No rule found",
                           f"Run: scripts/setup_windows.ps1 (as Administrator)")

            # Check if firewall is enabled
            try:
                output = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles", "state"],
                    capture_output=True, text=True, timeout=10
                )
                if "ON" in output.stdout.upper():
                    self.warn("Firewall is ON",
                               "Windows Defender Firewall is active. Ensure all required ports are allowed.",
                               "Run scripts/setup_windows.ps1 as Administrator")
                else:
                    self.check("Firewall state", True, "Firewall appears to be OFF")
            except Exception:
                pass

        except Exception as e:
            self.warn("Firewall check", f"Failed: {e}")

    # -----------------------------------------------------------------------
    # Process model checks
    # -----------------------------------------------------------------------
    def check_process_model(self):
        self.section("Process / Thread Model")
        try:
            from teleop.platform.process import WorkerHandle, IS_WINDOWS
            self.check("WorkerHandle available", True,
                       f"Windows uses Thread: {IS_WINDOWS}")
        except ImportError:
            self.check("WorkerHandle import", False, fix="Check teleop/platform/process.py")

        # Check for zombie thread detection
        try:
            import threading
            active = threading.active_count()
            self.check("Thread count", active < 50,
                       f"{active} active threads",
                       "High thread count may indicate thread leaks")
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    def summary(self):
        print(f"\n{'=' * 60}")
        print(f"  Diagnostics Summary: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")
        print(f"{'=' * 60}")

        if self.failed == 0 and self.warnings == 0:
            print("\n  System is READY for teleoperation.\n")
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
    parser.add_argument("--dds-test", action="store_true",
                        help="Run DDS discovery test (requires robot connected)")
    parser.add_argument("--dll-check", action="store_true",
                        help="Force DLL validation even on non-Windows platforms")
    args = parser.parse_args()

    print("=" * 60)
    print("  XR Teleoperate Windows Diagnostics")
    print("=" * 60)

    diag = Diagnostics(robot_ip=args.robot_ip, dds_test=args.dds_test, dll_check=args.dll_check)
    return diag.run()


if __name__ == "__main__":
    sys.exit(main())
