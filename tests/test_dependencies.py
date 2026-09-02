"""
Tests for Python dependency availability.

These tests check that all required Python packages can be imported.
They are hardware-independent and can run on any platform.
"""
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


# Core dependencies that must be available
REQUIRED_PACKAGES = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("opencv", "cv2"),
    ("pyzmq", "zmq"),
    ("pyyaml", "yaml"),
    ("casadi", "casadi"),
    ("pinocchio", "pinocchio"),
    ("pytorch", "torch"),
    ("meshcat", "meshcat"),
    ("psutil", "psutil"),
    ("sshkeyboard", "sshkeyboard"),
    ("logging_mp", "logging_mp"),
    ("pytransform3d", "pytransform3d"),
    ("trimesh", "trimesh"),
    ("anytree", "anytree"),
    ("lxml", "lxml"),
    ("nlopt", "nlopt"),
]

# Optional dependencies (warnings, not failures)
OPTIONAL_PACKAGES = [
    ("rerun", "rerun"),
    ("vuer", "vuer"),
    ("aiortc", "aiortc"),
    ("aiohttp", "aiohttp"),
]


class TestRequiredDependencies:
    @pytest.mark.parametrize("name,module", REQUIRED_PACKAGES)
    def test_import(self, name, module):
        try:
            __import__(module)
        except ImportError as e:
            pytest.fail(f"Required dependency '{name}' (import as '{module}') is not installed: {e}")


class TestOptionalDependencies:
    @pytest.mark.parametrize("name,module", OPTIONAL_PACKAGES)
    def test_import(self, name, module):
        try:
            __import__(module)
        except ImportError:
            pytest.skip(f"Optional dependency '{name}' is not installed")


class TestDependencyVersions:
    def test_numpy_version_compatible(self):
        import numpy as np
        # Must be < 2.0.0 per requirements
        assert np.__version__ < "2.0.0", f"NumPy {np.__version__} is >= 2.0.0, which may cause issues"

    def test_python_version_compatible(self):
        ver = sys.version_info
        assert ver >= (3, 10), "Python 3.10+ is required"
        assert ver < (3, 13), "Python 3.13+ is not yet tested"
