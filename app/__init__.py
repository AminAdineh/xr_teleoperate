"""
Unitree XR Teleoperate — Desktop Application Layer.

This package contains the Windows 11 GUI application built on top of the
existing teleoperation core (teleop/).  The GUI never contains robot-control
algorithms; it communicates with the core through a service layer and the
existing IPC mechanism.
"""
__version__ = "1.0.0"
__app_name__ = "Unitree XR Teleoperate"
__app_org__ = "UnitreeRobotics"
