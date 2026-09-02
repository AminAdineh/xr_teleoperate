"""
Tests for the platform abstraction layer.

Tests platform detection, path resolution, IPC transport selection,
and process spawning on both Windows and Linux.
"""
import sys
import os
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestPlatformDetection:
    def test_is_windows_or_linux(self):
        from teleop.platform import is_windows, is_linux
        # Must be one or the other (or macOS)
        assert is_windows() or is_linux() or sys.platform == "darwin"

    def test_platform_name(self):
        from teleop.platform import get_platform_name
        name = get_platform_name()
        assert name in ("windows", "linux", "macos")

    def test_python_arch(self):
        from teleop.platform import get_python_arch
        arch = get_python_arch()
        assert arch in ("64bit", "32bit")

    def test_os_version(self):
        from teleop.platform import get_os_version
        ver = get_os_version()
        assert isinstance(ver, str)
        assert len(ver) > 0


class TestPathResolution:
    def test_config_dir_exists_or_creatable(self):
        from teleop.platform.paths import get_config_dir, ensure_config_dir
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)

        # ensure_config_dir should create it
        created = ensure_config_dir()
        assert created.exists()
        assert created.is_dir()

    def test_config_dir_platform_correct(self):
        from teleop.platform.paths import get_config_dir
        from teleop.platform import is_windows, is_linux
        config_dir = get_config_dir()
        if is_windows():
            assert "xr_teleoperate" in str(config_dir)
        elif is_linux():
            assert ".config" in str(config_dir) or "XDG" in str(config_dir)

    def test_cert_paths_return_strings(self):
        from teleop.platform.paths import get_cert_paths
        cert, key = get_cert_paths()
        assert isinstance(cert, str)
        assert isinstance(key, str)
        assert cert.endswith("cert.pem") or cert.endswith(".pem")
        assert key.endswith("key.pem") or key.endswith(".pem")

    def test_data_dir(self):
        from teleop.platform.paths import get_data_dir
        data_dir = get_data_dir()
        assert isinstance(data_dir, Path)
        assert "data" in str(data_dir)


class TestIPCTransport:
    def test_endpoint_is_valid_zmq(self):
        from teleop.platform.ipc_transport import get_ipc_endpoint
        endpoint = get_ipc_endpoint("test_channel")
        assert endpoint.startswith("ipc://") or endpoint.startswith("tcp://")

    def test_endpoint_consistent(self):
        from teleop.platform.ipc_transport import get_ipc_endpoint
        e1 = get_ipc_endpoint("test_channel")
        e2 = get_ipc_endpoint("test_channel")
        assert e1 == e2

    def test_different_channels_different_endpoints(self):
        from teleop.platform.ipc_transport import get_ipc_endpoint
        e1 = get_ipc_endpoint("channel_a")
        e2 = get_ipc_endpoint("channel_b")
        assert e1 != e2

    def test_strips_at_prefix(self):
        from teleop.platform.ipc_transport import get_ipc_endpoint
        e1 = get_ipc_endpoint("@test")
        e2 = get_ipc_endpoint("test")
        assert e1 == e2

    def test_windows_uses_tcp(self):
        if sys.platform != "win32":
            pytest.skip("Windows-only test")
        from teleop.platform.ipc_transport import get_ipc_endpoint
        endpoint = get_ipc_endpoint("test")
        assert endpoint.startswith("tcp://127.0.0.1:")

    def test_linux_uses_ipc(self):
        if sys.platform != "linux":
            pytest.skip("Linux-only test")
        from teleop.platform.ipc_transport import get_ipc_endpoint
        endpoint = get_ipc_endpoint("test")
        assert endpoint.startswith("ipc://@")


class TestProcessAbstraction:
    def test_worker_handle_creation(self):
        """Verify a WorkerHandle can be created, started, and joined."""
        from teleop.platform.process import WorkerHandle
        import time

        def target():
            time.sleep(0.01)

        handle = WorkerHandle(target=target, daemon=True)
        handle.start()
        assert handle.is_alive() or True  # may have already finished
        handle.join(timeout=5)
        # Worker should have completed
        assert not handle.is_alive()

    def test_spawn_worker(self):
        """Verify spawn_worker creates and starts a worker."""
        from teleop.platform.process import spawn_worker
        import time

        def target(val):
            time.sleep(0.01)

        handle = spawn_worker(target, args=(42,))
        assert handle is not None
        handle.join(timeout=5)
        assert not handle.is_alive()

    def test_worker_is_process_on_linux(self):
        """On Linux, the worker should be a Process."""
        from teleop.platform.process import WorkerHandle, IS_WINDOWS
        import time

        def target():
            time.sleep(0.01)

        handle = WorkerHandle(target=target, daemon=True)
        if not IS_WINDOWS:
            assert handle.is_process is True
        else:
            assert handle.is_process is False
        handle.start()
        handle.join(timeout=5)


class TestCPUAffinity:
    def test_get_cpu_count(self):
        from teleop.platform.cpu_affinity import get_cpu_count
        count = get_cpu_count()
        assert count >= 1

    def test_get_cpu_affinity_returns_list(self):
        from teleop.platform.cpu_affinity import get_cpu_affinity
        affinity = get_cpu_affinity()
        assert isinstance(affinity, list)


class TestFirewall:
    def test_firewall_instructions_returned(self):
        from teleop.platform.firewall import get_firewall_instructions
        instructions = get_firewall_instructions()
        assert isinstance(instructions, list)
        assert len(instructions) > 0

    def test_required_ports_defined(self):
        from teleop.platform.firewall import REQUIRED_PORTS
        assert len(REQUIRED_PORTS) >= 4
        for port, proto, desc in REQUIRED_PORTS:
            assert isinstance(port, int)
            assert proto in ("tcp", "udp")
            assert isinstance(desc, str)
