"""
ExoArmur ADMO V2 Federation Clock Interface
Provides deterministic time abstraction for testing
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional


class Clock(ABC):
    """Clock interface for deterministic time handling"""
    
    @abstractmethod
    def now(self) -> datetime:
        """Get current time in UTC"""
        pass
    
    @abstractmethod
    def advance(self, delta: timedelta) -> None:
        """Advance time by delta (for testing)"""
        pass


class SystemClock(Clock):
    """System clock using actual time"""
    
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
