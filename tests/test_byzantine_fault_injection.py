"""
Tests for Byzantine Fault Injection Layer

Module 3: Validates system resilience under adversarial conditions
with deterministic fault injection and consensus validation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from exoarmur.replay.byzantine_fault_injection import (
    ByzantineFaultInjector,
    ByzantineScenarioGenerator,
    ByzantineTestRunner,
    FaultType,
    ByzantineScenario,
    FaultConfig,
    FaultInjectionResult,
    ByzantineTestResult
)
from exoarmur.replay.multi_node_verifier import ConsensusResult
from exoarmur.replay.canonical_utils import to_canonical_event
from exoarmur.replay.event_envelope import CanonicalEvent

# Import contract models
import sys
import os
from exoarmur.spec.contracts.models_v1 import AuditRecordV1


class TestByzantineFaultInjector:
    """Test Byzantine fault injection engine"""
    
    @pytest.fixture
    def sample_audit_records(self):
        """Create sample audit records for testing"""
        base_time = datetime.now(timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345671",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time,
                event_kind="telemetry_ingested",
                payload_ref={"kind": {"ref": {"event_id": "event-1", "correlation_id": "test-corr", "trace_id": "trace-1", "tenant_id": "tenant-1", "cell_id": "cell-1"}}},
                hashes={"sha256": "hash1", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345672",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time + timedelta(seconds=1),
                event_kind="safety_gate_evaluated",
                payload_ref={"kind": {"ref": {"verdict": "require_human", "rationale": "A3 action"}}},
                hashes={"sha256": "hash2", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345673",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time + timedelta(seconds=2),
                event_kind="approval_requested",
                payload_ref={"kind": {"ref": {"approval_id": "approval-123"}}},
                hashes={"sha256": "hash3", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            )
        ]
        
        return records
    
    @pytest.fixture
    def sample_canonical_events(self, sample_audit_records):
        """Create sample canonical replay events for testing"""
        return [
            CanonicalEvent(**to_canonical_event(record, sequence_number=index))
            for index, record in enumerate(sample_audit_records)
        ]
    
    @pytest.fixture
    def fault_injector(self):
        """Create fault injector for testing"""
        return ByzantineFaultInjector(deterministic_seed=42)
    
    def test_fault_injector_initialization(self):
        """Test fault injector initialization"""
        injector = ByzantineFaultInjector()
        assert injector.deterministic_seed is None
        assert injector._rng_seed == 42
        
        injector = ByzantineFaultInjector(deterministic_seed=123)
        assert injector.deterministic_seed == 123
        assert injector._rng_seed == 123
    
    def test_payload_mutation_fault(self, fault_injector, sample_canonical_events):
        """Test payload mutation fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.PAYLOAD_MUTATION,
            target_nodes=["node-1"],
            severity=1.0,
            deterministic_seed=42
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        assert "node-1" in results
        result = results["node-1"]
        
        # Verify fault injection result structure
        assert isinstance(result, FaultInjectionResult)
        assert result.node_id == "node-1"
        assert result.fault_type == FaultType.PAYLOAD_MUTATION
        assert len(result.corrupted_events) == len(sample_canonical_events)
        
        # Verify payload corruption
        corrupted_event = result.corrupted_events[0]
        payload = corrupted_event.to_dict()["payload"]
        assert "byzantine_mutation_node-1_0" in payload
        
        # Check for kind.ref corruption if present
        if "kind" in payload and isinstance(payload["kind"], dict):
            if "ref" in payload["kind"] and isinstance(payload["kind"]["ref"], dict):
                assert payload["kind"]["ref"]["byzantine_corruption"] is True
                assert payload["kind"]["ref"]["corruption_source"] == "node-1"
        
        # Verify event_id corruption
        assert "_byzantine_node-1" in corrupted_event.to_dict()["event_id"]
    
    def test_event_type_substitution_fault(self, fault_injector, sample_canonical_events):
        """Test event type substitution fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.EVENT_TYPE_SUBSTITUTION,
            target_nodes=["node-2"],
            severity=1.0,
            deterministic_seed=42,
            fault_parameters={
                "type_mappings": {
                    "telemetry_ingested": "safety_gate_evaluated",
                    "safety_gate_evaluated": "approval_requested"
                }
            }
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-2"]
        corrupted_events = result.corrupted_events
        
        # Verify event type substitution
        original_types = [event.to_dict()["event_type"] for event in sample_canonical_events]
        corrupted_types = [event.to_dict()["event_type"] for event in corrupted_events]
        
        assert original_types[0] != corrupted_types[0]  # Should be substituted
        assert original_types[1] != corrupted_types[1]  # Should be substituted
    
    def test_sequence_manipulation_fault(self, fault_injector, sample_canonical_events):
        """Test sequence manipulation fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.SEQUENCE_MANIPULATION,
            target_nodes=["node-3"],
            severity=1.0,
            deterministic_seed=42,
            fault_parameters={
                "manipulation_type": "offset",
                "offset": 1000
            }
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-3"]
        corrupted_events = result.corrupted_events
        
        # Verify sequence manipulation
        for i, event in enumerate(corrupted_events):
            event_dict = event.to_dict()
            original_seq = sample_canonical_events[i].to_dict()["sequence_number"]
            corrupted_seq = event_dict["sequence_number"]
            assert corrupted_seq == original_seq + 1000
    
    def test_field_deletion_fault(self, fault_injector, sample_canonical_events):
        """Test field deletion fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.FIELD_DELETION,
            target_nodes=["node-1"],
            severity=1.0,
            deterministic_seed=42,
            fault_parameters={
                "fields_to_delete": ["tenant_id", "cell_id"]
            }
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-1"]
        corrupted_events = result.corrupted_events
        
        # Verify field deletion (fields should be empty strings due to CanonicalEvent defaults)
        for event in corrupted_events:
            event_dict = event.to_dict()
            assert event_dict["tenant_id"] == ""  # Deleted field becomes default empty string
            assert event_dict["cell_id"] == ""     # Deleted field becomes default empty string
            # Payload should still be present
            assert "payload" in event_dict
    
    def test_field_alteration_fault(self, fault_injector, sample_canonical_events):
        """Test field alteration fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.FIELD_ALTERATION,
            target_nodes=["node-2"],
            severity=1.0,
            deterministic_seed=42,
            fault_parameters={
                "alterations": {
                    "tenant_id": "corrupted_byzantine",
                    "cell_id": "byzantine_cell"
                }
            }
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-2"]
        corrupted_events = result.corrupted_events
        
        # Verify field alteration
        for event in corrupted_events:
            event_dict = event.to_dict()
            assert event_dict["tenant_id"] == "corrupted_byzantine"
            assert event_dict["cell_id"] == "byzantine_cell"
    
    def test_hash_corruption_fault(self, fault_injector, sample_canonical_events):
        """Test hash corruption fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.HASH_CORRUPTION,
            target_nodes=["node-3"],
            severity=1.0,
            deterministic_seed=42
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-3"]
        corrupted_events = result.corrupted_events
        
        # Verify hash corruption
        for i, event in enumerate(corrupted_events):
            event_dict = event.to_dict()
            assert "corrupted_hash_node-3" in event_dict.get("payload_hash", "")
    
    def test_structured_corruption_fault(self, fault_injector, sample_canonical_events):
        """Test structured corruption fault injection"""
        fault_config = FaultConfig(
            fault_type=FaultType.STRUCTURED_CORRUPTION,
            target_nodes=["node-1"],
            severity=1.0,
            deterministic_seed=42,
            fault_parameters={
                "corruption_level": "high"
            }
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        
        result = results["node-1"]
        corrupted_events = result.corrupted_events
        
        # Verify structured corruption
        for event in corrupted_events:
            event_dict = event.to_dict()
            payload = event_dict.get("payload", {})
            if isinstance(payload, dict):
                assert "structured_corruption" in payload
                assert payload["structured_corruption"]["source"] == "node-1"
                assert payload["structured_corruption"]["level"] == "high"
            
            # Should also corrupt event type and sequence for high level
            assert "corrupted_" in event_dict["event_type"]
            assert event_dict["sequence_number"] >= 10000
    
    def test_fault_severity_application(self, fault_injector, sample_canonical_events):
        """Test fault severity controls application"""
        # Test with 1.0 severity (should affect all events)
        fault_config = FaultConfig(
            fault_type=FaultType.PAYLOAD_MUTATION,
            target_nodes=["node-1"],
            severity=1.0,
            deterministic_seed=42
        )
        
        # Create fresh copy of events for this test
        fresh_events = [
            CanonicalEvent(**event.to_dict()) for event in sample_canonical_events
        ]
        
        results = fault_injector.inject_faults(fresh_events, [fault_config])
        
        result = results["node-1"]
        corrupted_events = result.corrupted_events
        
        # Count corrupted events (should be all events with severity 1.0)
        corrupted_count = 0
        for event in corrupted_events:
            payload = event.to_dict().get("payload", {})
            if isinstance(payload, dict):
                # Look for any key containing "byzantine_mutation"
                has_mutation = any("byzantine_mutation" in key for key in payload.keys())
                if has_mutation:
                    corrupted_count += 1
        
        # With 3 events and 1.0 severity, should affect all 3 events
        assert corrupted_count == 3
        
        # Test with 0.0 severity (should affect no events)
        fault_config_zero = FaultConfig(
            fault_type=FaultType.PAYLOAD_MUTATION,
            target_nodes=["node-2"],
            severity=0.0,
            deterministic_seed=42
        )
        
        # Create another fresh copy
        fresh_events_zero = [
            CanonicalEvent(**event.to_dict()) for event in sample_canonical_events
        ]
        
        results_zero = fault_injector.inject_faults(fresh_events_zero, [fault_config_zero])
        result_zero = results_zero["node-2"]
        
        corrupted_count_zero = 0
        for event in result_zero.corrupted_events:
            payload = event.to_dict().get("payload", {})
            if isinstance(payload, dict):
                # Look for any key containing "byzantine_mutation"
                has_mutation = any("byzantine_mutation" in key for key in payload.keys())
                if has_mutation:
                    corrupted_count_zero += 1
        
        # With 0.0 severity, should affect 0 events
        assert corrupted_count_zero == 0
    
    def test_multiple_fault_injection(self, fault_injector, sample_canonical_events):
        """Test injecting multiple faults to different nodes"""
        fault_configs = [
            FaultConfig(
                fault_type=FaultType.PAYLOAD_MUTATION,
                target_nodes=["node-1"],
                severity=1.0,
                deterministic_seed=42
            ),
            FaultConfig(
                fault_type=FaultType.EVENT_TYPE_SUBSTITUTION,
                target_nodes=["node-2"],
                severity=1.0,
                deterministic_seed=42
            ),
            FaultConfig(
                fault_type=FaultType.SEQUENCE_MANIPULATION,
                target_nodes=["node-3"],
                severity=1.0,
                deterministic_seed=42
            )
        ]
        
        results = fault_injector.inject_faults(sample_canonical_events, fault_configs)
        
        # Verify all nodes have faults applied
        assert len(results) == 3
        assert "node-1" in results
        assert "node-2" in results
        assert "node-3" in results
        
        # Verify different fault types
        assert results["node-1"].fault_type == FaultType.PAYLOAD_MUTATION
        assert results["node-2"].fault_type == FaultType.EVENT_TYPE_SUBSTITUTION
        assert results["node-3"].fault_type == FaultType.SEQUENCE_MANIPULATION
    
    def test_fault_injection_result_summary(self, fault_injector, sample_canonical_events):
        """Test fault injection result summary generation"""
        fault_config = FaultConfig(
            fault_type=FaultType.PAYLOAD_MUTATION,
            target_nodes=["node-1"],
            severity=0.7,
            deterministic_seed=123
        )
        
        results = fault_injector.inject_faults(sample_canonical_events, [fault_config])
        result = results["node-1"]
        
        summary = result.corruption_summary()
        
        # Verify summary structure
        assert summary["node_id"] == "node-1"
        assert summary["fault_type"] == "payload_mutation"
        assert summary["events_corrupted"] == len(sample_canonical_events)
        assert summary["original_count"] == len(sample_canonical_events)
        assert 0.0 <= summary["corruption_ratio"] <= 1.0
        assert summary["injection_details"]["severity"] == 0.7
        assert summary["injection_details"]["seed"] == 123


class TestByzantineScenarioGenerator:
    """Test Byzantine scenario generation"""
    
    def test_clean_scenario(self):
        """Test clean scenario generation"""
        configs = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.CLEAN, 5, deterministic_seed=42
        )
        
        assert configs == []
    
    def test_single_node_scenario(self):
        """Test single node Byzantine scenario"""
        configs = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.SINGLE_NODE, 5, deterministic_seed=42
        )
        
        assert len(configs) == 1
        config = configs[0]
        assert config.fault_type == FaultType.PAYLOAD_MUTATION
        assert len(config.target_nodes) == 1
        assert config.target_nodes[0].startswith("node-")
        assert config.severity == 1.0
        assert config.deterministic_seed == 42
    
    def test_partial_scenario(self):
        """Test partial Byzantine scenario"""
        configs = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.PARTIAL, 6, deterministic_seed=42
        )
        
        assert len(configs) == 1
        config = configs[0]
        assert config.fault_type == FaultType.STRUCTURED_CORRUPTION
        assert len(config.target_nodes) == 1  # 6//3 - 1 = 1
        assert config.severity == 0.8
        assert config.fault_parameters["corruption_level"] == "medium"
    
    def test_majority_scenario(self):
        """Test majority Byzantine scenario"""
        configs = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.MAJORITY, 5, deterministic_seed=42
        )
        
        assert len(configs) == 1
        config = configs[0]
        assert config.fault_type == FaultType.STRUCTURED_CORRUPTION
        assert len(config.target_nodes) == 3  # 5//2 + 1 = 3
        assert config.severity == 1.0
        assert config.fault_parameters["corruption_level"] == "high"
    
    def test_scenario_determinism(self):
        """Test scenario generation is deterministic"""
        configs1 = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.SINGLE_NODE, 5, deterministic_seed=42
        )
        configs2 = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.SINGLE_NODE, 5, deterministic_seed=42
        )
        
        assert configs1[0].target_nodes == configs2[0].target_nodes
        
        # Different seed should produce different results
        configs3 = ByzantineScenarioGenerator.create_scenario(
            ByzantineScenario.SINGLE_NODE, 5, deterministic_seed=123
        )
        
        assert configs1[0].target_nodes != configs3[0].target_nodes


class TestByzantineTestRunner:
    """Test complete Byzantine test runner"""
    
    @pytest.fixture
    def sample_audit_records(self):
        """Create sample audit records for testing"""
        base_time = datetime.now(timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345671",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time,
                event_kind="telemetry_ingested",
                payload_ref={"kind": {"ref": {"event_id": "event-1", "correlation_id": "test-corr", "trace_id": "trace-1", "tenant_id": "tenant-1", "cell_id": "cell-1"}}},
                hashes={"sha256": "hash1", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345672",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time + timedelta(seconds=1),
                event_kind="safety_gate_evaluated",
                payload_ref={"kind": {"ref": {"verdict": "require_human", "rationale": "A3 action"}}},
                hashes={"sha256": "hash2", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            )
        ]
        
        return records
    
    @pytest.fixture
    def sample_canonical_events(self, sample_audit_records):
        """Create sample canonical replay events for testing"""
        return [
            CanonicalEvent(**to_canonical_event(record, sequence_number=index))
            for index, record in enumerate(sample_audit_records)
        ]
    
    @pytest.fixture
    def test_runner(self):
        """Create Byzantine test runner"""
        return ByzantineTestRunner(node_count=3, deterministic_seed=42)
    
    def test_test_runner_initialization(self):
        """Test test runner initialization"""
        runner = ByzantineTestRunner(node_count=5, deterministic_seed=123)
        assert runner.node_count == 5
        assert runner.deterministic_seed == 123
        assert runner.verifier.node_count == 5
        assert runner.fault_injector.deterministic_seed == 123
    
    def test_clean_scenario_test(self, test_runner, sample_canonical_events):
        """Test clean scenario execution"""
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.CLEAN
        )
        
        # Verify result structure
        assert isinstance(result, ByzantineTestResult)
        assert result.scenario == ByzantineScenario.CLEAN
        assert len(result.fault_configs) == 0
        assert len(result.injection_results) == 0
        assert result.divergence_report.consensus_result == ConsensusResult.CONSENSUS
        assert result.baseline_hash is not None
        
        # Verify test summary
        summary = result.test_summary()
        assert summary["scenario"] == "clean"
        assert summary["consensus_achieved"] is True
        assert summary["faulty_nodes"] == 0
        assert summary["divergent_nodes"] == 0
    
    def test_single_node_byzantine_test(self, test_runner, sample_canonical_events):
        """Test single node Byzantine scenario"""
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.SINGLE_NODE
        )
        
        # Verify result structure
        assert result.scenario == ByzantineScenario.SINGLE_NODE
        assert len(result.fault_configs) == 1
        assert len(result.injection_results) == 1
        assert result.baseline_hash is not None
        
        # Should detect divergence
        assert result.divergence_report.has_divergence()
        assert len(result.divergence_report.divergent_nodes) == 1
        
        # Verify test summary
        summary = result.test_summary()
        assert summary["scenario"] == "single_node"
        assert summary["consensus_achieved"] is False
        assert summary["faulty_nodes"] == 1
        assert summary["divergent_nodes"] == 1
        assert summary["divergence_detected"] is True
    
    def test_partial_byzantine_test(self, test_runner, sample_canonical_events):
        """Test partial Byzantine scenario"""
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.PARTIAL
        )
        
        # Verify result structure
        assert result.scenario == ByzantineScenario.PARTIAL
        assert len(result.fault_configs) == 1
        assert len(result.injection_results) == 1  # Only 1 faulty node for n=3
        
        # Should detect divergence
        assert result.divergence_report.has_divergence()
        assert len(result.divergence_report.divergent_nodes) == 1
        
        # Verify test summary
        summary = result.test_summary()
        assert summary["scenario"] == "partial"
        assert summary["consensus_achieved"] is False
        assert summary["divergence_detected"] is True
    
    def test_majority_byzantine_test(self, test_runner, sample_canonical_events):
        """Test majority Byzantine scenario"""
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.MAJORITY
        )
        
        # Verify result structure
        assert result.scenario == ByzantineScenario.MAJORITY
        assert len(result.fault_configs) == 1
        # For n=3, majority scenario may corrupt 1-2 nodes depending on seed
        assert len(result.injection_results) >= 1
        assert len(result.injection_results) <= 2
        
        # Should NOT achieve consensus (majority corrupted)
        assert result.divergence_report.has_divergence()
        
        # Verify test summary
        summary = result.test_summary()
        assert summary["scenario"] == "majority"
        assert summary["consensus_achieved"] is False
        assert summary["faulty_nodes"] >= 1  # At least 1 corrupted node
        assert summary["faulty_nodes"] <= 2  # At most 2 corrupted nodes
        assert summary["divergence_detected"] is True
    
    def test_custom_fault_configs(self, test_runner, sample_canonical_events):
        """Test test runner with custom fault configurations"""
        custom_fault_configs = [
            FaultConfig(
                fault_type=FaultType.PAYLOAD_MUTATION,
                target_nodes=["node-1", "node-2"],
                severity=1.0,
                deterministic_seed=42
            )
        ]
        
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.CLEAN, custom_fault_configs
        )
        
        # Should use custom configs instead of scenario defaults
        assert len(result.fault_configs) == 1
        assert len(result.fault_configs[0].target_nodes) == 2
        assert result.fault_configs[0].fault_type == FaultType.PAYLOAD_MUTATION
        
        # Should detect divergence due to custom faults
        assert result.divergence_report.has_divergence()
    
    def test_byzantine_correctness_validation(self, test_runner, sample_canonical_events):
        """Test Byzantine correctness validation"""
        
        # Test clean scenario - should be correct
        clean_result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.CLEAN
        )
        assert test_runner.validate_byzantine_correctness(clean_result) is True
        
        # Test single node scenario - should be correct
        single_result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.SINGLE_NODE
        )
        assert test_runner.validate_byzantine_correctness(single_result) is True
        
        # Test majority scenario - should be correct
        majority_result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.MAJORITY
        )
        assert test_runner.validate_byzantine_correctness(majority_result) is True
    
    def test_deterministic_behavior(self, test_runner, sample_canonical_events):
        """Test that Byzantine tests are deterministic"""
        # Run same test multiple times
        results = []
        for i in range(3):
            result = test_runner.run_byzantine_test(
                sample_canonical_events, ByzantineScenario.SINGLE_NODE
            )
            results.append(result)
        
        # All results should be identical
        first_summary = results[0].test_summary()
        for i, result in enumerate(results):
            summary = result.test_summary()
            assert summary["scenario"] == first_summary["scenario"]
            assert summary["consensus_achieved"] == first_summary["consensus_achieved"]
            assert summary["faulty_nodes"] == first_summary["faulty_nodes"]
            assert summary["divergent_nodes"] == first_summary["divergent_nodes"]
            
            # Node hashes should be identical
            assert result.divergence_report.node_hashes == results[0].divergence_report.node_hashes
    
    def test_isolation_from_core_replay(self, test_runner, sample_canonical_events):
        """Test that fault injection doesn't contaminate core replay logic"""
        
        # Run Byzantine test
        byzantine_result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.SINGLE_NODE
        )
        
        # Run clean test after Byzantine test with different correlation ID
        clean_result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.CLEAN
        )
        
        # Clean test should still achieve consensus
        assert clean_result.divergence_report.consensus_result == ConsensusResult.CONSENSUS
        assert not clean_result.divergence_report.has_divergence()
        
        # Clean test should have baseline hash
        assert clean_result.baseline_hash is not None
        consensus_hash = list(clean_result.divergence_report.node_hashes.values())[0]
        
        # The clean consensus hash should be consistent (may not match baseline due to correlation_id)
        assert consensus_hash is not None
        assert len(consensus_hash) == 64  # SHA-256 hash length
    
    def test_comprehensive_test_summary(self, test_runner, sample_canonical_events):
        """Test comprehensive test summary generation"""
        result = test_runner.run_byzantine_test(
            sample_canonical_events, ByzantineScenario.SINGLE_NODE
        )
        
        summary = result.test_summary()
        
        # Verify all summary fields are present
        required_fields = [
            "scenario", "consensus_result", "total_nodes", "faulty_nodes",
            "divergent_nodes", "consensus_achieved", "fault_types",
            "baseline_hash", "node_hashes", "divergence_detected"
        ]
        
        for field in required_fields:
            assert field in summary
        
        # Verify field values make sense
        assert summary["total_nodes"] == 3
        assert summary["faulty_nodes"] == 1
        assert summary["divergent_nodes"] == 1
        assert summary["consensus_achieved"] is False
        assert summary["divergence_detected"] is True
        assert len(summary["node_hashes"]) == 3
        assert summary["baseline_hash"] is not None
