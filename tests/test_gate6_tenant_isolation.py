#!/usr/bin/env python3
"""
Gate 6 Tenant Isolation Tests
Phase 5 Operational Safety Hardening
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tenancy import (
    TenantContext,
    TenantIsolationError,
    TenantContextManager,
    TenantScopedOperations,
    TenantScopedKVStore,
    TenantScopedStream,
    get_tenant_manager,
    require_tenant_context,
    set_tenant_context,
    get_tenant_context,
    requires_tenant_context,
    tenant_scoped
)


class MockKVStore:
    """Mock KV store for testing"""
    
    def __init__(self):
        self.data = {}
    
    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Key {key} not found")
    
    async def put(self, key, value):
        self.data[key] = value
    
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
        else:
            raise KeyError(f"Key {key} not found")


class MockStreamManager:
    """Mock stream manager for testing"""
    
    def __init__(self):
        self.published = []
        self.subscribed = []
    
    async def publish(self, subject, data):
        self.published.append({"subject": subject, "data": data})
    
    async def subscribe(self, subject, handler):
        self.subscribed.append({"subject": subject, "handler": handler})


async def test_tenant_context_validation():
    """Test tenant context validation"""
    print("Testing tenant context validation...")
    
    # Test valid context
    context = TenantContext(tenant_id="tenant-123")
    context.validate()  # Should not raise
    
    # Test invalid context (empty tenant_id)
    try:
        invalid_context = TenantContext(tenant_id="")
        invalid_context.validate()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    # Test invalid context (None tenant_id)
    try:
        invalid_context = TenantContext(tenant_id=None)
        invalid_context.validate()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    print("✓ Tenant context validation works correctly")


async def test_tenant_context_manager():
    """Test tenant context manager operations"""
    print("Testing tenant context manager...")
    
    manager = TenantContextManager()
    
    # Test require_context when no context is set
    try:
        manager.require_context("test operation")
        assert False, "Should have raised TenantIsolationError"
    except TenantIsolationError:
        pass  # Expected
    
    # Test set and get context
    context = TenantContext(tenant_id="tenant-456")
    manager.set_context(context)
    
    retrieved = manager.get_context()
    assert retrieved == context, "Context should be the same"
    
    # Test require_context with context set
    required = manager.require_context("test operation")
    assert required == context, "Required context should be the same"
    
    # Test context stack
    context2 = TenantContext(tenant_id="tenant-789")
    manager.push_context(context2)
    
    assert manager.get_context().tenant_id == "tenant-789", "Should have pushed context"
    
    popped = manager.pop_context()
    assert popped.tenant_id == "tenant-789", "Should pop correct context"
    assert manager.get_context().tenant_id == "tenant-456", "Should restore previous context"
    
    # Test clear context
    manager.clear_context()
    assert manager.get_context() is None, "Context should be cleared"
    
    print("✓ Tenant context manager works correctly")


async def test_tenant_scoped_kv_operations():
    """Test tenant-scoped KV operations"""
    print("Testing tenant-scoped KV operations...")
    
    # Set up tenant context and KV store
    context = TenantContext(tenant_id="tenant-abc")
    set_tenant_context(context)
    
    mock_kv = MockKVStore()
    scoped_kv = TenantScopedKVStore(mock_kv)
    
    # Test tenant-scoped key generation
    await scoped_kv.put("test_key", "test_value")
    
    # Verify key is tenant-scoped
    expected_key = "tenant-abc:test_key"
    assert expected_key in mock_kv.data, "Key should be tenant-scoped"
    assert mock_kv.data[expected_key] == "test_value", "Value should be stored correctly"
    
    # Test tenant-scoped get
    value = await scoped_kv.get("test_key")
    assert value == "test_value", "Should retrieve correct value"
    
    # Test tenant isolation
    # Switch to different tenant
    context2 = TenantContext(tenant_id="tenant-xyz")
    set_tenant_context(context2)
    
    # Try to access other tenant's data
    try:
        await scoped_kv.get("test_key")
        assert False, "Should not be able to access other tenant's data"
    except KeyError:
        pass  # Expected - different tenant can't access
    
    print("✓ Tenant-scoped KV operations work correctly")


async def test_tenant_scoped_stream_operations():
    """Test tenant-scoped stream operations"""
    print("Testing tenant-scoped stream operations...")
    
    # Set up tenant context and stream manager
    context = TenantContext(tenant_id="tenant-stream")
    set_tenant_context(context)
    
    mock_stream = MockStreamManager()
    scoped_stream = TenantScopedStream(mock_stream)
    
    # Test tenant-scoped stream name
    stream_name = scoped_stream.get_stream_name("audit")
    assert stream_name == "EXOARMUR_TENANT-STREAM_AUDIT", "Stream name should be tenant-scoped"
    
    # Test tenant-scoped subject
    subject = scoped_stream.get_subject("events.test")
    assert subject == "exoarmur.tenant-stream.events.test", "Subject should be tenant-scoped"
    
    # Test tenant-scoped publish
    await scoped_stream.publish("events.test", {"data": "test"})
    
    # Verify publish was tenant-scoped
    assert len(mock_stream.published) == 1, "Should have one published message"
    assert mock_stream.published[0]["subject"] == "exoarmur.tenant-stream.events.test"
    
    # Test tenant-scoped subscribe
    async def test_handler(msg):
        pass
    
    await scoped_stream.subscribe("events.test", test_handler)
    
    # Verify subscribe was tenant-scoped
    assert len(mock_stream.subscribed) == 1, "Should have one subscription"
    assert mock_stream.subscribed[0]["subject"] == "exoarmur.tenant-stream.events.test"
    
    print("✓ Tenant-scoped stream operations work correctly")


async def test_tenant_access_validation():
    """Test tenant access validation"""
    print("Testing tenant access validation...")
    
    operations = TenantScopedOperations()
    
    # Set up tenant context
    context = TenantContext(tenant_id="tenant-allowed")
    set_tenant_context(context)
    
    # Test valid tenant access
    operations._validate_tenant_access("tenant-allowed", "test operation")  # Should not raise
    
    # Test invalid tenant access
    try:
        operations._validate_tenant_access("tenant-forbidden", "test operation")
        assert False, "Should have raised TenantIsolationError"
    except TenantIsolationError as e:
        assert "tenant-allowed" in str(e), "Error should mention current tenant"
        assert "tenant-forbidden" in str(e), "Error should mention target tenant"
    
    print("✓ Tenant access validation works correctly")


@requires_tenant_context("decorated operation")
async def test_decorated_function():
    """Test decorator for tenant context requirement"""
    return "operation succeeded"


async def test_tenant_context_decorators():
    """Test tenant context decorators"""
    print("Testing tenant context decorators...")
    
    # Clear any existing context first
    get_tenant_manager().clear_context()
    
    # Test decorator without context
    try:
        await test_decorated_function()
        assert False, "Should have raised TenantIsolationError"
    except TenantIsolationError:
        pass  # Expected
    
    # Test decorator with context
    set_tenant_context(TenantContext(tenant_id="tenant-decorator"))
    result = await test_decorated_function()
    assert result == "operation succeeded", "Decorator should allow operation with context"
    
    print("✓ Tenant context decorators work correctly")


@tenant_scoped("scoped operation")
async def test_scoped_function(tenant_context=None):
    """Test decorator for tenant-scoped operations"""
    return f"operation for {tenant_context.tenant_id}"


async def test_tenant_scoped_decorator():
    """Test tenant-scoped decorator"""
    print("Testing tenant-scoped decorator...")
    
    # Clear any existing context first
    get_tenant_manager().clear_context()
    
    # Test scoped decorator with context
    set_tenant_context(TenantContext(tenant_id="tenant-scoped"))
    result = await test_scoped_function()
    assert result == "operation for tenant-scoped", "Scoped decorator should pass context"
    
    print("✓ Tenant-scoped decorator works correctly")


async def main():
    """Run all Gate 6 tenant isolation tests"""
    print("=" * 60)
    print("GATE 6: TENANT ISOLATION TESTS")
    print("=" * 60)
    
    tests = [
        test_tenant_context_validation,
        test_tenant_context_manager,
        test_tenant_scoped_kv_operations,
        test_tenant_scoped_stream_operations,
        test_tenant_access_validation,
        test_tenant_context_decorators,
        test_tenant_scoped_decorator
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
    print(f"GATE 6 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ ALL TENANT ISOLATION TESTS PASSED")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
