"""
ExoArmur ADMO Approval Wiring Tests
Minimum viable authority wiring tests for SafetyGate → Approval flow
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi.testclient import TestClient

# Add src and spec to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec'))

from contracts.models_v1 import TelemetryEventV1, ExecutionIntentV1
from safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState
from execution.execution_kernel import ExecutionKernel
from control_plane.approval_service import ApprovalService
from audit.audit_logger import AuditLogger
from main import app


class TestApprovalWiring:
    """Approval wiring minimum viable tests"""
    
    @pytest.fixture(autouse=True)
    def setup_components(self):
        """Initialize components for testing"""
        import main
        main.initialize_components(None)
    
    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)
    
    @pytest.fixture
    def approval_service(self):
        """Approval service for testing"""
        import main
        return main.approval_service
    
    @pytest.fixture
    def safety_gate(self):
        """Safety gate for testing"""
        return SafetyGate()
    
    @pytest.fixture
    def execution_kernel(self):
        """Execution kernel for testing"""
        return ExecutionKernel()
    
    @pytest.fixture
    def audit_logger(self):
        """Audit logger for testing"""
        import main
        return main.audit_logger
    
    @pytest.fixture
    def sample_telemetry(self):
        """Sample telemetry event"""
        return TelemetryEventV1(
            schema_version="1.0.0",
            event_id="01J4NR5X9Z8GABCDEF12345678",  # Valid ULID
            tenant_id="test-tenant",
            cell_id="test-cell",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source={
                "kind": "edr",
                "name": "test",
                "host": "sensor-01",
                "sensor_id": "sensor-123"
            },
            event_type="process_execution",
            severity="medium",
            attributes={
                "process_name": "suspicious.exe",
                "pid": 1234,
                "command_line": "suspicious.exe --malicious"
            },
            correlation_id="test-corr-001",
            trace_id="test-trace-001"
        )
    
    @pytest.fixture
    def sample_local_decision(self):
        """Sample local decision"""
        from contracts.models_v1 import LocalDecisionV1
        return LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345679",  # Valid ULID
            tenant_id="test-tenant",
            cell_id="test-cell",
            subject={
                "subject_type": "host",
                "subject_id": "host-123"
            },
            classification="benign",
            severity="low",
            confidence=0.95,
            evidence_refs={
                "event_ids": ["event-1"],
                "belief_ids": ["belief-1"],
                "feature_hashes": ["hash-1"]
            },
            correlation_id="test-corr-001",
            trace_id="test-trace-001"
        )
    
    @pytest.fixture
    def sample_local_decision_suspicious(self):
        """Sample local decision for A1/A2/A3 actions"""
        from contracts.models_v1 import LocalDecisionV1
        return LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345680",  # Valid ULID
            tenant_id="test-tenant",
            cell_id="test-cell",
            subject={
                "subject_type": "host",
                "subject_id": "host-123"
            },
            classification="suspicious",
            severity="medium",
            confidence=0.75,
            evidence_refs={
                "event_ids": ["event-1"],
                "belief_ids": ["belief-1"],
                "feature_hashes": ["hash-1"]
            },
            correlation_id="test-corr-002",
            trace_id="test-trace-002"
        )
    
    @pytest.fixture
    def sample_collective_state(self):
        """Sample collective state"""
        from collective_confidence.aggregator import CollectiveState
        return CollectiveState(
            quorum_count=1,
            aggregate_score=0.75,
            belief_ids=["belief-001"],
            consensus_level="partial"
        )
    
    def test_ingest_returns_pending_when_require_human(self, client, sample_telemetry):
        """Test D1: When SafetyGate returns require_human, ingest returns PENDING and does NOT execute"""
        
        # Mock the safety gate to return require_human
        from unittest.mock import patch
        with patch('main.safety_gate.evaluate_safety') as mock_safety:
            mock_safety.return_value = SafetyVerdict(
                verdict="require_human",
                rationale="Trust too low for A2/A3 execution.",
                rule_ids=["SG-301"]
            )
            
            # Submit telemetry
            response = client.post("/v1/telemetry/ingest", json=sample_telemetry.model_dump())
            
            # Verify request was accepted
            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert data["correlation_id"] == sample_telemetry.correlation_id
            assert data["event_id"] == sample_telemetry.event_id
            assert data["belief_id"] is not None
            assert data["approval_id"] is not None
            assert data["approval_status"] == "PENDING"
            assert data["safety_verdict"] == "require_human"
    
    def test_ingest_returns_pending_when_require_quorum(self, client, sample_telemetry):
        """Test D1: When SafetyGate returns require_quorum, ingest returns PENDING and does NOT execute"""
        
        # Mock the safety gate to return require_quorum
        from unittest.mock import patch
        with patch('main.safety_gate.evaluate_safety') as mock_safety:
            mock_safety.return_value = SafetyVerdict(
                verdict="require_quorum",
                rationale="Policy not verified; degrade and require escalation for non-A0.",
                rule_ids=["SG-201"]
            )
            
            # Submit telemetry
            response = client.post("/v1/telemetry/ingest", json=sample_telemetry.model_dump())
            
            # Verify request was accepted
            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert data["correlation_id"] == sample_telemetry.correlation_id
            assert data["event_id"] == sample_telemetry.event_id
            assert data["belief_id"] is not None
            assert data["approval_id"] is not None
            assert data["approval_status"] == "PENDING"
            assert data["safety_verdict"] == "require_quorum"
    
    def test_approve_endpoint_changes_status_to_approved(self, client, approval_service):
        """Test D2: Approve endpoint changes status to APPROVED"""
        
        # Create approval request
        approval_id = approval_service.create_request(
            correlation_id="test-corr-001",
            trace_id="test-trace-001",
            tenant_id="test-tenant",
            cell_id="test-cell",
            idempotency_key="test-key-001",
            requested_action_class="A1_soft_containment",
            payload_ref={"test": "data"}
        )
        
        # Verify initial status is PENDING
        assert approval_service.get_status(approval_id) == "PENDING"
        
        # Approve the request via API
        response = client.post(
            f"/v1/approvals/{approval_id}/approve",
            json={"operator_id": "operator-001", "reason": "Approved for testing"}
        )
        
        # Verify approval was successful
        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == approval_id
        assert data["status"] == "APPROVED"
        
        # Verify status changed in service
        assert approval_service.get_status(approval_id) == "APPROVED"
    
    def test_deny_endpoint_changes_status_to_denied(self, client, approval_service):
        """Test D3: Deny endpoint changes status to DENIED"""
        
        # Create approval request
        approval_id = approval_service.create_request(
            correlation_id="test-corr-002",
            trace_id="test-trace-002",
            tenant_id="test-tenant",
            cell_id="test-cell",
            idempotency_key="test-key-002",
            requested_action_class="A2_hard_containment",
            payload_ref={"test": "data"}
        )
        
        # Verify initial status is PENDING
        assert approval_service.get_status(approval_id) == "PENDING"
        
        # Deny the request via API
        response = client.post(
            f"/v1/approvals/{approval_id}/deny",
            json={"operator_id": "operator-002", "reason": "Risk too high"}
        )
        
        # Verify denial was successful
        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == approval_id
        assert data["status"] == "DENIED"
        
        # Verify status changed in service
        assert approval_service.get_status(approval_id) == "DENIED"
    
    def test_deny_endpoint_requires_reason(self, client, approval_service):
        """Test D3: Deny endpoint requires reason and returns 422 if missing"""
        
        # Create approval request
        approval_id = approval_service.create_request(
            correlation_id="test-corr-003",
            trace_id="test-trace-003",
            tenant_id="test-tenant",
            cell_id="test-cell",
            idempotency_key="test-key-003",
            requested_action_class="A3_irreversible",
            payload_ref={"test": "data"}
        )
        
        # Try to deny without reason
        response = client.post(
            f"/v1/approvals/{approval_id}/deny",
            json={"operator_id": "operator-003"}
        )
        
        # Verify 422 error
        assert response.status_code == 422
        assert "Reason is required for denial" in response.json()["detail"]
        
        # Verify status is still PENDING
        assert approval_service.get_status(approval_id) == "PENDING"
    
    def test_get_approval_status_endpoint(self, client, approval_service):
        """Test GET /v1/approvals/{approval_id} endpoint"""
        
        # Create approval request
        approval_id = approval_service.create_request(
            correlation_id="test-corr-003",
            trace_id="test-trace-003",
            tenant_id="test-tenant",
            cell_id="test-cell",
            idempotency_key="test-key-003",
            requested_action_class="A3_irreversible",
            payload_ref={"test": "data"}
        )
        
        # Get approval status
        response = client.get(f"/v1/approvals/{approval_id}")
        
        # Verify status response
        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == approval_id
        assert data["status"] == "PENDING"
        assert data["requested_action_class"] == "A3_irreversible"
        assert data["correlation_id"] == "test-corr-003"
    
    def test_execution_kernel_blocks_without_approval(self, execution_kernel, sample_local_decision_suspicious):
        """Test D2: ExecutionKernel blocks A1/A2/A3 intents without approval_id"""
        
        # Enable V2 feature flags for this test
        from unittest.mock import patch
        from feature_flags import get_feature_flags
        
        with patch.object(get_feature_flags(), 'is_v2_operator_approval_required', return_value=True):
            # Create safety verdict that allows execution
            safety_verdict = SafetyVerdict(
                verdict="allow",
                rationale="Test approval",
                rule_ids=["SG-401"]
            )
            
            # Create execution intent without human_approval_id
            intent = execution_kernel.create_execution_intent(
                local_decision=sample_local_decision_suspicious,
                safety_verdict=safety_verdict,
                idempotency_key="test-key-004"
            )
            
            # Modify intent to be A1 (should be blocked without approval)
            intent.action_class = "A1_soft_containment"
            intent.safety_context["human_approval_id"] = None
            
            # Execute intent (should be blocked)
            result = asyncio.run(execution_kernel.execute_intent(intent))
            
            # Verify execution was blocked
            assert result is False
    
    def test_execution_kernel_allows_a0_without_approval(self, execution_kernel, sample_local_decision):
        """Test D2: ExecutionKernel allows A0 intents without approval_id"""
        
        # Create safety verdict that allows execution
        safety_verdict = SafetyVerdict(
            verdict="allow",
            rationale="Test approval",
            rule_ids=["SG-501"]
        )
        
        # Create execution intent without human_approval_id
        intent = execution_kernel.create_execution_intent(
            local_decision=sample_local_decision,
            safety_verdict=safety_verdict,
            idempotency_key="test-key-005"
        )
        
        # Intent should be A0 (allowed without approval)
        assert intent.action_class == "A0_observe"
        assert intent.safety_context["human_approval_id"] is None
        
        # Execute intent (should be allowed)
        result = asyncio.run(execution_kernel.execute_intent(intent))
        
        # Verify execution was allowed
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
