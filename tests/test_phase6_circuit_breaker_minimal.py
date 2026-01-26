#!/usr/bin/env python3
"""
Phase 6 Circuit Breaker Tests - Minimal
Gate 7 Failure Survival & Crash Consistency
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from reliability.circuit_breaker import (
    CircuitState,
    CircuitBreakerError,
    CircuitBreakerConfig,
    CircuitBreaker,
    get_circuit_breaker_manager
)


async def test_circuit_breaker_basic():
    """Test basic circuit breaker functionality"""
    print("Testing circuit breaker basic functionality...")
    
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.5)
    breaker = CircuitBreaker("test-service", config)
    
    # Should start in CLOSED state
    assert breaker.is_closed == True, "Should start in CLOSED state"
    
    # Successful operation should work
    result = await breaker.call(lambda: "success")
    assert result == "success", "Should return result for successful operation"
    
    # Simulate failures to open circuit
    for i in range(2):
        try:
            await breaker.call(lambda: 1/0)  # Will raise ZeroDivisionError
        except Exception:
            pass  # Expected
    
    # Should be OPEN now
    assert breaker.is_open == True, "Should be OPEN after threshold failures"
    
    print("✓ Circuit breaker basic functionality works correctly")


async def test_circuit_breaker_manager_basic():
    """Test circuit breaker manager basic operations"""
    print("Testing circuit breaker manager...")
    
    manager = get_circuit_breaker_manager()
    
    # Create breaker for service
    breaker = manager.get_breaker("manager-test-service")
    
    assert breaker.service_name == "manager-test-service", "Should create breaker for service"
    
    # Test calling with breaker protection
    result = await manager.call_with_breaker("manager-test-service", lambda: "protected-result")
    assert result == "protected-result", "Should return result through breaker"
    
    print("✓ Circuit breaker manager works correctly")


async def main():
    """Run minimal circuit breaker tests"""
    print("=" * 60)
    print("PHASE 6: CIRCUIT BREAKER TESTS")
    print("Gate 7: Failure Survival & Crash Consistency")
    print("=" * 60)
    
    tests = [
        test_circuit_breaker_basic,
        test_circuit_breaker_manager_basic
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
