"""
Dashboard page — the main landing page showing system status.

Shows:
  - System status indicators (Windows, Network, Robot, DDS, XR, Teleop)
  - Robot info (model, end effector, network, IP, XR device)
  - Action buttons (Test Connection, Start Teleoperation, Stop)
  - Metrics (CPU, Memory, Latency, Control frequency)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.gui.widgets.status_indicator import StatusIndicator
from app.gui.widgets.status_card import StatusCard
from app.gui.widgets.metric_card import MetricCard
from app.models import StatusLevel, TeleopState


class DashboardPage(QWidget):
    """Main dashboard page."""

    start_teleop_requested = Signal()
    stop_teleop_requested = Signal()
    test_connection_requested = Signal()
    start_sim_requested = Signal()
    open_settings_requested = Signal()
    open_diagnostics_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Unitree XR Teleoperate")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        # System status section
        status_header = QLabel("SYSTEM STATUS")
        status_header.setObjectName("SectionHeader")
        layout.addWidget(status_header)

        status_frame = QFrame()
        status_frame.setObjectName("Card")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 16, 20, 16)
        status_layout.setSpacing(10)

        self.ind_windows = StatusIndicator("Windows")
        self.ind_network = StatusIndicator("Network")
        self.ind_robot = StatusIndicator("Robot")
        self.ind_dds = StatusIndicator("DDS")
        self.ind_xr = StatusIndicator("XR")
        self.ind_teleop = StatusIndicator("Teleoperation")

        for ind in [self.ind_windows, self.ind_network, self.ind_robot,
                    self.ind_dds, self.ind_xr, self.ind_teleop]:
            status_layout.addWidget(ind)

        layout.addWidget(status_frame)

        # Robot info section
        info_header = QLabel("ROBOT")
        info_header.setObjectName("SectionHeader")
        layout.addWidget(info_header)

        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        self.card_model = StatusCard("Robot", "")
        self.card_ee = StatusCard("End Effector", "")
        self.card_network = StatusCard("Network", "")
        self.card_ip = StatusCard("Robot IP", "")
        self.card_xr = StatusCard("XR", "")
        info_grid.addWidget(self.card_model, 0, 0)
        info_grid.addWidget(self.card_ee, 0, 1)
        info_grid.addWidget(self.card_network, 1, 0)
        info_grid.addWidget(self.card_ip, 1, 1)
        info_grid.addWidget(self.card_xr, 2, 0)
        layout.addLayout(info_grid)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setObjectName("PrimaryButton")
        self.btn_test.clicked.connect(self.test_connection_requested.emit)

        self.btn_start = QPushButton("Start Teleoperation")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self.start_teleop_requested.emit)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("DangerButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_teleop_requested.emit)

        self.btn_sim = QPushButton("Start Simulation")
        self.btn_sim.clicked.connect(self.start_sim_requested.emit)

        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_sim)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        # Metrics section
        metrics_header = QLabel("METRICS")
        metrics_header.setObjectName("SectionHeader")
        layout.addWidget(metrics_header)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(8)
        self.metric_cpu = MetricCard("CPU", "—")
        self.metric_mem = MetricCard("Memory", "—")
        self.metric_latency = MetricCard("Latency", "—")
        self.metric_control = MetricCard("Control", "—")
        metrics_grid.addWidget(self.metric_cpu, 0, 0)
        metrics_grid.addWidget(self.metric_mem, 0, 1)
        metrics_grid.addWidget(self.metric_latency, 0, 2)
        metrics_grid.addWidget(self.metric_control, 0, 3)
        layout.addLayout(metrics_grid)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # -- update methods ----------------------------------------------------

    def update_status(self, status):
        """Update the dashboard from a SystemStatus object."""
        self.ind_windows.set_status(status.windows)
        self.ind_network.set_status(status.network)
        self.ind_robot.set_status(status.robot)
        self.ind_dds.set_status(status.dds)
        self.ind_xr.set_status(status.xr)

        if status.teleop == TeleopState.ACTIVE:
            self.ind_teleop.set_status(StatusLevel.OK, "Active")
        elif status.teleop == TeleopState.READY:
            self.ind_teleop.set_status(StatusLevel.WARNING, "Ready")
        elif status.teleop == TeleopState.ERROR:
            self.ind_teleop.set_status(StatusLevel.ERROR, "Error")
        else:
            self.ind_teleop.set_status(StatusLevel.IDLE, "Stopped")

        # Robot info
        self.card_model.set_value(status.robot_model or "—")
        self.card_ee.set_value(status.end_effector or "—")
        self.card_network.set_value(status.network_name or "—")
        self.card_ip.set_value(status.robot_ip or "—")
        self.card_xr.set_value(status.xr_device or "—")

        # Metrics
        self.metric_cpu.set_value(f"{status.cpu_percent:.0f}%")
        self.metric_mem.set_value(f"{status.memory_mb:.1f} GB")
        if status.latency_ms > 0:
            self.metric_latency.set_value(f"{status.latency_ms:.1f} ms")
        else:
            self.metric_latency.set_value("—")
        if status.control_hz > 0:
            self.metric_control.set_value(f"{status.control_hz:.0f} Hz")
        else:
            self.metric_control.set_value("—")

    def update_metrics(self, metrics: dict):
        """Update metrics from MetricsWorker."""
        if "cpu_percent" in metrics:
            self.metric_cpu.set_value(f"{metrics['cpu_percent']:.0f}%")
        if "memory_mb" in metrics:
            self.metric_mem.set_value(f"{metrics['memory_mb'] / 1024:.1f} GB")

    def set_teleop_state(self, state: TeleopState):
        """Enable/disable buttons based on teleop state."""
        if state == TeleopState.ACTIVE:
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_sim.setEnabled(False)
        elif state == TeleopState.READY:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_sim.setEnabled(False)
        else:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_sim.setEnabled(True)
