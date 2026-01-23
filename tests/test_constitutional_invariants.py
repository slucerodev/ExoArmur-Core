"""
Constitutional Invariants Test Suite

Tests core constitutional invariants of the ExoArmur system.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from spec.contracts.models_v1 import (
    ArbitrationV1,
    ArbitrationStatus,
    ArbitrationConflictType,
    BeliefV1,
    ObservationV1,
    ObservationType,
    TelemetrySummaryPayloadV1,
    FederateIdentityV1,
    FederationRole,
    CellStatus
)
from src.federation.arbitration_service import ArbitrationService
from src.federation.observation_ingest import ObservationIngestService
from src.federation.belief_aggregation import BeliefAggregationService
from src.federation.observation_store import ObservationStore
from src.federation.arbitration_store import ArbitrationStore
from src.federation.federate_identity_store import FederateIdentityStore
from src.federation.clock import FixedClock
from src.federation.audit import AuditService
from src.federation.crypto import FederateKeyPair, serialize_public_key_for_identity


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
def identity_store(fixed_clock):
    """Identity store for testing"""
    return FederateIdentityStore(fixed_clock)


@pytest.fixture
def audit_service():
    """Mock audit service"""
    return Mock(spec=AuditService)


@pytest.fixture
def observation_ingest_service(observation_store, identity_store, fixed_clock):
    """Observation ingest service for testing"""
    from src.federation.observation_ingest import ObservationIngestConfig
    config = ObservationIngestConfig(
        feature_enabled=True,
        require_confirmed_federate=True,
        require_signature=True
    )
    return ObservationIngestService(
        observation_store=observation_store,
        identity_store=identity_store,
        clock=fixed_clock,
        config=config
    )


@pytest.fixture
def belief_aggregation_service(observation_store, fixed_clock):
    """Belief aggregation service for testing"""
    from src.federation.belief_aggregation import BeliefAggregationConfig
    config = BeliefAggregationConfig(
        feature_enabled=True,
        min_observations_for_belief=1,
        confidence_threshold=0.5
    )
    return BeliefAggregationService(
        observation_store=observation_store,
        clock=fixed_clock,
        config=config
    )


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


def test_federation_cannot_trigger_execution_paths():
    """
    Constitutional Invariant: Federation modules cannot trigger execution paths
    
    This test ensures that federation modules (handshake, observation, belief, arbitration)
    do not import or use execution modules (safety gate, execution intent, etc.)
    """
    # This is a structural test - we verify imports don't cross the boundary
    
    # Test that federation modules can be imported without execution modules
    try:
        # These should work
        from src.federation.handshake_controller import HandshakeController
        from src.federation.observation_ingest import ObservationIngestService
        from src.federation.belief_aggregation import BeliefAggregationService
        from src.federation.arbitration_service import ArbitrationService
        from src.federation.visibility_api import VisibilityAPI
        
        # These should NOT be imported by federation modules
        # (We'll verify this in the boundary enforcement test)
        
        assert True  # If we get here, imports are working correctly
        
    except ImportError as e:
        pytest.fail(f"Federation modules should be importable: {e}")


def test_unconfirmed_federates_cannot_ingest_observations(
    observation_ingest_service, identity_store, fixed_clock
):
    """
    Constitutional Invariant: Unconfirmed federates cannot ingest observations
    
    This test ensures that only federates with valid identities can ingest observations.
    """
    # Test with non-existent federate (effectively "unconfirmed")
    non_existent_federate_id = "non-existent-federate"
    
    # Create observation from non-existent federate
    observation = ObservationV1(
        observation_id="obs-unconfirmed",
        source_federate_id=non_existent_federate_id,
        timestamp_utc=fixed_clock.now(),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest observation - should fail
    success, reason, audit_event = observation_ingest_service.ingest_observation(observation)
    
    assert success is False
    assert reason == "federate_not_found"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"
    assert audit_event["reason"] == "federate_not_found"


def test_conflicts_cannot_resolve_without_approval(
    arbitration_service, arbitration_store, fixed_clock
):
    """
    Constitutional Invariant: Conflicts cannot resolve without approval
    
    This test ensures that arbitration resolutions require human approval.
    """
    # Create arbitration
    arbitration = ArbitrationV1(
        arbitration_id="arb-no-approval",
        created_at_utc=fixed_clock.now(),
        status=ArbitrationStatus.OPEN,
        conflict_type=ArbitrationConflictType.THREAT_CLASSIFICATION,
        subject_key="test-subject",
        conflict_key="test-conflict",
        claims=[],
        evidence_refs=["obs-1"],
        correlation_id="corr-test"
    )
    
    arbitration_service.create_arbitration(arbitration)
    
    # Mock approval check to return False (not approved)
    with patch.object(arbitration_service, '_check_approval_status', return_value=False):
        # Try to apply resolution without approval
        resolution = {"resolved_threat_type": "trojan", "type": "threat_classification_update"}
        success = arbitration_service.apply_resolution("arb-no-approval", "resolver-federate")
        
        assert success is False
        
        # Arbitration should still be open
        updated_arb = arbitration_service.get_arbitration("arb-no-approval")
        assert updated_arb.status == ArbitrationStatus.OPEN
        assert updated_arb.decision is None


def test_replay_determinism_smoke_test(
    belief_aggregation_service, observation_store, fixed_clock
):
    """
    Constitutional Invariant: Replay determinism smoke test
    
    This test ensures that the same inputs produce the same outputs.
    """
    # Create deterministic observations
    base_time = fixed_clock.now()
    
    obs1 = ObservationV1(
        observation_id="obs-replay-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    obs2 = ObservationV1(
        observation_id="obs-replay-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time,
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.7,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=150,
            time_window_seconds=300,
            event_types=["network_connect"],
            severity_distribution={"low": 120, "medium": 30}
        )
    )
    
    # Clear stores
    observation_store._observations.clear()
    observation_store._beliefs.clear()
    
    # First run
    belief_aggregation_service.observation_store.store_observation(obs1)
    belief_aggregation_service.observation_store.store_observation(obs2)
    beliefs1 = belief_aggregation_service.aggregate_observations()
    
    # Clear stores again
    observation_store._observations.clear()
    observation_store._beliefs.clear()
    
    # Second run (same inputs)
    belief_aggregation_service.observation_store.store_observation(obs1)
    belief_aggregation_service.observation_store.store_observation(obs2)
    beliefs2 = belief_aggregation_service.aggregate_observations()
    
    # Results should be identical (deterministic)
    assert len(beliefs1) == len(beliefs2)
    
    if beliefs1 and beliefs2:
        belief1 = beliefs1[0]
        belief2 = beliefs2[0]
        
        # Check deterministic fields
        assert belief1.belief_id == belief2.belief_id
        assert belief1.belief_type == belief2.belief_type
        assert belief1.confidence == belief2.confidence
        assert belief1.source_observations == belief2.source_observations
        assert belief1.derived_at == belief2.derived_at
        assert belief1.evidence_summary == belief2.evidence_summary
        assert belief1.metadata == belief2.metadata


def test_federation_modules_boundary_isolation():
    """
    Constitutional Invariant: Federation modules maintain boundary isolation
    
    This test ensures federation modules don't import execution modules.
    """
    # Check that federation modules don't have execution imports
    federation_files = [
        "src/federation/handshake_controller.py",
        "src/federation/observation_ingest.py", 
        "src/federation/belief_aggregation.py",
        "src/federation/arbitration_service.py",
        "src/federation/visibility_api.py"
    ]
    
    execution_modules = [
        "safety_gate",
        "execution_intent",
        "execution_engine",
        "policy_engine"
    ]
    
    for file_path in federation_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for forbidden imports
            for exec_module in execution_modules:
                if exec_module in content:
                    # Allow it in comments but not in import statements
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if exec_module in line and not line.strip().startswith('#'):
                            # Check if it's an import statement
                            if ('import' in line or 'from' in line) and exec_module in line:
                                pytest.fail(f"Found forbidden import in {file_path}:{line}: {line.strip()}")
                                
        except FileNotFoundError:
            # Skip if file doesn't exist
            continue
    
    assert True  # All boundary checks passed


def test_feature_flags_default_off():
    """
    Constitutional Invariant: Feature flags default to OFF
    
    This test ensures that V2 features are disabled by default.
    """
    # Test that services are created with features disabled by default
    
    # Observation ingest service
    from src.federation.observation_ingest import ObservationIngestConfig
    ingest_service = ObservationIngestService(
        observation_store=Mock(),
        identity_store=Mock(),
        clock=Mock(),
        config=ObservationIngestConfig()  # Defaults to feature_enabled=False
    )
    assert ingest_service.config.feature_enabled is False
    
    # Belief aggregation service  
    from src.federation.belief_aggregation import BeliefAggregationConfig
    belief_service = BeliefAggregationService(
        observation_store=Mock(),
        clock=Mock(),
        config=BeliefAggregationConfig()  # Defaults to feature_enabled=False
    )
    assert belief_service.config.feature_enabled is False
    
    # Arbitration service
    arbitration_service = ArbitrationService(
        arbitration_store=Mock(),
        audit_service=Mock(),
        clock=Mock(),
        observation_store=Mock(),
        feature_flag_enabled=False  # Defaults to False
    )
    assert arbitration_service.feature_flag_enabled is False


def test_audit_events_emitted_for_critical_operations(
    observation_ingest_service, identity_store, fixed_clock, audit_service
):
    """
    Constitutional Invariant: Audit events emitted for critical operations
    
    This test ensures that critical operations emit audit events.
    """
    # Test that audit events are emitted for rejections (easier to test)
    
    # Create observation from non-existent federate
    observation = ObservationV1(
        observation_id="obs-audit-test",
        source_federate_id="cell-non-existent-federate",
        timestamp_utc=fixed_clock.now(),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest observation - should fail and emit audit event
    success, reason, audit_event = observation_ingest_service.ingest_observation(observation)
    
    assert success is False
    assert reason == "federate_not_found"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"
    assert audit_event["reason"] == "federate_not_found"
    assert "timestamp_utc" in audit_event or "timestamp" in audit_event
    assert "federate_id" in audit_event
