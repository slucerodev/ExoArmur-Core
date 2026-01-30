"""
Tests for intent freezing and approval binding
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timezone
from unittest.mock import patch

# Add src to path

from fastapi.testclient import TestClient
from main import app
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.control_plane.intent_store import IntentStore
from safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState
from execution.execution_kernel import ExecutionKernel
from spec.contracts.models_v1 import TelemetryEventV1, LocalDecisionV1


class TestIntentFreezeBinding:
    """Tests for intent freezing and approval binding"""
    
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
        """Sample local decision for A1 action"""
        return LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345679",  # Valid ULID
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
            correlation_id="test-corr-001",
            trace_id="test-trace-001"
        )
    
    def test_require_human_freezes_intent_and_binds_approval(self, client, sample_telemetry):
        """Test that require_human verdict freezes intent and binds approval"""
        import main
        
        # Mock the safety gate to return require_human
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
            assert data["approval_id"] is not None
            assert data["approval_status"] == "PENDING"
            assert data["safety_verdict"] == "require_human"
            
            approval_id = data["approval_id"]
            
            # Assert approval service has a record with bound intent
            approval_details = main.approval_service.get_approval_details(approval_id)
            assert approval_details is not None
            assert approval_details.bound_intent_id is not None
            assert approval_details.bound_idempotency_key is not None
            assert approval_details.bound_intent_hash is not None
            
            # Assert intent store can return frozen intent
            frozen_intent = main.intent_store.get_intent_by_approval_id(approval_id)
            assert frozen_intent is not None
            assert frozen_intent.intent_id == approval_details.bound_intent_id
            assert frozen_intent.idempotency_key == approval_details.bound_idempotency_key
    
    def test_execution_blocked_until_approved(self, sample_local_decision):
        """Test that execution is blocked until approval is granted"""
        import main
        
        # Enable V2 feature flags for this test
        from unittest.mock import patch
        from feature_flags import get_feature_flags
        
        with patch.object(get_feature_flags(), 'is_v2_operator_approval_required', return_value=True):
            # Create execution kernel with services
            execution_kernel = ExecutionKernel(
                nats_client=None,
                approval_service=main.approval_service,
                intent_store=main.intent_store
            )
            
            # Create safety verdict that would allow execution
            safety_verdict = SafetyVerdict(
                verdict="allow",
                rationale="Test approval",
                rule_ids=["SG-401"]
            )
            
            # Create execution intent
            intent = execution_kernel.create_execution_intent(
                local_decision=sample_local_decision,
                safety_verdict=safety_verdict,
                idempotency_identifier="test-key-001"
            )
            
            # Modify intent to be A1 (requires approval)
            intent.action_class = "A1_soft_containment"
            
            # Execute intent (should be blocked without approval)
            result = asyncio.run(execution_kernel.execute_intent(intent))
            
            # Verify execution was blocked
            assert result is False
            
            # Create approval request
            approval_id = main.approval_service.create_request(
                correlation_id=intent.correlation_id,
                trace_id=intent.trace_id,
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
                idempotency_key=intent.idempotency_key,
                requested_action_class=intent.action_class,
                payload_ref={"test": "data"}
            )
        
            # Bind and freeze intent
            intent_hash = main.intent_store.compute_intent_hash(intent)
            main.approval_service.bind_intent(approval_id, intent.intent_id, intent.idempotency_key, intent_hash)
            main.intent_store.freeze_intent(approval_id, intent)
            
            # Set approval_id in intent but status is PENDING
            intent.safety_context["human_approval_id"] = approval_id
            
            # Execute intent (should be blocked due to PENDING status)
            result = asyncio.run(execution_kernel.execute_intent(intent))
            assert result is False
    
    def test_execution_allowed_after_approved_and_matches_binding(self, sample_local_decision):
        """Test that execution is allowed after approval and binding matches"""
        import main
        
        # Create execution kernel with services
        execution_kernel = ExecutionKernel(
            nats_client=None,
            approval_service=main.approval_service,
            intent_store=main.intent_store
        )
        
        # Create safety verdict that would allow execution
        safety_verdict = SafetyVerdict(
            verdict="allow",
            rationale="Test approval",
            rule_ids=["SG-401"]
        )
        
        # Create execution intent
        intent = execution_kernel.create_execution_intent(
            local_decision=sample_local_decision,
            safety_verdict=safety_verdict,
            idempotency_identifier="test-key-002"
        )
        
        # Modify intent to be A1 (requires approval)
        intent.action_class = "A1_soft_containment"
        
        # Create approval request and freeze intent
        approval_id = main.approval_service.create_request(
            correlation_id="test-corr-002",
            trace_id="test-trace-002",
            tenant_id="test-tenant",
            cell_id="test-cell",
            idempotency_key="test-key-002",
            requested_action_class="A1_soft_containment",
            payload_ref={"test": "data"}
        )
        
        # Set approval_id in intent BEFORE hashing
        intent.safety_context["human_approval_id"] = approval_id
        
        # Bind and freeze intent
        intent_hash = main.intent_store.compute_intent_hash(intent)
        main.approval_service.bind_intent(approval_id, intent.intent_id, intent.idempotency_key, intent_hash)
        main.intent_store.freeze_intent(approval_id, intent)
        
        # Approve the request
        main.approval_service.approve(approval_id, "operator-001")
        
        # Execute intent (should be allowed)
        result = asyncio.run(execution_kernel.execute_intent(intent))
        assert result is True
    
    def test_execution_blocked_on_binding_mismatch(self, sample_local_decision):
        """Test that execution is blocked on binding mismatch"""
        import main
        
        # Enable V2 feature flags for this test
        from unittest.mock import patch
        from feature_flags import get_feature_flags
        
        with patch.object(get_feature_flags(), 'is_v2_operator_approval_required', return_value=True):
            # Create execution kernel with services
            execution_kernel = ExecutionKernel(
                nats_client=None,
                approval_service=main.approval_service,
                intent_store=main.intent_store
            )
            
            # Create safety verdict that would allow execution
            safety_verdict = SafetyVerdict(
                verdict="allow",
                rationale="Test approval",
                rule_ids=["SG-401"]
            )
            
            # Create execution intent
            intent = execution_kernel.create_execution_intent(
                local_decision=sample_local_decision,
                safety_verdict=safety_verdict,
                idempotency_identifier="test-key-003"
            )
            
            # Modify intent to be A1 (requires approval)
            intent.action_class = "A1_soft_containment"
            
            # Create approval request and freeze intent
            approval_id = main.approval_service.create_request(
                correlation_id="test-corr-003",
                trace_id="test-trace-003",
                tenant_id="test-tenant",
                cell_id="test-cell",
                idempotency_key="test-key-003",
                requested_action_class="A1_soft_containment",
                payload_ref={"test": "data"}
            )
            
            # Set approval_id in intent BEFORE hashing
            intent.safety_context["human_approval_id"] = approval_id
            
            # Bind and freeze intent
            intent_hash = main.intent_store.compute_intent_hash(intent)
            main.approval_service.bind_intent(approval_id, intent.intent_id, intent.idempotency_key, intent_hash)
            main.intent_store.freeze_intent(approval_id, intent)
            
            # Approve the request
            main.approval_service.approve(approval_id, "operator-001")
            
            # Modify intent to create binding mismatch (change idempotency_key)
            intent.idempotency_key = "different-key"
            
            # Execute intent (should be blocked due to binding mismatch)
            result = asyncio.run(execution_kernel.execute_intent(intent))
            assert result is False
