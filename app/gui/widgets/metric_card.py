"""
MetricCard — a compact metric display (CPU %, memory, latency, etc.).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """Small card for a single metric (label + value + unit)."""

    def __init__(self, label: str = "", value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._label = QLabel(label)
        self._label.setStyleSheet("color: #a0a0b8; font-size: 12px;")
        self._value = QLabel(value)
        self._value.setStyleSheet("color: #e8e8f0; font-size: 16px; font-weight: bold;")

        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, value: str):
        self._value.setText(value)
