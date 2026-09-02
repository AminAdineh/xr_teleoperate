"""
Unitree XR Teleoperate — Application Entry Point.

Handles:
  - Single-instance protection (named mutex on Windows, lock file on Linux)
  - Logging initialization
  - Config loading and corruption check
  - QApplication setup and stylesheet
  - MainWindow launch
  - Crash protection (ensure worker shutdown on exit)
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from app import __version__, __app_name__
from app.services import ConfigService, LoggingService


def _check_single_instance() -> bool:
    """
    Ensure only one application instance is running.

    On Windows: uses a named mutex (ctypes).
    On Linux/macOS: uses a lock file in the config directory.

    Returns True if this is the first instance, False otherwise.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            mutex_name = f"Global\\{__app_name__}"
            # Try to create a named mutex
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
            last_error = ctypes.windll.kernel32.GetLastError()
            # ERROR_ALREADY_EXISTS = 183
            if last_error == 183:
                return False
            # Keep mutex handle alive
            globals()["_mutex_handle"] = mutex
            return True
        except Exception:
            return True
    else:
        # Lock file approach
        import tempfile
        lock_dir = Path(tempfile.gettempdir()) / "unitree_xr_teleoperate"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "singleton.lock"
        try:
            import fcntl
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            globals()["_lock_fd"] = fd
            return True
        except (ImportError, OSError):
            return False


def _show_already_running_dialog():
    """Show the 'already running' dialog."""
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication(sys.argv)
    msg = QMessageBox()
    msg.setWindowTitle(__app_name__)
    msg.setText(f"{__app_name__} is already running.")
    msg.setInformativeText("Only one instance can control the robot at a time.")
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


def _load_stylesheet(app) -> str:
    """Load the Qt stylesheet from the resources directory."""
    qss_path = Path(__file__).resolve().parent / "resources" / "style.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def _run_dependency_check() -> int:
    """Headless dependency check — used by the installer and CI smoke test."""
    print(f"{__app_name__} v{__version__}")
    print(f"Python {sys.version} on {sys.platform}")
    print()
    deps = [
        ("NumPy", "numpy"), ("SciPy", "scipy"), ("CasADi", "casadi"),
        ("OpenCV", "cv2"), ("PyZMQ", "zmq"), ("PyYAML", "yaml"),
        ("PyTorch", "torch"), ("psutil", "psutil"), ("Pinocchio", "pinocchio"),
        ("NLopt", "nlopt"), ("PySide6", "PySide6"), ("pytransform3d", "pytransform3d"),
        ("trimesh", "trimesh"), ("anytree", "anytree"), ("lxml", "lxml"),
    ]
    missing = []
    for name, mod in deps:
        try:
            __import__(mod)
            print(f"  [OK]   {name}")
        except ImportError:
            print(f"  [FAIL] {name}")
            missing.append(name)
    for name, mod in [("televuer", "televuer"), ("teleimager", "teleimager"),
                      ("dex-retargeting", "dex_retargeting"),
                      ("unitree_sdk2_python", "unitree_sdk2py.core"),
                      ("cyclonedds", "cyclonedds.core")]:
        try:
            __import__(mod)
            print(f"  [OK]   {name}")
        except ImportError:
            print(f"  [FAIL] {name}")
            missing.append(name)
    print()
    if missing:
        print(f"FAILED: {len(missing)} missing dependency(ies): {', '.join(missing)}")
        return 1
    print("All dependencies present.")
    return 0


def _configure_firewall(remove: bool = False) -> int:
    """Add or remove Windows Defender firewall rules (requires admin)."""
    if sys.platform != "win32":
        print("Firewall configuration is Windows-only.")
        return 0
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("ERROR: firewall configuration requires administrator privileges.")
        return 1
    rules = [
        ("xr_teleoperate HTTPS/WebRTC signaling", "8012", "TCP", "in"),
        ("xr_teleoperate Teleimager config", "60000", "TCP", "in"),
        ("xr_teleoperate DDS multicast", "7400", "UDP", "in"),
        ("xr_teleoperate DDS unicast range", "7401-7500", "UDP", "in"),
        ("xr_teleoperate WebRTC media", "49152-65535", "UDP", "in"),
    ]
    action = "delete" if remove else "add"
    verb = "Removing" if remove else "Adding"
    for name, port, proto, direction in rules:
        if remove:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={name}"],
                capture_output=True, timeout=10,
            )
        else:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={name}", f"dir={direction}", "action=allow",
                 f"protocol={proto}", f"localport={port}"],
                capture_output=True, timeout=10,
            )
        print(f"  {verb}: {name} ({proto}/{port})")
    print("Firewall configuration complete.")
    return 0


def main():
    # --- CLI modes (no GUI) ------------------------------------------------
    if "--version" in sys.argv:
        print(f"{__app_name__} v{__version__}")
        sys.exit(0)

    if "--check" in sys.argv:
        sys.exit(_run_dependency_check())

    if "--firewall" in sys.argv:
        sys.exit(_configure_firewall(remove=False))

    if "--firewall-remove" in sys.argv:
        sys.exit(_configure_firewall(remove=True))

    # --- Normal GUI launch ------------------------------------------------
    # Single-instance check
    if not _check_single_instance():
        _show_already_running_dialog()
        sys.exit(0)

    # Initialize logging
    logging_service = LoggingService()
    log = logging_service.get_logger("gui")
    log.info("=" * 60)
    log.info("%s v%s starting", __app_name__, __version__)
    log.info("Python %s on %s", sys.version, sys.platform)
    log.info("Project root: %s", _PROJECT_ROOT)
    log.info("=" * 60)

    # Load configuration
    config_service = ConfigService()

    # Check for corruption
    if config_service.is_corrupted():
        log.warning("Configuration file is corrupted")
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setWindowTitle("Configuration Error")
        msg.setText("Configuration is corrupted.")
        msg.setInformativeText("Would you like to repair (restore backup) or reset to defaults?")
        repair_btn = msg.addButton("Repair", QMessageBox.ButtonRole.AcceptRole)
        reset_btn = msg.addButton("Reset", QMessageBox.ButtonRole.ResetRole)
        msg.exec()
        if msg.clickedButton() == repair_btn:
            config_service.repair()
        else:
            config_service.reset()
        log.info("Configuration repaired/reset")

    config_service.load()

    # Validate
    errors = config_service.validate()
    if errors:
        log.warning("Config validation errors: %s", errors)

    # Create Qt application
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("UnitreeRobotics")

    # Apply stylesheet
    stylesheet = _load_stylesheet(app)
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Set up global exception handler (crash protection)
    def exception_hook(exc_type, exc_value, exc_traceback):
        log.error("Unhandled exception: %s", "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        # Show error dialog
        from app.gui.widgets.error_dialog import ErrorDialog
        dlg = ErrorDialog(
            problem="An unexpected error occurred.",
            causes=["Internal application error"],
            solutions=["Restart the application", "Check the logs for details"],
            technical_details="".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )
        dlg.exec()
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook

    # Create main window
    from app.gui.main_window import MainWindow
    window = MainWindow(config_service, logging_service)
    window.show()

    log.info("Application started successfully")

    # Run event loop
    exit_code = app.exec()

    # Cleanup
    log.info("Application exiting with code %d", exit_code)
    logging_service.save_to_file(
        str(logging_service.log_dir / "session_exit.log"),
        category="all",
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
