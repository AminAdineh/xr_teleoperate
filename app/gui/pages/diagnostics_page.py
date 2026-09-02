"""
Diagnostics page — system check and connection test.

Runs diagnostics checks in a background thread and displays results.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox,
)

from app.models import StatusLevel
from app.services import DiagnosticsService, CheckResult
from app.workers import DiagnosticsWorker


class DiagnosticsPage(QWidget):
    """System check / connection test page."""

    def __init__(self, config_service, parent=None):
        super().__init__(parent)
        self._config_service = config_service
        self._service = DiagnosticsService()
        self._worker: DiagnosticsWorker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("DIAGNOSTICS")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)
        mode_label = QLabel("Check mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["System Check", "Dependencies", "Connection Test", "Full Diagnostics"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        self.btn_run = QPushButton("Run Checks")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.clicked.connect(self._run_checks)
        mode_layout.addWidget(self.btn_run)
        layout.addLayout(mode_layout)

        # Results table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Check", "Status", "Detail", "Fix"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().resizeSection(1, 80)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 14px; color: #a0a0b8;")
        layout.addWidget(self.summary_label)

    def _run_checks(self):
        if self._worker and self._worker.isRunning():
            return
        mode_idx = self.mode_combo.currentIndex()
        mode_map = ["system", "dependencies", "connection", "all"]
        mode = mode_map[mode_idx]

        config = self._config_service.config
        self.table.setRowCount(0)
        self.summary_label.setText("Running checks...")
        self.btn_run.setEnabled(False)

        self._worker = DiagnosticsWorker(
            self._service, mode=mode,
            robot_ip=config.robot.ip,
            network_interface=config.network.interface,
        )
        self._worker.check_complete.connect(self._on_check)
        self._worker.all_complete.connect(self._on_all_complete)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_check(self, result: CheckResult):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(result.name))

        status_text = {"pass": "✓ Pass", "warn": "⚠ Warn", "fail": "✗ Fail", "skip": "○ Skip"}
        status_item = QTableWidgetItem(status_text.get(result.status, result.status))
        colors = {"pass": "#4ade80", "warn": "#fbbf24", "fail": "#f87171", "skip": "#a0a0b8"}
        status_item.setForeground(Qt.GlobalColor.white)
        status_item.setData(Qt.ItemDataRole.ForegroundRole, None)
        # Use HTML for coloring
        self.table.setItem(row, 1, status_item)
        # Color the cell
        color = colors.get(result.status, "#a0a0b8")
        for col in range(4):
            item = self.table.item(row, col)
            if item:
                item.setForeground(Qt.GlobalColor.white)

        self.table.setItem(row, 2, QTableWidgetItem(result.detail))
        self.table.setItem(row, 3, QTableWidgetItem(result.fix))

    def _on_all_complete(self, results):
        passed = sum(1 for r in results if r.status == "pass")
        warned = sum(1 for r in results if r.status == "warn")
        failed = sum(1 for r in results if r.status == "fail")
        skipped = sum(1 for r in results if r.status == "skip")
        self.summary_label.setText(
            f"Complete: {passed} passed, {warned} warnings, {failed} failed, {skipped} skipped"
        )
        self.btn_run.setEnabled(True)

    def _on_error(self, msg):
        self.summary_label.setText(f"Error: {msg}")
        self.btn_run.setEnabled(True)
