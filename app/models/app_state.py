"""
Application state models — dataclasses and enums used throughout the app.

No Qt imports, no robot-control algorithms.  Pure data.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RobotModel(str, enum.Enum):
    G1_29 = "G1_29"
    G1_23 = "G1_23"
    H1_2 = "H1_2"
    H1 = "H1"
    H2 = "H2"
    R1_A5 = "R1_A5"
    R1_A7 = "R1_A7"

    @property
    def display_name(self) -> str:
        names = {
            "G1_29": "G1 (29 DoF)",
            "G1_23": "G1 (23 DoF)",
            "H1_2": "H1-2",
            "H1": "H1",
            "H2": "H2",
            "R1_A5": "R1 (5 DoF Arm)",
            "R1_A7": "R1 (7 DoF Arm)",
        }
        return names.get(self.value, self.value)


class EndEffector(str, enum.Enum):
    dex3 = "dex3"
    dex1 = "dex1"
    dex1_internal = "dex1_internal"
    inspire_ftp = "inspire_ftp"
    inspire_dfx = "inspire_dfx"
    brainco = "brainco"

    @property
    def display_name(self) -> str:
        names = {
            "dex3": "Dex3",
            "dex1": "Dex1",
            "dex1_internal": "Dex1 (Internal)",
            "inspire_ftp": "Inspire (FTP)",
            "inspire_dfx": "Inspire (DFX)",
            "brainco": "BrainCo",
        }
        return names.get(self.value, self.value)


# Valid end-effectors per robot model
_VALID_EE: dict[str, list[str]] = {
    "G1_29": ["dex3", "dex1", "dex1_internal", "inspire_ftp", "inspire_dfx", "brainco"],
    "G1_23": ["dex3", "dex1", "inspire_ftp", "inspire_dfx", "brainco"],
    "H1_2": ["dex3", "dex1", "inspire_ftp", "inspire_dfx", "brainco"],
    "H1": ["dex3", "dex1", "inspire_ftp", "inspire_dfx", "brainco"],
    "H2": ["dex3", "dex1", "inspire_ftp", "inspire_dfx", "brainco"],
    "R1_A5": ["dex1", "inspire_ftp", "inspire_dfx", "brainco"],
    "R1_A7": ["dex3", "dex1", "inspire_ftp", "inspire_dfx", "brainco"],
}


def valid_end_effectors(robot: RobotModel) -> list[EndEffector]:
    """Return the list of valid end-effectors for a given robot model."""
    return [EndEffector(ee) for ee in _VALID_EE.get(robot.value, [])]


class XRDevice(str, enum.Enum):
    meta_quest = "meta_quest"
    pico = "pico"
    vision_pro = "vision_pro"
    other = "other"

    @property
    def display_name(self) -> str:
        names = {
            "meta_quest": "Meta Quest",
            "pico": "PICO 4 Ultra",
            "vision_pro": "Apple Vision Pro",
            "other": "Other XR Device",
        }
        return names.get(self.value, self.value)


class StatusLevel(enum.Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    IDLE = "idle"
    NOT_TESTED = "not_tested"


class ConnectionStatus(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TeleopState(enum.Enum):
    IDLE = "idle"           # teleop process not running
    READY = "ready"         # process running, waiting for start
    ACTIVE = "active"       # robot following XR motion
    STOPPING = "stopping"   # stop requested, shutting down
    ERROR = "error"         # worker crashed / watchdog failure


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RobotConfig:
    model: RobotModel = RobotModel.G1_29
    ip: str = "192.168.123.164"
    end_effector: EndEffector = EndEffector.dex3
    input_mode: str = "hand"          # "hand" or "controller"
    display_mode: str = "immersive"   # "immersive", "ego", "pass-through"
    motion: bool = False
    frequency: float = 30.0

    def to_dict(self) -> dict:
        return {
            "model": self.model.value,
            "ip": self.ip,
            "end_effector": self.end_effector.value,
            "input_mode": self.input_mode,
            "display_mode": self.display_mode,
            "motion": self.motion,
            "frequency": self.frequency,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RobotConfig":
        return cls(
            model=RobotModel(d.get("model", "G1_29")),
            ip=d.get("ip", "192.168.123.164"),
            end_effector=EndEffector(d.get("end_effector", "dex3")),
            input_mode=d.get("input_mode", "hand"),
            display_mode=d.get("display_mode", "immersive"),
            motion=d.get("motion", False),
            frequency=d.get("frequency", 30.0),
        )


@dataclass
class NetworkConfig:
    interface: Optional[str] = None    # None = auto-select
    auto_select: bool = True

    def to_dict(self) -> dict:
        return {"interface": self.interface, "auto_select": self.auto_select}

    @classmethod
    def from_dict(cls, d: dict) -> "NetworkConfig":
        return cls(interface=d.get("interface"), auto_select=d.get("auto_select", True))


@dataclass
class XRConfig:
    device: XRDevice = XRDevice.meta_quest
    port: int = 8012
    https_enabled: bool = True

    @property
    def server_url(self) -> str:
        return f"https://0.0.0.0:{self.port}"

    def to_dict(self) -> dict:
        return {"device": self.device.value, "port": self.port, "https_enabled": self.https_enabled}

    @classmethod
    def from_dict(cls, d: dict) -> "XRConfig":
        return cls(
            device=XRDevice(d.get("device", "meta_quest")),
            port=d.get("port", 8012),
            https_enabled=d.get("https_enabled", True),
        )


@dataclass
class RecordingConfig:
    enabled: bool = False
    save_dir: str = ""
    task_name: str = "pick cube"
    task_goal: str = "pick up cube."
    task_desc: str = "task description"
    task_steps: str = "step1: do this; step2: do that;"

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "save_dir": self.save_dir,
            "task_name": self.task_name,
            "task_goal": self.task_goal,
            "task_desc": self.task_desc,
            "task_steps": self.task_steps,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RecordingConfig":
        return cls(
            enabled=d.get("enabled", False),
            save_dir=d.get("save_dir", ""),
            task_name=d.get("task_name", "pick cube"),
            task_goal=d.get("task_goal", "pick up cube."),
            task_desc=d.get("task_desc", "task description"),
            task_steps=d.get("task_steps", "step1: do this; step2: do that;"),
        )


@dataclass
class AppSettings:
    theme: str = "dark"            # "dark" or "light"
    log_level: str = "INFO"
    start_behavior: str = "dashboard"  # "dashboard" or "wizard"
    sim_mode: bool = False

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "log_level": self.log_level,
            "start_behavior": self.start_behavior,
            "sim_mode": self.sim_mode,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppSettings":
        return cls(
            theme=d.get("theme", "dark"),
            log_level=d.get("log_level", "INFO"),
            start_behavior=d.get("start_behavior", "dashboard"),
            sim_mode=d.get("sim_mode", False),
        )


@dataclass
class AdvancedSettings:
    dds_domain: int = 0
    debug_mode: bool = False
    headless: bool = False

    def to_dict(self) -> dict:
        return {"dds_domain": self.dds_domain, "debug_mode": self.debug_mode, "headless": self.headless}

    @classmethod
    def from_dict(cls, d: dict) -> "AdvancedSettings":
        return cls(
            dds_domain=d.get("dds_domain", 0),
            debug_mode=d.get("debug_mode", False),
            headless=d.get("headless", False),
        )


@dataclass
class AppConfig:
    """Top-level application configuration."""
    robot: RobotConfig = field(default_factory=RobotConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    xr: XRConfig = field(default_factory=XRConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    app: AppSettings = field(default_factory=AppSettings)
    advanced: AdvancedSettings = field(default_factory=AdvancedSettings)
    wizard_completed: bool = False
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "wizard_completed": self.wizard_completed,
            "robot": self.robot.to_dict(),
            "network": self.network.to_dict(),
            "xr": self.xr.to_dict(),
            "recording": self.recording.to_dict(),
            "app": self.app.to_dict(),
            "advanced": self.advanced.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppConfig":
        return cls(
            robot=RobotConfig.from_dict(d.get("robot", {})),
            network=NetworkConfig.from_dict(d.get("network", {})),
            xr=XRConfig.from_dict(d.get("xr", {})),
            recording=RecordingConfig.from_dict(d.get("recording", {})),
            app=AppSettings.from_dict(d.get("app", {})),
            advanced=AdvancedSettings.from_dict(d.get("advanced", {})),
            wizard_completed=d.get("wizard_completed", False),
            version=d.get("version", "1.0.0"),
        )


# ---------------------------------------------------------------------------
# Runtime status (not persisted)
# ---------------------------------------------------------------------------

@dataclass
class SystemStatus:
    """Live system status shown on the dashboard."""
    windows: StatusLevel = StatusLevel.IDLE
    network: StatusLevel = StatusLevel.IDLE
    robot: StatusLevel = StatusLevel.IDLE
    dds: StatusLevel = StatusLevel.IDLE
    xr: StatusLevel = StatusLevel.IDLE
    teleop: TeleopState = TeleopState.IDLE

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    latency_ms: float = 0.0
    control_hz: float = 0.0
    xr_fps: float = 0.0

    robot_model: str = ""
    end_effector: str = ""
    network_name: str = ""
    robot_ip: str = ""
    xr_device: str = ""

    # Watchdog flags
    robot_connected: bool = False
    dds_healthy: bool = False
    xr_connected: bool = False
    worker_alive: bool = False
    recording_active: bool = False
    recording_duration: float = 0.0
    recording_frames: int = 0
