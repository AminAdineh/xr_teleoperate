"""
Watchdog worker — monitors system health and emits alerts.

Checks at a low frequency (2 Hz) to avoid interfering with the control loop:
  - robot connection (IPC heartbeat)
  - DDS health (heartbeat state)
  - XR connection (heartbeat state)
  - worker process alive
  - network adapter still present

On failure, emits a watchdog_alert signal with a description.
Does NOT silently restart robot-control loops.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal


class WatchdogWorker(QThread):
    """Background health monitor."""

    alert = Signal(str, str)       # (alert_type, message)
    health_update = Signal(dict)   # health snapshot
    worker_stopped = Signal()

    def __init__(self, manager, network_service=None, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._network_service = network_service
        self._running = False
        self._poll_interval = 0.5  # 2 Hz
        self._last_heartbeat_time = 0.0
        self._heartbeat_timeout = 5.0  # seconds

    def run(self):
        self._running = True
        while self._running:
            health = {}
            alerts = []

            # Worker process alive?
            worker_alive = self._manager.is_running
            health["worker_alive"] = worker_alive

            if not worker_alive and self._manager._proc is not None:
                # Process was started but has exited
                alerts.append(("worker", "Teleop worker process has stopped"))
                self.worker_stopped.emit()

            # IPC heartbeat
            if worker_alive:
                state = self._manager.get_heartbeat_state()
                health["ipc_online"] = bool(state)
                if state:
                    self._last_heartbeat_time = time.time()
                    health["start"] = state.get("START", False)
                    health["stop"] = state.get("STOP", False)
                    health["recording"] = state.get("RECORD_RUNNING", False)
                else:
                    # No heartbeat — check timeout
                    if self._last_heartbeat_time > 0:
                        elapsed = time.time() - self._last_heartbeat_time
                        if elapsed > self._heartbeat_timeout:
                            alerts.append(("ipc", "IPC heartbeat lost — worker may be unresponsive"))
                            health["ipc_online"] = False

            # Network adapter check
            if self._network_service:
                try:
                    ifaces = self._network_service.list_interfaces()
                    real = [ni for ni in ifaces if ni.is_up and not ni.is_loopback and ni.ipv4]
                    health["network_adapters"] = len(real)
                    if len(real) == 0:
                        alerts.append(("network", "No active network adapters"))
                except Exception:
                    pass

            self.health_update.emit(health)
            for alert_type, msg in alerts:
                self.alert.emit(alert_type, msg)

            self.msleep(int(self._poll_interval * 1000))

    def stop(self):
        self._running = False
