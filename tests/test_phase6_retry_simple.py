#!/usr/bin/env python3
"""
Phase 6 Retry Policy Tests - Simplified
Gate 7 Failure Survival & Crash Consistency
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reliability import (
    RetryCategory,
    RetryPolicy,
    RetryAttempt,
    RetryError,
    IdempotencyManager,
    RetryManager,
    get_retry_manager
)


class MockAuditEmitter:
    """Mock audit emitter for testing"""
    
    def __init__(self):
        self.events = []
    
    async def emit(self, audit_data):
        self.events.append(audit_data)


async def test_retry_policy():
    """Test retry policy configuration"""
    print("Testing retry policy...")
    
    policy = RetryPolicy(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=2.0,
        jitter_enabled=True,
        jitter_factor=0.1
    )
    
    assert policy.max_attempts == 5, "Max attempts should be 5"
    assert policy.base_delay == 1.0, "Base delay should be 1.0"
    assert policy.max_delay == 30.0, "Max delay should be 30.0"
    assert policy.backoff_multiplier == 2.0, "Backoff multiplier should be 2.0"
    assert policy.jitter_enabled == True, "Jitter should be enabled"
    
    print("✓ Retry policy configuration works correctly")


async def test_idempotency_manager():
    """Test idempotency manager operations"""
    print("Testing idempotency manager...")
    
    manager = IdempotencyManager()
    
    # Test idempotency key generation
    key1 = manager.compute_idempotency_key("test_op", "tenant1", "corr1")
    key2 = manager.compute_idempotency_key("test_op", "tenant1", "corr1")
    key3 = manager.compute_idempotency_key("test_op", "tenant2", "corr1")
    
    assert key1 == key2, "Same parameters should generate same key"
    assert key1 != key3, "Different tenant should generate different key"
    assert len(key1) == 64, "Key should be SHA256 hash (64 chars)"
    
    # Test idempotency check and record
    assert await manager.check_idempotency(key1) is None, "Should return None for new key"
    
    await manager.record_result(key1, "result1", {"meta": "data"})
    assert await manager.check_idempotency(key1) == "result1", "Should return recorded result"
    
    # Test clearing
    await manager.clear_idempotency(key1)
    assert await manager.check_idempotency(key1) is None, "Should return None after clearing"
    
    print("✓ Idempotency manager works correctly")


async def test_retry_manager():
    """Test retry manager operations"""
    print("Testing retry manager...")
    
    manager = RetryManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test policy retrieval
    nats_policy = manager.get_policy(RetryCategory.NATS_CONNECT)
    assert nats_policy.max_attempts == 5, "NATS connect should have 5 attempts"
    
    kv_policy = manager.get_policy(RetryCategory.KV_GET)
    assert kv_policy.max_attempts == 3, "KV get should have 3 attempts"
    
    # Test unknown category (should return default)
    unknown_policy = manager.get_policy("RETRY_UNKNOWN")
    assert unknown_policy.max_attempts == 3, "Unknown category should return default policy"
    
    print("✓ Retry manager works correctly")


async def test_retry_success():
    """Test retry with successful operation"""
    print("Testing retry success case...")
    
    manager = RetryManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test successful operation (no retries)
    async def successful_operation():
        return "success"
    
    result = await manager.execute_with_retry(
        category=RetryCategory.NATS_PUBLISH,
        operation="Successful operation",
        coro=successful_operation,
        tenant_id="test-tenant",
        correlation_id="test-corr",
        trace_id="test-trace"
    )
    
    assert result == "success", "Operation should succeed"
    assert len(mock_emitter.events) == 0, "No audit events for successful operations"
    
    print("✓ Retry success case works correctly")


async def test_retry_with_failures():
    """Test retry with failing operation"""
    print("Testing retry with failures...")
    
    manager = RetryManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Create a counter-based failing operation
    attempt_count = 0
    
    async def failing_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count <= 2:  # Fail first 2 attempts
            raise Exception(f"Attempt {attempt_count} failed")
        return "success"
    
    result = await manager.execute_with_retry(
        category=RetryCategory.KV_GET,
        operation="Failing operation",
        coro=failing_operation,
        tenant_id="test-tenant",
        correlation_id="test-corr",
        trace_id="test-trace"
    )
    
    assert result == "success", "Operation should eventually succeed"
    assert attempt_count == 3, "Should have attempted 3 times (2 fails + 1 success)"
    
    # Check retry attempt audit events
    retry_events = [e for e in mock_emitter.events if e["event_type"] == "retry_attempt"]
    assert len(retry_events) == 2, "Should have 2 retry attempt events"
    
    # Check retry attempt details
    for i, event in enumerate(retry_events):
        assert event["attempt_number"] == i + 1, f"Attempt {i+1} should be recorded"
        assert event["max_attempts"] == 3, "Should record max attempts"
        assert event["retry_category"] == "RETRY_KV_GET", "Should preserve category"
        assert event["operation"] == "Failing operation", "Should preserve operation"
        assert event["exception_type"] == "Exception", "Should record exception type"
    
    print("✓ Retry with failures works correctly")


async def test_retry_exhaustion():
    """Test retry exhaustion (all attempts fail)"""
    print("Testing retry exhaustion...")
    
    manager = RetryManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Create operation that always fails
    async def always_failing_operation():
        raise Exception("Always fails")
    
    try:
        await manager.execute_with_retry(
            category=RetryCategory.NATS_PUBLISH,
            operation="Always failing operation",
            coro=always_failing_operation,
            tenant_id="test-tenant",
            correlation_id="test-corr",
            trace_id="test-trace"
        )
        assert False, "Should have raised RetryError"
    except RetryError as e:
        assert e.category == RetryCategory.NATS_PUBLISH, "Should preserve category"
        assert len(e.attempts) == 3, "Should have 3 attempts (default max)"
        assert "Always failing operation" in str(e), "Should include operation name"
    
    # Check retry exhaustion audit event
    exhausted_events = [e for e in mock_emitter.events if e["event_type"] == "retry_exhausted"]
    assert len(exhausted_events) == 1, "Should emit retry exhausted event"
    
    exhausted_event = exhausted_events[0]
    assert exhausted_event["retry_category"] == "RETRY_NATS_PUBLISH", "Should preserve category"
    assert exhausted_event["operation"] == "Always failing operation", "Should preserve operation"
    assert exhausted_event["total_attempts"] == 3, "Should record total attempts"
    
    print("✓ Retry exhaustion works correctly")


async def test_retry_with_idempotency():
    """Test retry with idempotency protection"""
    print("Testing retry with idempotency...")
    
    manager = RetryManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Create a counter-based failing operation
    attempt_count = 0
    
    async def idempotent_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count <= 2:  # Fail first 2 attempts
            raise Exception(f"Attempt {attempt_count} failed")
        return "success"
    
    idempotency_key = manager.idempotency_manager.compute_idempotency_key(
        "idempotent_operation", "tenant1", "corr1"
    )
    
    # First execution (should fail twice then succeed)
    result1 = await manager.execute_with_retry(
        category=RetryCategory.KV_PUT,
        operation="Idempotent operation",
        coro=lambda: idempotent_operation(),
        idempotency_key=idempotency_key,
        tenant_id="tenant1",
        correlation_id="corr1",
        trace_id="trace1"
    )
    
    assert result1 == "success", "First execution should succeed"
    assert attempt_count == 3, "Should have attempted 3 times"
    
    # Reset counter for second execution
    attempt_count = 0
    
    # Second execution (should hit idempotency cache)
    result2 = await manager.execute_with_retry(
        category=RetryCategory.KV_PUT,
        operation="Idempotent operation",
        coro=lambda: idempotent_operation(),
        idempotency_key=idempotency_key,
        tenant_id="tenant1",
        correlation_id="corr1",
        trace_id="trace2"
    )
    
    assert result2 == "success", "Second execution should return cached result"
    assert attempt_count == 0, "Should not execute operation again"
    
    # Check idempotency audit events
    idempotency_events = [e for e in mock_emitter.events if e["event_type"] == "idempotency"]
    assert len(idempotency_events) == 2, "Should have 2 idempotency events"
    
    hit_events = [e for e in idempotency_events if e["action"] == "hit"]
    record_events = [e for e in idempotency_events if e["action"] == "record"]
    
    assert len(hit_events) == 1, "Should have 1 idempotency hit"
    assert len(record_events) == 1, "Should have 1 idempotency record"
    
    print("✓ Retry with idempotency works correctly")


async def test_retry_backoff_and_jitter():
    """Test exponential backoff and jitter"""
    print("Testing retry backoff and jitter...")
    
    manager = RetryManager()
    
    # Test delay computation
    policy = RetryPolicy(
        base_delay=1.0,
        backoff_multiplier=2.0,
        max_delay=10.0,
        jitter_enabled=True,
        jitter_factor=0.1
    )
    
    # Test exponential backoff
    delay1 = manager._compute_delay(1, policy)  # 1st attempt
    delay2 = manager._compute_delay(2, policy)  # 2nd attempt
    delay3 = manager._compute_delay(3, policy)  # 3rd attempt
    
    # Should follow exponential pattern: 1.0, 2.0, 4.0 (with jitter)
    assert 0.9 <= delay1 <= 1.1, f"Delay 1 should be ~1.0s with jitter: {delay1}"
    assert 1.8 <= delay2 <= 2.2, f"Delay 2 should be ~2.0s with jitter: {delay2}"
    assert 3.6 <= delay3 <= 4.4, f"Delay 3 should be ~4.0s with jitter: {delay3}"
    
    # Test max delay capping
    policy_max = RetryPolicy(
        base_delay=10.0,
        backoff_multiplier=3.0,
        max_delay=20.0,
        jitter_enabled=False
    )
    
    delay_capped = manager._compute_delay(3, policy_max)  # Would be 90.0, but capped at 20.0
    assert delay_capped == 20.0, f"Delay should be capped at max_delay: {delay_capped}"
    
    print("✓ Retry backoff and jitter work correctly")


async def test_retry_exception_classification():
    """Test retry exception classification"""
    print("Testing retry exception classification...")
    
    manager = RetryManager()
    
    # Test default policy (retry all exceptions)
    default_policy = RetryPolicy()
    assert manager._is_retryable_exception(Exception(), default_policy), "Should retry Exception by default"
    assert manager._is_retryable_exception(ValueError(), default_policy), "Should retry ValueError by default"
    
    # Test non-retryable exceptions
    non_retry_policy = RetryPolicy(
        retryable_exceptions=[],  # Clear default retryable exceptions
        non_retryable_exceptions=[ValueError, TypeError]
    )
    
    assert not manager._is_retryable_exception(ValueError(), non_retry_policy), "Should not retry ValueError"
    assert not manager._is_retryable_exception(TypeError(), non_retry_policy), "Should not retry TypeError"
    assert manager._is_retryable_exception(RuntimeError(), non_retry_policy), "Should retry RuntimeError"
    
    # Test retryable exceptions (override non-retryable)
    retry_policy = RetryPolicy(
        non_retryable_exceptions=[ValueError],
        retryable_exceptions=[ValueError, TypeError]  # ValueError appears in both
    )
    
    # retryable_exceptions should take precedence
    assert manager._is_retryable_exception(ValueError(), retry_policy), "Should retry ValueError (retryable overrides)"
    assert manager._is_retryable_exception(TypeError(), retry_policy), "Should retry TypeError"
    assert not manager._is_retryable_exception(RuntimeError(), retry_policy), "Should not retry RuntimeError"
    
    print("✓ Retry exception classification works correctly")


async def main():
    """Run all retry policy tests"""
    print("=" * 60)
    print("PHASE 6: RETRY POLICY TESTS")
    print("Gate 7: Failure Survival & Crash Consistency")
    print("=" * 60)
    
    tests = [
        test_retry_policy,
        test_idempotency_manager,
        test_retry_manager,
        test_retry_success,
        test_retry_with_failures,
        test_retry_exhaustion,
        test_retry_with_idempotency,
        test_retry_backoff_and_jitter,
        test_retry_exception_classification
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
    print(f"RETRY POLICY TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL RETRY POLICY TESTS PASSED")
        return True
    else:
        print("❌ SOME RETRY TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
