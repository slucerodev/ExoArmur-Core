#!/usr/bin/env python3
"""
Gate 5D Operator Approval Tests
Phase 5 Operational Safety Hardening
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from approval import (
    ApprovalStatus,
    ActionType,
    ApprovalRequest,
    ApprovalDecision,
    ApprovalError,
    ApprovalGate,
    get_approval_gate,
    enforce_approval_gate
)


class MockKVStore:
    """Mock KV store for testing"""
    
    def __init__(self):
        self.data = {}
    
    async def create_key_value(self, bucket, description):
        return self
    
    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Key {key} not found")
    
    async def put(self, key, value):
        if isinstance(value, str):
            self.data[key] = value.encode('utf-8')
        else:
            self.data[key] = value


class MockNATSClient:
    """Mock NATS client for testing"""
    
    def __init__(self):
        self.published_messages = []
        self.js = MockJS(self)
    
    async def publish(self, subject, data):
        self.published_messages.append({
            "subject": subject,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


class MockJS:
    def __init__(self, parent):
        self.parent = parent
    
    async def create_key_value(self, bucket, description):
        return MockKVStore()


async def test_approval_requirement_by_action_type():
    """Test approval requirement by action type"""
    print("Testing approval requirement by action type...")
    
    gate = ApprovalGate()
    
    # A0_observe should not require approval
    assert not gate._requires_approval(ActionType.A0_OBSERVE), "A0 should not require approval"
    
    # A1, A2, A3 should require approval
    assert gate._requires_approval(ActionType.A1_SOFT_CONTAINMENT), "A1 should require approval"
    assert gate._requires_approval(ActionType.A2_HARD_CONTAINMENT), "A2 should require approval"
    assert gate._requires_approval(ActionType.A3_IRREVERSIBLE), "A3 should require approval"
    
    print("✓ Approval requirement by action type works correctly")


async def test_approval_request_creation():
    """Test approval request creation"""
    print("Testing approval request creation...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    request = ApprovalRequest(
        request_id="req-123",
        tenant_id="tenant-456",
        action_type=ActionType.A2_HARD_CONTAINMENT,
        subject="host-789",
        intent_hash="hash-abc",
        principal_id="operator-123",
        rationale="Suspicious activity detected"
    )
    
    request_id = await gate.create_approval_request(request)
    
    assert request_id == "req-123", "Request ID should be returned"
    
    print("✓ Approval request creation works correctly")


async def test_approval_grant():
    """Test approval grant"""
    print("Testing approval grant...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    decision = ApprovalDecision(
        approval_id="approval-123",
        request_id="req-123",
        status=ApprovalStatus.APPROVED,
        approver_id="supervisor-456",
        rationale="Threat confirmed, containment approved"
    )
    
    await gate.grant_approval(decision)
    
    print("✓ Approval grant works correctly")


async def test_approval_deny():
    """Test approval denial"""
    print("Testing approval denial...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    decision = ApprovalDecision(
        approval_id="approval-456",
        request_id="req-123",
        status=ApprovalStatus.DENIED,
        approver_id="supervisor-456",
        rationale="Insufficient evidence for containment"
    )
    
    await gate.deny_approval(decision)
    
    print("✓ Approval denial works correctly")


async def test_approval_gate_enforcement_no_approval_required():
    """Test approval gate enforcement for actions that don't require approval"""
    print("Testing approval gate enforcement for A0 (no approval required)...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    # A0_observe should be allowed without approval
    result = await gate.enforce_approval_gate(
        action_type=ActionType.A0_OBSERVE,
        tenant_id="tenant-123",
        subject="host-456",
        intent_hash="hash-abc",
        principal_id="operator-789"
        # No approval_id provided
    )
    
    assert result == True, "A0 should be allowed without approval"
    
    print("✓ A0 actions allowed without approval")


async def test_approval_gate_enforcement_missing_approval():
    """Test approval gate enforcement when approval is missing"""
    print("Testing approval gate enforcement for missing approval...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    # A2 should require approval
    result = await gate.enforce_approval_gate(
        action_type=ActionType.A2_HARD_CONTAINMENT,
        tenant_id="tenant-123",
        subject="host-456",
        intent_hash="hash-abc",
        principal_id="operator-789"
        # No approval_id provided
    )
    
    assert result == False, "A2 should be denied without approval"
    
    # Check audit event was emitted
    assert len(mock_nats.published_messages) == 1, "Should have one audit message"
    audit_msg = mock_nats.published_messages[0]
    assert audit_msg["data"]["event_type"] == "approval_denied", "Should emit approval_denied"
    assert audit_msg["data"]["denial_reason"] == "missing_approval_id", "Should cite missing approval"
    
    print("✓ Missing approval correctly denied and audited")


async def test_approval_gate_enforcement_invalid_approval():
    """Test approval gate enforcement with invalid approval"""
    print("Testing approval gate enforcement for invalid approval...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    # A2 with invalid approval ID
    result = await gate.enforce_approval_gate(
        action_type=ActionType.A2_HARD_CONTAINMENT,
        tenant_id="tenant-123",
        subject="host-456",
        intent_hash="hash-abc",
        principal_id="operator-789",
        approval_id="invalid-approval-id"
    )
    
    assert result == False, "Invalid approval should be denied"
    
    # Check audit event was emitted
    assert len(mock_nats.published_messages) == 1, "Should have one audit message"
    audit_msg = mock_nats.published_messages[0]
    assert audit_msg["data"]["event_type"] == "approval_denied", "Should emit approval_denied"
    assert "approval_error" in audit_msg["data"]["denial_reason"], "Should cite approval error"
    
    print("✓ Invalid approval correctly denied and audited")


async def test_convenience_function():
    """Test convenience function for approval enforcement"""
    print("Testing convenience function...")
    
    mock_nats = MockNATSClient()
    
    # Override global gate for testing
    from approval import _approval_gate
    _approval_gate = ApprovalGate(nats_client=mock_nats)
    
    # Test A0 (should be allowed)
    result = await enforce_approval_gate(
        action_type=ActionType.A0_OBSERVE,
        tenant_id="tenant-123",
        subject="host-456",
        intent_hash="hash-abc",
        principal_id="operator-789"
    )
    
    assert result == True, "Convenience function should work for A0"
    
    print("✓ Convenience function works correctly")


async def test_approval_request_validation():
    """Test approval request validation"""
    print("Testing approval request validation...")
    
    mock_nats = MockNATSClient()
    gate = ApprovalGate(nats_client=mock_nats)
    
    # Try to create request for A0 (should fail)
    try:
        request = ApprovalRequest(
            request_id="req-invalid",
            tenant_id="tenant-123",
            action_type=ActionType.A0_OBSERVE,  # A0 doesn't require approval
            subject="host-456",
            intent_hash="hash-abc",
            principal_id="operator-789"
        )
        
        await gate.create_approval_request(request)
        assert False, "Should have raised ApprovalError for A0"
    except ApprovalError:
        pass  # Expected
    
    print("✓ Approval request validation works correctly")


async def main():
    """Run all Gate 5D operator approval tests"""
    print("=" * 60)
    print("GATE 5D: OPERATOR APPROVAL TESTS")
    print("=" * 60)
    
    tests = [
        test_approval_requirement_by_action_type,
        test_approval_request_creation,
        test_approval_grant,
        test_approval_deny,
        test_approval_gate_enforcement_no_approval_required,
        test_approval_gate_enforcement_missing_approval,
        test_approval_gate_enforcement_invalid_approval,
        test_convenience_function,
        test_approval_request_validation
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
    print(f"GATE 5D TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ ALL OPERATOR APPROVAL TESTS PASSED")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
