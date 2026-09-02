"""
Cross-platform process/thread abstraction for multiprocessing.

On Linux, multiprocessing uses fork() by default, which allows bound methods
to be passed as Process targets (the child inherits the parent's memory).

On Windows, multiprocessing uses spawn(), which requires the target callable
and all arguments to be picklable. Bound methods of objects containing
non-picklable members (DDS channels, ZMQ sockets, Vuer instances) will fail.

This module provides:
  - spawn_worker(target, args, kwargs): Creates a Process on Linux, or a
    Thread on Windows, with the same interface.
  - The caller does not need to know which is used.

For robot-control code, threads are safe because:
  - DDS communication is I/O-bound (not CPU-bound)
  - The GIL does not significantly impact I/O-bound workloads
  - Shared memory (multiprocessing.Array/Value) works with both threads and processes
"""
import sys
import threading
import multiprocessing
import logging
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"


class WorkerHandle:
    """
    Unified handle for a worker (Process or Thread).

    Provides the same interface regardless of the underlying implementation:
      - start()
      - join(timeout)
      - terminate()
      - is_alive()
    """

    def __init__(self, target: Callable, args: tuple = (), kwargs: dict = None,
                 daemon: bool = True):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self._daemon = daemon
        self._worker = None
        self._is_process = False

        self._create_worker()

    def _create_worker(self):
        if IS_WINDOWS:
            # On Windows, use a Thread to avoid pickling issues with spawn().
            # Threads work correctly for I/O-bound DDS/ZMQ/WebRTC workloads.
            self._worker = threading.Thread(
                target=self._target,
                args=self._args,
                kwargs=self._kwargs,
                daemon=self._daemon,
            )
            self._is_process = False
        else:
            # On Linux, use a Process to preserve the original behavior (fork).
            self._worker = multiprocessing.Process(
                target=self._target,
                args=self._args,
                kwargs=self._kwargs,
            )
            self._worker.daemon = self._daemon
            self._is_process = True

    def start(self):
        """Start the worker."""
        self._worker.start()

    def join(self, timeout: Optional[float] = None):
        """Wait for the worker to finish."""
        self._worker.join(timeout=timeout)

    def terminate(self):
        """
        Terminate the worker.

        For Process: calls process.terminate()
        For Thread: sets a stop event (the thread must check it) or just returns
                    (daemon threads are killed when the main process exits)
        """
        if self._is_process and self._worker.is_alive():
            self._worker.terminate()
        # Threads cannot be forcibly terminated in Python.
        # Daemon threads will be cleaned up when the main process exits.

    def is_alive(self) -> bool:
        """Check if the worker is still running."""
        return self._worker.is_alive()

    @property
    def is_process(self) -> bool:
        """Return True if the underlying worker is a Process (not a Thread)."""
        return self._is_process


def spawn_worker(target: Callable, args: tuple = (), kwargs: dict = None,
                 daemon: bool = True) -> WorkerHandle:
    """
    Create and start a cross-platform worker (Process on Linux, Thread on Windows).

    Args:
        target: Callable to run in the worker
        args: Positional arguments for the target
        kwargs: Keyword arguments for the target
        daemon: Whether the worker is a daemon

    Returns:
        WorkerHandle instance (already started)
    """
    handle = WorkerHandle(target, args, kwargs, daemon)
    handle.start()
    return handle
