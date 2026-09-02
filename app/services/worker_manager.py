"""
Worker manager — launches and monitors the teleoperation core as a subprocess.

The GUI never runs robot-control code directly.  Instead, it launches
``teleop/teleop_hand_and_arm.py`` with the ``--ipc`` flag as a separate
process and communicates via the existing ZMQ IPC mechanism
(``teleop.utils.ipc.IPC_Client``).

This keeps the real-time control loop in its own process, isolated from
GUI thread interruptions, and uses the existing safe-stop mechanism
(CMD_STOP → STOP flag → graceful shutdown in teleop_hand_and_arm.py).
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Project root (parent of the app/ directory)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TELEOP_SCRIPT = _PROJECT_ROOT / "teleop" / "teleop_hand_and_arm.py"


class WorkerManager:
    """
    Manages the teleoperation worker subprocess.

    Lifecycle:
        start(config)  → launch subprocess with --ipc
        send_start()   → IPC CMD_START (robot begins following XR)
        send_stop()     → IPC CMD_STOP  (graceful shutdown)
        send_record()  → IPC CMD_RECORD_TOGGLE
        monitor()      → heartbeat subscription (thread)
        shutdown()     → safe stop + kill if needed
    """

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._ipc_client = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._state_callback: Optional[Callable[[dict], None]] = None
        self._crash_callback: Optional[Callable[[str], None]] = None
        self._lock = threading.Lock()

    # -- properties --------------------------------------------------------

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    @property
    def ipc_online(self) -> bool:
        try:
            return self._ipc_client is not None and self._ipc_client.is_online()
        except Exception:
            return False

    # -- callbacks ---------------------------------------------------------

    def set_state_callback(self, cb: Callable[[dict], None]):
        self._state_callback = cb

    def set_crash_callback(self, cb: Callable[[str], None]):
        self._crash_callback = cb

    # -- build command line ------------------------------------------------

    def _build_args(self, config) -> list[str]:
        """Build the command-line arguments for teleop_hand_and_arm.py."""
        c = config
        args = [
            sys.executable,
            str(_TELEOP_SCRIPT),
            "--ipc",                          # use IPC server (no keyboard)
            "--arm", c.robot.model.value,
            "--ee", c.robot.end_effector.value,
            "--img-server-ip", c.robot.ip,
            "--frequency", str(c.robot.frequency),
            "--input-mode", c.robot.input_mode,
            "--display-mode", c.robot.display_mode,
        ]
        if c.network.interface:
            args += ["--network-interface", c.network.interface]
        if c.robot.motion:
            args.append("--motion")
        if c.advanced.headless or c.app.sim_mode:
            args.append("--headless")
        if c.app.sim_mode:
            args.append("--sim")
        if c.recording.enabled:
            args.append("--record")
            args += ["--task-dir", c.recording.save_dir or "./teleop/data/"]
            args += ["--task-name", c.recording.task_name]
            args += ["--task-goal", c.recording.task_goal]
            args += ["--task-desc", c.recording.task_desc]
            args += ["--task-steps", c.recording.task_steps]
        return args

    # -- start / stop ------------------------------------------------------

    def start(self, config) -> bool:
        """Launch the teleop subprocess.  Returns True on success."""
        with self._lock:
            if self.is_running:
                logger.warning("Worker already running")
                return False

            args = self._build_args(config)
            logger.info("Starting teleop worker: %s", " ".join(args))

            try:
                self._proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(_PROJECT_ROOT),
                    env={**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)},
                )
            except Exception as exc:
                logger.error("Failed to start worker: %s", exc)
                if self._crash_callback:
                    self._crash_callback(str(exc))
                return False

            self._running = True
            # Start monitoring threads
            self._start_stdout_reader()
            self._start_monitor()
            return True

    def _start_stdout_reader(self):
        """Read subprocess stdout in a thread and log it."""
        def _reader():
            proc = self._proc
            if proc is None or proc.stdout is None:
                return
            try:
                for line in iter(proc.stdout.readline, b""):
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        logger.info("[teleop] %s", text)
            except Exception as exc:
                logger.warning("stdout reader error: %s", exc)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

    def _start_monitor(self):
        """Start the heartbeat monitor and crash watcher."""
        def _monitor():
            # Wait for IPC to come online
            time.sleep(1.0)
            self._init_ipc()

            # Watch for process exit
            while self._running:
                if self._proc is not None and self._proc.poll() is not None:
                    # Process exited
                    code = self._proc.returncode
                    logger.warning("Teleop worker exited with code %d", code)
                    self._running = False
                    if self._crash_callback:
                        self._crash_callback(f"Worker exited (code {code})")
                    break
                time.sleep(0.5)

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()
        self._monitor_thread = t

    def _init_ipc(self):
        """Initialize the IPC client to communicate with the worker."""
        try:
            from teleop.utils.ipc import IPC_Client
            self._ipc_client = IPC_Client(hb_fps=10.0)
            logger.info("IPC client connected to teleop worker")
        except Exception as exc:
            logger.warning("IPC client init failed: %s", exc)
            self._ipc_client = None

    # -- IPC commands ------------------------------------------------------

    def send_start(self) -> dict:
        """Send CMD_START — robot begins following XR motion."""
        if not self._ipc_client:
            return {"status": "error", "msg": "IPC not connected"}
        return self._ipc_client.send_data("CMD_START")

    def send_stop(self) -> dict:
        """Send CMD_STOP — graceful shutdown of the teleop worker."""
        if not self._ipc_client:
            return {"status": "error", "msg": "IPC not connected"}
        return self._ipc_client.send_data("CMD_STOP")

    def send_record_toggle(self) -> dict:
        """Send CMD_RECORD_TOGGLE — start/stop recording."""
        if not self._ipc_client:
            return {"status": "error", "msg": "IPC not connected"}
        return self._ipc_client.send_data("CMD_RECORD_TOGGLE")

    def get_heartbeat_state(self) -> dict:
        """Return the latest heartbeat state from the worker."""
        if not self._ipc_client:
            return {}
        try:
            return self._ipc_client.get_state()
        except Exception:
            return {}

    # -- shutdown ----------------------------------------------------------

    def shutdown(self) -> bool:
        """
        Safe shutdown: send CMD_STOP via IPC, then wait, then kill if needed.
        Returns True if the worker stopped gracefully.
        """
        with self._lock:
            if not self.is_running:
                return True

            logger.info("Shutting down teleop worker (safe stop)")
            # Try graceful IPC stop first
            if self._ipc_client:
                try:
                    self._ipc_client.send_data("CMD_STOP")
                except Exception:
                    pass

            # Wait up to 5 seconds for graceful exit
            if self._proc is not None:
                try:
                    self._proc.wait(timeout=5)
                    logger.info("Worker stopped gracefully")
                    self._running = False
                    return True
                except subprocess.TimeoutExpired:
                    logger.warning("Worker did not stop in 5s; terminating")
                    self._terminate()
                    return False
            return False

    def _terminate(self):
        """Force-terminate the worker process."""
        if self._proc is None:
            return
        try:
            if sys.platform == "win32":
                # On Windows, send CTRL_BREAK_EVENT to the process group
                self._proc.send_signal(signal.SIGTERM)
            else:
                self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._running = False

    def force_kill(self):
        """Immediately kill the worker (last resort)."""
        if self._proc is not None:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._running = False
