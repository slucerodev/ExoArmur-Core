"""
Tests for ExoArmur ADMO V2 Restrained Autonomy Pipeline

These tests verify the minimal V2 capability slice:
- Feature flag enforcement (V2 disabled = no action)
- Operator approval workflow (approve/deny/refuse)
- Deterministic audit and replay
- Idempotency and safety constraints
- Boundary gate compatibility
"""

import pytest
import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Dict, Any

from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, ExecutionIntentV1, AuditRecordV1
from exoarmur.v2_restrained_autonomy import (
    RestrainedAutonomyPipeline,
    RestrainedAutonomyConfig,
    ActionOutcome,
    MockActionExecutor
)
from exoarmur.feature_flags import FeatureFlagContext, get_feature_flags
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.audit.audit_logger import AuditLogger

def create_mock_audit_record(audit_id: str = "audit-001") -> Mock:
    """Create a mock audit record for testing"""
    mock_record = Mock(spec=AuditRecordV1)
    mock_record.audit_id = audit_id
    return mock_record


@pytest.fixture
def sample_telemetry_event():
    """Create a sample telemetry event for testing"""
    return TelemetryEventV1(
        schema_version="1.0.0",
        event_id="01J4NR5X9Z8GABCDEF12345678",  # Valid ULID
        tenant_id="test_tenant",
        cell_id="cell-test-01",
        observed_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        source={
            "kind": "edr",
            "name": "test_edr",
            "host": "sensor-01",
            "sensor_id": "sensor-123"
        },
        event_type="suspicious_process",
        severity="high",
        attributes={
            "endpoint_id": "endpoint-test-001",
            "process_name": "malware.exe",
            "process_path": "/tmp/malware.exe"
        },
        entity_refs={
            "host": "host-test-001",
            "user": "user-test-001"
        },
        correlation_id="test-correlation-001",
        trace_id="test-trace-001"
    )


@pytest.fixture
def feature_flag_context():
    """Create feature flag context for testing"""
    return FeatureFlagContext(
        cell_id="cell-test-01",
        tenant_id="test_tenant",
        environment="test"
    )


@pytest.fixture
def pipeline_config():
    """Create pipeline configuration for testing"""
    return RestrainedAutonomyConfig(
        enabled=True,
        require_approval_for_A3=True,
        deterministic_seed="test-seed-12345"
    )


@pytest.fixture
def mock_approval_service():
    """Create mock approval service"""
    return Mock(spec=ApprovalService)


@pytest.fixture
def mock_audit_logger():
    """Create mock audit logger"""
    return Mock(spec=AuditLogger)


@pytest.fixture
def mock_action_executor():
    """Create mock action executor"""
    return Mock(spec=MockActionExecutor)


@pytest.fixture
def pipeline(pipeline_config, mock_approval_service, mock_audit_logger, mock_action_executor):
    """Create pipeline instance for testing"""
    return RestrainedAutonomyPipeline(
        config=pipeline_config,
        approval_service=mock_approval_service,
        audit_logger=mock_audit_logger,
        action_executor=mock_action_executor
    )


class TestFeatureFlagEnforcement:
    """Test feature flag enforcement"""
    
    @pytest.mark.sensitive
    def test_v2_disabled_refuses_action(self, pipeline, sample_telemetry_event, feature_flag_context):
        """Test that pipeline refuses action when V2 flags are disabled"""
        # Mock feature flags to return disabled
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=False):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=False):
                
                result = asyncio.run(pipeline.process_event_to_action(sample_telemetry_event))
                
                assert result.action_taken is False
                assert "V2 restrained autonomy pipeline is disabled" in result.refusal_reason
                assert result.approval_id is None
                assert result.execution_id is None
    
    @pytest.mark.sensitive
    def test_partial_v2_enabled_refuses_action(self, pipeline, sample_telemetry_event, feature_flag_context):
        """Test that pipeline refuses action when only some V2 flags are enabled"""
        # Control plane enabled but approval required disabled
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=False):
                
                result = asyncio.run(pipeline.process_event_to_action(sample_telemetry_event))
                
                assert result.action_taken is False
                assert result.refusal_reason is not None
    
    @pytest.mark.sensitive
    def test_v2_enabled_allows_processing(self, pipeline, sample_telemetry_event, feature_flag_context):
        """Test that pipeline allows processing when all V2 flags are enabled"""
        # Mock all required services
        pipeline.approval_service.create_request.return_value = "test-approval-001"
        pipeline.approval_service.get_approval_details.return_value = Mock(
            status="PENDING",
            requested_action_class="A2_hard_containment"
        )
        pipeline.action_executor.has_executed_recently.return_value = False
        pipeline.action_executor.execute_isolate_endpoint.return_value = {
            "execution_id": "exec-001",
            "action_type": "isolate_endpoint",
            "endpoint_id": "endpoint-test-001"
        }
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = asyncio.run(pipeline.process_event_to_action(
                    sample_telemetry_event,
                    operator_decision="approve",
                    operator_id="operator-001"
                ))
                
                # Should successfully execute action with operator approval
                assert result.action_taken is True
                assert result.refusal_reason is None
                assert result.execution_id == "exec-001"


class TestOperatorApprovalWorkflow:
    """Test operator approval workflow"""
    
    @pytest.mark.sensitive
    async def test_approval_request_created(self, pipeline, sample_telemetry_event):
        """Test that approval request is created for A2 actions"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = await pipeline.process_event_to_action(sample_telemetry_event)
                
                # Should create approval request
                pipeline.approval_service.create_request.assert_called_once()
                assert result.approval_id == "approval-001"
                assert result.action_taken is False  # No operator decision provided
                assert "Operator approval required" in result.refusal_reason
    
    @pytest.mark.sensitive
    async def test_operator_approves_action_executed(self, pipeline, sample_telemetry_event):
        """Test that action executes when operator approves"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.approval_service.approve.return_value = "APPROVED"
        pipeline.action_executor.has_executed_recently.return_value = False
        pipeline.action_executor.execute_isolate_endpoint.return_value = {
            "execution_id": "exec-001",
            "action_type": "isolate_endpoint",
            "endpoint_id": "endpoint-test-001"
        }
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = await pipeline.process_event_to_action(
                    sample_telemetry_event,
                    operator_decision="approve",
                    operator_id="operator-001"
                )
                
                assert result.action_taken is True
                assert result.execution_id == "exec-001"
                assert result.approval_id == "approval-001"
                assert result.refusal_reason is None
                
                # Verify approval was granted
                pipeline.approval_service.approve.assert_called_once_with("approval-001", "operator-001")
                
                # Verify action was executed
                pipeline.action_executor.execute_isolate_endpoint.assert_called_once()
    
    @pytest.mark.sensitive
    async def test_operator_denies_action_refused(self, pipeline, sample_telemetry_event):
        """Test that action is refused when operator denies"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.approval_service.deny.return_value = "DENIED"
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = await pipeline.process_event_to_action(
                    sample_telemetry_event,
                    operator_decision="deny",
                    operator_id="operator-001"
                )
                
                assert result.action_taken is False
                assert result.approval_id == "approval-001"
                assert "Operator approval denied" in result.refusal_reason
                assert result.execution_id is None
                
                # Verify approval was denied
                pipeline.approval_service.deny.assert_called_once_with(
                    "approval-001", "operator-001", "Operator denied in demo"
                )
                
                # Verify action was NOT executed
                pipeline.action_executor.execute_isolate_endpoint.assert_not_called()


class TestDeterministicAuditAndReplay:
    """Test deterministic audit and replay functionality"""
    
    @pytest.mark.sensitive
    async def test_audit_events_emitted(self, pipeline, sample_telemetry_event):
        """Test that audit events are emitted for each step"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        
        # Create mock audit record
        mock_audit_record = Mock(spec=AuditRecordV1)
        mock_audit_record.audit_id = "audit-001"
        pipeline.audit_logger.record_audit.return_value = mock_audit_record
        pipeline.audit_logger.get_records_by_correlation.return_value = []
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                await pipeline.process_event_to_action(sample_telemetry_event)
                
                # Verify audit events were recorded
                assert pipeline.audit_logger.record_audit.call_count >= 3  # At least: belief, intent, approval
    
    @pytest.mark.sensitive
    async def test_deterministic_id_generation(self, pipeline):
        """Test that IDs are deterministic with same seed"""
        seed_data = {"test": "data", "number": 42}
        
        id1 = pipeline.create_deterministic_id(seed_data)
        id2 = pipeline.create_deterministic_id(seed_data)
        
        assert id1 == id2  # Should be identical
        assert id1.startswith("det-")  # Should have deterministic prefix
        
        # Different seed should produce different ID
        different_seed = {"test": "data", "number": 43}
        id3 = pipeline.create_deterministic_id(different_seed)
        assert id1 != id3
    
    @pytest.mark.sensitive
    def test_replay_audit_stream(self, pipeline):
        """Test audit stream replay functionality"""
        # Mock audit records
        mock_records = [
            Mock(
                event_kind="belief_created",
                recorded_at=datetime.now(timezone.utc),
                payload_ref={"kind": "inline", "ref": json.dumps({"belief_id": "belief-001"})}
            ),
            Mock(
                event_kind="approval_requested",
                recorded_at=datetime.now(timezone.utc),
                payload_ref={"kind": "inline", "ref": json.dumps({"approval_id": "approval-001"})}
            ),
            Mock(
                event_kind="approval_denied",
                recorded_at=datetime.now(timezone.utc),
                payload_ref={"kind": "inline", "ref": json.dumps({"reason": "Operator denied"})}
            )
        ]
        
        pipeline.audit_logger.get_records_by_correlation.return_value = mock_records
        pipeline.audit_logger.get_audit_records.return_value = mock_records
        
        replay_result = pipeline.replay_audit_stream("test-stream-id")
        
        assert replay_result["audit_stream_id"] == "test-stream-id"
        assert len(replay_result["replay_timeline"]) == 3
        assert replay_result["final_outcome"] == "approval_denied"
        assert "deterministic_hash" in replay_result
        
        # Verify timeline structure
        timeline = replay_result["replay_timeline"]
        assert timeline[0]["event_kind"] == "belief_created"
        assert timeline[1]["event_kind"] == "approval_requested"
        assert timeline[2]["event_kind"] == "approval_denied"


class TestIdempotencyAndSafety:
    """Test idempotency and safety constraints"""
    
    @pytest.mark.sensitive
    async def test_idempotency_check_prevents_duplicate_execution(self, pipeline, sample_telemetry_event):
        """Test that recent duplicate actions are refused"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.approval_service.approve.return_value = "APPROVED"
        pipeline.action_executor.has_executed_recently.return_value = True  # Recently executed
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = await pipeline.process_event_to_action(
                    sample_telemetry_event,
                    operator_decision="approve",
                    operator_id="operator-001"
                )
                
                assert result.action_taken is False
                assert "already executed recently" in result.refusal_reason
                assert result.approval_id == "approval-001"
                
                # Verify action was NOT executed due to idempotency check
                pipeline.action_executor.execute_isolate_endpoint.assert_not_called()
    
    @pytest.mark.sensitive
    async def test_action_execution_with_approval(self, pipeline, sample_telemetry_event):
        """Test that action executes when not recently executed and approved"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.approval_service.approve.return_value = "APPROVED"
        pipeline.action_executor.has_executed_recently.return_value = False  # Not recently executed
        pipeline.action_executor.execute_isolate_endpoint.return_value = {
            "execution_id": "exec-001",
            "action_type": "isolate_endpoint",
            "endpoint_id": "endpoint-test-001"
        }
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                result = await pipeline.process_event_to_action(
                    sample_telemetry_event,
                    operator_decision="approve",
                    operator_id="operator-001"
                )
                
                assert result.action_taken is True
                assert result.execution_id == "exec-001"
                
                # Verify action was executed
                pipeline.action_executor.execute_isolate_endpoint.assert_called_once_with(
                    "endpoint-test-001", "test-correlation-001", "approval-001"
                )


class TestMockActionExecutor:
    """Test mock action executor functionality"""
    
    def test_execute_isolate_endpoint_creates_record(self):
        """Test that mock executor creates execution record"""
        executor = MockActionExecutor()
        
        result = executor.execute_isolate_endpoint(
            "endpoint-001", "correlation-001", "approval-001"
        )
        
        assert result["execution_id"].startswith("exec-")
        assert result["action_type"] == "isolate_endpoint"
        assert result["endpoint_id"] == "endpoint-001"
        assert result["correlation_id"] == "correlation-001"
        assert result["approval_id"] == "approval-001"
        assert result["status"] == "completed"
        assert result["mock"] is True
        assert "executed_at" in result
    
    def test_has_executed_recently_false_initially(self):
        """Test that has_executed_recently returns False initially"""
        executor = MockActionExecutor()
        
        result = executor.has_executed_recently("endpoint-001", "correlation-001")
        assert result is False
    
    def test_has_executed_recently_true_after_execution(self):
        """Test that has_executed_recently returns True after execution"""
        executor = MockActionExecutor()
        
        # Execute action
        executor.execute_isolate_endpoint("endpoint-001", "correlation-001")
        
        # Check if recently executed
        result = executor.has_executed_recently("endpoint-001", "correlation-001")
        assert result is True
    
    def test_get_execution_record(self):
        """Test getting execution record by ID"""
        executor = MockActionExecutor()
        
        # Execute action
        result = executor.execute_isolate_endpoint("endpoint-001", "correlation-001")
        execution_id = result["execution_id"]
        
        # Get record
        record = executor.get_execution_record(execution_id)
        assert record is not None
        assert record["execution_id"] == execution_id
        
        # Non-existent record
        record = executor.get_execution_record("non-existent")
        assert record is None


class TestBoundaryGateCompatibility:
    """Test compatibility with boundary gate (sensitive tests)"""
    
    @pytest.mark.sensitive
    async def test_pipeline_respects_boundary_gate_constraints(self, pipeline, sample_telemetry_event):
        """Test that pipeline respects boundary gate safety constraints"""
        # Setup mocks to simulate boundary gate constraints
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                # Test without operator decision (should be refused by safety constraints)
                result = await pipeline.process_event_to_action(sample_telemetry_event)
                
                assert result.action_taken is False
                assert result.refusal_reason is not None
                assert "approval required" in result.refusal_reason.lower()
    
    @pytest.mark.sensitive
    def test_deterministic_behavior_across_runs(self, pipeline, sample_telemetry_event):
        """Test that behavior is deterministic across multiple runs"""
        # Test deterministic ID generation
        seed_data = {"correlation_id": "test-123", "event_kind": "belief_created"}
        
        # Generate multiple IDs with same seed
        ids = [pipeline.create_deterministic_id(seed_data) for _ in range(5)]
        
        # All should be identical
        assert all(id_val == ids[0] for id_val in ids)
        
        # Test with different seed
        different_seed = {"correlation_id": "test-456", "event_kind": "belief_created"}
        different_id = pipeline.create_deterministic_id(different_seed)
        
        assert different_id != ids[0]
    
    @pytest.mark.sensitive
    async def test_audit_trail_integrity(self, pipeline, sample_telemetry_event):
        """Test that audit trail maintains integrity"""
        # Setup mocks
        pipeline.approval_service.create_request.return_value = "approval-001"
        pipeline.approval_service.bind_intent.return_value = None
        pipeline.audit_logger.record_audit.return_value = create_mock_audit_record()
        
        audit_calls = []
        
        def capture_audit_call(event_kind, payload_ref, correlation_id, trace_id, tenant_id, cell_id, idempotency_key):
            mock_record = create_mock_audit_record()
            mock_record.event_kind = event_kind
            mock_record.correlation_id = correlation_id
            mock_record.trace_id = trace_id
            mock_record.tenant_id = tenant_id
            mock_record.cell_id = cell_id
            mock_record.idempotency_key = idempotency_key
            mock_record.recorded_at = datetime.now(timezone.utc)
            mock_record.payload_ref = payload_ref
            mock_record.hashes = {"sha256": "test-hash"}
            audit_calls.append(mock_record)
            return mock_record
        
        pipeline.audit_logger.record_audit.side_effect = capture_audit_call
        
        with patch.object(pipeline.feature_flags, 'is_v2_control_plane_enabled', return_value=True):
            with patch.object(pipeline.feature_flags, 'is_v2_operator_approval_required', return_value=True):
                
                await pipeline.process_event_to_action(sample_telemetry_event)
                
                # Verify audit trail structure
                assert len(audit_calls) >= 3
                
                # Check audit record structure
                for record in audit_calls:
                    assert hasattr(record, 'audit_id')
                    assert hasattr(record, 'event_kind')
                    assert hasattr(record, 'correlation_id')
                    assert hasattr(record, 'recorded_at')
                    assert hasattr(record, 'payload_ref')
                    assert hasattr(record, 'hashes')
                
                # Verify correlation ID consistency (all events should use the same audit_stream_id)
                correlation_ids = [record.correlation_id for record in audit_calls]
                # All correlation IDs should be the same (the audit_stream_id)
                assert len(set(correlation_ids)) == 1
                # The correlation ID should be a deterministic audit stream ID
                assert correlation_ids[0].startswith("det-")
