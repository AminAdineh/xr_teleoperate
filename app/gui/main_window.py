"""
Main window — the application shell with sidebar navigation.

Hosts all pages and manages the service/worker lifecycle:
  - ConfigService (load/save config)
  - NetworkService
  - CertificateService
  - WorkerManager (teleop subprocess)
  - WatchdogWorker (health monitoring)
  - MetricsWorker (CPU/memory)
  - TeleopWorker (heartbeat polling)

Handles:
  - Single-instance protection
  - Crash protection (ensure worker shutdown on close)
  - Safe start / safe stop
  - Watchdog alerts
  - Error dialogs
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from app.models import (
    AppConfig, SystemStatus, StatusLevel, TeleopState,
    RobotModel, EndEffector, XRDevice,
)
from app.services import (
    ConfigService, NetworkService, CertificateService,
    WorkerManager, LoggingService,
)
from app.workers import WatchdogWorker, MetricsWorker, TeleopWorker
from app.gui.pages.dashboard_page import DashboardPage
from app.gui.pages.teleop_page import TeleopPage
from app.gui.pages.diagnostics_page import DiagnosticsPage
from app.gui.pages.logs_page import LogsPage
from app.gui.pages.settings_page import SettingsPage
from app.gui.wizard.wizard_dialog import WizardDialog
from app.gui.widgets.error_dialog import ErrorDialog
from app.gui.widgets.start_confirm_dialog import StartConfirmDialog

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    """Main application window with sidebar navigation."""

    def __init__(self, config_service: ConfigService, logging_service: LoggingService):
        super().__init__()
        self._config_service = config_service
        self._logging = logging_service
        self._network_service = NetworkService()
        self._cert_service = CertificateService()
        self._worker_manager = WorkerManager()

        self._status = SystemStatus()
        self._teleop_state = TeleopState.IDLE
        self._recording_start_time = 0.0

        self._build_ui()
        self._setup_workers()
        self._refresh_status()

        # Check if wizard is needed
        if not self._config_service.config.wizard_completed:
            QTimer.singleShot(500, self._show_wizard)

    def _build_ui(self):
        self.setWindowTitle("Unitree XR Teleoperate")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = self._build_sidebar()
        layout.addWidget(sidebar)

        # Page stack
        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.teleop_page = TeleopPage()
        self.diagnostics_page = DiagnosticsPage(self._config_service)
        self.logs_page = LogsPage(self._logging)
        self.settings_page = SettingsPage(self._config_service, self._network_service)

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.teleop_page)
        self.stack.addWidget(self.diagnostics_page)
        self.stack.addWidget(self.logs_page)
        self.stack.addWidget(self.settings_page)

        layout.addWidget(self.stack, stretch=1)

        # Connect signals
        self.dashboard_page.start_teleop_requested.connect(self._on_start_teleop)
        self.dashboard_page.stop_teleop_requested.connect(self._on_stop_teleop)
        self.dashboard_page.test_connection_requested.connect(self._on_test_connection)
        self.dashboard_page.start_sim_requested.connect(self._on_start_sim)
        self.teleop_page.stop_requested.connect(self._on_stop_teleop)
        self.settings_page.config_changed.connect(self._on_config_changed)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(4)

        # App name
        app_label = QLabel("Unitree XR\nTeleoperate")
        app_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #4cc2ff; padding: 16px;"
        )
        layout.addWidget(app_label)

        # Nav buttons
        self.nav_buttons = []
        nav_items = [
            ("Dashboard", 0),
            ("Teleoperation", 1),
            ("Diagnostics", 2),
            ("Logs", 3),
            ("Settings", 4),
        ]
        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Version label
        from app import __version__
        ver_label = QLabel(f"v{__version__}")
        ver_label.setStyleSheet("color: #606070; font-size: 12px; padding: 12px;")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)

        # Select dashboard by default
        self._navigate(0)

        return sidebar

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    # -- workers -----------------------------------------------------------

    def _setup_workers(self):
        # Watchdog
        self._watchdog = WatchdogWorker(self._worker_manager, self._network_service)
        self._watchdog.alert.connect(self._on_watchdog_alert)
        self._watchdog.health_update.connect(self._on_health_update)
        self._watchdog.worker_stopped.connect(self._on_worker_stopped)
        self._watchdog.start()

        # Metrics
        self._metrics = MetricsWorker()
        self._metrics.metrics_update.connect(self._on_metrics_update)
        self._metrics.start()

        # Status refresh timer (5 Hz)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(200)

    def _refresh_status(self):
        """Update system status from services and workers."""
        c = self._config_service.config
        s = self._status

        # Static info
        s.robot_model = c.robot.model.display_name
        s.end_effector = c.robot.end_effector.display_name
        s.robot_ip = c.robot.ip
        s.xr_device = c.xr.device.display_name

        # Network
        try:
            ifaces = self._network_service.list_interfaces()
            real = [ni for ni in ifaces if ni.is_up and not ni.is_loopback and ni.ipv4]
            if real:
                s.network = StatusLevel.OK
                if c.network.interface:
                    for ni in real:
                        if ni.name == c.network.interface:
                            s.network_name = ni.name
                            break
                    else:
                        s.network_name = real[0].name
                else:
                    s.network_name = real[0].name
            else:
                s.network = StatusLevel.ERROR
                s.network_name = ""
        except Exception:
            s.network = StatusLevel.IDLE

        # Windows
        s.windows = StatusLevel.OK

        # Worker state
        if self._worker_manager.is_running:
            hb = self._worker_manager.get_heartbeat_state()
            s.worker_alive = True
            if hb:
                s.dds_healthy = True
                s.robot_connected = True
                if hb.get("START"):
                    s.teleop = TeleopState.ACTIVE
                    s.xr_connected = True
                elif hb.get("STOP"):
                    s.teleop = TeleopState.STOPPING
                else:
                    s.teleop = TeleopState.READY
                s.recording_active = hb.get("RECORD_RUNNING", False)
                if s.recording_active and self._recording_start_time == 0:
                    self._recording_start_time = time.time()
                elif not s.recording_active:
                    self._recording_start_time = 0
                    s.recording_duration = 0
                    s.recording_frames = 0
                if s.recording_active:
                    s.recording_duration = time.time() - self._recording_start_time
            else:
                s.teleop = TeleopState.READY
                s.dds_healthy = False
                s.robot_connected = False
                s.xr_connected = False
        else:
            s.teleop = TeleopState.IDLE
            s.worker_alive = False
            s.robot_connected = False
            s.dds_healthy = False
            s.xr_connected = False
            s.recording_active = False
            self._teleop_state = TeleopState.IDLE

        # Certificate
        try:
            cert_info = self._cert_service.get_info()
            s.xr = StatusLevel.OK if cert_info.valid else StatusLevel.WARNING
        except Exception:
            s.xr = StatusLevel.IDLE

        # Robot / DDS status
        if s.worker_alive:
            s.robot = StatusLevel.OK if s.robot_connected else StatusLevel.WARNING
            s.dds = StatusLevel.OK if s.dds_healthy else StatusLevel.WARNING
        else:
            s.robot = StatusLevel.IDLE
            s.dds = StatusLevel.IDLE

        # Update GUI
        self.dashboard_page.update_status(s)
        self.dashboard_page.set_teleop_state(s.teleop)
        self.teleop_page.update_status(s)

    # -- signal handlers ----------------------------------------------------

    def _on_metrics_update(self, metrics: dict):
        self.dashboard_page.update_metrics(metrics)

    def _on_health_update(self, health: dict):
        pass  # handled in _refresh_status

    def _on_watchdog_alert(self, alert_type: str, message: str):
        logger.warning("Watchdog alert [%s]: %s", alert_type, message)
        # Show alert dialog for critical issues
        if alert_type in ("worker", "ipc"):
            causes = {
                "worker": [
                    "The teleoperation process crashed",
                    "Network connection to the robot was lost",
                    "DDS communication failed",
                    "The XR device disconnected",
                ],
                "ipc": [
                    "The worker process is unresponsive",
                    "IPC communication was interrupted",
                ],
            }
            solutions = {
                "worker": [
                    "Check the robot is powered on and connected",
                    "Review the Logs page for error details",
                    "Run Diagnostics to identify the issue",
                ],
                "ipc": [
                    "Stop teleoperation safely",
                    "Restart the application",
                ],
            }
            dlg = ErrorDialog(
                problem=message,
                causes=causes.get(alert_type, []),
                solutions=solutions.get(alert_type, []),
                technical_details=f"Alert type: {alert_type}",
                parent=self,
            )
            dlg.exec()

    def _on_worker_stopped(self):
        self._teleop_state = TeleopState.IDLE
        logger.info("Worker stopped signal received")

    # -- actions -----------------------------------------------------------

    def _on_start_teleop(self):
        c = self._config_service.config
        dlg = StartConfirmDialog(
            robot=c.robot.model.display_name,
            end_effector=c.robot.end_effector.display_name,
            network=c.network.interface or "Auto",
            xr_device=c.xr.device.display_name,
            sim_mode=False,
            parent=self,
        )
        if dlg.exec():
            self._do_start(sim_mode=False)

    def _on_start_sim(self):
        c = self._config_service.config
        dlg = StartConfirmDialog(
            robot=c.robot.model.display_name,
            end_effector=c.robot.end_effector.display_name,
            network=c.network.interface or "Auto",
            xr_device=c.xr.device.display_name,
            sim_mode=True,
            parent=self,
        )
        if dlg.exec():
            self._do_start(sim_mode=True)

    def _do_start(self, sim_mode: bool):
        """Launch the teleop worker subprocess."""
        c = self._config_service.config
        if sim_mode:
            c.app.sim_mode = True
        else:
            c.app.sim_mode = False

        # Ensure certificates
        try:
            self._cert_service.ensure()
        except Exception as exc:
            dlg = ErrorDialog(
                problem="Failed to generate SSL certificate",
                causes=["OpenSSL is not installed or not on PATH"],
                solutions=["Install Git for Windows (includes OpenSSL)"],
                technical_details=str(exc),
                parent=self,
            )
            dlg.exec()
            return

        # Start the worker
        if not self._worker_manager.start(c):
            dlg = ErrorDialog(
                problem="Failed to start teleoperation worker",
                causes=["Another instance may be running", "Missing dependencies"],
                solutions=["Check the Logs page", "Run Diagnostics"],
                parent=self,
            )
            dlg.exec()
            return

        self._teleop_state = TeleopState.READY
        self._navigate(1)  # Switch to teleop page
        logger.info("Teleop worker started")

        # Auto-send start after a delay (wait for IPC to come online)
        QTimer.singleShot(3000, self._send_start_command)

    def _send_start_command(self):
        """Send CMD_START to begin robot following."""
        if self._worker_manager.is_running:
            result = self._worker_manager.send_start()
            if result.get("status") == "ok":
                self._teleop_state = TeleopState.ACTIVE
                logger.info("CMD_START sent successfully")
            else:
                logger.warning("CMD_START failed: %s", result.get("msg", ""))

    def _on_stop_teleop(self):
        """Safe stop — uses the existing CMD_STOP mechanism."""
        logger.info("Stop teleoperation requested")
        if self._worker_manager.is_running:
            result = self._worker_manager.send_stop()
            logger.info("CMD_STOP result: %s", result)
            # Wait for graceful shutdown
            QTimer.singleShot(5000, self._check_worker_shutdown)

    def _check_worker_shutdown(self):
        if self._worker_manager.is_running:
            logger.warning("Worker did not stop gracefully; forcing shutdown")
            self._worker_manager.shutdown()

    def _on_test_connection(self):
        self._navigate(2)  # Switch to diagnostics page

    def _on_config_changed(self):
        self._refresh_status()

    def _show_wizard(self):
        wizard = WizardDialog(self._config_service, self)
        wizard.wizard_completed.connect(self._refresh_status)
        wizard.exec()

    # -- shutdown ----------------------------------------------------------

    def closeEvent(self, event):
        """Ensure safe worker shutdown on window close (crash protection)."""
        logger.info("Close event — ensuring safe worker shutdown")
        if self._worker_manager.is_running:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Teleoperation is still running. Stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            # Safe stop
            self._worker_manager.shutdown()

        # Stop workers
        self._watchdog.stop()
        self._metrics.stop()
        self._status_timer.stop()
        self.logs_page.stop()

        # Save config
        self._config_service.save()

        event.accept()
