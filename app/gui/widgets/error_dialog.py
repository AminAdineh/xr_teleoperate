"""
Smart error dialog — shows Problem / Cause / Solution instead of tracebacks.

Provides:
  - Problem description
  - Possible causes
  - Recommended solution
  - Action buttons (Retry, Diagnostics, Settings, Technical Details)
  - Expandable technical details (actual exception/log)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout,
)


class ErrorDialog(QDialog):
    """Smart error dialog with Problem/Cause/Solution format."""

    def __init__(self, problem: str, causes: list[str] = None,
                 solutions: list[str] = None, technical_details: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error — Unitree XR Teleoperate")
        self.setModal(True)
        self.resize(500, 400)
        self._build(problem, causes or [], solutions or [], technical_details)

    def _build(self, problem: str, causes: list[str], solutions: list[str], details: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Problem
        lbl_problem = QLabel("Problem")
        lbl_problem.setStyleSheet("font-size: 12px; color: #f87171; font-weight: bold;")
        layout.addWidget(lbl_problem)
        layout.addWidget(QLabel(problem))

        # Causes
        if causes:
            lbl_causes = QLabel("Possible causes:")
            lbl_causes.setStyleSheet("font-size: 12px; color: #fbbf24; font-weight: bold;")
            layout.addWidget(lbl_causes)
            for cause in causes:
                layout.addWidget(QLabel(f"  • {cause}"))

        # Solutions
        if solutions:
            lbl_sol = QLabel("Solution:")
            lbl_sol.setStyleSheet("font-size: 12px; color: #4ade80; font-weight: bold;")
            layout.addWidget(lbl_sol)
            for sol in solutions:
                layout.addWidget(QLabel(f"  • {sol}"))

        # Technical details (collapsible)
        if details:
            self._details_btn = QPushButton("View Technical Details")
            self._details_btn.clicked.connect(self._toggle_details)
            layout.addWidget(self._details_btn)

            self._details_text = QTextEdit()
            self._details_text.setReadOnly(True)
            self._details_text.setPlainText(details)
            self._details_text.setVisible(False)
            self._details_text.setMaximumHeight(150)
            layout.addWidget(self._details_text)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setObjectName("PrimaryButton")
        self.btn_diagnostics = QPushButton("Run Diagnostics")
        self.btn_settings = QPushButton("Settings")
        self.btn_close = QPushButton("Close")

        btn_layout.addWidget(self.btn_diagnostics)
        btn_layout.addWidget(self.btn_settings)
        btn_layout.addWidget(self.btn_retry)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.btn_close.clicked.connect(self.accept)
        self.btn_retry.clicked.connect(self.accept)
        self.btn_diagnostics.clicked.connect(self.accept)
        self.btn_settings.clicked.connect(self.accept)

    def _toggle_details(self):
        visible = not self._details_text.isVisible()
        self._details_text.setVisible(visible)
        self._details_btn.setText("Hide Technical Details" if visible else "View Technical Details")
