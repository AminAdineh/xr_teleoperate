"""
Teleoperation page — live teleoperation monitoring screen.

Shows real-time status of the teleop session and a large STOP button.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.gui.widgets.status_indicator import StatusIndicator
from app.gui.widgets.metric_card import MetricCard
from app.models import StatusLevel, TeleopState


class TeleopPage(QWidget):
    """Live teleoperation monitoring page."""

    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("TELEOPERATION")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        # Status indicators
        status_frame = QFrame()
        status_frame.setObjectName("Card")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 16, 20, 16)
        status_layout.setSpacing(10)

        self.ind_robot = StatusIndicator("Robot")
        self.ind_dds = StatusIndicator("DDS")
        self.ind_xr = StatusIndicator("XR")
        self.ind_control = StatusIndicator("Control")
        self.ind_arm = StatusIndicator("Arm")
        self.ind_hands = StatusIndicator("Hands")

        for ind in [self.ind_robot, self.ind_dds, self.ind_xr,
                    self.ind_control, self.ind_arm, self.ind_hands]:
            status_layout.addWidget(ind)

        layout.addWidget(status_frame)

        # Metrics
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(8)
        self.metric_freq = MetricCard("Frequency", "—")
        self.metric_latency = MetricCard("Latency", "—")
        self.metric_xr_fps = MetricCard("XR Tracking", "—")
        metrics_grid.addWidget(self.metric_freq, 0, 0)
        metrics_grid.addWidget(self.metric_latency, 0, 1)
        metrics_grid.addWidget(self.metric_xr_fps, 0, 2)
        layout.addLayout(metrics_grid)

        # Recording status (if active)
        self.recording_frame = QFrame()
        self.recording_frame.setObjectName("Card")
        rec_layout = QGridLayout(self.recording_frame)
        rec_layout.setContentsMargins(20, 12, 20, 12)
        rec_layout.setSpacing(8)
        rec_layout.addWidget(QLabel("Recording"), 0, 0)
        self.rec_status = QLabel("● INACTIVE")
        self.rec_status.setStyleSheet("color: #a0a0b8; font-size: 14px; font-weight: bold;")
        rec_layout.addWidget(self.rec_status, 0, 1)
        self.rec_duration = MetricCard("Duration", "00:00:00")
        self.rec_frames = MetricCard("Frames", "0")
        rec_layout.addWidget(self.rec_duration, 1, 0)
        rec_layout.addWidget(self.rec_frames, 1, 1)
        layout.addWidget(self.recording_frame)

        layout.addStretch()

        # Large STOP button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_stop = QPushButton("STOP TELEOPERATION")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def update_status(self, status):
        """Update from SystemStatus."""
        if status.robot_connected:
            self.ind_robot.set_status(StatusLevel.OK, "Connected")
        else:
            self.ind_robot.set_status(StatusLevel.ERROR, "Disconnected")

        if status.dds_healthy:
            self.ind_dds.set_status(StatusLevel.OK, "Healthy")
        else:
            self.ind_dds.set_status(StatusLevel.ERROR, "Unhealthy")

        if status.xr_connected:
            self.ind_xr.set_status(StatusLevel.OK, "Connected")
        else:
            self.ind_xr.set_status(StatusLevel.WARNING, "Waiting")

        if status.teleop == TeleopState.ACTIVE:
            self.ind_control.set_status(StatusLevel.OK, "ACTIVE")
            self.ind_arm.set_status(StatusLevel.OK, "ACTIVE")
            self.ind_hands.set_status(StatusLevel.OK, "ACTIVE")
            self.btn_stop.setEnabled(True)
        elif status.teleop == TeleopState.READY:
            self.ind_control.set_status(StatusLevel.WARNING, "Ready")
            self.ind_arm.set_status(StatusLevel.IDLE, "Idle")
            self.ind_hands.set_status(StatusLevel.IDLE, "Idle")
            self.btn_stop.setEnabled(True)
        else:
            self.ind_control.set_status(StatusLevel.IDLE, "Stopped")
            self.ind_arm.set_status(StatusLevel.IDLE, "Idle")
            self.ind_hands.set_status(StatusLevel.IDLE, "Idle")
            self.btn_stop.setEnabled(False)

        if status.control_hz > 0:
            self.metric_freq.set_value(f"{status.control_hz:.0f} Hz")
        if status.latency_ms > 0:
            self.metric_latency.set_value(f"{status.latency_ms:.1f} ms")

        # Recording
        if status.recording_active:
            self.rec_status.setText("● ACTIVE")
            self.rec_status.setStyleSheet("color: #f87171; font-size: 14px; font-weight: bold;")
            secs = int(status.recording_duration)
            h = secs // 3600
            m = (secs % 3600) // 60
            s = secs % 60
            self.rec_duration.set_value(f"{h:02d}:{m:02d}:{s:02d}")
            self.rec_frames.set_value(f"{status.recording_frames:,}")
        else:
            self.rec_status.setText("● INACTIVE")
            self.rec_status.setStyleSheet("color: #a0a0b8; font-size: 14px; font-weight: bold;")
