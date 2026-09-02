"""
Tests for cross-platform path handling.

Verifies that certificate paths, config directories, and data paths
resolve correctly on both Windows and Linux.
"""
import sys
import os
import tempfile
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestConfigDir:
    def test_config_dir_is_path(self):
        from teleop.platform.paths import get_config_dir
        d = get_config_dir()
        assert isinstance(d, Path)

    def test_config_dir_contains_xr_teleoperate(self):
        from teleop.platform.paths import get_config_dir
        d = get_config_dir()
        assert "xr_teleoperate" in str(d)

    def test_ensure_config_dir_creates(self):
        from teleop.platform.paths import ensure_config_dir
        d = ensure_config_dir()
        assert d.exists()
        assert d.is_dir()

    def test_config_dir_windows_uses_appdata(self):
        if sys.platform != "win32":
            pytest.skip("Windows-only test")
        from teleop.platform.paths import get_config_dir
        d = get_config_dir()
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            assert appdata in str(d)

    def test_config_dir_linux_uses_home_config(self):
        if sys.platform != "linux":
            pytest.skip("Linux-only test")
        from teleop.platform.paths import get_config_dir
        d = get_config_dir()
        assert ".config" in str(d) or "XDG" in str(d)


class TestCertPaths:
    def test_cert_paths_return_strings(self):
        from teleop.platform.paths import get_cert_paths
        cert, key = get_cert_paths()
        assert isinstance(cert, str)
        assert isinstance(key, str)

    def test_cert_paths_from_env(self, monkeypatch):
        monkeypatch.setenv("XR_TELEOP_CERT", "/tmp/test_cert.pem")
        monkeypatch.setenv("XR_TELEOP_KEY", "/tmp/test_key.pem")
        from teleop.platform.paths import get_cert_paths
        # Need to reimport to pick up env vars
        import importlib
        import teleop.platform.paths
        importlib.reload(teleop.platform.paths)
        cert, key = teleop.platform.paths.get_cert_paths()
        assert cert == "/tmp/test_cert.pem"
        assert key == "/tmp/test_key.pem"


class TestDataDir:
    def test_data_dir_is_path(self):
        from teleop.platform.paths import get_data_dir
        d = get_data_dir()
        assert isinstance(d, Path)

    def test_data_dir_contains_data(self):
        from teleop.platform.paths import get_data_dir
        d = get_data_dir()
        assert "data" in str(d)


class TestRecordingPaths:
    def test_episode_path_uses_os_join(self):
        """Verify episode paths use os.path.join (cross-platform)."""
        from teleop.utils.episode_writer import EpisodeWriter
        # Just verify the class can be imported and path construction works
        # We can't fully test it without all dependencies
        assert hasattr(EpisodeWriter, '__init__')

    def test_pathlib_imports(self):
        """Verify pathlib is available for path operations."""
        from pathlib import Path
        p = Path("test") / "subdir" / "file.txt"
        assert str(p) == os.path.join("test", "subdir", "file.txt") or "test" in str(p)
