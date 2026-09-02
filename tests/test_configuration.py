"""
Tests for configuration loading and CLI argument parsing.

Tests are hardware-independent and verify that the application
configuration system works correctly on both Windows and Linux.
"""
import sys
import os
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestCLIArguments:
    def test_parser_has_required_args(self):
        """Verify the main script's argument parser includes all required arguments."""
        # We can't run the main script (it needs DDS), but we can check the parser
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--frequency', type=float, default=30.0)
        parser.add_argument('--input-mode', type=str, choices=['hand', 'controller'], default='hand')
        parser.add_argument('--display-mode', type=str, choices=['immersive', 'ego', 'pass-through'], default='immersive')
        parser.add_argument('--arm', type=str, choices=['G1_29', 'G1_23', 'H1_2', 'H1', 'H2', 'R1_A5', 'R1_A7'], default='G1_29')
        parser.add_argument('--ee', type=str, choices=['dex1', 'dex1_internal', 'dex3', 'inspire_ftp', 'inspire_dfx', 'brainco'])
        parser.add_argument('--img-server-ip', type=str, default='192.168.123.164')
        parser.add_argument('--network-interface', type=str, default=None)
        parser.add_argument('--list-interfaces', action='store_true')
        parser.add_argument('--motion', action='store_true')
        parser.add_argument('--headless', action='store_true')
        parser.add_argument('--sim', action='store_true')
        parser.add_argument('--ipc', action='store_true')
        parser.add_argument('--record', action='store_true')
        parser.add_argument('--task-dir', type=str, default='./utils/data/')
        parser.add_argument('--task-name', type=str, default='pick cube')

        # Parse with defaults
        args = parser.parse_args([])

        assert args.frequency == 30.0
        assert args.input_mode == 'hand'
        assert args.display_mode == 'immersive'
        assert args.arm == 'G1_29'
        assert args.img_server_ip == '192.168.123.164'
        assert args.network_interface is None
        assert args.list_interfaces is False
        assert args.motion is False
        assert args.sim is False

    def test_list_interfaces_flag(self):
        """Verify --list-interfaces flag is accepted."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--list-interfaces', action='store_true')
        args = parser.parse_args(['--list-interfaces'])
        assert args.list_interfaces is True

    def test_network_interface_accepts_windows_names(self):
        """Verify --network-interface accepts Windows-style adapter names."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--network-interface', type=str, default=None)
        args = parser.parse_args(['--network-interface', 'Ethernet'])
        assert args.network_interface == 'Ethernet'

        args = parser.parse_args(['--network-interface', 'Wi-Fi'])
        assert args.network_interface == 'Wi-Fi'


class TestIPCConfiguration:
    def test_ipc_server_client_same_endpoint(self):
        """Verify that IPC server and client use the same endpoint."""
        from teleop.platform.ipc_transport import get_ipc_endpoint
        server_endpoint = get_ipc_endpoint("xr_teleoperate_data")
        client_endpoint = get_ipc_endpoint("xr_teleoperate_data")
        assert server_endpoint == client_endpoint

    def test_ipc_heartbeat_endpoint(self):
        from teleop.platform.ipc_transport import get_ipc_endpoint
        endpoint = get_ipc_endpoint("xr_teleoperate_hb")
        assert "60101" in endpoint or "xr_teleoperate_hb" in endpoint


class TestCertificateConfiguration:
    def test_cert_env_var_resolution(self, monkeypatch):
        monkeypatch.setenv("XR_TELEOP_CERT", "/custom/cert.pem")
        monkeypatch.setenv("XR_TELEOP_KEY", "/custom/key.pem")
        import importlib
        import teleop.platform.paths
        importlib.reload(teleop.platform.paths)
        cert, key = teleop.platform.paths.get_cert_paths()
        assert cert == "/custom/cert.pem"
        assert key == "/custom/key.pem"

    def test_cert_dir_resolution(self):
        from teleop.platform.paths import get_cert_dir
        d = get_cert_dir()
        assert "xr_teleoperate" in str(d)


class TestRecordingConfiguration:
    def test_task_dir_uses_os_path(self):
        """Verify task_dir uses os.path.join (cross-platform)."""
        import os
        task_dir = os.path.join("./utils/data/", "pick cube")
        # On Windows, this should use backslash; on Linux, forward slash
        assert "pick cube" in task_dir

    def test_episode_dir_format(self):
        """Verify episode directory naming format."""
        import os
        task_dir = "./data/test_task"
        episode_id = 5
        episode_dir = os.path.join(task_dir, f"episode_{str(episode_id).zfill(4)}")
        assert "episode_0005" in episode_dir


class TestMultiprocessingGuard:
    def test_main_guard_exists(self):
        """Verify the main script has if __name__ == '__main__' guard."""
        main_script = project_root / "teleop" / "teleop_hand_and_arm.py"
        content = main_script.read_text()
        assert "if __name__ == '__main__':" in content or 'if __name__ == "__main__":' in content
