#!/usr/bin/env python3
"""
Phase 6 Backpressure Tests
Gate 8 Bounded Load & Backpressure
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.reliability import (
    BackpressureAction,
    RateLimitExceeded,
    QueueFullError,
    RateLimitConfig,
    QueueConfig,
    TokenBucket,
    TenantRateLimiter,
    BoundedQueue,
    BackpressureManager,
    get_backpressure_manager
)


class MockAuditEmitter:
    """Mock audit emitter for testing"""
    
    def __init__(self):
        self.events = []
    
    async def emit(self, audit_data):
        self.events.append(audit_data)


async def test_token_bucket():
    """Test token bucket rate limiter"""
    print("Testing token bucket...")
    
    bucket = TokenBucket(rate=10.0, burst=20.0, window_size=1.0)
    
    # Should start with full burst
    assert await bucket.consume(5) == True, "Should consume 5 tokens from full bucket"
    assert await bucket.consume(15) == True, "Should consume remaining 15 tokens"
    assert await bucket.consume(1) == False, "Should fail when bucket is empty"
    
    # Test refill after time
    import time
    time.sleep(0.2)  # Wait for refill
    
    assert await bucket.consume(1) == True, "Should have tokens after refill"
    
    print("✓ Token bucket works correctly")


async def test_rate_limit_config():
    """Test rate limit configuration"""
    print("Testing rate limit configuration...")
    
    config = RateLimitConfig(
        global_requests_per_second=100.0,
        tenant_requests_per_second=10.0,
        window_size_seconds=1.0,
        burst_multiplier=2.0,
        cleanup_interval_seconds=60.0
    )
    
    assert config.global_requests_per_second == 100.0, "Global rate should be 100"
    assert config.tenant_requests_per_second == 10.0, "Tenant rate should be 10"
    assert config.window_size_seconds == 1.0, "Window should be 1s"
    assert config.burst_multiplier == 2.0, "Burst multiplier should be 2.0"
    assert config.cleanup_interval_seconds == 60.0, "Cleanup interval should be 60s"
    
    print("✓ Rate limit configuration works correctly")


async def test_tenant_rate_limiter():
    """Test tenant rate limiter"""
    print("Testing tenant rate limiter...")
    
    config = RateLimitConfig(
        global_requests_per_second=100.0,
        tenant_requests_per_second=10.0,
        burst_multiplier=2.0
    )
    
    limiter = TenantRateLimiter("test-tenant", config)
    
    # Should allow requests within limit
    for i in range(20):  # 20 requests (within burst of 20)
        await limiter.check_rate_limit(f"request-{i}")
    
    # Should fail when burst is exhausted
    try:
        await limiter.check_rate_limit("request-21")
        assert False, "Should have raised RateLimitExceeded"
    except RateLimitExceeded as e:
        assert e.tenant_id == "test-tenant", "Should preserve tenant ID"
        assert e.limit_type in ["global", "tenant"], "Should specify limit type"
        assert e.current_rate < e.limit, "Current rate should be below limit"
    
    # Test rate statistics
    rates = limiter.get_current_rates()
    assert "global_rate" in rates, "Should include global rate"
    assert "tenant_rate" in rates, "Should include tenant rate"
    assert "global_limit" in rates, "Should include global limit"
    assert "tenant_limit" in rates, "Should include tenant limit"
    
    print("✓ Tenant rate limiter works correctly")


async def test_bounded_queue():
    """Test bounded queue operations"""
    print("Testing bounded queue...")
    
    config = QueueConfig(
        max_size=5,
        drop_policy="reject",
        max_wait_time=30.0
    )
    
    queue = BoundedQueue("test-queue", config)
    
    # Should allow adding items up to capacity
    for i in range(5):
        await queue.put(f"item-{i}")
    
    assert queue.size() == 5, "Queue should have 5 items"
    assert queue.is_full() == True, "Queue should be full"
    
    # Should reject when full (drop_policy="reject")
    try:
        await queue.put("item-6")
        assert False, "Should have raised QueueFullError"
    except QueueFullError as e:
        assert e.queue_name == "test-queue", "Should preserve queue name"
        assert e.capacity == 5, "Should preserve capacity"
        assert e.current_size == 5, "Should preserve current size"
    
    # Test getting items
    item = await queue.get()
    assert item == "item-0", "Should get first item"
    assert queue.size() == 4, "Queue should have 4 items"
    
    # Test queue statistics
    stats = queue.get_stats()
    assert stats["name"] == "test-queue", "Should include queue name"
    assert stats["current_size"] == 4, "Should include current size"
    assert stats["max_size"] == 5, "Should include max size"
    assert stats["is_full"] == False, "Should indicate not full"
    
    print("✓ Bounded queue works correctly")


async def test_backpressure_manager():
    """Test backpressure manager operations"""
    print("Testing backpressure manager...")
    
    manager = BackpressureManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test rate limiter creation
    limiter1 = manager.get_rate_limiter("tenant-1")
    limiter2 = manager.get_rate_limiter("tenant-2")
    
    assert limiter1.tenant_id == "tenant-1", "Should create rate limiter for tenant-1"
    assert limiter2.tenant_id == "tenant-2", "Should create rate limiter for tenant-2"
    assert limiter1 is not limiter2, "Should create separate instances"
    
    # Test queue creation
    queue1 = manager.get_queue("queue-1")
    queue2 = manager.get_queue("queue-2")
    
    assert queue1.name == "queue-1", "Should create queue with correct name"
    assert queue2.name == "queue-2", "Should create queue with correct name"
    assert queue1 is not queue2, "Should create separate instances"
    
    print("✓ Backpressure manager works correctly")


async def test_backpressure_check():
    """Test backpressure checking"""
    print("Testing backpressure check...")
    
    manager = BackpressureManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test successful backpressure check
    status = await manager.check_backpressure("tenant-123", None, "test-operation")
    
    assert status["tenant_id"] == "tenant-123", "Should preserve tenant ID"
    assert status["operation"] == "test-operation", "Should preserve operation"
    assert status["backpressure_action"] is None, "Should have no backpressure action"
    assert status["rate_limited"] == False, "Should not be rate limited"
    assert status["queue_full"] == False, "Should not have queue full"
    
    # Test rate limit check (exhaust burst)
    limiter = manager.get_rate_limiter("tenant-123")
    
    # Consume all burst tokens
    for i in range(20):  # 20 tokens in burst
        try:
            await limiter.check_rate_limit(f"request-{i}")
        except RateLimitExceeded:
            break
    
    # Now check backpressure should detect rate limiting
    try:
        await manager.check_backpressure("tenant-123", None, "rate-limited-op")
        assert False, "Should have raised RateLimitExceeded"
    except RateLimitExceeded:
        pass  # Expected
    
    # Check audit events
    backpressure_events = [e for e in mock_emitter.events if e["event_type"] == "backpressure"]
    assert len(backpressure_events) > 0, "Should emit backpressure audit events"
    
    event = backpressure_events[0]
    assert event["tenant_id"] == "tenant-123", "Should preserve tenant ID"
    assert event["backpressure_action"] == BackpressureAction.RATE_LIMITED, "Should record action"
    
    print("✓ Backpressure check works correctly")


async def test_execute_with_backpressure():
    """Test execution with backpressure protection"""
    print("Testing execute with backpressure...")
    
    manager = BackpressureManager()
    mock_emitter = MockAuditEmitter()
    manager.set_audit_emitter(mock_emitter.emit)
    
    # Test successful execution
    async def successful_operation():
        return "operation-success"
    
    result = await manager.execute_with_backpressure(
        tenant_id="tenant-456",
        operation="test-operation",
        coro=successful_operation
    )
    
    assert result == "operation-success", "Should return operation result"
    
    # Test execution with rate limiting
    async def rate_limited_operation():
        return "rate-limited-success"
    
    # Exhaust rate limit
    limiter = manager.get_rate_limiter("tenant-456")
    for i in range(25):  # Exhaust burst
        try:
            await limiter.check_rate_limit(f"request-{i}")
        except RateLimitExceeded:
            break
    
    # Should fail with rate limit
    try:
        await manager.execute_with_backpressure(
            tenant_id="tenant-456",
            operation="rate-limited-operation",
            coro=rate_limited_operation
        )
        assert False, "Should have raised RateLimitExceeded"
    except RateLimitExceeded:
        pass  # Expected
    
    print("✓ Execute with backpressure works correctly")


async def main():
    """Run all backpressure tests"""
    print("=" * 60)
    print("PHASE 6: BACKPRESSURE TESTS")
    print("Gate 8: Bounded Load & Backpressure")
    print("=" * 60)
    
    tests = [
        test_token_bucket,
        test_rate_limit_config,
        test_tenant_rate_limiter,
        test_bounded_queue,
        test_backpressure_manager,
        test_backpressure_check,
        test_execute_with_backpressure
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
    print(f"BACKPRESSURE TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL BACKPRESSURE TESTS PASSED")
        return True
    else:
        print("❌ SOME BACKPRESSURE TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
