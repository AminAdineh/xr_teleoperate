"""
StatusCard — a card panel showing a label and value (for dashboard info).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatusCard(QFrame):
    """A card showing a title and value."""

    def __init__(self, title: str = "", value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("CardTitle")
        self._value_label = QLabel(value)
        self._value_label.setObjectName("CardValue")

        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)

    def set_title(self, title: str):
        self._title_label.setText(title)

    def set_value(self, value: str):
        self._value_label.setText(value)
