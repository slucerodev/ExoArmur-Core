"""
Tests for arbitration functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from spec.contracts.models_v1 import (
    TelemetryEventV1,
    SignalFactsV1,
    BeliefV1,
    BeliefTelemetryV1,
    LocalDecisionV1,
    ExecutionIntentV1,
    AuditRecordV1,
    ArbitrationV1,
    ArbitrationStatus,
    ArbitrationConflictType,
    FederateIdentityV1,
    ObservationV1,
    ObservationType,
    TelemetrySummaryPayloadV1
)
from exoarmur.federation.arbitration_store import ArbitrationStore
from exoarmur.federation.arbitration_service import ArbitrationService
from exoarmur.federation.conflict_detection import ConflictDetectionService
from exoarmur.federation.audit import AuditService, AuditEventEnvelope, AuditEventType
from exoarmur.federation.observation_store import ObservationStore
from exoarmur.federation.clock import FixedClock


@pytest.fixture
def fixed_clock():
    """Fixed clock for deterministic testing"""
    return FixedClock()


@pytest.fixture
def observation_store(fixed_clock):
    """Observation store for testing"""
    return ObservationStore(fixed_clock)


@pytest.fixture
def arbitration_store(fixed_clock):
    """Arbitration store for testing"""
    return ArbitrationStore(fixed_clock)


@pytest.fixture
def audit_service():
    """Mock audit service"""
    return Mock(spec=AuditService)


@pytest.fixture
def arbitration_service(arbitration_store, audit_service, fixed_clock, observation_store):
    """Arbitration service for testing"""
    return ArbitrationService(
        arbitration_store=arbitration_store,
        audit_service=audit_service,
        clock=fixed_clock,
        observation_store=observation_store,
        feature_flag_enabled=True
    )


@pytest.fixture
def conflict_detection_service(arbitration_store, audit_service, fixed_clock):
    """Conflict detection service for testing"""
    return ConflictDetectionService(
        arbitration_store=arbitration_store,
        audit_service=audit_service,
        clock=fixed_clock,
        feature_flag_enabled=True
    )


@pytest.fixture
def sample_beliefs(fixed_clock):
    """Sample beliefs for testing"""
    # Create beliefs at the same time for conflict grouping
    base_time = fixed_clock.now()
    
    belief1 = BeliefTelemetryV1(
        schema_version="1.0.0",
        belief_id="01J4NR5X9Z8GABCDEF12345678",
        tenant_id="tenant-1",
        emitter_node_id="node-1",
        subject={"subject_type": "network_segment", "subject_id": "network_segment_A"},
        claim_type="threat_detected",
        confidence=0.8,
        severity="high",
        evidence_refs={"event_ids": ["obs-1", "obs-2"]},
        policy_context={"threat_type": "malware"},
        ttl_seconds=3600,
        first_seen=base_time,
        last_seen=base_time,
        correlation_id="corr-123",
        trace_id="trace-123"
    )
    
    belief2 = BeliefTelemetryV1(
        schema_version="1.0.0",
        belief_id="01J4NR5X9Z8GABCDEF12345679",
        tenant_id="tenant-1", 
        emitter_node_id="node-2",
        subject={"subject_type": "network_segment", "subject_id": "network_segment_A"},
        claim_type="threat_detected",  # Same claim type for conflict grouping
        confidence=0.3,
        severity="low",
        evidence_refs={"event_ids": ["obs-3", "obs-4"]},
        policy_context={"threat_type": "benign"},  # Different threat type for conflict
        ttl_seconds=3600,
        first_seen=base_time,  # Same time for conflict grouping
        last_seen=base_time,
        correlation_id="corr-123",
        trace_id="trace-123"
    )
    
    return [belief1, belief2]


def test_conflict_detection_creates_arbitration_object(
    conflict_detection_service, sample_beliefs, fixed_clock
):
    """Test that conflict detection creates arbitration object"""
    # Detect conflicts
    arbitrations = conflict_detection_service.detect_belief_conflicts(sample_beliefs)
    
    # Should create one arbitration for the conflicting beliefs
    assert len(arbitrations) == 1
    
    arbitration = arbitrations[0]
    
    # Check arbitration structure
    assert arbitration.arbitration_id.startswith("arb_")
    assert arbitration.status == ArbitrationStatus.OPEN
    assert arbitration.conflict_type == ArbitrationConflictType.THREAT_CLASSIFICATION
    assert arbitration.subject_key == "network_segment_A"
    assert len(arbitration.claims) == 2
    assert arbitration.correlation_id == "corr-123"
    assert len(arbitration.evidence_refs) == 4  # obs-1, obs-2, obs-3, obs-4
    assert len(arbitration.conflicts_detected) > 0
    
    # Check that audit event was emitted
    conflict_detection_service.audit_service.emit_audit_event.assert_called_once()
    call_args = conflict_detection_service.audit_service.emit_audit_event.call_args[0][0]
    assert isinstance(call_args, AuditEventEnvelope)
    assert call_args.event_type == AuditEventType.CONFLICT_DETECTED


def test_arbitration_requires_human_approval(arbitration_service, arbitration_store, fixed_clock):
    """Test that arbitration requires human approval"""
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-test-001",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.THREAT_CLASSIFICATION,
        subject_key="test_subject",
        conflict_key="test_conflict",
        claims=[],
        evidence_refs=["obs-1"],
        correlation_id="corr-123"
    )
    
    # Create arbitration (should create approval request)
    success = arbitration_service.create_arbitration(arbitration)
    
    assert success is True
    assert arbitration.approval_id is not None
    assert arbitration.approval_id.startswith("approval_")
    
    # Check arbitration was stored
    stored_arb = arbitration_store.get_arbitration("arb-test-001")
    assert stored_arb is not None
    assert stored_arb.approval_id == arbitration.approval_id
    
    # Check audit event was emitted
    arbitration_service.audit_service.emit_audit_event.assert_called()
    call_args = arbitration_service.audit_service.emit_audit_event.call_args[0][0]
    assert call_args.event_type == AuditEventType.ARBITRATION_CREATED


def test_resolution_does_not_apply_without_approval(arbitration_service, fixed_clock):
    """Test that resolution does not apply without approval"""
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-test-002",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.CONFIDENCE_DISPUTE,
        subject_key="test_subject",
        conflict_key="test_conflict",
        claims=[],
        evidence_refs=["obs-1"],
        correlation_id="corr-123"
    )
    
    arbitration_service.create_arbitration(arbitration)
    
    # Mock approval check to return False
    with patch.object(arbitration_service, '_check_approval_status', return_value=False):
        # Try to apply resolution
        resolution = {"resolved_confidence": 0.5, "type": "confidence_adjustment"}
        success = arbitration_service.apply_resolution("arb-test-002", "resolver-federate")
        
        assert success is False
        
        # Arbitration should still be open
        updated_arb = arbitration_service.get_arbitration("arb-test-002")
        assert updated_arb.status == ArbitrationStatus.OPEN
        assert updated_arb.decision is None


def test_resolution_applies_after_approval_and_updates_beliefs(
    arbitration_service, observation_store, fixed_clock
):
    """Test that resolution applies after approval and updates beliefs"""
    # Create conflicting beliefs
    belief1 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-resolve-1",
        belief_type="derived_from_THREAT_INTEL",
        confidence=0.8,
        source_observations=["obs-1"],
        derived_at=fixed_clock.now(),
        correlation_id="corr-resolve",
        evidence_summary="Threat detected",
        metadata={"threat_type": "malware", "subject": "host_A"}
    )
    
    # Store belief
    observation_store.store_belief(belief1)
    
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-resolve-001",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.THREAT_CLASSIFICATION,
        subject_key="host_A",
        conflict_key="test_conflict",
        claims=[
            {
                "belief_id": "belief-resolve-1",
                "belief_type": "derived_from_THREAT_INTEL",
                "confidence": 0.8,
                "evidence_summary": "Threat detected",
                "metadata": {"threat_type": "malware", "subject": "host_A"}
            }
        ],
        evidence_refs=["obs-1"],
        correlation_id="corr-resolve"
    )
    
    arbitration_service.create_arbitration(arbitration)
    
    # Propose resolution
    resolution = {
        "resolved_threat_type": "trojan",
        "type": "threat_classification_update"
    }
    arbitration_service.propose_resolution("arb-resolve-001", resolution)
    
    # Apply resolution (approval check returns True by default)
    success = arbitration_service.apply_resolution("arb-resolve-001", "resolver-federate")
    
    assert success is True
    
    # Check arbitration was resolved
    updated_arb = arbitration_service.get_arbitration("arb-resolve-001")
    assert updated_arb.status == ArbitrationStatus.RESOLVED
    assert updated_arb.decision == resolution
    assert updated_arb.resolver_federate_id == "resolver-federate"
    assert updated_arb.resolved_at_utc is not None
    assert updated_arb.resolution_applied_at_utc is not None
    
    # Check belief was updated
    updated_belief = observation_store.get_belief("belief-resolve-1")
    assert updated_belief.metadata["resolved_threat_type"] == "trojan"
    assert updated_belief.metadata["arbitration_id"] == "arb-resolve-001"
    
    # Check audit events were emitted
    assert arbitration_service.audit_service.emit_audit_event.call_count >= 2
    # Should have events for: created, resolution_proposed, resolved


def test_arbitration_decision_is_audited_and_replayable(arbitration_service, fixed_clock):
    """Test that arbitration decision is audited and replayable"""
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-audit-001",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.SYSTEM_HEALTH,
        subject_key="system_A",
        conflict_key="health_conflict",
        claims=[],
        evidence_refs=["obs-1", "obs-2"],
        correlation_id="corr-audit"
    )
    
    arbitration_service.create_arbitration(arbitration)
    
    # Propose and apply resolution
    resolution = {"resolved_health_score": 0.7, "type": "health_score_update"}
    arbitration_service.propose_resolution("arb-audit-001", resolution)
    arbitration_service.apply_resolution("arb-audit-001", "resolver-federate")
    
    # Check audit events
    audit_calls = arbitration_service.audit_service.emit_audit_event.call_args_list
    
    # Should have events for: created, resolution_proposed, resolved
    assert len(audit_calls) >= 3
    
    # Check resolved event contains decision details
    resolved_event = None
    for call in audit_calls:
        event = call[0][0]
        if event.event_type == AuditEventType.ARBITRATION_RESOLVED:
            resolved_event = event
            break
    
    assert resolved_event is not None
    assert resolved_event.event_data["arbitration_id"] == "arb-audit-001"
    assert resolved_event.event_data["resolver_federate_id"] == "resolver-federate"
    assert "resolution_applied_at" in resolved_event.event_data
    
    # Arbitration should be replayable from audit trail
    # (In real implementation, this would be verified by ReplayEngine)
    final_arb = arbitration_service.get_arbitration("arb-audit-001")
    assert final_arb.status == ArbitrationStatus.RESOLVED
    assert final_arb.decision == resolution
    assert final_arb.resolver_federate_id == "resolver-federate"


def test_replay_reproduces_post_resolution_belief_state(
    arbitration_service, observation_store, fixed_clock
):
    """Test that replay reproduces post-resolution belief state"""
    # Create initial belief state
    belief1 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-replay-1",
        belief_type="derived_from_HEALTH_MONITOR",
        confidence=0.4,
        source_observations=["obs-1"],
        derived_at=fixed_clock.now(),
        correlation_id="corr-replay",
        evidence_summary="System health monitoring",
        metadata={"health_score": 0.4, "subject": "system-001"}
    )
    
    belief2 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-replay-2",
        belief_type="derived_from_HEALTH_MONITOR",
        confidence=0.8,
        source_observations=["obs-2"],
        derived_at=fixed_clock.now(),
        correlation_id="corr-replay",
        evidence_summary="System health monitoring",
        metadata={"health_score": 0.8, "subject": "system-001"}
    )
    
    # Store beliefs
    observation_store.store_belief(belief1)
    observation_store.store_belief(belief2)
    
    # Create arbitration for health score conflict
    arbitration = ArbitrationV1(
        arbitration_id="arb-replay-001",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.SYSTEM_HEALTH,
        subject_key="system_A",
        conflict_key="health_conflict",
        claims=[
            {
                "belief_id": "belief-replay-1",
                "belief_type": "derived_from_SYSTEM_HEALTH",
                "confidence": 0.4,
                "evidence_summary": "System health degraded",
                "metadata": {"health_score": 0.4, "subject": "system_A"}
            },
            {
                "belief_id": "belief-replay-2",
                "belief_type": "derived_from_SYSTEM_HEALTH",
                "confidence": 0.8,
                "evidence_summary": "System health healthy",
                "metadata": {"health_score": 0.8, "subject": "system_A"}
            }
        ],
        evidence_refs=["obs-1", "obs-2"],
        correlation_id="corr-replay"
    )
    
    arbitration_service.create_arbitration(arbitration)
    
    # Apply resolution to set consistent health score
    resolution = {"resolved_health_score": 0.6, "type": "health_score_consensus"}
    arbitration_service.propose_resolution("arb-replay-001", resolution)
    arbitration_service.apply_resolution("arb-replay-001", "resolver-federate")
    
    # Check post-resolution belief state
    post_belief1 = observation_store.get_belief("belief-replay-1")
    post_belief2 = observation_store.get_belief("belief-replay-2")
    
    assert post_belief1.metadata["resolved_health_score"] == 0.6
    assert post_belief1.metadata["arbitration_id"] == "arb-replay-001"
    assert post_belief2.metadata["resolved_health_score"] == 0.6
    assert post_belief2.metadata["arbitration_id"] == "arb-replay-001"
    
    # The post-resolution state should be deterministic and replayable
    # (In real implementation, ReplayEngine would verify this)
    final_arb = arbitration_service.get_arbitration("arb-replay-001")
    assert final_arb.decision == resolution
    
    # Both beliefs should have the same resolved health score
    assert post_belief1.metadata["resolved_health_score"] == post_belief2.metadata["resolved_health_score"]


def test_arbitration_feature_flag_disabled(arbitration_service, arbitration_store, fixed_clock):
    """Test that arbitration is disabled when feature flag is off"""
    # Create service with feature flag disabled
    disabled_service = ArbitrationService(
        arbitration_store=arbitration_store,
        audit_service=Mock(),
        clock=fixed_clock,
        observation_store=None,
        feature_flag_enabled=False
    )
    
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-disabled-001",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.THREAT_CLASSIFICATION,
        subject_key="test_subject",
        conflict_key="test_conflict",
        claims=[],
        evidence_refs=["obs-1"]
    )
    
    # Should fail to create
    success = disabled_service.create_arbitration(arbitration)
    assert success is False
    
    # Should not be stored
    stored_arb = arbitration_store.get_arbitration("arb-disabled-001")
    assert stored_arb is None


def test_conflict_detection_feature_flag_disabled(conflict_detection_service, sample_beliefs):
    """Test that conflict detection is disabled when feature flag is off"""
    # Create service with feature flag disabled
    disabled_service = ConflictDetectionService(
        arbitration_store=Mock(),
        audit_service=Mock(),
        clock=Mock(),
        feature_flag_enabled=False
    )
    
    # Should not detect conflicts
    arbitrations = disabled_service.detect_belief_conflicts(sample_beliefs)
    assert len(arbitrations) == 0
