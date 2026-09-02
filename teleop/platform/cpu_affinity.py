"""
Cross-platform CPU affinity management.

On Linux: uses os.sched_setaffinity() or psutil.Process().cpu_affinity()
On Windows: uses psutil.Process().cpu_affinity() (requires psutil)

If psutil is not available or affinity cannot be set, the function
returns gracefully without error.
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def set_cpu_affinity(cores: list) -> bool:
    """
    Set CPU affinity for the current process to the specified core indices.

    Args:
        cores: List of CPU core indices (e.g. [0, 1, 2, 3])

    Returns:
        True if affinity was set successfully, False otherwise.
    """
    if not cores:
        return False

    try:
        if HAS_PSUTIL:
            p = psutil.Process()
            p.cpu_affinity(cores)
            logger.info(f"CPU affinity set to cores: {cores}")
            return True
        elif sys.platform != "win32":
            # Linux fallback without psutil
            os.sched_setaffinity(0, set(cores))
            logger.info(f"CPU affinity set to cores: {cores}")
            return True
        else:
            logger.warning("Cannot set CPU affinity on Windows without psutil.")
            return False
    except Exception as e:
        logger.warning(f"Failed to set CPU affinity: {e}")
        return False


def get_cpu_affinity() -> list:
    """
    Get the current CPU affinity for this process.

    Returns:
        List of CPU core indices, or empty list if unavailable.
    """
    try:
        if HAS_PSUTIL:
            return psutil.Process().cpu_affinity()
        elif sys.platform != "win32":
            return list(os.sched_getaffinity(0))
        else:
            return []
    except Exception:
        return []


def get_cpu_count() -> int:
    """Return the number of available CPU cores."""
    if HAS_PSUTIL:
        return psutil.cpu_count(logical=True)
    return os.cpu_count() or 1
