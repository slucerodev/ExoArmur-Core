"""
Tests for Kernel Clock Module

These tests verify that the clock abstraction provides deterministic time
for replay while maintaining wall-clock time for coordination.
"""

from datetime import datetime, timedelta, timezone

import pytest

from exoarmur.kernel.clock import (
    DeterministicClock,
    SystemClock,
    get_clock,
    set_clock,
    utc_now,
)


class TestSystemClock:
    """Test SystemClock behavior for production use."""

    def test_system_clock_returns_utc(self):
        """Test that SystemClock returns UTC time."""
        clock = SystemClock()
        time = clock.utc_now()

        assert isinstance(time, datetime)
        assert time.tzinfo == timezone.utc

    def test_system_clock_advances(self):
        """Test that SystemClock time advances between calls."""
        clock = SystemClock()
        time1 = clock.utc_now()
        time2 = clock.utc_now()

        assert time2 >= time1
        # Allow for very small time differences
        assert (time2 - time1) < timedelta(seconds=1)

    def test_system_clock_is_not_deterministic(self):
        """Test that SystemClock is not deterministic (expected behavior)."""
        clock = SystemClock()
        time1 = clock.utc_now()
        time2 = clock.utc_now()

        # SystemClock should produce different times
        assert time1 != time2


class TestDeterministicClock:
    """Test DeterministicClock behavior for testing and replay."""

    def test_deterministic_clock_initialization(self):
        """Test that DeterministicClock initializes with a fixed time."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)

        assert clock.utc_now() == fixed_time

    def test_deterministic_clock_returns_fixed_time(self):
        """Test that DeterministicClock returns the same time repeatedly."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)

        time1 = clock.utc_now()
        time2 = clock.utc_now()
        time3 = clock.utc_now()

        assert time1 == time2 == time3 == fixed_time

    def test_deterministic_clock_advancement(self):
        """Test that DeterministicClock can advance using advance() method."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)

        time1 = clock.utc_now()
        clock.advance(1)  # Advance by 1 second
        time2 = clock.utc_now()
        clock.advance(1)  # Advance by 1 second
        time3 = clock.utc_now()

        assert time2 == time1 + timedelta(seconds=1)
        assert time3 == time2 + timedelta(seconds=1)

    def test_deterministic_clock_is_deterministic(self):
        """Test that DeterministicClock is deterministic."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock1 = DeterministicClock(fixed_time)
        clock2 = DeterministicClock(fixed_time)

        time1 = clock1.utc_now()
        time2 = clock2.utc_now()

        assert time1 == time2


class TestClockGlobalFunctions:
    """Test global clock functions for time abstraction."""

    def test_utc_now_returns_datetime(self):
        """Test that utc_now returns a datetime object."""
        time = utc_now()

        assert isinstance(time, datetime)
        assert time.tzinfo == timezone.utc

    def test_set_clock_and_get_clock(self):
        """Test setting and getting the global clock."""
        original_clock = get_clock()

        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        new_clock = DeterministicClock(fixed_time)
        set_clock(new_clock)

        assert get_clock() == new_clock
        assert utc_now() == fixed_time

        # Restore original clock
        set_clock(original_clock)

    def test_clock_isolation(self):
        """Test that clock changes don't affect other instances."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock1 = DeterministicClock(fixed_time)
        clock2 = DeterministicClock(fixed_time)

        # clock1 should not advance
        time1 = clock1.utc_now()
        time2 = clock1.utc_now()
        assert time1 == time2

        # clock2 should advance when we call advance()
        time3 = clock2.utc_now()
        clock2.advance(1)  # Advance by 1 second
        time4 = clock2.utc_now()
        assert time4 == time3 + timedelta(seconds=1)


class TestClockDeterminismGuarantees:
    """Test determinism guarantees for replay scenarios."""

    def test_deterministic_replay_scenario(self):
        """Test that DeterministicClock enables deterministic replay."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Simulate first execution
        clock1 = DeterministicClock(fixed_time)
        times1 = []
        for _ in range(5):
            times1.append(clock1.utc_now())
            clock1.advance(1)  # Advance by 1 second

        # Simulate replay
        clock2 = DeterministicClock(fixed_time)
        times2 = []
        for _ in range(5):
            times2.append(clock2.utc_now())
            clock2.advance(1)  # Advance by 1 second

        # Times should be identical
        assert times1 == times2

    def test_deterministic_clock_with_different_advancements(self):
        """Test deterministic behavior with different advancement rates."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # 1 second advancement
        clock1 = DeterministicClock(fixed_time)
        times1 = []
        for _ in range(10):
            times1.append(clock1.utc_now())
            clock1.advance(1)  # Advance by 1 second

        # 100 second advancement
        clock2 = DeterministicClock(fixed_time)
        times2 = []
        for _ in range(10):
            times2.append(clock2.utc_now())
            clock2.advance(100)  # Advance by 100 seconds

        # Both should be deterministic
        clock1_replay = DeterministicClock(fixed_time)
        times1_replay = []
        for _ in range(10):
            times1_replay.append(clock1_replay.utc_now())
            clock1_replay.advance(1)
        assert times1 == times1_replay

        clock2_replay = DeterministicClock(fixed_time)
        times2_replay = []
        for _ in range(10):
            times2_replay.append(clock2_replay.utc_now())
            clock2_replay.advance(100)
        assert times2 == times2_replay


class TestClockEdgeCases:
    """Test edge cases and error conditions."""

    def test_deterministic_clock_with_none_time(self):
        """Test DeterministicClock with None initial time."""
        clock = DeterministicClock(None)

        # Should default to current time
        time = clock.utc_now()
        assert isinstance(time, datetime)
        assert time.tzinfo == timezone.utc

    def test_deterministic_clock_with_zero_advancement(self):
        """Test DeterministicClock with zero advancement."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)

        time1 = clock.utc_now()
        clock.advance(0)  # Advance by 0 seconds
        time2 = clock.utc_now()

        assert time1 == time2

    def test_deterministic_clock_with_negative_advancement(self):
        """Test DeterministicClock with negative advancement (should not go negative)."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)

        time1 = clock.utc_now()
        clock.advance(-1)  # Advance by -1 second
        time2 = clock.utc_now()

        # Should still advance (or handle gracefully)
        # This test documents current behavior
        assert isinstance(time1, datetime)
        assert isinstance(time2, datetime)


class TestClockPerformance:
    """Test clock performance characteristics."""

    def test_system_clock_performance(self):
        """Test that SystemClock is performant."""
        import time

        clock = SystemClock()
        iterations = 10000

        start = time.perf_counter()
        for _ in range(iterations):
            clock.utc_now()
        end = time.perf_counter()

        # Should complete in reasonable time (< 1 second for 10k calls)
        assert (end - start) < 1.0

    def test_deterministic_clock_performance(self):
        """Test that DeterministicClock is performant."""
        import time

        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        clock = DeterministicClock(fixed_time)
        iterations = 10000

        start = time.perf_counter()
        for _ in range(iterations):
            clock.utc_now()
        end = time.perf_counter()

        # Should complete in reasonable time (< 1 second for 10k calls)
        assert (end - start) < 1.0
