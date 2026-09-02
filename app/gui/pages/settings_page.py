"""
Settings page — application configuration with sections.

Sections:
  - Robot (model, IP, end effector, input/display mode)
  - Network (adapter, auto-select)
  - XR (device, port, HTTPS)
  - Recording (save dir, task info)
  - Application (theme, log level, start behavior, sim mode)
  - Advanced (DDS domain, debug, headless)
  - About (version info)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget,
)

from app.models import RobotModel, EndEffector, XRDevice, valid_end_effectors
from app import __version__, __app_name__


class SettingsPage(QWidget):
    """Application settings page."""

    config_changed = Signal()

    def __init__(self, config_service, network_service, parent=None):
        super().__init__(parent)
        self._config_service = config_service
        self._network_service = network_service
        self._build_ui()
        self._load_from_config()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("SETTINGS")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        # --- Robot section ---
        robot_group = QGroupBox("Robot")
        robot_layout = QGridLayout(robot_group)
        robot_layout.setSpacing(8)

        robot_layout.addWidget(QLabel("Model:"), 0, 0)
        self.combo_robot_model = QComboBox()
        for m in RobotModel:
            self.combo_robot_model.addItem(m.display_name, m.value)
        self.combo_robot_model.currentIndexChanged.connect(self._on_robot_model_changed)
        robot_layout.addWidget(self.combo_robot_model, 0, 1)

        robot_layout.addWidget(QLabel("Robot IP:"), 1, 0)
        self.edit_robot_ip = QLineEdit()
        robot_layout.addWidget(self.edit_robot_ip, 1, 1)

        robot_layout.addWidget(QLabel("End Effector:"), 2, 0)
        self.combo_ee = QComboBox()
        robot_layout.addWidget(self.combo_ee, 2, 1)

        robot_layout.addWidget(QLabel("Input Mode:"), 3, 0)
        self.combo_input_mode = QComboBox()
        self.combo_input_mode.addItems(["hand", "controller"])
        robot_layout.addWidget(self.combo_input_mode, 3, 1)

        robot_layout.addWidget(QLabel("Display Mode:"), 4, 0)
        self.combo_display_mode = QComboBox()
        self.combo_display_mode.addItems(["immersive", "ego", "pass-through"])
        robot_layout.addWidget(self.combo_display_mode, 4, 1)

        robot_layout.addWidget(QLabel("Frequency (Hz):"), 5, 0)
        self.spin_frequency = QDoubleSpinBox()
        self.spin_frequency.setRange(1.0, 200.0)
        self.spin_frequency.setValue(30.0)
        robot_layout.addWidget(self.spin_frequency, 5, 1)

        robot_layout.addWidget(QLabel("Motion Control:"), 6, 0)
        self.chk_motion = QCheckBox("Enable motion control mode")
        robot_layout.addWidget(self.chk_motion, 6, 1)

        layout.addWidget(robot_group)

        # --- Network section ---
        net_group = QGroupBox("Network")
        net_layout = QGridLayout(net_group)
        net_layout.setSpacing(8)

        net_layout.addWidget(QLabel("Adapter:"), 0, 0)
        self.combo_network = QComboBox()
        self._refresh_network()
        net_layout.addWidget(self.combo_network, 0, 1)

        btn_refresh_net = QPushButton("Refresh")
        btn_refresh_net.clicked.connect(self._refresh_network)
        net_layout.addWidget(btn_refresh_net, 0, 2)

        net_layout.addWidget(QLabel("Auto Select:"), 1, 0)
        self.chk_auto_select = QCheckBox("Automatically select best adapter")
        net_layout.addWidget(self.chk_auto_select, 1, 1)

        layout.addWidget(net_group)

        # --- XR section ---
        xr_group = QGroupBox("XR")
        xr_layout = QGridLayout(xr_group)
        xr_layout.setSpacing(8)

        xr_layout.addWidget(QLabel("Device:"), 0, 0)
        self.combo_xr_device = QComboBox()
        for d in XRDevice:
            self.combo_xr_device.addItem(d.display_name, d.value)
        xr_layout.addWidget(self.combo_xr_device, 0, 1)

        xr_layout.addWidget(QLabel("Port:"), 1, 0)
        self.spin_xr_port = QSpinBox()
        self.spin_xr_port.setRange(1, 65535)
        self.spin_xr_port.setValue(8012)
        xr_layout.addWidget(self.spin_xr_port, 1, 1)

        xr_layout.addWidget(QLabel("HTTPS:"), 2, 0)
        self.chk_https = QCheckBox("Enable HTTPS for XR server")
        xr_layout.addWidget(self.chk_https, 2, 1)

        layout.addWidget(xr_group)

        # --- Recording section ---
        rec_group = QGroupBox("Recording")
        rec_layout = QGridLayout(rec_group)
        rec_layout.setSpacing(8)

        rec_layout.addWidget(QLabel("Save Directory:"), 0, 0)
        self.edit_save_dir = QLineEdit()
        rec_layout.addWidget(self.edit_save_dir, 0, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_save_dir)
        rec_layout.addWidget(btn_browse, 0, 2)

        rec_layout.addWidget(QLabel("Task Name:"), 1, 0)
        self.edit_task_name = QLineEdit()
        rec_layout.addWidget(self.edit_task_name, 1, 1)

        layout.addWidget(rec_group)

        # --- Application section ---
        app_group = QGroupBox("Application")
        app_layout = QGridLayout(app_group)
        app_layout.setSpacing(8)

        app_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"])
        app_layout.addWidget(self.combo_theme, 0, 1)

        app_layout.addWidget(QLabel("Log Level:"), 1, 0)
        self.combo_log_level = QComboBox()
        self.combo_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        app_layout.addWidget(self.combo_log_level, 1, 1)

        app_layout.addWidget(QLabel("Start Behavior:"), 2, 0)
        self.combo_start_behavior = QComboBox()
        self.combo_start_behavior.addItems(["dashboard", "wizard"])
        app_layout.addWidget(self.combo_start_behavior, 2, 1)

        app_layout.addWidget(QLabel("Simulation Mode:"), 3, 0)
        self.chk_sim = QCheckBox("Start in simulation mode (no physical robot)")
        app_layout.addWidget(self.chk_sim, 3, 1)

        layout.addWidget(app_group)

        # --- Advanced section ---
        adv_group = QGroupBox("Advanced")
        adv_layout = QGridLayout(adv_group)
        adv_layout.setSpacing(8)

        adv_layout.addWidget(QLabel("DDS Domain:"), 0, 0)
        self.spin_dds_domain = QSpinBox()
        self.spin_dds_domain.setRange(0, 255)
        adv_layout.addWidget(self.spin_dds_domain, 0, 1)

        adv_layout.addWidget(QLabel("Debug Mode:"), 1, 0)
        self.chk_debug = QCheckBox("Enable verbose debug logging")
        adv_layout.addWidget(self.chk_debug, 1, 1)

        adv_layout.addWidget(QLabel("Headless:"), 2, 0)
        self.chk_headless = QCheckBox("Run XR server without display")
        adv_layout.addWidget(self.chk_headless, 2, 1)

        layout.addWidget(adv_group)

        # --- About section ---
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout(about_group)
        about_layout.addWidget(QLabel(f"{__app_name__}"))
        about_layout.addWidget(QLabel(f"Version {__version__}"))
        about_layout.addWidget(QLabel("© Unitree Robotics"))
        layout.addWidget(about_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save)
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.clicked.connect(self._reset)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _refresh_network(self):
        self.combo_network.clear()
        self.combo_network.addItem("Auto (recommended)", None)
        try:
            for ni in self._network_service.list_interfaces():
                if ni.is_up and not ni.is_loopback:
                    label = f"{ni.name} ({ni.ipv4})"
                    if ni.is_virtual:
                        label += " [virtual]"
                    self.combo_network.addItem(label, ni.name)
        except Exception:
            pass

    def _on_robot_model_changed(self):
        model_val = self.combo_robot_model.currentData()
        if not model_val:
            return
        model = RobotModel(model_val)
        self.combo_ee.clear()
        for ee in valid_end_effectors(model):
            self.combo_ee.addItem(ee.display_name, ee.value)

    def _browse_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Recording Directory")
        if d:
            self.edit_save_dir.setText(d)

    def _load_from_config(self):
        c = self._config_service.config
        # Robot
        idx = self.combo_robot_model.findData(c.robot.model.value)
        if idx >= 0:
            self.combo_robot_model.setCurrentIndex(idx)
        self._on_robot_model_changed()
        self.edit_robot_ip.setText(c.robot.ip)
        ee_idx = self.combo_ee.findData(c.robot.end_effector.value)
        if ee_idx >= 0:
            self.combo_ee.setCurrentIndex(ee_idx)
        im_idx = self.combo_input_mode.findText(c.robot.input_mode)
        if im_idx >= 0:
            self.combo_input_mode.setCurrentIndex(im_idx)
        dm_idx = self.combo_display_mode.findText(c.robot.display_mode)
        if dm_idx >= 0:
            self.combo_display_mode.setCurrentIndex(dm_idx)
        self.spin_frequency.setValue(c.robot.frequency)
        self.chk_motion.setChecked(c.robot.motion)
        # Network
        if c.network.interface:
            ni_idx = self.combo_network.findData(c.network.interface)
            if ni_idx >= 0:
                self.combo_network.setCurrentIndex(ni_idx)
        self.chk_auto_select.setChecked(c.network.auto_select)
        # XR
        xr_idx = self.combo_xr_device.findData(c.xr.device.value)
        if xr_idx >= 0:
            self.combo_xr_device.setCurrentIndex(xr_idx)
        self.spin_xr_port.setValue(c.xr.port)
        self.chk_https.setChecked(c.xr.https_enabled)
        # Recording
        self.edit_save_dir.setText(c.recording.save_dir)
        self.edit_task_name.setText(c.recording.task_name)
        # App
        t_idx = self.combo_theme.findText(c.app.theme)
        if t_idx >= 0:
            self.combo_theme.setCurrentIndex(t_idx)
        l_idx = self.combo_log_level.findText(c.app.log_level)
        if l_idx >= 0:
            self.combo_log_level.setCurrentIndex(l_idx)
        sb_idx = self.combo_start_behavior.findText(c.app.start_behavior)
        if sb_idx >= 0:
            self.combo_start_behavior.setCurrentIndex(sb_idx)
        self.chk_sim.setChecked(c.app.sim_mode)
        # Advanced
        self.spin_dds_domain.setValue(c.advanced.dds_domain)
        self.chk_debug.setChecked(c.advanced.debug_mode)
        self.chk_headless.setChecked(c.advanced.headless)

    def _save(self):
        c = self._config_service.config
        # Robot
        model_val = self.combo_robot_model.currentData()
        if model_val:
            c.robot.model = RobotModel(model_val)
        c.robot.ip = self.edit_robot_ip.text().strip()
        ee_val = self.combo_ee.currentData()
        if ee_val:
            c.robot.end_effector = EndEffector(ee_val)
        c.robot.input_mode = self.combo_input_mode.currentText()
        c.robot.display_mode = self.combo_display_mode.currentText()
        c.robot.frequency = self.spin_frequency.value()
        c.robot.motion = self.chk_motion.isChecked()
        # Network
        c.network.interface = self.combo_network.currentData()
        c.network.auto_select = self.chk_auto_select.isChecked()
        # XR
        xr_val = self.combo_xr_device.currentData()
        if xr_val:
            c.xr.device = XRDevice(xr_val)
        c.xr.port = self.spin_xr_port.value()
        c.xr.https_enabled = self.chk_https.isChecked()
        # Recording
        c.recording.save_dir = self.edit_save_dir.text().strip()
        c.recording.task_name = self.edit_task_name.text().strip()
        # App
        c.app.theme = self.combo_theme.currentText()
        c.app.log_level = self.combo_log_level.currentText()
        c.app.start_behavior = self.combo_start_behavior.currentText()
        c.app.sim_mode = self.chk_sim.isChecked()
        # Advanced
        c.advanced.dds_domain = self.spin_dds_domain.value()
        c.advanced.debug_mode = self.chk_debug.isChecked()
        c.advanced.headless = self.chk_headless.isChecked()

        self._config_service.save()
        self.config_changed.emit()

    def _reset(self):
        self._config_service.reset()
        self._load_from_config()
        self.config_changed.emit()
