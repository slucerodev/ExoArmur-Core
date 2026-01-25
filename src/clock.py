"""
Clock interface for deterministic time handling
"""

from datetime import datetime, timezone
from typing import Protocol, Optional
from abc import ABC, abstractmethod


class Clock(Protocol):
    """Clock interface for deterministic time handling"""
    
    def now(self) -> datetime:
        """Get current time"""
        ...
    
    def utc_now(self) -> datetime:
        """Get current UTC time"""
        ...


class SystemClock:
    """System clock implementation"""
    
    def now(self) -> datetime:
        """Get current time"""
        return datetime.now()
    
    def utc_now(self) -> datetime:
        """Get current UTC time"""
        return datetime.now(timezone.utc)


class DeterministicClock:
    """Deterministic clock for testing and replay"""
    
    def __init__(self, fixed_time: Optional[datetime] = None):
        if fixed_time is None:
            fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self._fixed_time = fixed_time
        self._current_time = fixed_time
    
    def now(self) -> datetime:
        """Get deterministic current time"""
        return self._current_time
    
    def utc_now(self) -> datetime:
        """Get deterministic current UTC time"""
        return self._current_time
    
    def advance(self, seconds: int) -> None:
        """Advance time by specified seconds"""
        from datetime import timedelta
        self._current_time += timedelta(seconds=seconds)
    
    def set_time(self, new_time: datetime) -> None:
        """Set the current time"""
        self._current_time = new_time


# Global clock instance (can be injected for testing)
_default_clock = SystemClock()


def get_clock() -> Clock:
    """Get the global clock instance"""
    return _default_clock


def set_clock(clock: Clock) -> None:
    """Set the global clock instance"""
    global _default_clock
    _default_clock = clock


def utc_now() -> datetime:
    """Get current UTC time using global clock"""
    return get_clock().utc_now()
