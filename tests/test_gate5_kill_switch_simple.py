#!/usr/bin/env python3
"""
Gate 5 Kill Switch Enforcement Tests - Simplified
Phase 5 Operational Safety Hardening
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add src to path

from exoarmur.safety import (
    ExecutionGate, 
    ExecutionContext, 
    ExecutionActionType,
    GateDecision,
    DenialReason
)


class MockKVStore:
    """Mock KV store for testing"""
    
    def __init__(self, nats_client, bucket_name):
        self.nats_client = nats_client
        self.bucket_name = bucket_name
        self.data = {}
    
    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Key {key} not found")
    
    async def put(self, key, value):
        self.data[key] = value.encode('utf-8')


class MockJS:
    def __init__(self, parent):
        self.parent = parent
    
    async def create_key_value(self, bucket, description):
        return MockKVStore(self.parent, bucket)


class MockNATSClient:
    """Mock NATS client for testing"""
    
    def __init__(self):
        self.global_kv = {}
        self.tenant_kv = {}
        self.published_messages = []
        self.js = MockJS(self)
    
    async def publish(self, subject, data):
        self.published_messages.append({
            "subject": subject,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


async def test_execution_gate_fail_closed():
    """Test that execution gate defaults to DENY when no storage available"""
    print("Testing execution gate FAIL CLOSED behavior...")
    
    gate = ExecutionGate(nats_client=None)
    
    # Test without tenant context (should DENY)
    context = ExecutionContext(
        action_type=ExecutionActionType.IDENTITY_CONTAINMENT_APPLY,
        tenant_id=None
    )
    
    result = await gate.evaluate_execution(context)
    
    assert result.decision == GateDecision.DENY, f"Expected DENY, got {result.decision}"
    assert result.reason == DenialReason.MISSING_TENANT_CONTEXT, f"Expected missing tenant context, got {result.reason}"
    
    print("✓ Execution gate correctly DENIES without tenant context")


async def test_global_kill_switch_enforcement(kill_switch_test_mode):
    """Test that global kill switch blocks execution"""
    print("Testing global kill switch enforcement...")
    
    mock_nats = MockNATSClient()
    gate = ExecutionGate(nats_client=mock_nats)
    
    # Set global kill switch to ACTIVE
    await gate._ensure_kv_stores()
    await gate._global_kill_switch_kv.put("switch_all_execution", "active")
    
    # Test execution with active global kill switch
    context = ExecutionContext(
        action_type=ExecutionActionType.IDENTITY_CONTAINMENT_APPLY,
        tenant_id="tenant-123"
    )
    
    result = await gate.evaluate_execution(context)
    
    assert result.decision == GateDecision.DENY, f"Expected DENY, got {result.decision}"
    assert result.reason == DenialReason.GLOBAL_KILL_SWITCH_ACTIVE, f"Expected global kill switch, got {result.reason}"
    
    print("✓ Global kill switch correctly blocks execution")


async def test_execution_allowed_when_switches_inactive():
    """Test that execution is allowed when both switches are inactive"""
    print("Testing execution allowed when switches inactive...")
    
    mock_nats = MockNATSClient()
    gate = ExecutionGate(nats_client=mock_nats)
    
    # Set both kill switches to INACTIVE
    await gate._ensure_kv_stores()
    await gate._global_kill_switch_kv.put("switch_all_execution", "inactive")
    await gate._tenant_kill_switch_kv.put("tenant-123_switch_all_execution", "inactive")
    
    # Test execution with inactive switches
    context = ExecutionContext(
        action_type=ExecutionActionType.IDENTITY_CONTAINMENT_APPLY,
        tenant_id="tenant-123"
    )
    
    result = await gate.evaluate_execution(context)
    
    assert result.decision == GateDecision.ALLOW, f"Expected ALLOW, got {result.decision}"
    assert result.reason is None, f"Expected no reason for ALLOW, got {result.reason}"
    
    print("✓ Execution allowed when switches are inactive")


async def main():
    """Run core Gate 5 kill switch tests"""
    print("=" * 60)
    print("GATE 5: KILL SWITCH ENFORCEMENT TESTS")
    print("=" * 60)
    
    tests = [
        test_execution_gate_fail_closed,
        test_global_kill_switch_enforcement,
        test_execution_allowed_when_switches_inactive
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
    print(f"GATE 5 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ ALL KILL SWITCH TESTS PASSED")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
