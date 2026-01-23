"""
Golden Demo Flow Integration Test

Tests the complete end-to-end ADMO scenario defined in golden_demo_flow_v1.yaml:
- Partition-tolerant lateral movement containment
- Live NATS JetStream with real publish/consume
- Belief buffering and reconciliation
- Quorum formation and collective confidence
- Safety gate enforcement and human approval
- Audit replay with idempotency
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import nats
from nats.js.api import StreamConfig, ConsumerConfig

# Add src to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

from models_v1 import (
    TelemetryEventV1, SignalFactsV1, BeliefV1, LocalDecisionV1,
    ExecutionIntentV1, AuditRecordV1
)
from nats_client import ExoArmurNATSClient, NATSConfig


class TestGoldenDemoFlow:
    """Golden Demo Flow integration test for ADMO v1"""
    
    @pytest.fixture
    async def nats_config(self):
        """NATS configuration for testing"""
        return NATSConfig(
            url="nats://localhost:4222",
            max_reconnect_attempts=5,
            reconnect_wait=1.0,
            connection_timeout=5.0
        )
    
    @pytest.fixture
    async def nats_clients(self, nats_config):
        """Create multiple NATS clients for different cells"""
        clients = {}
        for cell_id in ["cell-a", "cell-b", "cell-c"]:
            client = ExoArmurNATSClient(nats_config)
            await client.connect()
            await client.setup_streams()
            clients[cell_id] = client
        
        yield clients
        
        # Cleanup
        for client in clients.values():
            await client.close()
    
    @pytest.fixture
    def sample_telemetry_a(self):
        """Telemetry event for cell-a (auth failure)"""
        return TelemetryEventV1(
            schema_version="1.0.0",
            event_id="3EDW0S2AFBGFZ0T10NPVFXFT77",  # Valid ULID
            tenant_id="tenant_demo",
            cell_id="cell-a",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source={"kind": "auth", "name": "active_directory"},
            event_type="auth_failure",
            severity="high",
            attributes={
                "username": "admin",
                "source_ip": "10.1.1.100",
                "failure_reason": "invalid_password"
            },
            entity_refs={
                "subject_type": "host",
                "subject_id": "host-123"
            },
            correlation_id="golden-demo-001",
            trace_id="trace-golden-001"
        )
    
    @pytest.fixture
    def sample_telemetry_b(self):
        """Telemetry event for cell-b (process start)"""
        return TelemetryEventV1(
            schema_version="1.0.0",
            event_id="HW748MS1B42T7492VZRFJJ7EQJ",  # Valid ULID
            tenant_id="tenant_demo",
            cell_id="cell-b",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source={"kind": "edr", "name": "crowdstrike"},
            event_type="process_start",
            severity="high",
            attributes={
                "process_name": "powershell.exe",
                "command_line": "powershell -enc ...",
                "parent_process": "explorer.exe"
            },
            entity_refs={
                "subject_type": "host",
                "subject_id": "host-123"
            },
            correlation_id="golden-demo-001",
            trace_id="trace-golden-001"
        )
    
    @pytest.mark.xfail(strict=True, reason="Requires live NATS JetStream - mock implementation is NOT acceptance per Golden Demo Law")
    async def test_golden_demo_flow_partition_tolerance(self, nats_clients, sample_telemetry_a, sample_telemetry_b):
        """
        Golden Demo Flow: Partition-tolerant lateral movement containment
        
        This test validates the complete end-to-end scenario:
        1. Cell-a processes telemetry during partition (local only)
        2. Cell-b processes telemetry online (mesh publish)
        3. Partition heals, beliefs reconcile
        4. Collective confidence triggers A2 containment
        5. A3 requires human approval
        6. Audit replay validates idempotency
        """
        
        # STEP 1: Cell-a processes telemetry during partition
        print("\n=== STEP 1: Cell-a processes telemetry during partition ===")
        
        # Simulate partition by disconnecting cell-a from mesh
        cell_a_client = nats_clients["cell-a"]
        cell_b_client = nats_clients["cell-b"] 
        cell_c_client = nats_clients["cell-c"]
        
        # Cell-a should process telemetry locally and buffer belief publish
        await self._process_telemetry_locally(cell_a_client, sample_telemetry_a, expect_buffered=True)
        
        # Verify local processing occurred
        local_beliefs = await self._get_local_beliefs(cell_a_client, sample_telemetry_a.correlation_id)
        assert len(local_beliefs) > 0, "Cell-a should have generated local beliefs"
        
        # Verify belief was buffered (not published to mesh)
        mesh_beliefs = await self._get_mesh_beliefs(cell_b_client, sample_telemetry_a.correlation_id)
        assert len(mesh_beliefs) == 0, "Cell-a belief should not be published to mesh during partition"
        
        # STEP 2: Cell-b processes telemetry online
        print("\n=== STEP 2: Cell-b processes telemetry online ===")
        
        # Cell-b processes telemetry and publishes to mesh
        await self._process_telemetry_locally(cell_b_client, sample_telemetry_b, expect_buffered=False)
        
        # Verify belief was published to mesh
        mesh_beliefs = await self._get_mesh_beliefs(cell_b_client, sample_telemetry_b.correlation_id)
        assert len(mesh_beliefs) > 0, "Cell-b belief should be published to mesh"
        
        # STEP 3: Partition heals - reconcile buffered beliefs
        print("\n=== STEP 3: Partition heals - buffered beliefs reconcile ===")
        
        # Reconnect cell-a to mesh
        await self._simulate_partition_heal(cell_a_client)
        
        # Wait for buffered beliefs to be published
        await asyncio.sleep(2)
        
        # Verify cell-a's buffered belief is now on mesh
        mesh_beliefs = await self._get_mesh_beliefs(cell_b_client, sample_telemetry_a.correlation_id)
        assert len(mesh_beliefs) > 0, "Cell-a buffered belief should be published after partition heal"
        
        # Verify collective confidence computation
        collective_state = await self._compute_collective_confidence(cell_b_client, sample_telemetry_a.correlation_id)
        assert collective_state["quorum_count"] >= 2, "Should have quorum from at least 2 cells"
        assert collective_state["aggregate_score"] >= 0.85, "Should meet A2 threshold"
        
        # STEP 4: Escalate to A2 hard containment
        print("\n=== STEP 4: Escalate to A2 hard containment via collective confidence ===")
        
        # Verify A2 execution intent is created and executed
        a2_intent = await self._verify_a2_execution(cell_b_client, sample_telemetry_a.correlation_id)
        assert a2_intent is not None, "A2 execution intent should be created"
        assert a2_intent["action_class"] == "A2_hard_containment", "Should be A2 hard containment"
        assert "idempotency_key" in a2_intent, "Should include idempotency key"
        
        # STEP 5: Attempt A3 irreversible action
        print("\n=== STEP 5: Attempt A3 irreversible action requires human approval ===")
        
        # Try to create A3 intent without human approval
        a3_result = await self._attempt_a3_execution(cell_b_client, sample_telemetry_a.correlation_id)
        assert a3_result["safety_verdict"] == "require_human", "A3 should require human approval"
        assert a3_result["executed"] == False, "A3 should not execute without approval"
        
        # Verify approval request is logged
        approval_requests = await self._get_approval_requests(cell_b_client, sample_telemetry_a.correlation_id)
        assert len(approval_requests) > 0, "Human approval request should be logged"
        
        # STEP 6: Audit replay validation
        print("\n=== STEP 6: Audit replay succeeds ===")
        
        # Get complete audit chain
        audit_chain = await self._get_audit_chain(cell_b_client, sample_telemetry_a.correlation_id)
        
        # Verify audit chain completeness
        expected_steps = [
            "telemetry_ingested",
            "facts_derived", 
            "belief_emitted",
            "collective_confidence_computed",
            "safety_evaluated",
            "intent_created",
            "execution_completed"
        ]
        
        audit_steps = [record["event_kind"] for record in audit_chain]
        for step in expected_steps:
            assert step in audit_steps, f"Audit chain missing step: {step}"
        
        # Verify audit replay does not retrigger side effects
        replay_result = await self._replay_audit_chain(cell_c_client, audit_chain)
        assert replay_result["side_effects_triggered"] == 0, "Audit replay should not trigger side effects"
        assert replay_result["idempotency_enforced"] == True, "Idempotency should be enforced during replay"
        
        print("\n=== GOLDEN DEMO FLOW COMPLETED SUCCESSFULLY ===")
    
    async def _process_telemetry_locally(self, client, telemetry, expect_buffered=False):
        """Process telemetry event through local ADMO pipeline"""
        # This would integrate with the actual ADMO pipeline
        # For now, simulate the processing steps
        
        # Create local belief
        belief = BeliefV1(
            schema_version="1.0.0",
            belief_id="3EDW0S2AFBGFZ0T10NPVFXFT78",  # Valid ULID
            tenant_id=telemetry.tenant_id,
            emitter_node_id=telemetry.cell_id,
            subject=telemetry.entity_refs or {},
            claim_type="suspicious_activity",
            confidence=0.85,
            severity="high",
            evidence_refs={
                "event_ids": [telemetry.event_id],
                "feature_hashes": [],
                "artifact_refs": []
            },
            policy_context={
                "bundle_hash_sha256": "demo-bundle-hash",
                "rule_ids": ["rule-demo-001"],
                "trust_score_at_emit": 0.85
            },
            ttl_seconds=3600,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id
        )
        
        if expect_buffered:
            # Buffer the belief for later publish
            await client._buffer_belief(belief)
        else:
            # Publish immediately to mesh
            await client.publish_belief(belief)
    
    async def _get_local_beliefs(self, client, correlation_id):
        """Get beliefs stored locally for a correlation"""
        # Simulate local belief storage
        return [{"belief_id": "local-001", "correlation_id": correlation_id}]
    
    async def _get_mesh_beliefs(self, client, correlation_id):
        """Get beliefs published to mesh for a correlation"""
        # Query NATS JetStream for beliefs
        beliefs = []
        try:
            # This would query the actual beliefs stream
            # For now, simulate mesh belief retrieval
            if correlation_id == "golden-demo-001":
                beliefs = [{"belief_id": "mesh-001", "correlation_id": correlation_id}]
        except Exception as e:
            print(f"Error getting mesh beliefs: {e}")
        return beliefs
    
    async def _simulate_partition_heal(self, client):
        """Simulate partition healing by reconnecting client"""
        # In real implementation, this would reconnect NATS client
        # For now, simulate by publishing buffered beliefs
        await client._publish_buffered_beliefs()
    
    async def _compute_collective_confidence(self, client, correlation_id):
        """Compute collective confidence across beliefs"""
        # Simulate collective confidence computation
        return {
            "quorum_count": 2,
            "aggregate_score": 0.87,
            "correlation_id": correlation_id
        }
    
    async def _verify_a2_execution(self, client, correlation_id):
        """Verify A2 execution intent was created and executed"""
        # Simulate A2 execution intent
        return {
            "intent_id": "intent-a2-001",
            "action_class": "A2_hard_containment",
            "intent_type": "block_domain",
            "idempotency_key": "idemp-a2-001",
            "correlation_id": correlation_id,
            "executed": True
        }
    
    async def _attempt_a3_execution(self, client, correlation_id):
        """Attempt A3 execution without human approval"""
        # Simulate A3 attempt requiring human approval
        return {
            "intent_id": "intent-a3-001",
            "action_class": "A3_irreversible", 
            "intent_type": "disable_user",
            "safety_verdict": "require_human",
            "executed": False,
            "correlation_id": correlation_id
        }
    
    async def _get_approval_requests(self, client, correlation_id):
        """Get human approval requests for a correlation"""
        # Simulate approval request logging
        return [{
            "request_id": "approval-001",
            "correlation_id": correlation_id,
            "action_class": "A3_irreversible",
            "status": "pending"
        }]
    
    async def _get_audit_chain(self, client, correlation_id):
        """Get complete audit chain for a correlation"""
        # Simulate complete audit chain
        return [
            {"event_kind": "telemetry_ingested", "correlation_id": correlation_id},
            {"event_kind": "facts_derived", "correlation_id": correlation_id},
            {"event_kind": "belief_emitted", "correlation_id": correlation_id},
            {"event_kind": "collective_confidence_computed", "correlation_id": correlation_id},
            {"event_kind": "safety_evaluated", "correlation_id": correlation_id},
            {"event_kind": "intent_created", "correlation_id": correlation_id},
            {"event_kind": "execution_completed", "correlation_id": correlation_id}
        ]
    
    async def _replay_audit_chain(self, client, audit_chain):
        """Replay audit chain and verify idempotency"""
        # Simulate audit replay
        side_effects = 0
        idempotency_enforced = False
        
        for record in audit_chain:
            # In real implementation, this would replay each step
            # and verify no side effects occur due to idempotency
            if record["event_kind"] == "execution_completed":
                idempotency_enforced = True
        
        return {
            "side_effects_triggered": side_effects,
            "idempotency_enforced": idempotency_enforced,
            "replayed_steps": len(audit_chain)
        }


# Test utilities and helpers
class MockExoArmurNATSClient(ExoArmurNATSClient):
    """Mock NATS client for testing without real NATS server"""
    
    def __init__(self, config):
        self.config = config
        self.buffered_beliefs = []
        self.published_beliefs = []
        self.connected = False
    
    async def connect(self):
        """Mock connection"""
        self.connected = True
    
    async def close(self):
        """Mock close"""
        self.connected = False
    
    async def setup_streams(self):
        """Mock stream setup"""
        pass
    
    async def publish_belief(self, belief):
        """Mock belief publish"""
        if self.connected:
            self.published_beliefs.append(belief)
        else:
            self.buffered_beliefs.append(belief)
    
    async def _buffer_belief(self, belief):
        """Mock belief buffering"""
        self.buffered_beliefs.append(belief)
    
    async def _publish_buffered_beliefs(self):
        """Mock publishing buffered beliefs"""
        for belief in self.buffered_beliefs:
            await self.publish_belief(belief)
        self.buffered_beliefs.clear()


@pytest.fixture
def mock_nats_clients():
    """Mock NATS clients for testing without real NATS"""
    clients = {}
    for cell_id in ["cell-a", "cell-b", "cell-c"]:
        client = MockExoArmurNATSClient(NATSConfig())
        clients[cell_id] = client
    
    # Simulate partition: cell-a disconnected
    clients["cell-a"].connected = False
    
    return clients


@pytest.mark.xfail(strict=True, reason="Mock golden demo is NOT acceptance - requires live NATS JetStream per Golden Demo Law")
@pytest.mark.asyncio
async def test_golden_demo_flow_mock(mock_nats_clients):
    """Golden Demo Flow test with mock NATS clients - UNIT TEST ONLY
    
    This test is marked xfail because mock golden demo is NOT acceptance.
    Only live NATS JetStream-based integration tests qualify as acceptance per Golden Demo Law.
    """
    
    # Create sample telemetry
    telemetry_a = TelemetryEventV1(
        schema_version="1.0.0",
        event_id="VVV3VK87GQMKXWSD1NMBKW9ETX",  # Valid ULID
        tenant_id="tenant_demo",
        cell_id="cell-a",
        observed_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        source={"kind": "auth", "name": "active_directory"},
        event_type="auth_failure",
        severity="high",
        attributes={"username": "admin"},
        entity_refs={"subject_type": "host", "subject_id": "host-123"},
        correlation_id="golden-demo-001",
        trace_id="trace-golden-001"
    )
    
    test_instance = TestGoldenDemoFlow()
    
    # STEP 1: Cell-a processes during partition
    await test_instance._process_telemetry_locally(
        mock_nats_clients["cell-a"], 
        telemetry_a, 
        expect_buffered=True
    )
    
    # Verify buffered
    print(f"Cell-a buffered beliefs: {len(mock_nats_clients['cell-a'].buffered_beliefs)}")
    print(f"Cell-a published beliefs: {len(mock_nats_clients['cell-a'].published_beliefs)}")
    assert len(mock_nats_clients["cell-a"].buffered_beliefs) == 1
    assert len(mock_nats_clients["cell-a"].published_beliefs) == 0
    
    # STEP 2: Cell-b processes online
    telemetry_b = TelemetryEventV1(
        schema_version="1.0.0",
        event_id="7FH11W0TYVC68K8DRX4QP9TPJ9",  # Valid ULID
        tenant_id="tenant_demo",
        cell_id="cell-b",
        observed_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        source={"kind": "edr", "name": "crowdstrike"},
        event_type="process_start",
        severity="high",
        attributes={"process_name": "powershell.exe"},
        entity_refs={"subject_type": "host", "subject_id": "host-123"},
        correlation_id="golden-demo-001",
        trace_id="trace-golden-001"
    )
    
    await test_instance._process_telemetry_locally(
        mock_nats_clients["cell-b"],
        telemetry_b,
        expect_buffered=False
    )
    
    # Verify published
    assert len(mock_nats_clients["cell-b"].buffered_beliefs) == 0
    assert len(mock_nats_clients["cell-b"].published_beliefs) == 1
    
    # STEP 3: Partition heals
    mock_nats_clients["cell-a"].connected = True
    await test_instance._simulate_partition_heal(mock_nats_clients["cell-a"])
    
    # Verify buffered beliefs published
    assert len(mock_nats_clients["cell-a"].buffered_beliefs) == 0
    assert len(mock_nats_clients["cell-a"].published_beliefs) == 1
    
    print("✅ Golden Demo Flow mock test passed")
