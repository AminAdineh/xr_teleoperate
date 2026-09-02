"""
Metrics worker — collects CPU, memory, and latency metrics at low frequency.

Updates at 2-5 Hz to avoid interfering with the real-time control loop.
The control loop's own frequency is reported via IPC heartbeat, not here.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal


class MetricsWorker(QThread):
    """Background metrics collector."""

    metrics_update = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._interval = 0.5  # 2 Hz

    def run(self):
        self._running = True
        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False

        while self._running:
            metrics = {}
            if has_psutil:
                try:
                    metrics["cpu_percent"] = psutil.cpu_percent(interval=0.3)
                    mem = psutil.virtual_memory()
                    metrics["memory_mb"] = mem.used / (1024 * 1024)
                    metrics["memory_percent"] = mem.percent
                except Exception:
                    pass
            else:
                metrics["cpu_percent"] = 0.0
                metrics["memory_mb"] = 0.0

            self.metrics_update.emit(metrics)
            self.msleep(int(self._interval * 1000))

    def stop(self):
        self._running = False
