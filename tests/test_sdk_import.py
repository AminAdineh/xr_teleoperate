"""
Tests for Unitree SDK import and DDS availability.

These tests verify that the unitree_sdk2_python package is installed
and that DDS communication can be initialized.

NOTE: DDS initialization requires a network interface. Tests that
require hardware are marked as skip when no robot is available.
"""
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestSDKImport:
    def test_import_channel_factory(self):
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            assert ChannelFactoryInitialize is not None
        except ImportError:
            pytest.fail("unitree_sdk2_python is not installed. "
                        "git clone https://github.com/unitreerobotics/unitree_sdk2_python.git && "
                        "cd unitree_sdk2_python && pip install -e .")

    def test_import_channel_publisher(self):
        try:
            from unitree_sdk2py.core.channel import ChannelPublisher
            assert ChannelPublisher is not None
        except ImportError:
            pytest.fail("unitree_sdk2py.core.channel.ChannelPublisher not available")

    def test_import_channel_subscriber(self):
        try:
            from unitree_sdk2py.core.channel import ChannelSubscriber
            assert ChannelSubscriber is not None
        except ImportError:
            pytest.fail("unitree_sdk2py.core.channel.ChannelSubscriber not available")

    def test_import_crc(self):
        try:
            from unitree_sdk2py.utils.crc import CRC
            assert CRC is not None
        except ImportError:
            pytest.fail("unitree_sdk2py.utils.crc.CRC not available")

    def test_import_hg_lowcmd(self):
        try:
            from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_ as hg_LowCmd
            assert hg_LowCmd is not None
        except ImportError:
            pytest.fail("unitree_sdk2py.idl.unitree_hg.msg.dds_.LowCmd_ not available")

    def test_import_go_lowcmd(self):
        try:
            from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowCmd_ as go_LowCmd
            assert go_LowCmd is not None
        except ImportError:
            pytest.fail("unitree_sdk2py.idl.unitree_go.msg.dds_.LowCmd_ not available")

    def test_import_motion_switcher(self):
        try:
            from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient
            assert MotionSwitcherClient is not None
        except ImportError:
            pytest.skip("MotionSwitcherClient not available (may not be needed for all robot types)")

    def test_import_loco_client(self):
        try:
            from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
            assert LocoClient is not None
        except ImportError:
            pytest.skip("LocoClient not available (may not be needed for all robot types)")


class TestDDSInitialization:
    def test_cyclonedds_available(self):
        try:
            import cyclonedds
            assert cyclonedds is not None
        except ImportError:
            pytest.skip("cyclonedds Python bindings not installed")

    def test_dds_factory_init(self):
        """Test that DDS can be initialized (requires network interface)."""
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            ChannelFactoryInitialize(0)
        except ImportError:
            pytest.skip("unitree_sdk2_python not installed")
        except Exception as e:
            pytest.skip(f"DDS initialization failed (no network interface?): {e}")


class TestSubmoduleImports:
    def test_televuer_import(self):
        try:
            import televuer
            assert hasattr(televuer, 'TeleVuerWrapper')
        except ImportError:
            pytest.fail("televuer submodule not installed. cd teleop/televuer && pip install -e .")

    def test_teleimager_import(self):
        try:
            from teleimager.image_client import ImageClient
            assert ImageClient is not None
        except ImportError:
            pytest.fail("teleimager submodule not installed. cd teleop/teleimager && pip install -e . --no-deps")

    def test_dex_retargeting_import(self):
        try:
            import dex_retargeting
            assert hasattr(dex_retargeting, 'RetargetingConfig')
        except ImportError:
            pytest.fail("dex-retargeting submodule not installed. cd teleop/robot_control/dex-retargeting && pip install -e .")
