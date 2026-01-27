#!/usr/bin/env python3
"""
Gate 5E Authentication/Authorization Tests
Phase 5 Operational Safety Hardening
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.auth import (
    AuthError,
    Permission,
    APIKey,
    AuthContext,
    APIKeyStore,
    AuthService,
    get_auth_service,
    requires_auth,
    create_api_key,
    revoke_api_key
)


async def test_api_key_creation():
    """Test API key creation"""
    print("Testing API key creation...")
    
    store = APIKeyStore()
    
    # Create key with multiple permissions
    actual_key = store.create_key(
        key_id="key-123",
        tenant_ids=["tenant-abc", "tenant-xyz"],
        permissions=[Permission.EXECUTE_A1, Permission.EXECUTE_A2, Permission.VIEW_STATUS],
        principal_id="operator-456",
        description="Test key for operations"
    )
    
    # Verify key was created
    assert "key-123" in store.keys, "Key should be stored"
    key = store.keys["key-123"]
    
    assert key.key_id == "key-123", "Key ID should match"
    assert key.principal_id == "operator-456", "Principal should match"
    assert len(key.tenant_ids) == 2, "Should have 2 tenant IDs"
    assert Permission.EXECUTE_A1 in key.permissions, "Should have EXECUTE_A1 permission"
    assert key.is_active == True, "Key should be active"
    assert actual_key is not None, "Should return actual key value"
    
    print("✓ API key creation works correctly")


async def test_api_key_validation():
    """Test API key validation"""
    print("Testing API key validation...")
    
    store = APIKeyStore()
    
    # Create expired key
    expired_key = store.create_key(
        key_id="expired-key",
        tenant_ids=["tenant-123"],
        permissions=[Permission.EXECUTE_A0],
        principal_id="operator-123",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired 1 hour ago
    )
    
    # Create inactive key
    store.create_key(
        key_id="inactive-key",
        tenant_ids=["tenant-123"],
        permissions=[Permission.EXECUTE_A0],
        principal_id="operator-123"
    )
    store.keys["inactive-key"].is_active = False
    
    # Test expired key
    expired_api_key = store.keys["expired-key"]
    assert expired_api_key.is_expired() == True, "Key should be expired"
    assert expired_api_key.is_valid() == False, "Expired key should be invalid"
    
    # Test inactive key
    inactive_api_key = store.keys["inactive-key"]
    assert inactive_api_key.is_active == False, "Key should be inactive"
    assert inactive_api_key.is_valid() == False, "Inactive key should be invalid"
    
    # Test valid key
    valid_key = store.create_key(
        key_id="valid-key",
        tenant_ids=["tenant-123"],
        permissions=[Permission.EXECUTE_A0],
        principal_id="operator-123"
    )
    valid_api_key = store.keys["valid-key"]
    assert valid_api_key.is_valid() == True, "Valid key should be valid"
    
    print("✓ API key validation works correctly")


async def test_authentication():
    """Test authentication process"""
    print("Testing authentication...")
    
    store = APIKeyStore()
    auth_service = AuthService(store)
    
    # Create a key
    actual_key = store.create_key(
        key_id="auth-test-key",
        tenant_ids=["tenant-auth"],
        permissions=[Permission.EXECUTE_A1],
        principal_id="operator-auth"
    )
    
    # Test successful authentication
    auth_context = await auth_service.authenticate(actual_key)
    
    assert auth_context.principal_id == "operator-auth", "Principal should match"
    assert Permission.EXECUTE_A1 in auth_context.permissions, "Permissions should be preserved"
    assert auth_context.api_key.key_id == "auth-test-key", "Key ID should match"
    
    # Test failed authentication (invalid key)
    try:
        await auth_service.authenticate("invalid-key")
        assert False, "Should have raised AuthError"
    except AuthError as e:
        assert "Invalid API key" in str(e), "Should cite invalid key"
    
    # Test failed authentication (missing key)
    try:
        await auth_service.authenticate("")
        assert False, "Should have raised AuthError"
    except AuthError as e:
        assert "Missing API key" in str(e), "Should cite missing key"
    
    print("✓ Authentication works correctly")


async def test_authorization():
    """Test authorization process"""
    print("Testing authorization...")
    
    store = APIKeyStore()
    auth_service = AuthService(store)
    
    # Create a key with limited permissions
    actual_key = store.create_key(
        key_id="authz-test-key",
        tenant_ids=["tenant-authz"],
        permissions=[Permission.EXECUTE_A0, Permission.VIEW_STATUS],  # No A1/A2/A3
        principal_id="operator-authz"
    )
    
    # Authenticate first
    auth_context = await auth_service.authenticate(actual_key)
    
    # Test successful authorization (has permission)
    authorized_context = await auth_service.authorize(
        auth_context, Permission.EXECUTE_A0, "tenant-authz"
    )
    assert authorized_context.tenant_id == "tenant-authz", "Tenant should be set"
    
    # Test failed authorization (missing permission)
    try:
        await auth_service.authorize(auth_context, Permission.EXECUTE_A2, "tenant-authz")
        assert False, "Should have raised AuthError"
    except AuthError as e:
        assert "missing required permission" in str(e), "Should cite missing permission"
    
    # Test failed authorization (wrong tenant)
    try:
        await auth_service.authorize(auth_context, Permission.EXECUTE_A0, "wrong-tenant")
        assert False, "Should have raised AuthError"
    except AuthError as e:
        assert "not authorized for tenant" in str(e), "Should cite tenant access"
    
    print("✓ Authorization works correctly")


async def test_combined_auth_and_authorization():
    """Test combined authenticate and authorize"""
    print("Testing combined auth and authorize...")
    
    store = APIKeyStore()
    auth_service = AuthService(store)
    
    # Create a key
    actual_key = store.create_key(
        key_id="combined-test-key",
        tenant_ids=["tenant-combined"],
        permissions=[Permission.EXECUTE_A1, Permission.GRANT_APPROVAL],
        principal_id="operator-combined"
    )
    
    # Test successful combined auth
    auth_context = await auth_service.authenticate_and_authorize(
        api_key=actual_key,
        required_permission=Permission.EXECUTE_A1,
        tenant_id="tenant-combined",
        correlation_id="corr-123",
        trace_id="trace-456"
    )
    
    assert auth_context.principal_id == "operator-combined", "Principal should match"
    assert auth_context.tenant_id == "tenant-combined", "Tenant should be set"
    assert auth_context.correlation_id == "corr-123", "Correlation ID should be set"
    assert auth_context.trace_id == "trace-456", "Trace ID should be set"
    
    # Test failed combined auth (wrong permission)
    try:
        await auth_service.authenticate_and_authorize(
            api_key=actual_key,
            required_permission=Permission.EXECUTE_A3,  # Key doesn't have this
            tenant_id="tenant-combined"
        )
        assert False, "Should have raised AuthError"
    except AuthError as e:
        assert "missing required permission" in str(e), "Should cite missing permission"
    
    print("✓ Combined auth and authorize works correctly")


@requires_auth(Permission.EXECUTE_A1)
async def _test_decorated_function(api_key=None, tenant_id=None, auth_context=None, **kwargs):
    """Test function with auth decorator (not a test itself)"""
    return f"Executed by {auth_context.principal_id} on {auth_context.tenant_id}"


async def test_auth_decorator():
    """Test authentication decorator"""
    print("Testing auth decorator...")
    
    store = APIKeyStore()
    
    # Override global auth service for testing
    import src.auth.auth_service as auth_module
    original_service = auth_module._auth_service
    auth_module._auth_service = AuthService(store)
    
    try:
        # Create a key
        actual_key = store.create_key(
            key_id="decorator-test-key",
            tenant_ids=["tenant-decorator"],
            permissions=[Permission.EXECUTE_A1],
            principal_id="operator-decorator"
        )
        
        # Test successful decorated function call
        result = await _test_decorated_function(
            api_key=actual_key,
            tenant_id="tenant-decorator"
        )
        
        assert "operator-decorator" in result, "Should include principal"
        assert "tenant-decorator" in result, "Should include tenant"
        
        # Test failed decorated function call (no API key)
        try:
            await _test_decorated_function(tenant_id="tenant-decorator", api_key=None)
            assert False, "Should have raised AuthError"
        except AuthError as e:
            assert "Missing API key" in str(e), "Should cite missing API key"
        
        print("✓ Auth decorator works correctly")
    
    finally:
        # Restore original service
        auth_module._auth_service = original_service


async def test_key_management():
    """Test key management operations"""
    print("Testing key management...")
    
    # Test key creation via convenience function
    actual_key = await create_api_key(
        key_id="mgmt-test-key",
        tenant_ids=["tenant-mgmt"],
        permissions=[Permission.EXECUTE_A0, Permission.EXECUTE_A1],
        principal_id="operator-mgmt",
        description="Management test key"
    )
    
    assert actual_key is not None, "Should return actual key"
    
    # Test key revocation
    revoked = await revoke_api_key("mgmt-test-key")
    assert revoked == True, "Key should be revoked"
    
    # Test revoking non-existent key
    revoked = await revoke_api_key("non-existent-key")
    assert revoked == False, "Should return False for non-existent key"
    
    print("✓ Key management works correctly")


async def test_permission_enforcement():
    """Test permission enforcement for different action types"""
    print("Testing permission enforcement...")
    
    store = APIKeyStore()
    auth_service = AuthService(store)
    
    # Create keys with different permission levels
    observer_key = store.create_key(
        key_id="observer-key",
        tenant_ids=["tenant-perms"],
        permissions=[Permission.EXECUTE_A0],  # Read-only
        principal_id="operator-observer"
    )
    
    operator_key = store.create_key(
        key_id="operator-key",
        tenant_ids=["tenant-perms"],
        permissions=[Permission.EXECUTE_A0, Permission.EXECUTE_A1, Permission.EXECUTE_A2],
        principal_id="operator-full"
    )
    
    # Test observer key (should only allow A0)
    observer_auth = await auth_service.authenticate(observer_key)
    
    # Should allow A0
    await auth_service.authorize(observer_auth, Permission.EXECUTE_A0, "tenant-perms")
    
    # Should deny A1
    try:
        await auth_service.authorize(observer_auth, Permission.EXECUTE_A1, "tenant-perms")
        assert False, "Observer should not have A1 permission"
    except AuthError:
        pass  # Expected
    
    # Test operator key (should allow A0, A1, A2)
    operator_auth = await auth_service.authenticate(operator_key)
    
    # Should allow A0, A1, A2
    await auth_service.authorize(operator_auth, Permission.EXECUTE_A0, "tenant-perms")
    await auth_service.authorize(operator_auth, Permission.EXECUTE_A1, "tenant-perms")
    await auth_service.authorize(operator_auth, Permission.EXECUTE_A2, "tenant-perms")
    
    # Should deny A3 (not granted)
    try:
        await auth_service.authorize(operator_auth, Permission.EXECUTE_A3, "tenant-perms")
        assert False, "Operator should not have A3 permission"
    except AuthError:
        pass  # Expected
    
    print("✓ Permission enforcement works correctly")


async def main():
    """Run all Gate 5E auth tests"""
    print("=" * 60)
    print("GATE 5E: AUTHENTICATION/AUTHORIZATION TESTS")
    print("=" * 60)
    
    tests = [
        test_api_key_creation,
        test_api_key_validation,
        test_authentication,
        test_authorization,
        test_combined_auth_and_authorization,
        test_auth_decorator,
        test_key_management,
        test_permission_enforcement
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
    print(f"GATE 5E TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ ALL AUTHENTICATION TESTS PASSED")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
