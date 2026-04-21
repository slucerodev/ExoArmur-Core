"""
Deterministic Clock for Critical Execution Paths

Provides a deterministic clock abstraction that eliminates wall-clock time
nondeterminism from critical execution paths. This is essential for
replay, audit verification, and any scenario where identical inputs
must produce identical outputs.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional
import threading
from contextlib import contextmanager


class Clock(ABC):
    """Abstract clock interface for time operations."""

    @abstractmethod
    def now(self) -> datetime:
        """Get the current time."""
        pass

    @abstractmethod
    def advance(self, delta: timedelta) -> None:
        """Advance the clock by a specified delta."""
        pass


class DeterministicClock(Clock):
    """
    Deterministic clock that does not use wall-clock time.

    This clock uses a fixed starting timestamp and can be advanced
    programmatically. It is designed for use in critical execution
    paths where determinism is required.
    """

    def __init__(
        self,
        initial_time: Optional[datetime] = None,
        auto_advance: bool = False
    ):
        """
        Initialize deterministic clock.

        Args:
            initial_time: Starting timestamp. Defaults to epoch (1970-01-01).
            auto_advance: If True, each call to now() advances time by 1 second.
                         This simulates time progression without using wall-clock.
        """
        self._current_time = initial_time or datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self._auto_advance = auto_advance
        self._lock = threading.Lock()

    def now(self) -> datetime:
        """Get the current deterministic time."""
        with self._lock:
            current = self._current_time
            if self._auto_advance:
                self._current_time += timedelta(seconds=1)
            return current

    def advance(self, delta: timedelta) -> None:
        """Advance the clock by a specified delta."""
        with self._lock:
            self._current_time += delta

    def set_time(self, new_time: datetime) -> None:
        """Set the clock to a specific time."""
        with self._lock:
            self._current_time = new_time

    def reset(self) -> None:
        """Reset clock to initial epoch time."""
        with self._lock:
            self._current_time = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class WallClock(Clock):
    """
    Wall-clock implementation that uses system time.

    This should NOT be used in critical execution paths. It is provided
    for non-critical operations like logging, metrics, and UI display.
    """

    def now(self) -> datetime:
        """Get current wall-clock time."""
        return datetime.now(timezone.utc)

    def advance(self, delta: timedelta) -> None:
        """
        Wall-clock cannot be advanced programmatically.

        Raises:
            NotImplementedError: Wall-clock cannot be advanced
        """
        raise NotImplementedError("Wall-clock cannot be advanced programmatically")


# Global clock instance - can be replaced with DeterministicClock for testing
_default_clock: Clock = WallClock()


def get_clock() -> Clock:
    """Get the global clock instance."""
    return _default_clock


def set_clock(clock: Clock) -> None:
    """
    Set the global clock instance.

    This is primarily used for testing to replace the wall-clock
    with a deterministic clock.

    Args:
        clock: Clock instance to use as global clock
    """
    global _default_clock
    _default_clock = clock


def reset_to_wall_clock() -> None:
    """Reset the global clock to wall-clock (default for production)."""
    set_clock(WallClock())


@contextmanager
def deterministic_clock_context(initial_time: Optional[datetime] = None):
    """
    Context manager for temporarily using a deterministic clock.

    Usage:
        with deterministic_clock_context():
            # Code here uses deterministic clock
            result = critical_operation()

    Args:
        initial_time: Starting timestamp for deterministic clock
    """
    original_clock = get_clock()
    det_clock = DeterministicClock(initial_time=initial_time)
    set_clock(det_clock)

    try:
        yield det_clock
    finally:
        set_clock(original_clock)
