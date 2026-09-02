"""
Confirmation dialog for starting teleoperation.

Shows a summary of the configuration and asks for confirmation
before starting teleoperation (safety requirement).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


class StartConfirmDialog(QDialog):
    """Confirmation dialog before starting teleoperation."""

    def __init__(self, robot: str, end_effector: str, network: str,
                 xr_device: str, sim_mode: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start Teleoperation")
        self.setModal(True)
        self.resize(450, 300)
        self._build(robot, end_effector, network, xr_device, sim_mode)

    def _build(self, robot, ee, network, xr, sim):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Ready to start teleoperation.")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel(f"Robot: {robot}"))
        layout.addWidget(QLabel(f"End Effector: {ee}"))
        layout.addWidget(QLabel(f"Network: {network}"))
        layout.addWidget(QLabel(f"XR: {xr}"))
        if sim:
            layout.addWidget(QLabel(""))
            warn = QLabel("⚠ SIMULATION MODE — No physical robot commands will be sent.")
            warn.setStyleSheet("color: #fbbf24; font-weight: bold;")
            layout.addWidget(warn)
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Make sure the robot is in a safe state."))
        layout.addWidget(QLabel(""))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("PrimaryButton")
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_start.clicked.connect(self.accept)
