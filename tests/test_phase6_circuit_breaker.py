#!/usr/bin/env python3
"""
Phase 6 Circuit Breaker Tests
Gate 7 Failure Survival & Crash Consistency
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from exoarmur.reliability import (
    CircuitState,
    CircuitBreakerError,
    CircuitBreakerConfig,
    CircuitStateTransition,
    CircuitBreaker,
    CircuitBreakerManager,
    get_circuit_breaker_manager,
    with_circuit_breaker
)


class MockAuditEmitter:
    """Mock audit emitter for testing"""
    
    def __init__(self):
        self.events = []
    
    async def emit(self, audit_data):
        self.events.append(audit_data)


async def test_circuit_breaker_config():
    """Test circuit breaker configuration"""
    print("Testing circuit breaker configuration...")
    
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=3,
        failure_window_seconds=60.0,
        success_window_seconds=60.0,
        monitor_interval=10.0,
        health_check_timeout=5.0,
        state_ttl=3600.0
    )
    
    assert config.failure_threshold == 5, "Failure threshold should be 5"
    assert config.recovery_timeout == 60.0, "Recovery timeout should be 60s"
    assert config.success_threshold == 3, "Success threshold should be 3"
    assert config.failure_window_seconds == 60.0, "Failure window should be 60s"
    assert config.success_window_seconds == 60.0, "Success window should be 60s"
    
    print("✓ Circuit breaker configuration works correctly")


async def test_circuit_breaker_states():
    """Test circuit breaker state transitions"""
    print("Testing circuit breaker states...")
    
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
    breaker = CircuitBreaker("test-service", config)
    
    # Should start in CLOSED state
    assert breaker.is_closed == True, "Should start in CLOSED state"
    assert breaker.is_open == False, "Should not be OPEN"
    assert breaker.is_half_open == False, "Should not be HALF_OPEN"
    
    # Simulate failures to open circuit
    for i in range(3):
        try:
            await breaker.call(lambda: 1/0)  # Will raise ZeroDivisionError
        except Exception:
            pass  # Expected
    
    # Should be OPEN now
    assert breaker.is_open == True, "Should be OPEN after threshold failures"
    assert breaker.is_closed == False, "Should not be CLOSED"
    assert breaker.is_half_open == False, "Should not be HALF_OPEN"
    
    print("✓ Circuit breaker states work correctly")


async def test_circuit_breaker_success():
    """Test circuit breaker with successful operations"""
    print("Testing circuit breaker success case...")
    
    config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=1.0)
    breaker = CircuitBreaker("test-service", config)
    
    # Successful operation should work
    result = await breaker.call(lambda: "success")
    assert result == "success", "Should return result for successful operation"
    
    # Should remain CLOSED
    assert breaker.is_closed == True, "Should remain CLOSED after success"
    
    print("✓ Circuit breaker success case works correctly")


async def test_circuit_breaker_open():
    """Test circuit breaker opening behavior"""
    print("Testing circuit breaker opening...")
    
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
    breaker = CircuitBreaker("test-service", config)
    
    # Simulate failures to open circuit
    for i in range(3):
        try:
            await breaker.call(lambda: 1/0)  # Will raise ZeroDivisionError
        except Exception:
            pass  # Expected
    
    # Should be OPEN now
    assert breaker.is_open == True, "Should be OPEN after threshold failures"
    
    # Should raise CircuitBreakerError when OPEN
    try:
        await breaker.call(lambda: "should-not-execute")
        assert False, "Should have raised CircuitBreakerError"
    except CircuitBreakerError as e:
        assert e.service_name == "test-service", "Should preserve service name"
        assert e.state == CircuitState.OPEN, "Should preserve state"
        assert e.failure_count == 3, "Should preserve failure count"
    
    print("✓ Circuit breaker opening works correctly")


async def test_circuit_breaker_half_open():
    """Test circuit breaker half-open recovery"""
    print("Testing circuit breaker half-open recovery...")
    
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.5, success_threshold=2)
    breaker = CircuitBreaker("test-service", config)
    
    # Open the circuit
    for i in range(2):
        try:
            await breaker.call(lambda: 1/0)
        except Exception:
            pass
    
    assert breaker.is_open == True, "Should be OPEN"
    
    # Wait for recovery timeout
    await asyncio.sleep(0.6)
    
    # Next call should trigger HALF_OPEN and succeed
    result = await breaker.call(lambda: "recovery-success")
    assert result == "recovery-success", "Should succeed in HALF_OPEN"
    
    # Should be HALF_OPEN now
    assert breaker.is_half_open == True, "Should be HALF_OPEN after recovery timeout"
    
    # Another success should close circuit
    result = await breaker.call(lambda: "recovery-success-2")
    assert result == "recovery-success-2", "Should succeed again"
    
    # Should be CLOSED now
    assert breaker.is_closed == True, "Should be CLOSED after sufficient successes"
    
    print("✓ Circuit breaker half-open recovery works correctly")


async def test_circuit_breaker_health_check():
    """Test circuit breaker health check functionality"""
    print("Testing circuit breaker health check...")
    
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
    breaker = CircuitBreaker("test-service", config)
    
    # Set up health check function
    health_status = True
    
    def health_check():
        return health_status
    
    breaker.set_health_check(health_check)
    
    # Health check should pass when healthy
    result = await breaker.health_check()
    assert result == True, "Health check should pass when healthy"
    
    # Health check should fail when unhealthy
    health_status = False
    result = await breaker.health_check()
    assert result == False, "Health check should fail when unhealthy"
    
    print("✓ Circuit breaker health check works correctly")


async def test_circuit_breaker_manager():
    """Test circuit breaker manager operations"""
    print("Testing circuit breaker manager...")
    
    manager = CircuitBreakerManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Create breakers for different services
    breaker1 = manager.get_breaker("service-1")
    breaker2 = manager.get_breaker("service-2")
    
    assert breaker1.service_name == "service-1", "Should create breaker for service-1"
    assert breaker2.service_name == "service-2", "Should create breaker for service-2"
    assert breaker1 is not breaker2, "Should create separate instances"
    
    # Test calling with breaker protection
    result = await manager.call_with_breaker("service-1", lambda: "protected-result")
    assert result == "protected-result", "Should return result through breaker"
    
    # Test statistics
    stats = manager.get_all_stats()
    assert "service-1" in stats, "Should include stats for service-1"
    assert "service-2" in stats, "Should include stats for service-2"
    
    service1_stats = stats["service-1"]
    assert service1_stats["service_name"] == "service-1", "Should preserve service name"
    assert service1_stats["state"] == "CLOSED", "Should show current state"
    
    print("✓ Circuit breaker manager works correctly")


async def test_circuit_breaker_decorator():
    """Test circuit breaker decorator"""
    print("Testing circuit breaker decorator...")
    
    # Test successful decorated function
    @with_circuit_breaker("decorated-service")
    async def decorated_function():
        return "decorated-success"
    
    result = await decorated_function()
    assert result == "decorated-success", "Decorated function should succeed"
    
    # Test failing decorated function
    call_count = 0
    
    @with_circuit_breaker("failing-service", CircuitBreakerConfig(failure_threshold=2))
    async def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ValueError("Intentional failure")
        return "eventual-success"
    
    # First two calls should fail
    try:
        await failing_function()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    try:
        await failing_function()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    # Third call should succeed
    result = await failing_function()
    assert result == "eventual-success", "Should succeed after failures"
    
    print("✓ Circuit breaker decorator works correctly")


async def test_circuit_breaker_statistics():
    """Test circuit breaker statistics"""
    print("Testing circuit breaker statistics...")
    
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
    breaker = CircuitBreaker("stats-service", config)
    
    # Generate some activity
    for i in range(5):
        try:
            await breaker.call(lambda: f"success-{i}")
        except Exception:
            pass  # Ignore failures
    
    # Get statistics
    stats = breaker.get_stats()
    
    assert stats["service_name"] == "stats-service", "Should include service name"
    assert "state" in stats, "Should include current state"
    assert "failure_count" in stats, "Should include failure count"
    assert "success_count" in stats, "Should include success count"
    assert "recent_failures" in stats, "Should include recent failures"
    assert "recent_successes" in stats, "Should include recent successes"
    assert "state_history_count" in stats, "Should include state history count"
    
    print("✓ Circuit breaker statistics work correctly")


async def test_circuit_breaker_reset():
    """Test circuit breaker reset functionality"""
    print("Testing circuit breaker reset...")
    
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
    breaker = CircuitBreaker("reset-service", config)
    
    # Open the circuit
    for i in range(2):
        try:
            await breaker.call(lambda: 1/0)
        except Exception:
            pass
    
    assert breaker.is_open == True, "Should be OPEN"
    
    # Reset the circuit
    await breaker.reset()
    
    assert breaker.is_closed == True, "Should be CLOSED after reset"
    
    # Check counts via get_stats
    stats = breaker.get_stats()
    assert stats["failure_count"] == 0, "Failure count should be reset"
    assert stats["success_count"] == 0, "Success count should be reset"
    
    print("✓ Circuit breaker reset works correctly")


async def main():
    """Run all circuit breaker tests"""
    print("=" * 60)
    print("PHASE 6: CIRCUIT BREAKER TESTS")
    print("Gate 7: Failure Survival & Crash Consistency")
    print("=" * 60)
    
    tests = [
        test_circuit_breaker_config,
        test_circuit_breaker_states,
        test_circuit_breaker_success,
        test_circuit_breaker_open,
        test_circuit_breaker_half_open,
        test_circuit_breaker_health_check,
        test_circuit_breaker_manager,
        test_circuit_breaker_decorator,
        test_circuit_breaker_statistics,
        test_circuit_breaker_reset
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"CIRCUIT BREAKER TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL CIRCUIT BREAKER TESTS PASSED")
        return True
    else:
        print("❌ SOME CIRCUIT BREAKER TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
