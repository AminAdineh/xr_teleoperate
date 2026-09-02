"""
StatusIndicator — a small colored dot + label for system status display.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from app.models import StatusLevel


class StatusIndicator(QFrame):
    """A status row: colored dot + label + detail text."""

    _DOTS = {
        StatusLevel.OK: ("●", "#4ade80"),
        StatusLevel.WARNING: ("●", "#fbbf24"),
        StatusLevel.ERROR: ("●", "#f87171"),
        StatusLevel.IDLE: ("●", "#a0a0b8"),
        StatusLevel.NOT_TESTED: ("○", "#a0a0b8"),
    }

    _LABELS = {
        StatusLevel.OK: "Ready",
        StatusLevel.WARNING: "Warning",
        StatusLevel.ERROR: "Error",
        StatusLevel.IDLE: "Idle",
        StatusLevel.NOT_TESTED: "Not Tested",
    }

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._status = StatusLevel.IDLE
        self._detail = ""
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(16)
        self._dot.setStyleSheet("color: #a0a0b8;")

        self._label = QLabel(self._label_text)
        self._label.setStyleSheet("color: #a0a0b8; font-size: 14px;")

        self._value = QLabel("Idle")
        self._value.setStyleSheet("color: #a0a0b8; font-size: 14px;")
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()
        layout.addWidget(self._value)

    def set_status(self, status: StatusLevel, detail: str = ""):
        self._status = status
        self._detail = detail
        dot_char, color = self._DOTS.get(status, ("●", "#a0a0b8"))
        label_text = self._LABELS.get(status, "Unknown")
        self._dot.setText(dot_char)
        self._dot.setStyleSheet(f"color: {color};")
        if detail:
            self._value.setText(f"{label_text} — {detail}")
        else:
            self._value.setText(label_text)
        self._value.setStyleSheet(f"color: {color}; font-size: 14px;")
