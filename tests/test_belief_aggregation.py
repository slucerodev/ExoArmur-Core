"""
Tests for belief aggregation service
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from tests.factories import make_observation_v1
from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1,
    AnomalyDetectionPayloadV1,
    SystemHealthPayloadV1,
    NetworkActivityPayloadV1
)
from exoarmur.federation.belief_aggregation import BeliefAggregationService, BeliefAggregationConfig
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
def belief_config():
    """Belief aggregation configuration for testing"""
    return BeliefAggregationConfig(
        feature_enabled=True,
        min_observations_for_belief=1,
        confidence_threshold=0.5
    )


@pytest.fixture
def belief_service(observation_store, fixed_clock, belief_config):
    """Belief aggregation service for testing"""
    return BeliefAggregationService(
        observation_store=observation_store,
        clock=fixed_clock,
        config=belief_config
    )


def test_belief_aggregation_is_deterministic(belief_service, fixed_clock):
    """Test that belief aggregation is deterministic"""
    # Create multiple observations of same type
    base_time = fixed_clock.now()
    
    observations = []
    for i in range(3):
        obs = make_observation_v1(
            observation_id=f"obs-{i}",
            source_federate_id=f"federate-{i}",
            timestamp_utc=base_time + timedelta(minutes=i),
            observation_type=ObservationType.TELEMETRY_SUMMARY,
            confidence=0.8,
            event_count=100 + i * 10,
            time_window_seconds=300,
            event_types=["process_start", "network_connect"],
            severity_distribution={"low": 80 - i * 5, "medium": 20 + i * 5}
        )
        observations.append(obs)
        belief_service.observation_store.store_observation(obs)
    
    # Aggregate beliefs
    beliefs1 = belief_service.aggregate_observations(
        observation_type=ObservationType.TELEMETRY_SUMMARY
    )
    
    # Clear belief store and aggregate again with same observations
    belief_service.observation_store._beliefs.clear()
    
    beliefs2 = belief_service.aggregate_observations(
        observation_type=ObservationType.TELEMETRY_SUMMARY
    )
    
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


def test_belief_aggregation_with_different_types(belief_service, fixed_clock):
    """Test belief aggregation with different observation types"""
    base_time = fixed_clock.now()
    
    # Create telemetry observations
    telemetry_obs = make_observation_v1(
        observation_id="obs-telemetry",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.9,
        event_count=100,
        time_window_seconds=300,
        event_types=["process_start", "file_access"],
        severity_distribution={"low": 70, "medium": 20, "high": 10}
    )
    
    # Create threat intel observations
    threat_obs = make_observation_v1(
        observation_id="obs-threat",
        source_federate_id="federate-2",
        timestamp_utc=base_time,
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.8,
        ioc_count=5,
        threat_types=["malware", "c2"],
        confidence_score=0.8,
        sources=["vendor1", "vendor2"]
    )
    
    # Store observations
    belief_service.observation_store.store_observation(telemetry_obs)
    belief_service.observation_store.store_observation(threat_obs)
    
    # Aggregate all beliefs
    all_beliefs = belief_service.aggregate_observations()
    
    # Should have beliefs for each observation type
    assert len(all_beliefs) >= 2
    
    # Check belief types
    belief_types = [belief.belief_type for belief in all_beliefs]
    assert any("TELEMETRY_SUMMARY" in bt for bt in belief_types)
    assert any("THREAT_INTEL" in bt for bt in belief_types)


def test_belief_aggregation_with_correlation_id(belief_service, fixed_clock):
    """Test belief aggregation with correlation ID filtering"""
    base_time = fixed_clock.now()
    correlation_id = "corr-123"
    
    # Create observations with same correlation ID
    obs1 = ObservationV1(
        observation_id="obs-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        correlation_id=correlation_id,
        observation_type=ObservationType.ANOMALY_DETECTION,
        confidence=0.7,
        payload=AnomalyDetectionPayloadV1(
            payload_type="anomaly_detection",
            data={},
            anomaly_score=0.8,
            affected_entities=["host-1"],
            anomaly_type="behavioral",
            baseline_deviation=2.5
        )
    )
    
    obs2 = ObservationV1(
        observation_id="obs-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time + timedelta(minutes=5),
        correlation_id=correlation_id,
        observation_type=ObservationType.ANOMALY_DETECTION,
        confidence=0.9,
        payload=AnomalyDetectionPayloadV1(
            payload_type="anomaly_detection",
            data={},
            anomaly_score=0.9,
            affected_entities=["host-2"],
            anomaly_type="behavioral",
            baseline_deviation=3.0
        )
    )
    
    # Create observation with different correlation ID
    obs3 = ObservationV1(
        observation_id="obs-3",
        source_federate_id="federate-3",
        timestamp_utc=base_time,
        correlation_id="different-corr",
        observation_type=ObservationType.ANOMALY_DETECTION,
        confidence=0.6,
        payload=AnomalyDetectionPayloadV1(
            payload_type="anomaly_detection",
            data={},
            anomaly_score=0.6,
            affected_entities=["host-3"],
            anomaly_type="statistical",
            baseline_deviation=1.5
        )
    )
    
    # Store observations
    belief_service.observation_store.store_observation(obs1)
    belief_service.observation_store.store_observation(obs2)
    belief_service.observation_store.store_observation(obs3)
    
    # Aggregate with correlation ID filter
    corr_beliefs = belief_service.aggregate_observations(correlation_id=correlation_id)
    
    # Should only aggregate observations with specified correlation ID
    assert len(corr_beliefs) == 1
    belief = corr_beliefs[0]
    
    # Should include both obs1 and obs2
    assert obs1.observation_id in belief.source_observations
    assert obs2.observation_id in belief.source_observations
    assert obs3.observation_id not in belief.source_observations
    assert belief.correlation_id == correlation_id


def test_belief_aggregation_system_health(belief_service, fixed_clock):
    """Test belief aggregation for system health observations"""
    base_time = fixed_clock.now()
    
    # Create system health observations
    obs1 = make_observation_v1(
        observation_id="obs-health-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        observation_type=ObservationType.SYSTEM_HEALTH,
        confidence=0.8,
        cpu_utilization=45.0,
        memory_utilization=60.0,
        disk_utilization=30.0,
        network_latency_ms=25.5,
        service_status={"web": "healthy", "db": "healthy"}
    )
    
    obs2 = make_observation_v1(
        observation_id="obs-health-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time,
        observation_type=ObservationType.SYSTEM_HEALTH,
        confidence=0.8,  # Same confidence as obs1
        cpu_utilization=55.0,
        memory_utilization=70.0,
        disk_utilization=40.0,
        network_latency_ms=35.7,
        service_status={"web": "healthy", "db": "healthy"}  # Same status as obs1
    )
    
    # Store observations
    belief_service.observation_store.store_observation(obs1)
    belief_service.observation_store.store_observation(obs2)
    
    # Aggregate beliefs
    beliefs = belief_service.aggregate_observations(
        observation_type=ObservationType.SYSTEM_HEALTH
    )
    
    assert len(beliefs) == 1
    belief = beliefs[0]
    
    # Check aggregated values
    metadata = belief.metadata
    assert "average_cpu_utilization" in metadata
    assert "average_memory_utilization" in metadata
    assert "average_disk_utilization" in metadata
    assert "average_network_latency" in metadata
    assert "health_score" in metadata
    
    # Verify averages
    expected_cpu = (45.0 + 55.0) / 2
    expected_mem = (60.0 + 70.0) / 2
    expected_disk = (30.0 + 40.0) / 2
    expected_latency = (25.5 + 35.7) / 2
    
    assert abs(metadata["average_cpu_utilization"] - expected_cpu) < 0.01
    assert abs(metadata["average_memory_utilization"] - expected_mem) < 0.01
    assert abs(metadata["average_disk_utilization"] - expected_disk) < 0.01
    assert abs(metadata["average_network_latency"] - expected_latency) < 0.01


def test_belief_aggregation_network_activity(belief_service, fixed_clock):
    """Test belief aggregation for network activity observations"""
    base_time = fixed_clock.now()
    
    # Create network activity observations
    obs1 = make_observation_v1(
        observation_id="obs-network-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        observation_type=ObservationType.NETWORK_ACTIVITY,
        confidence=0.7,
        connection_count=1000,
        bytes_transferred=1024000,
        top_protocols=["tcp", "udp"],
        suspicious_ips=["192.168.1.100"]
    )
    
    obs2 = make_observation_v1(
        observation_id="obs-network-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time + timedelta(minutes=5),
        observation_type=ObservationType.NETWORK_ACTIVITY,
        confidence=0.8,
        connection_count=1500,
        bytes_transferred=2048000,
        top_protocols=["tcp", "http"],
        suspicious_ips=["10.0.0.50", "172.16.0.1"]
    )
    
    # Store observations
    belief_service.observation_store.store_observation(obs1)
    belief_service.observation_store.store_observation(obs2)
    
    # Aggregate beliefs
    beliefs = belief_service.aggregate_observations(
        observation_type=ObservationType.NETWORK_ACTIVITY
    )
    
    assert len(beliefs) == 1
    belief = beliefs[0]
    
    # Check aggregated values
    metadata = belief.metadata
    assert "total_connections" in metadata
    assert "total_bytes_transferred" in metadata
    assert "protocols" in metadata
    assert "suspicious_ip_count" in metadata
    
    # Verify totals
    expected_connections = 1000 + 1500
    expected_bytes = 1024000 + 2048000
    expected_protocols = {"tcp", "udp", "http"}
    expected_suspicious_count = 3  # 1 + 2
    
    assert metadata["total_connections"] == expected_connections
    assert metadata["total_bytes_transferred"] == expected_bytes
    assert set(metadata["protocols"]) == expected_protocols
    assert metadata["suspicious_ip_count"] == expected_suspicious_count


def test_belief_aggregation_with_feature_disabled(belief_service, fixed_clock):
    """Test belief aggregation when feature is disabled"""
    # Disable feature
    belief_service.config.feature_enabled = False
    
    # Create observation
    obs = make_observation_v1(
        observation_id="obs-1",
        source_federate_id="federate-1",
        timestamp_utc=fixed_clock.now(),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        event_count=100,
        time_window_seconds=300,
        event_types=["process_start"],
        severity_distribution={"low": 80, "medium": 20}
    )
    
    # Store observation
    belief_service.observation_store.store_observation(obs)
    
    # Try to aggregate
    beliefs = belief_service.aggregate_observations()
    
    # Should return empty list when feature disabled
    assert len(beliefs) == 0


def test_belief_aggregation_time_window_grouping(belief_service, fixed_clock):
    """Test that observations are grouped by time windows"""
    base_time = fixed_clock.now()
    
    # Create observations with same correlation ID
    obs1 = make_observation_v1(
        observation_id="obs-1",
        source_federate_id="federate-1",
        timestamp_utc=base_time,
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.8,
        correlation_id="corr-123",
        event_count=50,
        time_window_seconds=300,
        event_types=["login"],
        severity_distribution={"low": 30, "medium": 20}
    )
    
    obs2 = make_observation_v1(
        observation_id="obs-2",
        source_federate_id="federate-2",
        timestamp_utc=base_time + timedelta(minutes=5),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.7,
        correlation_id="corr-123",
        event_count=30,
        time_window_seconds=300,
        event_types=["login"],
        severity_distribution={"low": 10, "medium": 20}
    )
    
    obs3 = make_observation_v1(
        observation_id="obs-3",
        source_federate_id="federate-3",
        timestamp_utc=base_time + timedelta(hours=2),
        observation_type=ObservationType.TELEMETRY_SUMMARY,
        confidence=0.9,
        correlation_id="different-corr",
        event_count=200,
        time_window_seconds=300,
        event_types=["file_access"],
        severity_distribution={"low": 60, "medium": 40}
    )
    
    # Store observations
    belief_service.observation_store.store_observation(obs1)
    belief_service.observation_store.store_observation(obs2)
    belief_service.observation_store.store_observation(obs3)
    
    # Aggregate beliefs
    beliefs = belief_service.aggregate_observations(
        observation_type=ObservationType.TELEMETRY_SUMMARY
    )
    
    # Should create 2 beliefs (one for each time window)
    assert len(beliefs) == 2
    
    # Check that obs1 and obs2 are in same belief
    belief_with_obs1_obs2 = None
    belief_with_obs3 = None
    
    for belief in beliefs:
        if obs1.observation_id in belief.source_observations:
            belief_with_obs1_obs2 = belief
        if obs3.observation_id in belief.source_observations:
            belief_with_obs3 = belief
    
    assert belief_with_obs1_obs2 is not None
    assert belief_with_obs3 is not None
    
    # obs1 and obs2 should be together
    assert obs1.observation_id in belief_with_obs1_obs2.source_observations
    assert obs2.observation_id in belief_with_obs1_obs2.source_observations
    assert obs3.observation_id not in belief_with_obs1_obs2.source_observations
    
    # obs3 should be separate
    assert obs3.observation_id in belief_with_obs3.source_observations
    assert obs1.observation_id not in belief_with_obs3.source_observations
    assert obs2.observation_id not in belief_with_obs3.source_observations
