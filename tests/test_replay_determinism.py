"""
Replay Determinism Test

Tests that the system produces identical results when replayed.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from spec.contracts.models_v1 import (
    BeliefV1,
    ObservationV1,
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1
)
from src.federation.belief_aggregation import BeliefAggregationService
from src.federation.observation_store import ObservationStore
from src.federation.clock import FixedClock


@pytest.fixture
def fixed_clock():
    """Fixed clock for deterministic testing"""
    return FixedClock()


@pytest.fixture
def observation_store(fixed_clock):
    """Observation store for testing"""
    return ObservationStore(fixed_clock)


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


def test_deterministic_belief_aggregation_repeatability(
    belief_aggregation_service, observation_store, fixed_clock
):
    """
    Test that belief aggregation produces identical results when run twice
    
    This is a core determinism requirement for replay functionality.
    """
    # Create deterministic test scenario
    base_time = fixed_clock.now()
    
    # Scenario: Multiple federates observing the same system
    observations = [
        ObservationV1(
            observation_id="obs-001",
            source_federate_id="federate-alpha",
            timestamp_utc=base_time,
            observation_type=ObservationType.TELEMETRY_SUMMARY,
            confidence=0.9,
            payload=TelemetrySummaryPayloadV1(
                payload_type="telemetry_summary",
                data={},
                event_count=100,
                time_window_seconds=300,
                event_types=["process_start", "file_access"],
                severity_distribution={"low": 70, "medium": 30}
            ),
            correlation_id="scenario-123"
        ),
        ObservationV1(
            observation_id="obs-002", 
            source_federate_id="federate-beta",
            timestamp_utc=base_time + timedelta(minutes=5),
            observation_type=ObservationType.TELEMETRY_SUMMARY,
            confidence=0.8,
            payload=TelemetrySummaryPayloadV1(
                payload_type="telemetry_summary",
                data={},
                event_count=80,
                time_window_seconds=300,
                event_types=["network_connect"],
                severity_distribution={"low": 60, "medium": 20}
            ),
            correlation_id="scenario-123"
        ),
        ObservationV1(
            observation_id="obs-003",
            source_federate_id="federate-gamma", 
            timestamp_utc=base_time + timedelta(minutes=10),
            observation_type=ObservationType.THREAT_INTEL,
            confidence=0.7,
            payload=ThreatIntelPayloadV1(
                payload_type="threat_intel",
                data={},
                ioc_count=5,
                threat_types=["malware"],
                confidence_score=0.7,
                sources=["threat_feed_1"]
            ),
            correlation_id="scenario-123"
        )
    ]
    
    # First run - establish baseline
    print("\n=== FIRST RUN ===")
    observation_store._observations.clear()
    observation_store._beliefs.clear()
    
    for obs in observations:
        observation_store.store_observation(obs)
    
    beliefs_run1 = belief_aggregation_service.aggregate_observations()
    
    # Capture results for comparison
    run1_results = {
        'belief_count': len(beliefs_run1),
        'belief_ids': sorted([b.belief_id for b in beliefs_run1]),
        'belief_types': sorted([b.belief_type for b in beliefs_run1]),
        'confidence_scores': sorted([b.confidence for b in beliefs_run1]),
        'source_observations': [sorted(b.source_observations) for b in beliefs_run1],
        'evidence_summaries': [b.evidence_summary for b in beliefs_run1],
        'metadata': [b.metadata for b in beliefs_run1]
    }
    
    print(f"Run 1: Generated {run1_results['belief_count']} beliefs")
    print(f"Belief IDs: {run1_results['belief_ids']}")
    
    # Second run - should be identical
    print("\n=== SECOND RUN ===")
    observation_store._observations.clear()
    observation_store._beliefs.clear()
    
    # Use exactly the same observations (same objects)
    for obs in observations:
        observation_store.store_observation(obs)
    
    beliefs_run2 = belief_aggregation_service.aggregate_observations()
    
    # Capture results for comparison
    run2_results = {
        'belief_count': len(beliefs_run2),
        'belief_ids': sorted([b.belief_id for b in beliefs_run2]),
        'belief_types': sorted([b.belief_type for b in beliefs_run2]),
        'confidence_scores': sorted([b.confidence for b in beliefs_run2]),
        'source_observations': [sorted(b.source_observations) for b in beliefs_run2],
        'evidence_summaries': [b.evidence_summary for b in beliefs_run2],
        'metadata': [b.metadata for b in beliefs_run2]
    }
    
    print(f"Run 2: Generated {run2_results['belief_count']} beliefs")
    print(f"Belief IDs: {run2_results['belief_ids']}")
    
    # Assert complete determinism
    assert run1_results['belief_count'] == run2_results['belief_count'], \
        f"Belief count mismatch: {run1_results['belief_count']} vs {run2_results['belief_count']}"
    
    assert run1_results['belief_ids'] == run2_results['belief_ids'], \
        f"Belief IDs mismatch: {run1_results['belief_ids']} vs {run2_results['belief_ids']}"
    
    assert run1_results['belief_types'] == run2_results['belief_types'], \
        f"Belief types mismatch: {run1_results['belief_types']} vs {run2_results['belief_types']}"
    
    assert run1_results['confidence_scores'] == run2_results['confidence_scores'], \
        f"Confidence scores mismatch: {run1_results['confidence_scores']} vs {run2_results['confidence_scores']}"
    
    assert run1_results['source_observations'] == run2_results['source_observations'], \
        f"Source observations mismatch: {run1_results['source_observations']} vs {run2_results['source_observations']}"
    
    assert run1_results['evidence_summaries'] == run2_results['evidence_summaries'], \
        f"Evidence summaries mismatch: {run1_results['evidence_summaries']} vs {run2_results['evidence_summaries']}"
    
    assert run1_results['metadata'] == run2_results['metadata'], \
        f"Metadata mismatch: {run1_results['metadata']} vs {run2_results['metadata']}"
    
    # Detailed belief comparison
    for i, (belief1, belief2) in enumerate(zip(beliefs_run1, beliefs_run2)):
        assert belief1.belief_id == belief2.belief_id, f"Belief {i} ID mismatch"
        assert belief1.belief_type == belief2.belief_type, f"Belief {i} type mismatch"
        assert belief1.confidence == belief2.confidence, f"Belief {i} confidence mismatch"
        assert belief1.source_observations == belief2.source_observations, f"Belief {i} sources mismatch"
        assert belief1.derived_at == belief2.derived_at, f"Belief {i} derived_at mismatch"
        assert belief1.evidence_summary == belief2.evidence_summary, f"Belief {i} evidence summary mismatch"
        assert belief1.metadata == belief2.metadata, f"Belief {i} metadata mismatch"
        assert belief1.correlation_id == belief2.correlation_id, f"Belief {i} correlation_id mismatch"
    
    print("\n✅ DETERMINISM VERIFIED: Both runs produced identical results")


def test_deterministic_belief_ids_across_runs(belief_aggregation_service, observation_store, fixed_clock):
    """
    Test that belief IDs are deterministic across multiple runs
    """
    # Create simple scenario
    base_time = fixed_clock.now()
    
    observations = [
        ObservationV1(
            observation_id="obs-deterministic-1",
            source_federate_id="federate-test",
            timestamp_utc=base_time,
            observation_type=ObservationType.TELEMETRY_SUMMARY,
            confidence=0.8,
            payload=TelemetrySummaryPayloadV1(
                payload_type="telemetry_summary",
                data={},
                event_count=50,
                time_window_seconds=300,
                event_types=["process_start"],
                severity_distribution={"low": 40, "medium": 10}
            )
        )
    ]
    
    # Run multiple times and collect belief IDs
    all_belief_ids = []
    
    for run_num in range(5):
        print(f"\n=== DETERMINISTIC RUN {run_num + 1} ===")
        
        # Clear state
        observation_store._observations.clear()
        observation_store._beliefs.clear()
        
        # Store observations and aggregate
        for obs in observations:
            observation_store.store_observation(obs)
        
        beliefs = belief_aggregation_service.aggregate_observations()
        
        # Collect belief IDs
        run_belief_ids = [b.belief_id for b in beliefs]
        all_belief_ids.append(run_belief_ids)
        
        print(f"Run {run_num + 1} belief IDs: {run_belief_ids}")
    
    # All runs should produce identical belief IDs
    first_run_ids = all_belief_ids[0]
    
    for i, run_ids in enumerate(all_belief_ids[1:], 1):
        assert run_ids == first_run_ids, \
            f"Run {i + 1} produced different belief IDs: {run_ids} vs {first_run_ids}"
    
    print(f"\n✅ DETERMINISTIC IDS: All {len(all_belief_ids)} runs produced identical belief IDs")


def test_replay_scenario_summary_determinism(belief_aggregation_service, observation_store, fixed_clock):
    """
    Test that replay scenario summaries are deterministic
    """
    # Create a complex scenario
    base_time = fixed_clock.now()
    
    scenario_observations = [
        ObservationV1(
            observation_id=f"obs-scenario-{i}",
            source_federate_id=f"federate-{chr(97 + i)}",  # federate-a, federate-b, etc.
            timestamp_utc=base_time + timedelta(minutes=i*10),
            observation_type=ObservationType.TELEMETRY_SUMMARY,
            confidence=0.8 - (i * 0.1),
            payload=TelemetrySummaryPayloadV1(
                payload_type="telemetry_summary",
                data={},
                event_count=100 + i*10,
                time_window_seconds=300,
                event_types=["process_start", "network_connect"],
                severity_distribution={"low": 80 - i*5, "medium": 20 + i*5}
            ),
            correlation_id="replay-scenario-123"
        )
        for i in range(3)
    ]
    
    def run_scenario_and_generate_summary():
        """Run scenario and generate summary"""
        # Clear state
        observation_store._observations.clear()
        observation_store._beliefs.clear()
        
        # Store observations
        for obs in scenario_observations:
            observation_store.store_observation(obs)
        
        # Aggregate beliefs
        beliefs = belief_aggregation_service.aggregate_observations()
        
        # Generate deterministic summary
        summary = {
            "scenario_id": "replay-scenario-123",
            "observation_count": len(scenario_observations),
            "belief_count": len(beliefs),
            "belief_ids": sorted([b.belief_id for b in beliefs]),
            "total_confidence": sum(b.confidence for b in beliefs),
            "avg_confidence": sum(b.confidence for b in beliefs) / len(beliefs) if beliefs else 0,
            "belief_types": sorted(list(set(b.belief_type for b in beliefs))),
            "correlation_ids": sorted(list(set(b.correlation_id for b in beliefs if b.correlation_id))),
            "source_federates": sorted(list(set(obs.source_federate_id for obs in scenario_observations))),
            "timestamp_range": {
                "start": min(obs.timestamp_utc for obs in scenario_observations).isoformat(),
                "end": max(obs.timestamp_utc for obs in scenario_observations).isoformat()
            }
        }
        
        return summary
    
    # Run scenario multiple times
    summaries = []
    
    for i in range(3):
        print(f"\n=== REPLAY SUMMARY RUN {i + 1} ===")
        summary = run_scenario_and_generate_summary()
        summaries.append(summary)
        
        print(f"Summary: {summary}")
    
    # All summaries should be identical
    first_summary = summaries[0]
    
    for i, summary in enumerate(summaries[1:], 1):
        assert summary == first_summary, \
            f"Run {i + 1} produced different summary: {summary} vs {first_summary}"
    
    print(f"\n✅ REPLAY SUMMARY DETERMINISM: All {len(summaries)} runs produced identical summaries")


def test_deterministic_ordering_of_results(belief_aggregation_service, observation_store, fixed_clock):
    """
    Test that the ordering of results is deterministic
    """
    # Create observations in random order
    base_time = fixed_clock.now()
    
    observations_data = [
        ("obs-order-3", "federate-c", base_time + timedelta(minutes=20)),
        ("obs-order-1", "federate-a", base_time),
        ("obs-order-2", "federate-b", base_time + timedelta(minutes=10))
    ]
    
    def run_with_order(order):
        """Run with specific observation order"""
        observation_store._observations.clear()
        observation_store._beliefs.clear()
        
        # Store observations in specified order
        for obs_id, federate_id, timestamp in order:
            obs = ObservationV1(
                observation_id=obs_id,
                source_federate_id=federate_id,
                timestamp_utc=timestamp,
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
            observation_store.store_observation(obs)
        
        beliefs = belief_aggregation_service.aggregate_observations()
        
        # Return ordered results
        return [
            {
                "belief_id": b.belief_id,
                "confidence": b.confidence,
                "source_observations": sorted(b.source_observations)
            }
            for b in beliefs
        ]
    
    # Test with different input orders
    results = []
    
    for i, order in enumerate([
        observations_data,  # Original order
        list(reversed(observations_data)),  # Reversed order
        observations_data  # Original order again
    ]):
        print(f"\n=== ORDERING TEST {i + 1} ===")
        result = run_with_order(order)
        results.append(result)
        print(f"Result: {result}")
    
    # All results should be identical regardless of input order
    first_result = results[0]
    
    for i, result in enumerate(results[1:], 1):
        assert result == first_result, \
            f"Ordering test {i + 1} produced different result: {result} vs {first_result}"
    
    print(f"\n✅ ORDERING DETERMINISM: All {len(results)} runs produced identical results")
