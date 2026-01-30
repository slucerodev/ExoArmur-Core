#!/usr/bin/env python3
"""
Phase 6 Timeout Enforcement Tests
Gate 7 Failure Survival & Crash Consistency
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from exoarmur.reliability import (
    TimeoutCategory,
    TimeoutConfig,
    TimeoutError,
    TimeoutManager,
    get_timeout_manager,
    with_timeout
)


class MockAuditEmitter:
    """Mock audit emitter for testing"""
    
    def __init__(self):
        self.events = []
    
    async def emit(self, audit_data):
        self.events.append(audit_data)


async def test_timeout_config():
    """Test timeout configuration"""
    print("Testing timeout configuration...")
    
    config = TimeoutConfig()
    
    # Test default values
    assert config.nats_connect == 10.0, "NATS connect timeout should be 10s"
    assert config.kv_get == 5.0, "KV get timeout should be 5s"
    assert config.execution_intent == 30.0, "Execution intent timeout should be 30s"
    assert config.default_timeout == 30.0, "Default timeout should be 30s"
    
    print("✓ Timeout configuration works correctly")


async def test_timeout_manager():
    """Test timeout manager operations"""
    print("Testing timeout manager...")
    
    manager = TimeoutManager()
    
    # Test timeout retrieval by category
    nats_timeout = manager.get_timeout(TimeoutCategory.NATS_CONNECT)
    assert nats_timeout == 10.0, "NATS connect timeout should be 10s"
    
    kv_timeout = manager.get_timeout(TimeoutCategory.KV_GET)
    assert kv_timeout == 5.0, "KV get timeout should be 5s"
    
    # Test timeout retrieval by string
    string_timeout = manager.get_timeout("TIMEOUT_NATS_CONNECT")
    assert string_timeout == 10.0, "String timeout should work"
    
    # Test unknown category (should return default)
    unknown_timeout = manager.get_timeout("TIMEOUT_UNKNOWN")
    assert unknown_timeout == 30.0, "Unknown category should return default"
    
    print("✓ Timeout manager works correctly")


async def test_timeout_enforcement():
    """Test timeout enforcement with successful operations"""
    print("Testing timeout enforcement (success case)...")
    
    manager = TimeoutManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test successful operation within timeout
    async def quick_operation():
        await asyncio.sleep(0.1)  # Fast operation
        return "success"
    
    result = await manager.execute_with_timeout(
        category=TimeoutCategory.NATS_PUBLISH,
        operation="Quick operation test",
        coro=quick_operation(),
        tenant_id="test-tenant",
        correlation_id="test-corr",
        trace_id="test-trace"
    )
    
    assert result == "success", "Operation should succeed"
    assert len(mock_emitter.events) == 0, "No audit events for successful operations"
    
    print("✓ Timeout enforcement works correctly for successful operations")


async def test_timeout_failure():
    """Test timeout enforcement with failing operations"""
    print("Testing timeout enforcement (timeout case)...")
    
    manager = TimeoutManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test operation that times out
    async def slow_operation():
        await asyncio.sleep(2.0)  # Slower than timeout
        return "success"
    
    try:
        await manager.execute_with_timeout(
            category=TimeoutCategory.NATS_PUBLISH,
            operation="Slow operation test",
            coro=slow_operation(),
            timeout=0.5,  # Override to 0.5s timeout
            tenant_id="test-tenant",
            correlation_id="test-corr",
            trace_id="test-trace"
        )
        assert False, "Should have raised TimeoutError"
    except TimeoutError as e:
        assert e.category == TimeoutCategory.NATS_PUBLISH, "Should preserve timeout category"
        assert e.timeout_seconds == 0.5, "Should preserve timeout duration"
        assert "Slow operation test" in str(e), "Should include operation name"
    
    # Verify audit event was emitted
    assert len(mock_emitter.events) == 1, "Should emit audit event for timeout"
    
    audit_event = mock_emitter.events[0]
    assert audit_event["event_type"] == "timeout_occurred", "Should be timeout event"
    assert audit_event["timeout_category"] == "TIMEOUT_NATS_PUBLISH", "Should preserve category"
    assert audit_event["operation"] == "Slow operation test", "Should preserve operation"
    assert audit_event["timeout_seconds"] == 0.5, "Should preserve timeout"
    assert audit_event["tenant_id"] == "test-tenant", "Should preserve tenant context"
    
    print("✓ Timeout enforcement works correctly for timeout failures")


async def test_timeout_decorator():
    """Test timeout decorator functionality"""
    print("Testing timeout decorator...")
    
    manager = get_timeout_manager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test successful decorated function
    @with_timeout(
        category=TimeoutCategory.KV_GET,
        operation="Decorated function test",
        timeout=1.0
    )
    async def decorated_function():
        await asyncio.sleep(0.1)
        return "decorated_success"
    
    result = await decorated_function()
    assert result == "decorated_success", "Decorated function should succeed"
    
    # Test timeout in decorated function
    @with_timeout(
        category=TimeoutCategory.KV_PUT,
        operation="Decorated timeout test",
        timeout=0.5
    )
    async def slow_decorated_function():
        await asyncio.sleep(1.0)  # Slower than timeout
        return "should_not_reach"
    
    try:
        await slow_decorated_function()
        assert False, "Should have raised TimeoutError"
    except TimeoutError as e:
        assert e.category == TimeoutCategory.KV_PUT, "Should preserve category"
        assert "Decorated timeout test" in str(e), "Should preserve operation name"
    
    # Verify audit event was emitted
    assert len(mock_emitter.events) == 1, "Should emit audit event for timeout"
    assert mock_emitter.events[0]["timeout_category"] == "TIMEOUT_KV_PUT", "Should preserve category"
    
    print("✓ Timeout decorator works correctly")


async def test_convenience_functions():
    """Test convenience timeout functions"""
    print("Testing convenience timeout functions...")
    
    manager = TimeoutManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test NATS timeout convenience
    from reliability import execute_with_nats_timeout
    
    async def nats_operation():
        await asyncio.sleep(0.1)
        return "nats_success"
    
    result = await execute_with_nats_timeout("NATS test", nats_operation())
    assert result == "nats_success", "NATS convenience function should work"
    
    # Test KV timeout convenience
    from reliability import execute_with_kv_timeout
    
    async def kv_operation():
        await asyncio.sleep(0.1)
        return "kv_success"
    
    result = await execute_with_kv_timeout("KV test", kv_operation())
    assert result == "kv_success", "KV convenience function should work"
    
    # Test execution timeout convenience
    from reliability import execute_with_execution_timeout
    
    async def execution_operation():
        await asyncio.sleep(0.1)
        return "execution_success"
    
    result = await execute_with_execution_timeout("Execution test", execution_operation())
    assert result == "execution_success", "Execution convenience function should work"
    
    print("✓ Convenience timeout functions work correctly")


async def test_timeout_audit_classification():
    """Test deterministic timeout audit classification"""
    print("Testing timeout audit classification...")
    
    manager = TimeoutManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test different timeout categories produce different audit codes
    categories_to_test = [
        (TimeoutCategory.NATS_CONNECT, "NATS connection"),
        (TimeoutCategory.KV_GET, "KV get operation"),
        (TimeoutCategory.EXECUTION_INTENT, "Intent execution"),
        (TimeoutCategory.APPROVAL_CHECK, "Approval verification")
    ]
    
    for category, operation in categories_to_test:
        mock_emitter.events = []  # Reset for each test
        
        async def timeout_operation():
            await asyncio.sleep(1.0)  # Will timeout
            return "should_not_reach"
        
        try:
            await manager.execute_with_timeout(
                category=category,
                operation=operation,
                coro=timeout_operation(),
                timeout=0.1  # Force timeout
            )
            assert False, f"Should have raised TimeoutError for {category}"
        except TimeoutError:
            pass  # Expected
        
        # Verify audit event classification
        assert len(mock_emitter.events) == 1, f"Should emit audit event for {category}"
        
        audit_event = mock_emitter.events[0]
        assert audit_event["timeout_category"] == category.value, f"Should preserve {category}"
        assert audit_event["operation"] == operation, f"Should preserve operation for {category}"
        assert "timestamp" in audit_event, f"Should include timestamp for {category}"
    
    print("✓ Timeout audit classification works correctly")


async def main():
    """Run all timeout enforcement tests"""
    print("=" * 60)
    print("PHASE 6: TIMEOUT ENFORCEMENT TESTS")
    print("Gate 7: Failure Survival & Crash Consistency")
    print("=" * 60)
    
    tests = [
        test_timeout_config,
        test_timeout_manager,
        test_timeout_enforcement,
        test_timeout_failure,
        test_timeout_decorator,
        test_convenience_functions,
        test_timeout_audit_classification
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
    print(f"TIMEOUT ENFORCEMENT TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL TIMEOUT ENFORCEMENT TESTS PASSED")
        return True
    else:
        print("❌ SOME TIMEOUT TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
