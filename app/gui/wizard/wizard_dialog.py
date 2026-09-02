"""
First-run setup wizard.

Steps:
  Welcome → System Check → Network → Robot → End Effector → XR →
  Certificate → Connection Test → Finish

The wizard saves the configuration on completion.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QCheckBox, QGridLayout,
)

from app.models import (
    AppConfig, RobotModel, EndEffector, XRDevice, valid_end_effectors,
)
from app.services import (
    DiagnosticsService, NetworkService, CertificateService, CheckResult,
)
from app.workers import DiagnosticsWorker


class WizardDialog(QDialog):
    """Multi-step first-run setup wizard."""

    wizard_completed = Signal()

    STEPS = [
        "Welcome",
        "System Check",
        "Network",
        "Robot",
        "End Effector",
        "XR",
        "Certificate",
        "Connection Test",
        "Finish",
    ]

    def __init__(self, config_service, parent=None):
        super().__init__(parent)
        self._config_service = config_service
        self._network_service = NetworkService()
        self._cert_service = CertificateService()
        self._diag_service = DiagnosticsService()
        self._step = 0
        self._build_ui()
        self._go_to_step(0)

    def _build_ui(self):
        self.setWindowTitle("Setup Wizard — Unitree XR Teleoperate")
        self.setModal(True)
        self.resize(700, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Step indicator bar
        self.step_bar = QLabel()
        self.step_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step_bar.setStyleSheet(
            "background-color: #16161e; color: #a0a0b8; padding: 12px; font-size: 14px;"
        )
        layout.addWidget(self.step_bar)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        layout.addWidget(self.progress)

        # Content area (scrollable)
        self.content = QScrollArea()
        self.content.setWidgetResizable(True)
        self.content.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.content)

        # Button bar
        btn_bar = QFrame()
        btn_bar.setStyleSheet("background-color: #16161e;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 12, 16, 12)
        btn_layout.setSpacing(8)

        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self._prev_step)
        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryButton")
        self.btn_next.clicked.connect(self._next_step)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_back)
        btn_layout.addWidget(self.btn_next)
        layout.addWidget(btn_bar)

    # -- navigation --------------------------------------------------------

    def _update_step_bar(self):
        self.step_bar.setText(f"Step {self._step + 1} of {len(self.STEPS)}: {self.STEPS[self._step]}")
        self.progress.setValue(int((self._step + 1) / len(self.STEPS) * 100))
        self.btn_back.setEnabled(self._step > 0)
        if self._step == len(self.STEPS) - 1:
            self.btn_next.setText("Finish")
        else:
            self.btn_next.setText("Next")

    def _go_to_step(self, step: int):
        self._step = max(0, min(step, len(self.STEPS) - 1))
        self._update_step_bar()
        builder = self._step_builders.get(self._step)
        if builder:
            widget = builder(self)
            self.content.setWidget(widget)

    def _next_step(self):
        if self._step == len(self.STEPS) - 1:
            self._finish()
        else:
            self._save_current_step()
            self._go_to_step(self._step + 1)

    def _prev_step(self):
        self._go_to_step(self._step - 1)

    def _save_current_step(self):
        """Save data from the current step into config."""
        c = self._config_service.config
        if self._step == 2:  # Network
            idx = self._network_combo.currentIndex()
            if idx > 0:
                c.network.interface = self._network_combo.currentData()
            else:
                c.network.interface = None
                c.network.auto_select = True
        elif self._step == 3:  # Robot
            model_val = self._robot_combo.currentData()
            if model_val:
                c.robot.model = RobotModel(model_val)
            c.robot.ip = self._robot_ip.text().strip()
        elif self._step == 4:  # End Effector
            ee_val = self._ee_combo.currentData()
            if ee_val:
                c.robot.end_effector = EndEffector(ee_val)
        elif self._step == 5:  # XR
            xr_val = self._xr_combo.currentData()
            if xr_val:
                c.xr.device = XRDevice(xr_val)

    def _finish(self):
        c = self._config_service.config
        c.wizard_completed = True
        self._config_service.save()
        self.wizard_completed.emit()
        self.accept()

    # -- step builders -----------------------------------------------------

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("Welcome to Unitree XR Teleoperate")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        lines = [
            "This wizard will guide you through the initial setup of your",
            "Unitree XR Teleoperation system.",
            "",
            "You will configure:",
            "  • Network adapter for robot communication",
            "  • Robot model and IP address",
            "  • End effector type",
            "  • XR device settings",
            "  • SSL certificate for HTTPS",
            "  • Connection test",
            "",
            "Click Next to begin.",
        ]
        for line in lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("font-size: 14px; color: #a0a0b8;")
            layout.addWidget(lbl)

        layout.addStretch()
        return w

    def _build_system_check(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("System Check"))
        layout.addWidget(QLabel(
            "Checking your system for required components...\n"
            "This runs in the background; results appear below."
        ))

        self._sys_table = QTableWidget(0, 3)
        self._sys_table.setHorizontalHeaderLabels(["Check", "Status", "Detail"])
        self._sys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._sys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._sys_table.horizontalHeader().resizeSection(1, 80)
        self._sys_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._sys_table.verticalHeader().setVisible(False)
        layout.addWidget(self._sys_table)

        self._sys_summary = QLabel("Running checks...")
        layout.addWidget(self._sys_summary)

        # Run diagnostics
        self._sys_worker = DiagnosticsWorker(self._diag_service, mode="system")
        self._sys_worker.check_complete.connect(self._on_sys_check)
        self._sys_worker.all_complete.connect(self._on_sys_all)
        self._sys_worker.start()

        layout.addStretch()
        return w

    def _on_sys_check(self, result: CheckResult):
        row = self._sys_table.rowCount()
        self._sys_table.insertRow(row)
        self._sys_table.setItem(row, 0, QTableWidgetItem(result.name))
        status_text = {"pass": "✓", "warn": "⚠", "fail": "✗", "skip": "○"}
        self._sys_table.setItem(row, 1, QTableWidgetItem(status_text.get(result.status, "?")))
        self._sys_table.setItem(row, 2, QTableWidgetItem(result.detail))

    def _on_sys_all(self, results):
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        self._sys_summary.setText(f"{passed} passed, {failed} failed. You can continue even with warnings.")

    def _build_network(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("Network"))
        layout.addWidget(QLabel("Select the network adapter connected to the robot:"))

        self._network_combo = QComboBox()
        self._network_combo.addItem("Auto (recommended)", None)
        for ni in self._network_service.list_interfaces():
            if ni.is_up and not ni.is_loopback:
                label = f"{ni.name} ({ni.ipv4})"
                if ni.ipv4.startswith("192.168.123."):
                    label += " — Recommended"
                self._network_combo.addItem(label, ni.name)

        # Pre-select current config
        c = self._config_service.config
        if c.network.interface:
            for i in range(self._network_combo.count()):
                if self._network_combo.itemData(i) == c.network.interface:
                    self._network_combo.setCurrentIndex(i)
                    break

        layout.addWidget(self._network_combo)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(lambda: self._go_to_step(2))
        layout.addWidget(btn_refresh)

        layout.addStretch()
        return w

    def _build_robot(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("Robot"))
        layout.addWidget(QLabel("Select your robot model and enter its IP address:"))

        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(QLabel("Robot Model:"), 0, 0)
        self._robot_combo = QComboBox()
        for m in RobotModel:
            self._robot_combo.addItem(m.display_name, m.value)
        # Pre-select
        c = self._config_service.config
        idx = self._robot_combo.findData(c.robot.model.value)
        if idx >= 0:
            self._robot_combo.setCurrentIndex(idx)
        self._robot_combo.currentIndexChanged.connect(self._on_wizard_robot_changed)
        grid.addWidget(self._robot_combo, 0, 1)

        grid.addWidget(QLabel("Robot IP:"), 1, 0)
        self._robot_ip = QLineEdit(c.robot.ip)
        grid.addWidget(self._robot_ip, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return w

    def _on_wizard_robot_changed(self):
        model_val = self._robot_combo.currentData()
        if model_val and hasattr(self, "_ee_combo"):
            model = RobotModel(model_val)
            self._ee_combo.clear()
            for ee in valid_end_effectors(model):
                self._ee_combo.addItem(ee.display_name, ee.value)

    def _build_end_effector(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("End Effector"))
        layout.addWidget(QLabel("Select the end effector attached to the robot:"))

        self._ee_combo = QComboBox()
        c = self._config_service.config
        for ee in valid_end_effectors(c.robot.model):
            self._ee_combo.addItem(ee.display_name, ee.value)
        idx = self._ee_combo.findData(c.robot.end_effector.value)
        if idx >= 0:
            self._ee_combo.setCurrentIndex(idx)
        layout.addWidget(self._ee_combo)

        layout.addStretch()
        return w

    def _build_xr(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("XR Device"))
        layout.addWidget(QLabel("Select your XR headset:"))

        self._xr_combo = QComboBox()
        for d in XRDevice:
            self._xr_combo.addItem(d.display_name, d.value)
        c = self._config_service.config
        idx = self._xr_combo.findData(c.xr.device.value)
        if idx >= 0:
            self._xr_combo.setCurrentIndex(idx)
        layout.addWidget(self._xr_combo)

        # Server address
        try:
            lan_ip = self._network_service.get_lan_ip()
            url = f"https://{lan_ip}:{c.xr.port}"
            layout.addWidget(QLabel(f"Server address: {url}"))
        except Exception:
            pass

        layout.addStretch()
        return w

    def _build_certificate(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("Certificate"))
        layout.addWidget(QLabel("SSL certificate status for HTTPS XR communication:"))

        info = self._cert_service.get_info()
        if info.exists and info.valid:
            layout.addWidget(QLabel("✓ Certificate is valid"))
            layout.addWidget(QLabel(f"Location: {info.cert_dir}"))
            if info.expiry:
                layout.addWidget(QLabel(f"Expires: {info.expiry}"))
        elif info.exists:
            layout.addWidget(QLabel("⚠ Certificate exists but may be invalid"))
            layout.addWidget(QLabel(f"Error: {info.error}"))
        else:
            layout.addWidget(QLabel("✗ No certificate found"))

        self._btn_regen = QPushButton("Generate Certificate")
        self._btn_regen.setObjectName("PrimaryButton")
        self._btn_regen.clicked.connect(self._regen_cert)
        layout.addWidget(self._btn_regen)

        self._cert_status = QLabel("")
        layout.addWidget(self._cert_status)

        layout.addStretch()
        return w

    def _regen_cert(self):
        try:
            lan_ip = self._network_service.get_lan_ip()
            self._cert_service.regenerate(lan_ip)
            self._cert_status.setText("✓ Certificate generated successfully")
            self._cert_status.setStyleSheet("color: #4ade80;")
        except Exception as exc:
            self._cert_status.setText(f"✗ Failed: {exc}")
            self._cert_status.setStyleSheet("color: #f87171;")

    def _build_connection_test(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(QLabel("Connection Test"))
        layout.addWidget(QLabel("Testing connection to the robot..."))

        self._conn_table = QTableWidget(0, 3)
        self._conn_table.setHorizontalHeaderLabels(["Check", "Status", "Detail"])
        self._conn_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._conn_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._conn_table.horizontalHeader().resizeSection(1, 80)
        self._conn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._conn_table.verticalHeader().setVisible(False)
        layout.addWidget(self._conn_table)

        self._conn_summary = QLabel("Running connection test...")
        layout.addWidget(self._conn_summary)

        c = self._config_service.config
        self._conn_worker = DiagnosticsWorker(
            self._diag_service, mode="connection",
            robot_ip=c.robot.ip,
            network_interface=c.network.interface,
        )
        self._conn_worker.check_complete.connect(self._on_conn_check)
        self._conn_worker.all_complete.connect(self._on_conn_all)
        self._conn_worker.start()

        layout.addStretch()
        return w

    def _on_conn_check(self, result: CheckResult):
        row = self._conn_table.rowCount()
        self._conn_table.insertRow(row)
        self._conn_table.setItem(row, 0, QTableWidgetItem(result.name))
        status_text = {"pass": "✓", "warn": "⚠", "fail": "✗", "skip": "○"}
        self._conn_table.setItem(row, 1, QTableWidgetItem(status_text.get(result.status, "?")))
        self._conn_table.setItem(row, 2, QTableWidgetItem(result.detail))

    def _on_conn_all(self, results):
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        self._conn_summary.setText(f"{passed} passed, {failed} failed")

    def _build_finish(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("Setup Complete!")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4ade80;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Your Unitree XR Teleoperate system is configured."))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("You can now:"))
        layout.addWidget(QLabel("  • Return to the dashboard"))
        layout.addWidget(QLabel("  • Test your connection"))
        layout.addWidget(QLabel("  • Start teleoperation"))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Click Finish to return to the dashboard."))

        layout.addStretch()
        return w

    # Map step index → builder method
    _step_builders = {
        0: _build_welcome,
        1: _build_system_check,
        2: _build_network,
        3: _build_robot,
        4: _build_end_effector,
        5: _build_xr,
        6: _build_certificate,
        7: _build_connection_test,
        8: _build_finish,
    }
