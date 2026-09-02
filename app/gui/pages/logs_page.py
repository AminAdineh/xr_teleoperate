"""
Logs page — live log viewer with filtering, save, copy, and clear.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QVBoxLayout, QWidget, QFileDialog,
)


class LogsPage(QWidget):
    """Live application log viewer."""

    def __init__(self, logging_service, parent=None):
        super().__init__(parent)
        self._logging = logging_service
        self._build_ui()

        # Refresh timer (5 Hz)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(200)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("LOGS")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e8e8f0;")
        layout.addWidget(title)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["all", "gui", "app", "robot", "dds", "xr"])
        filter_layout.addWidget(self.category_combo)

        filter_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        filter_layout.addWidget(self.level_combo)

        filter_layout.addStretch()

        self.btn_save = QPushButton("Save Logs")
        self.btn_save.clicked.connect(self._save_logs)
        self.btn_copy = QPushButton("Copy Logs")
        self.btn_copy.clicked.connect(self._copy_logs)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear)
        filter_layout.addWidget(self.btn_save)
        filter_layout.addWidget(self.btn_copy)
        filter_layout.addWidget(self.btn_clear)
        layout.addLayout(filter_layout)

        # Log view
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(10000)
        layout.addWidget(self.log_view)

    def _refresh(self):
        category = self.category_combo.currentText()
        level = self.level_combo.currentText()
        records = self._logging.get_records(category=category, level=level)
        # Build text (only append new records to avoid flicker)
        lines = [
            f"{r['timestamp']} {r['level']:8s} {r['message']}"
            for r in records[-200:]
        ]
        self.log_view.setPlainText("\n".join(lines))
        # Auto-scroll to bottom
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _save_logs(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "unitree_teleop_logs.txt", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            category = self.category_combo.currentText()
            level = self.level_combo.currentText()
            count = self._logging.save_to_file(path, category=category, level=level)
            self.log_view.appendPlainText(f"\n--- Saved {count} log lines to {path} ---")

    def _copy_logs(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_view.toPlainText())

    def _clear(self):
        self._logging.clear_buffer()
        self.log_view.clear()

    def stop(self):
        self._timer.stop()
