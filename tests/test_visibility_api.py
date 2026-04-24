"""
Tests for visibility API endpoints
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    BeliefTelemetryV1,
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1
)
from exoarmur.federation.visibility_api import VisibilityAPI
from exoarmur.federation.observation_store import ObservationStore
from exoarmur.federation.federate_identity_store import FederateIdentityStore
from exoarmur.federation.belief_aggregation import BeliefAggregationService
from exoarmur.federation.observation_ingest import ObservationIngestService
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
def identity_store():
    """Identity store for testing"""
    return FederateIdentityStore()


@pytest.fixture
def belief_service(observation_store, fixed_clock):
    """Belief aggregation service for testing"""
    config = Mock()
    config.feature_enabled = True
    return BeliefAggregationService(observation_store, fixed_clock, config)


@pytest.fixture
def ingest_service(observation_store, identity_store, fixed_clock):
    """Observation ingest service for testing"""
    config = Mock()
    config.feature_enabled = True
    return ObservationIngestService(observation_store, identity_store, fixed_clock, config)


@pytest.fixture
def visibility_api(observation_store, identity_store, belief_service, ingest_service, fixed_clock):
    """Visibility API for testing"""
    return VisibilityAPI(
        observation_store=observation_store,
        identity_store=identity_store,
        belief_service=belief_service,
        ingest_service=ingest_service,
        clock=fixed_clock
    )


@pytest.fixture
def client(visibility_api):
    """Test client for API"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(visibility_api.get_router())
    return TestClient(app)


def test_visibility_endpoints_return_provenance(client, observation_store, fixed_clock):
    """Test that visibility endpoints return provenance information"""
    base_time = fixed_clock.now()
    
    # Create test observation
    observation = ObservationV1(
        observation_id="obs-123",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        correlation_id="corr-123",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        evidence_refs=["evidence-1", "evidence-2"],
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={"custom_field": "value"},
            event_count=100,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80, "medium": 20}
        )
    )
    
    # Store observation
    observation_store.store_observation(observation)
    
    # Create test belief
    belief = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-456",
        belief_type="derived_from_telemetry_summary",
        confidence=0.75,
        source_observations=["obs-123"],
        derived_at=base_time + timedelta(minutes=5),
        correlation_id="corr-123",
        evidence_summary="Aggregated telemetry from 1 observation",
        metadata={"total_events": 100, "observation_count": 1}
    )
    
    # Store belief
    observation_store.store_belief(belief)
    
    # Test observations endpoint
    response = client.get("/api/v2/visibility/observations")
    assert response.status_code == 200
    
    observations = response.json()
    assert len(observations) == 1
    
    obs_data = observations[0]
    # Check provenance fields
    assert obs_data["observation_id"] == "obs-123"
    assert obs_data["source_federate_id"] == "federate-1"
    assert obs_data["timestamp_utc"] == base_time.isoformat().replace('+00:00', 'Z')
    assert obs_data["correlation_id"] == "corr-123"
    assert obs_data["observation_type"] == "telemetry_summary"
    assert obs_data["confidence"] == 0.8
    assert obs_data["evidence_refs"] == ["evidence-1", "evidence-2"]
    assert obs_data["payload_type"] == "telemetry_summary"
    assert obs_data["payload_data"]["custom_field"] == "value"
    
    # Test beliefs endpoint
    response = client.get("/api/v2/visibility/beliefs")
    assert response.status_code == 200
    
    beliefs = response.json()
    assert len(beliefs) == 1
    
    belief_data = beliefs[0]
    # Check provenance fields
    assert belief_data["belief_id"] == "belief-456"
    assert belief_data["belief_type"] == "derived_from_telemetry_summary"
    assert belief_data["confidence"] == 0.75
    assert belief_data["source_observations"] == ["obs-123"]
    assert belief_data["derived_at"] == (base_time + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')
    assert belief_data["correlation_id"] == "corr-123"
    assert belief_data["evidence_summary"] == "Aggregated telemetry from 1 observation"
    assert belief_data["conflicts"] == []
    assert belief_data["metadata"]["total_events"] == 100
    assert belief_data["metadata"]["observation_count"] == 1


def test_timeline_endpoint_returns_provenance(client, observation_store, fixed_clock):
    """Test that timeline endpoint returns provenance with correlation links"""
    base_time = fixed_clock.now()
    correlation_id = "corr-timeline-123"
    
    # Create multiple observations with same correlation ID
    obs1 = ObservationV1(
        observation_id="obs-timeline-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        correlation_id=correlation_id,
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        evidence_refs=["evidence-1"],
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
        observation_id="obs-timeline-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time + timedelta(minutes=10),
        correlation_id=correlation_id,
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.9,
        evidence_refs=["evidence-2"],
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=5,
            threat_types=["malware"],
            confidence_score=0.9,
            sources=["source1"]
        )
    )
    
    # Create belief derived from observations
    belief = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-timeline-1",
        belief_type="derived_from_threat_intel",
        confidence=0.85,
        source_observations=["obs-timeline-1"],
        derived_at=fixed_clock.now(),
        correlation_id=correlation_id,
        evidence_summary="Threat intelligence from external source",
        metadata={"threat_type": "malware", "severity": "high"}
    )
    
    # Store data
    observation_store.store_observation(obs1)
    observation_store.store_observation(obs2)
    observation_store.store_belief(belief)
    
    # Get timeline
    response = client.get(f"/api/v2/visibility/timeline/{correlation_id}")
    assert response.status_code == 200
    
    timeline = response.json()
    assert timeline["correlation_id"] == correlation_id
    
    # Check observations
    observations = timeline["observations"]
    assert len(observations) == 2
    
    # Should be sorted by timestamp
    assert observations[0]["observation_id"] == "obs-timeline-1"
    assert observations[1]["observation_id"] == "obs-timeline-2"
    
    # Check correlation links
    for obs in observations:
        assert obs["correlation_id"] == correlation_id
    
    # Check beliefs
    beliefs = timeline["beliefs"]
    assert len(beliefs) == 1
    
    belief_data = beliefs[0]
    assert belief_data["belief_id"] == "belief-timeline-1"
    assert belief_data["correlation_id"] == correlation_id
    assert belief_data["source_observations"] == ["obs-timeline-1"]  # Links to observation


def test_observations_endpoint_with_filters(client, observation_store, fixed_clock):
    """Test observations endpoint with various filters"""
    base_time = fixed_clock.now()
    
    # Create observations with different attributes
    obs1 = ObservationV1(
        observation_id="obs-filter-1",
        source_federate_id="federate-alpha",
        timestamp_utc=base_time,
        correlation_id="corr-alpha",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        evidence_refs=[],
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
        observation_id="obs-filter-2",
        source_federate_id="federate-beta",
        timestamp_utc=base_time + timedelta(hours=1),
        correlation_id="corr-beta",
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.9,
        evidence_refs=[],
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=5,
            threat_types=["malware"],
            confidence_score=0.9,
            sources=["source1"]
        )
    )
    
    obs3 = ObservationV1(
        observation_id="obs-filter-3",
        source_federate_id="federate-alpha",
        timestamp_utc=base_time + timedelta(hours=2),
        correlation_id="corr-alpha",
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.7,
        evidence_refs=[],
        payload=TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={},
            event_count=50,
            time_window_seconds=300,
            event_types=["network_connect"],
            severity_distribution={"low": 60, "medium": 40}
        )
    )
    
    # Store observations
    observation_store.store_observation(obs1)
    observation_store.store_observation(obs2)
    observation_store.store_observation(obs3)
    
    # Test federate filter
    response = client.get("/api/v2/visibility/observations?federate_id=federate-alpha")
    assert response.status_code == 200
    
    federate_obs = response.json()
    assert len(federate_obs) == 2
    assert all(obs["source_federate_id"] == "federate-alpha" for obs in federate_obs)
    
    # Test observation type filter
    response = client.get("/api/v2/visibility/observations?observation_type=telemetry_summary")
    assert response.status_code == 200
    
    type_obs = response.json()
    assert len(type_obs) == 2
    assert all(obs["observation_type"] == "telemetry_summary" for obs in type_obs)
    
    # Test correlation filter
    response = client.get("/api/v2/visibility/observations?correlation_id=corr-alpha")
    assert response.status_code == 200
    
    corr_obs = response.json()
    assert len(corr_obs) == 2
    assert all(obs["correlation_id"] == "corr-alpha" for obs in corr_obs)
    
    # Test since filter
    since_time = base_time + timedelta(minutes=30)
    response = client.get(f"/api/v2/visibility/observations?since={since_time.isoformat().replace('+00:00', 'Z')}")
    assert response.status_code == 200
    
    since_obs = response.json()
    assert len(since_obs) == 2  # obs2 and obs3
    
    # Test limit filter
    response = client.get("/api/v2/visibility/observations?limit=2")
    assert response.status_code == 200
    
    limit_obs = response.json()
    assert len(limit_obs) == 2
    
    # Test combined filters
    response = client.get(
        "/api/v2/visibility/observations?"
        "federate_id=federate-alpha&"
        "observation_type=telemetry_summary&"
        "limit=1"
    )
    assert response.status_code == 200
    
    combined_obs = response.json()
    assert len(combined_obs) == 1
    assert combined_obs[0]["source_federate_id"] == "federate-alpha"
    assert combined_obs[0]["observation_type"] == "telemetry_summary"


def test_beliefs_endpoint_with_filters(client, observation_store, fixed_clock):
    """Test beliefs endpoint with filters"""
    base_time = fixed_clock.now()
    
    # Create beliefs with different attributes
    belief1 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-filter-1",
        belief_type="derived_from_telemetry_summary",
        confidence=0.8,
        source_observations=["obs-filter-1"],
        derived_at=base_time,
        correlation_id="corr-filter",
        evidence_summary="Telemetry summary data",
        metadata={"type": "telemetry"}
    )
    
    belief2 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-filter-2",
        belief_type="derived_from_threat_intel",
        confidence=0.9,
        source_observations=["obs-filter-2"],
        derived_at=base_time + timedelta(minutes=5),
        correlation_id="corr-filter",
        evidence_summary="Threat intelligence data",
        metadata={"type": "threat"}
    )
    
    belief3 = BeliefV1(
        schema_version="2.0.0",
        belief_id="belief-filter-3",
        belief_type="derived_from_telemetry_summary",
        confidence=0.7,
        source_observations=["obs-filter-3"],
        derived_at=base_time + timedelta(minutes=10),
        correlation_id="corr-filter",
        evidence_summary="Another telemetry summary",
        metadata={"type": "telemetry"}
    )
    
    # Store beliefs
    observation_store.store_belief(belief1)
    observation_store.store_belief(belief2)
    observation_store.store_belief(belief3)
    
    # Test belief type filter
    response = client.get("/api/v2/visibility/beliefs?belief_type=derived_from_telemetry_summary")
    assert response.status_code == 200
    
    type_beliefs = response.json()
    assert len(type_beliefs) == 2
    assert all(belief["belief_type"] == "derived_from_telemetry_summary" for belief in type_beliefs)
    
    # Test correlation filter
    response = client.get("/api/v2/visibility/beliefs?correlation_id=corr-filter")
    assert response.status_code == 200
    
    corr_beliefs = response.json()
    assert len(corr_beliefs) == 3
    assert all(belief["correlation_id"] == "corr-filter" for belief in corr_beliefs)
    
    # Test since filter
    since_time = base_time + timedelta(minutes=7)
    response = client.get(f"/api/v2/visibility/beliefs?since={since_time.isoformat().replace('+00:00', 'Z')}")
    assert response.status_code == 200
    
    since_beliefs = response.json()
    assert len(since_beliefs) == 1  # Only belief3 (at +10 minutes) should be returned
    
    # Test limit filter
    response = client.get("/api/v2/visibility/beliefs?limit=2")
    assert response.status_code == 200
    
    limit_beliefs = response.json()
    assert len(limit_beliefs) == 2


def test_statistics_endpoint(client, belief_service, ingest_service, observation_store, fixed_clock):
    """Test statistics endpoint"""
    # Mock statistics
    ingest_stats = {
        "feature_enabled": True,
        "require_confirmed_federate": True,
        "require_signature": True,
        "store_statistics": {
            "total_observations": 10,
            "total_beliefs": 5,
            "federates": ["federate-1", "federate-2"],
            "correlation_ids": ["corr-1", "corr-2"],
            "used_nonces": 3
        }
    }
    
    belief_stats = {
        "feature_enabled": True,
        "min_observations_for_belief": 1,
        "confidence_threshold": 0.5,
        "store_statistics": {
            "total_observations": 10,
            "total_beliefs": 5,
            "federates": ["federate-1", "federate-2"],
            "correlation_ids": ["corr-1", "corr-2"],
            "used_nonces": 3
        }
    }
    
    store_stats = {
        "total_observations": 10,
        "total_beliefs": 5,
        "federates": ["federate-1", "federate-2"],
        "correlation_ids": ["corr-1", "corr-2"],
        "used_nonces": 3
    }
    
    # Mock service methods
    ingest_service.get_ingest_statistics = Mock(return_value=ingest_stats)
    belief_service.get_aggregation_statistics = Mock(return_value=belief_stats)
    observation_store.get_statistics = Mock(return_value=store_stats)
    
    # Get statistics
    response = client.get("/api/v2/visibility/statistics")
    assert response.status_code == 200
    
    stats = response.json()
    assert "ingest_statistics" in stats
    assert "belief_statistics" in stats
    assert "store_statistics" in stats
    assert "timestamp" in stats
    
    # Check statistics content
    assert stats["ingest_statistics"]["feature_enabled"] is True
    assert stats["belief_statistics"]["min_observations_for_belief"] == 1
    assert stats["store_statistics"]["total_observations"] == 10


def test_timeline_endpoint_not_found(client):
    """Test timeline endpoint with non-existent correlation ID"""
    response = client.get("/api/v2/visibility/timeline/non-existent")
    assert response.status_code == 200
    
    timeline = response.json()
    assert timeline["correlation_id"] == "non-existent"
    assert len(timeline["observations"]) == 0
    assert len(timeline["beliefs"]) == 0


def test_invalid_timestamp_filter(client, observation_store, fixed_clock):
    """Test invalid timestamp filter format"""
    response = client.get("/api/v2/visibility/observations?since=invalid-timestamp")
    assert response.status_code == 400
    
    error = response.json()
    assert "detail" in error
    assert "Invalid since timestamp format" in error["detail"]
