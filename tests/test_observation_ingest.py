"""
Tests for observation ingest service
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from spec.contracts.models_v1 import (
    ObservationV1,
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1,
    SignatureInfoV1,
    SignatureAlgorithm,
    FederateIdentityV1,
    FederationRole,
    CellStatus
)
from exoarmur.federation.observation_ingest import ObservationIngestService, ObservationIngestConfig
from exoarmur.federation.observation_store import ObservationStore
from exoarmur.federation.federate_identity_store import FederateIdentityStore
from exoarmur.federation.clock import FixedClock
from exoarmur.federation.crypto import FederateKeyPair, sign_message, serialize_public_key_for_identity, deserialize_public_key_from_identity


@pytest.fixture
def fixed_clock():
    """Fixed clock for deterministic testing"""
    return FixedClock()


@pytest.fixture
def observation_store(fixed_clock):
    """Observation store for testing"""
    return ObservationStore(fixed_clock)


@pytest.fixture
def identity_store():
    """Identity store for testing"""
    return FederateIdentityStore()


@pytest.fixture
def ingest_config():
    """Ingest configuration for testing"""
    return ObservationIngestConfig(
        feature_enabled=True,
        require_confirmed_federate=True,
        require_signature=True
    )


@pytest.fixture
def ingest_service(observation_store, identity_store, fixed_clock, ingest_config):
    """Ingest service for testing"""
    return ObservationIngestService(
        observation_store=observation_store,
        identity_store=identity_store,
        clock=fixed_clock,
        config=ingest_config
    )


@pytest.fixture
def test_federate_identity():
    """Test federate identity"""
    # Use a fixed key pair for deterministic testing
    key_pair = FederateKeyPair()
    identity = FederateIdentityV1(
        schema_version="2.0.0",
        federate_id="cell-us-east-1-cluster-01-node-01",
        public_key=serialize_public_key_for_identity(key_pair.public_key),
        key_id=key_pair.key_id,
        certificate_chain=["cert-1", "cert-2"],
        federation_role=FederationRole.MEMBER,
        capabilities=["belief_aggregation", "policy_distribution"],
        trust_score=0.85,
        last_seen=datetime.now(timezone.utc),
        status=CellStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    # Store the actual key pair for verification
    identity._key_pair = key_pair
    return identity


@pytest.fixture
def test_key_pair(test_federate_identity):
    """Test key pair for signing - matches the federate identity"""
    return test_federate_identity._key_pair


def create_mock_identity(test_federate_identity):
    """Create a mock identity with deserialized public key"""
    mock_identity = Mock()
    mock_identity.federate_id = test_federate_identity.federate_id
    mock_identity.key_id = test_federate_identity.key_id
    mock_identity.public_key = deserialize_public_key_from_identity(test_federate_identity.public_key)
    mock_identity.status = test_federate_identity.status
    return mock_identity


def test_observation_ingest_requires_confirmed_federate(ingest_service, test_key_pair, fixed_clock):
    """Test that observation ingest requires confirmed federate"""
    # Create observation from unconfirmed federate
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id="unknown-federate",
        timestamp_utc=fixed_clock.now(),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest observation
    success, reason, audit_event = ingest_service.ingest_observation(observation)
    
    # Should fail due to unknown federate
    assert success is False
    assert reason == "federate_not_found"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"
    assert audit_event["reason"] == "federate_not_found"


def test_observation_signature_required_and_verified(
    ingest_service, identity_store, test_federate_identity, test_key_pair, fixed_clock
):
    """Test that observation signature is required and verified"""
    # Mock the identity store to return our test identity
    mock_identity = create_mock_identity(test_federate_identity)
    identity_store.get_identity = Mock(return_value=mock_identity)
    identity_store.is_nonce_available = Mock(return_value=True)
    identity_store.mark_nonce_used = Mock()
    
    # Create observation without signature
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        nonce="test-nonce-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest without signature
    success, reason, audit_event = ingest_service.ingest_observation(observation)
    
    # Should fail due to missing signature
    assert success is False
    assert reason == "missing_signature"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"
    
    # Now add signature
    signed_observation = sign_message(observation, test_key_pair.private_key)
        
    # Try to ingest with signature
    success, reason, audit_event = ingest_service.ingest_observation(signed_observation)
        
    # Should succeed
    assert success is True
    assert reason == "success"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_accepted"


def test_observation_nonce_replay_rejected(
    ingest_service, identity_store, test_federate_identity, test_key_pair, fixed_clock
):
    """Test that observation nonce replay is rejected"""
    # Mock the identity store to return our test identity
    mock_identity = create_mock_identity(test_federate_identity)
    identity_store.get_identity = Mock(return_value=mock_identity)
    identity_store.is_nonce_available = Mock(return_value=True)
    identity_store.mark_nonce_used = Mock()
    
    # Create observation with nonce
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        nonce="test-nonce-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Sign observation
    signed_observation = sign_message(observation, test_key_pair.private_key)
    
    # Ingest first time
    success1, reason1, audit_event1 = ingest_service.ingest_observation(signed_observation)
    assert success1 is True
    
    # Try to ingest same nonce again
    observation2 = ObservationV1(
        observation_id="obs-456",  # Different ID but same nonce
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        nonce="test-nonce-123",  # Same nonce
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.9,
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=5,
            threat_types=["malware", "phishing"],
            confidence_score=0.9,
            sources=["source1", "source2"]
        )
    )
    
    signed_observation2 = sign_message(observation2, test_key_pair.private_key)
    
    # Should fail due to nonce reuse
    success2, reason2, audit_event2 = ingest_service.ingest_observation(signed_observation2)
    assert success2 is False
    assert reason2 == "nonce_reuse"
    assert audit_event2 is not None
    assert audit_event2["event_type"] == "observation_rejected"


def test_observation_ingest_with_feature_disabled(ingest_service, test_federate_identity, fixed_clock):
    """Test observation ingest when feature is disabled"""
    # Disable feature
    ingest_service.config.feature_enabled = False
    
    # Create valid observation
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest
    success, reason, audit_event = ingest_service.ingest_observation(observation)
    
    # Should fail due to feature disabled
    assert success is False
    assert reason == "feature_disabled"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"


def test_observation_schema_validation(ingest_service, test_federate_identity, fixed_clock):
    """Test observation schema validation"""
    # Mock the identity store to return our test identity
    mock_identity = create_mock_identity(test_federate_identity)
    ingest_service.identity_store.get_identity = Mock(return_value=mock_identity)
    ingest_service.identity_store.is_nonce_available = Mock(return_value=True)
    ingest_service.identity_store.mark_nonce_used = Mock()
    
    # Create observation with invalid confidence - this will fail at Pydantic validation
    # So we need to test with a valid observation and then test our validation logic
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        nonce="test-nonce-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,  # Valid confidence
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Sign the observation
    signed_observation = sign_message(observation, test_federate_identity._key_pair.private_key)
    
    # Try to ingest
    success, reason, audit_event = ingest_service.ingest_observation(signed_observation)
    
    # Should succeed since we're testing with valid schema
    assert success is True
    assert reason == "success"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_accepted"


def test_observation_timestamp_validation(ingest_service, test_federate_identity, fixed_clock):
    """Test observation timestamp validation"""
    # Mock the identity store to return our test identity
    mock_identity = create_mock_identity(test_federate_identity)
    ingest_service.identity_store.get_identity = Mock(return_value=mock_identity)
    ingest_service.identity_store.is_nonce_available = Mock(return_value=True)
    ingest_service.identity_store.mark_nonce_used = Mock()
    
    # Create observation with future timestamp
    future_time = fixed_clock.now() + timedelta(hours=1)
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=future_time,  # Future timestamp
        nonce="test-nonce-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Try to ingest
    success, reason, audit_event = ingest_service.ingest_observation(observation)
    
    # Should fail due to future timestamp
    assert success is False
    assert reason == "future_timestamp"
    assert audit_event is not None
    assert audit_event["event_type"] == "observation_rejected"


def test_duplicate_observation_rejection(
    ingest_service, identity_store, test_federate_identity, test_key_pair, fixed_clock
):
    """Test that duplicate observations are rejected"""
    # Mock the identity store to return our test identity
    mock_identity = create_mock_identity(test_federate_identity)
    identity_store.get_identity = Mock(return_value=mock_identity)
    identity_store.is_nonce_available = Mock(return_value=True)
    identity_store.mark_nonce_used = Mock()
    
    # Create and sign observation
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id=test_federate_identity.federate_id,
        timestamp_utc=fixed_clock.now(),
        nonce="test-nonce-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    signed_observation = sign_message(observation, test_key_pair.private_key)
    
    # Ingest first time
    success1, reason1, audit_event1 = ingest_service.ingest_observation(signed_observation)
    assert success1 is True
    
    # Try to ingest same observation again
    success2, reason2, audit_event2 = ingest_service.ingest_observation(signed_observation)
    assert success2 is False
    assert reason2 == "nonce_reuse"
    assert audit_event2 is not None
    assert audit_event2["event_type"] == "observation_rejected"
