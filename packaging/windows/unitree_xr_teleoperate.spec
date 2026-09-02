# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Unitree XR Teleoperate.

Builds a Windows executable that bundles:
  - The PySide6 GUI application
  - The teleoperation core (teleop/)
  - All Python dependencies
  - Native DLLs (CycloneDDS, Pinocchio, NLopt, CasADi, OpenCV, ZMQ)

Usage:
    pyinstaller packaging/windows/unitree_xr_teleoperate.spec

Output:
    dist/UnitreeXRTeleoperate/UnitreeXRTeleoperate.exe
"""
import os
import sys
from pathlib import Path

block_cipher = None

# Project root (parent of packaging/)
project_root = Path(SPECPATH).parent.parent

# Collect all data files (URDF, assets, etc.)
datas = []
# Include teleop assets and URDF files
for root, dirs, files in os.walk(str(project_root / "teleop")):
    for f in files:
        if f.endswith(('.urdf', '.xml', '.yaml', '.yml', '.pem', '.key', '.json')):
            src = os.path.join(root, f)
            rel = os.path.relpath(src, str(project_root))
            datas.append((src, os.path.dirname(rel)))

# Include submodule source (televuer, teleimager, dex-retargeting)
for submodule in ["teleop/televuer/src", "teleop/teleimager/src", "teleop/robot_control/dex-retargeting"]:
    sm_path = project_root / submodule
    if sm_path.exists():
        for root, dirs, files in os.walk(str(sm_path)):
            for f in files:
                if f.endswith(('.py', '.urdf', '.xml', '.json', '.txt')):
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, str(project_root))
                    datas.append((src, os.path.dirname(rel)))

# Include app resources
datas.append((str(project_root / "app" / "resources" / "style.qss"), "app" / "resources"))

# Include assets directory
assets_path = project_root / "assets"
if assets_path.exists():
    datas.append((str(assets_path), "assets"))

# Collect PySide6 Qt plugins and data files (Qt platforms, styles, image formats)
extra_binaries = []
try:
    from PyInstaller.utils.hooks import collect_all
    for pkg in ("PySide6",):
        d, b, hidden = collect_all(pkg)
        datas += d
        extra_binaries += b
        # hidden already added below via hiddenimports
except Exception:
    pass  # PyInstaller hooks handle PySide6 automatically if this fails

a = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Submodules
        "televuer",
        "teleimager",
        "dex_retargeting",
        # Platform modules
        "teleop.platform",
        "teleop.platform.network",
        "teleop.platform.paths",
        "teleop.platform.certs",
        "teleop.platform.firewall",
        "teleop.platform.process",
        "teleop.platform.ipc_transport",
        "teleop.platform.cpu_affinity",
        # Robot control
        "teleop.robot_control.robot_arm",
        "teleop.robot_control.robot_arm_ik",
        "teleop.robot_control.hand_retargeting",
        "teleop.robot_control.robot_hand_unitree",
        "teleop.robot_control.robot_hand_inspire",
        "teleop.robot_control.robot_hand_brainco",
        # Utils
        "teleop.utils.ipc",
        "teleop.utils.episode_writer",
        "teleop.utils.motion_switcher",
        "teleop.utils.weighted_moving_filter",
        "teleop.utils.sim_state_topic",
        # GUI app
        "app",
        "app.main",
        "app.gui",
        "app.gui.main_window",
        "app.services",
        "app.workers",
        "app.models",
        # External deps
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtNetwork",
        "PySide6.QtConcurrent",
        "zmq",
        "cv2",
        "numpy",
        "scipy",
        "yaml",
        "psutil",
        "qrcode",
        # Optional (may not be installed)
        "pinocchio",
        "nlopt",
        "casadi",
        "torch",
        "cyclonedds",
        "unitree_sdk2py",
        "unitree_sdk2py.core",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    binaries=extra_binaries,
    excludes=["tkinter", "matplotlib", "meshcat", "rerun_sdk", "rerun"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UnitreeXRTeleoperate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application (no console window)
    disable_windowed_traceback=False,
    icon=str(project_root / "packaging" / "windows" / "icon.ico") if (project_root / "packaging" / "windows" / "icon.ico").exists() else None,
    target_arch="x64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="UnitreeXRTeleoperate",
)
