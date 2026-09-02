"""
Teleop worker — wraps WorkerManager operations in QThread signals.

This worker is NOT the teleop process itself; it is a thin QThread that
calls WorkerManager methods (which manage the subprocess) and emits Qt
signals for the GUI to react to state changes.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.services.worker_manager import WorkerManager


class TeleopWorker(QThread):
    """
    Monitors the teleop subprocess and emits state-change signals.

    Runs a periodic poll loop that checks:
      - process alive
      - IPC heartbeat state
      - crash detection
    """

    state_changed = Signal(dict)     # heartbeat state
    worker_crashed = Signal(str)     # error message
    worker_started = Signal()
    worker_stopped = Signal()

    def __init__(self, manager: WorkerManager, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._running = False
        self._poll_interval = 0.5  # seconds

    def run(self):
        self._running = True
        self._manager.set_state_callback(self._on_state)
        self._manager.set_crash_callback(self._on_crash)

        while self._running:
            if self._manager.is_running:
                state = self._manager.get_heartbeat_state()
                if state:
                    self.state_changed.emit(state)
            else:
                # Worker not running — could be crashed or not started
                pass
            self.msleep(int(self._poll_interval * 1000))

    def stop(self):
        self._running = False

    def _on_state(self, state: dict):
        self.state_changed.emit(state)

    def _on_crash(self, msg: str):
        self.worker_crashed.emit(msg)
