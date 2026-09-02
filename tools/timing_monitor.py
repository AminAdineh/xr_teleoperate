#!/usr/bin/env python3
"""
Control loop timing monitor for xr_teleoperate.

Measures actual control loop frequency on the current platform and
compares against the target frequency. Reports min/max/avg/jitter.

Usage:
    python tools/timing_monitor.py --frequency 30
    python tools/timing_monitor.py --frequency 100 --duration 60
"""
import time
import argparse
import statistics
from collections import deque


class TimingMonitor:
    """
    Lightweight timing monitor that records loop iteration times
    and computes frequency statistics.
    """

    def __init__(self, target_fps: float = 30.0, window_size: int = 1000):
        self.target_fps = target_fps
        self.target_interval = 1.0 / target_fps
        self.window_size = window_size
        self._timestamps = deque(maxlen=window_size)
        self._intervals = deque(maxlen=window_size)

    def tick(self):
        """Record a single loop iteration timestamp."""
        now = time.perf_counter()
        self._timestamps.append(now)
        if len(self._timestamps) >= 2:
            interval = now - self._timestamps[-2]
            self._intervals.append(interval)

    def get_stats(self) -> dict:
        """Compute timing statistics from recorded intervals."""
        if len(self._intervals) < 2:
            return {
                "target_fps": self.target_fps,
                "actual_fps": 0.0,
                "min_interval": 0.0,
                "max_interval": 0.0,
                "avg_interval": 0.0,
                "std_interval": 0.0,
                "jitter": 0.0,
                "samples": len(self._intervals),
            }

        intervals = list(self._intervals)
        fps_values = [1.0 / i for i in intervals if i > 0]

        return {
            "target_fps": self.target_fps,
            "actual_fps": statistics.mean(fps_values) if fps_values else 0.0,
            "min_fps": min(fps_values) if fps_values else 0.0,
            "max_fps": max(fps_values) if fps_values else 0.0,
            "min_interval": min(intervals),
            "max_interval": max(intervals),
            "avg_interval": statistics.mean(intervals),
            "std_interval": statistics.stdev(intervals) if len(intervals) > 1 else 0.0,
            "jitter": statistics.stdev(intervals) if len(intervals) > 1 else 0.0,
            "samples": len(intervals),
        }

    def print_stats(self):
        """Print timing statistics in a readable format."""
        stats = self.get_stats()
        print(f"\n--- Timing Statistics ({stats['samples']} samples) ---")
        print(f"  Target frequency:  {stats['target_fps']:.1f} Hz")
        print(f"  Actual frequency:  {stats['actual_fps']:.2f} Hz")
        print(f"  Min frequency:     {stats['min_fps']:.2f} Hz")
        print(f"  Max frequency:     {stats['max_fps']:.2f} Hz")
        print(f"  Avg interval:      {stats['avg_interval'] * 1000:.3f} ms")
        print(f"  Min interval:      {stats['min_interval'] * 1000:.3f} ms")
        print(f"  Max interval:      {stats['max_interval'] * 1000:.3f} ms")
        print(f"  Std interval:      {stats['std_interval'] * 1000:.3f} ms")
        print(f"  Jitter:            {stats['jitter'] * 1000:.3f} ms")

        # Assessment
        target = stats['target_fps']
        actual = stats['actual_fps']
        if actual >= target * 0.95:
            print(f"  Assessment:        PASS (within 5% of target)")
        elif actual >= target * 0.90:
            print(f"  Assessment:        WARN (within 10% of target)")
        else:
            print(f"  Assessment:        FAIL (below 90% of target)")
        print()


def run_monitor(target_fps: float, duration: float):
    """Run a timing monitor for the specified duration."""
    monitor = TimingMonitor(target_fps=target_fps)
    target_interval = 1.0 / target_fps

    print(f"Monitoring control loop at {target_fps} Hz for {duration} seconds...")
    print("Press Ctrl+C to stop early.\n")

    start = time.perf_counter()
    try:
        while time.perf_counter() - start < duration:
            loop_start = time.perf_counter()
            monitor.tick()
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("\nStopped by user.")

    monitor.print_stats()
    return monitor.get_stats()


def main():
    parser = argparse.ArgumentParser(description="Control loop timing monitor")
    parser.add_argument("--frequency", type=float, default=30.0,
                        help="Target control frequency in Hz (default: 30)")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="Monitoring duration in seconds (default: 10)")
    args = parser.parse_args()

    run_monitor(args.frequency, args.duration)


if __name__ == "__main__":
    main()
