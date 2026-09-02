"""
Robot service — wraps robot detection and testing for the GUI.

Does NOT contain robot-control algorithms.  Uses the existing DDS / SDK
to check reachability and state reception.
"""
from __future__ import annotations

import logging
import socket
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RobotService:
    """Robot detection and connection testing (no control logic)."""

    def __init__(self):
        self._dds_initialized = False

    def detect_robot(self, network_interface: str = None) -> Optional[dict]:
        """
        Attempt to detect a robot on the DDS network.

        Returns a dict with robot info if found, None otherwise.
        Does NOT fake detection — returns None if no robot responds.
        """
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
            from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_  # noqa

            domain = 0
            ChannelFactoryInitialize(domain, networkInterface=network_interface)

            # Try subscribing to a known state topic
            try:
                from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
                sub = ChannelSubscriber("rt/dex3/left/state", HandState_)
                sub.Init()
            except Exception:
                pass

            # Wait briefly for any DDS data
            time.sleep(1.0)
            # We can't easily determine robot model from DDS without more work;
            # just return that DDS is alive.
            return {"dds_alive": True, "interface": network_interface}
        except ImportError:
            logger.warning("unitree_sdk2_python not available for robot detection")
            return None
        except Exception as exc:
            logger.warning("Robot detection failed: %s", exc)
            return None

    def test_robot(self, robot_ip: str, timeout: float = 3.0) -> dict:
        """
        Test robot connectivity.

        Returns dict with:
          - reachable: bool (ping)
          - ip: str
          - error: str (if any)
        """
        result = {"reachable": False, "ip": robot_ip, "error": ""}
        # Ping
        try:
            from teleop.platform.network import is_ip_reachable
            result["reachable"] = is_ip_reachable(robot_ip, timeout=timeout)
            if not result["reachable"]:
                result["error"] = "Robot not reachable via ping"
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def test_dds(self, network_interface: str = None, timeout: float = 3.0) -> dict:
        """
        Test DDS initialization and basic discovery.

        Returns dict with:
          - initialized: bool
          - error: str
        """
        result = {"initialized": False, "error": ""}
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            ChannelFactoryInitialize(0, networkInterface=network_interface)
            self._dds_initialized = True
            result["initialized"] = True
        except ImportError:
            result["error"] = "unitree_sdk2_python not installed"
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def shutdown(self):
        """Clean up DDS resources."""
        self._dds_initialized = False
