"""
Diagnostics worker — runs diagnostics checks in a background QThread.

Emits results as they complete so the GUI can update progressively.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.services import DiagnosticsService, CheckResult


class DiagnosticsWorker(QThread):
    """Runs diagnostics checks in the background."""

    check_complete = Signal(object)   # CheckResult
    all_complete = Signal(list)        # list[CheckResult]
    error = Signal(str)

    def __init__(self, service: DiagnosticsService, mode: str = "system",
                 robot_ip: str = "", network_interface: str = None,
                 parent=None):
        super().__init__(parent)
        self._service = service
        self._mode = mode
        self._robot_ip = robot_ip
        self._network_interface = network_interface

    def run(self):
        try:
            results: list[CheckResult] = []
            if self._mode == "system":
                results = self._service.run_system_check()
            elif self._mode == "dependencies":
                results = self._service.run_dependency_check()
            elif self._mode == "connection":
                results = self._service.run_connection_test(
                    self._robot_ip, self._network_interface,
                )
            elif self._mode == "all":
                results = (
                    self._service.run_system_check()
                    + self._service.run_dependency_check()
                    + self._service.run_connection_test(
                        self._robot_ip, self._network_interface,
                    )
                )
            else:
                results = []

            for r in results:
                self.check_complete.emit(r)
            self.all_complete.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))
