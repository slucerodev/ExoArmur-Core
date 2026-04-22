"""
ExoArmur ADMO V2 Federation Clock Interface
Provides deterministic time abstraction for testing
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional
import os

# Import deterministic clock from stability module for enforcement
from exoarmur.stability.deterministic_clock import (
    DeterministicClock as StabilityDeterministicClock,
    WallClock as StabilityWallClock
)


class Clock(ABC):
    """Clock interface for deterministic time handling"""

    @abstractmethod
    def now(self) -> datetime:
        """Get current time in UTC"""

    @abstractmethod
    def advance(self, delta: timedelta) -> None:
        """Advance time by delta (for testing)"""


class SystemClock(Clock):
    """System clock using actual time - NON-CRITICAL PATHS ONLY"""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def advance(self, delta: timedelta) -> None:
        """System clock cannot be advanced"""
        raise NotImplementedError("System clock cannot be advanced")


class FixedClock(Clock):
    """Fixed clock for deterministic testing"""

    def __init__(self, start_time: Optional[datetime] = None):
        """Initialize with start time (defaults to 2023-01-01 12:00:00 UTC)"""
        if start_time is None:
            start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def advance(self, delta: timedelta) -> None:
        """Advance the fixed clock time"""
        self._current_time += delta

    def set_time(self, new_time: datetime) -> None:
        """Set the clock to a specific time"""
        self._current_time = new_time.replace(tzinfo=timezone.utc)


# Default clock for federation - use deterministic clock by default for critical paths
# Set EXOARMUR_FEDERATION_DETERMINISTIC_CLOCK=false to use wall-clock (for non-critical only)
if os.getenv("EXOARMUR_FEDERATION_DETERMINISTIC_CLOCK", "true").lower() == "true":
    _default_clock = StabilityDeterministicClock()
else:
    _default_clock = StabilityWallClock()


def get_federation_clock() -> Clock:
    """Get the default federation clock instance"""
    return _default_clock


def set_federation_clock(clock: Clock) -> None:
    """Set the federation clock instance (for testing)"""
    global _default_clock
    _default_clock = clock
