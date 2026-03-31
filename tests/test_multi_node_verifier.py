"""
Tests for Multi-Node Replay Verifier

Tests deterministic consensus validation across independent replay nodes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from exoarmur.replay.multi_node_verifier import (
    MultiNodeReplayVerifier,
    ConsensusResult,
    NodeResult,
    DivergenceReport
)
from exoarmur.replay.canonical_utils import to_canonical_event, stable_hash, canonical_json
from exoarmur.replay.event_envelope import CanonicalEvent
from exoarmur.replay.replay_engine import ReplayEngine, ReplayResult

# Import contract models
import sys
import os
from exoarmur.spec.contracts.models_v1 import AuditRecordV1


class TestMultiNodeReplayVerifier:
    """Test multi-node replay verifier functionality"""
    
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
    def verifier(self):
        """Create multi-node verifier for testing"""
        return MultiNodeReplayVerifier(node_count=3)
    
    def test_verifier_initialization(self):
        """Test verifier initialization with valid parameters"""
        verifier = MultiNodeReplayVerifier(node_count=3)
        assert verifier.node_count == 3
        
        verifier = MultiNodeReplayVerifier(node_count=5)
        assert verifier.node_count == 5
    
    def test_verifier_initialization_invalid_node_count(self):
        """Test verifier initialization rejects invalid node count"""
        with pytest.raises(ValueError, match="node_count must be at least 2"):
            MultiNodeReplayVerifier(node_count=1)
        
        with pytest.raises(ValueError, match="node_count must be at least 2"):
            MultiNodeReplayVerifier(node_count=0)
    
    def test_consensus_success_identical_inputs(self, verifier, sample_canonical_events):
        """Test consensus achieved with identical inputs across nodes"""
        correlation_id = "test-consensus-success"
        
        # Verify consensus with identical inputs
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id
        )
        
        # Assert consensus achieved
        assert divergence_report.consensus_result == ConsensusResult.CONSENSUS
        assert not divergence_report.has_divergence()
        assert len(divergence_report.divergent_nodes) == 0
        assert len(divergence_report.node_hashes) == verifier.node_count
        
        # Assert all nodes have identical hashes
        unique_hashes = set(divergence_report.node_hashes.values())
        assert len(unique_hashes) == 1
        
        # Assert consensus details
        consensus_hash = list(unique_hashes)[0]
        assert divergence_report.divergence_details["consensus_hash"] == consensus_hash
        assert len(consensus_hash) == 64  # SHA-256 hex length
        
        # Assert all nodes are consensus nodes
        consensus_nodes = divergence_report.get_consensus_nodes()
        assert len(consensus_nodes) == verifier.node_count
        assert set(consensus_nodes) == set(divergence_report.node_hashes.keys())
    
    def test_divergence_detection_payload_modification(self, verifier, sample_canonical_events):
        """Test divergence detection with payload modification"""
        correlation_id = "test-divergence-payload"
        
        # Inject divergence by modifying payload in one node
        node_inputs = verifier.inject_divergence(
            base_events=sample_canonical_events,
            target_node="node-2",
            divergence_type="payload"
        )
        
        # Verify divergence is detected
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=node_inputs
        )
        
        # Assert divergence detected
        assert divergence_report.consensus_result == ConsensusResult.DIVERGENCE
        assert divergence_report.has_divergence()
        assert len(divergence_report.divergent_nodes) == 1
        assert "node-2" in divergence_report.divergent_nodes
        
        # Assert hash distribution shows divergence
        hash_distribution = divergence_report.divergence_details["hash_distribution"]
        assert len(hash_distribution) == 2  # Two different hashes
        
        # Assert majority consensus exists
        majority_hash = divergence_report.divergence_details["majority_hash"]
        majority_count = divergence_report.divergence_details["majority_node_count"]
        assert majority_count == 2  # 2 out of 3 nodes agree
        assert divergence_report.divergence_details["divergent_node_count"] == 1
        
        # Assert consensus nodes exclude divergent node
        consensus_nodes = divergence_report.get_consensus_nodes()
        assert len(consensus_nodes) == 2
        assert "node-2" not in consensus_nodes
    
    def test_divergence_detection_event_type_modification(self, verifier, sample_canonical_events):
        """Test divergence detection with event type modification"""
        correlation_id = "test-divergence-event-type"
        
        # Inject divergence by modifying event type in one node
        node_inputs = verifier.inject_divergence(
            base_events=sample_canonical_events,
            target_node="node-3",
            divergence_type="event_type"
        )
        
        # Verify divergence is detected
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=node_inputs
        )
        
        # Assert divergence detected
        assert divergence_report.consensus_result == ConsensusResult.DIVERGENCE
        assert divergence_report.has_divergence()
        assert "node-3" in divergence_report.divergent_nodes
        
        # Assert canonical outputs differ
        canonical_outputs = divergence_report.canonical_outputs
        assert len(canonical_outputs) == verifier.node_count
        
        # Find the divergent output
        node3_output = canonical_outputs["node-3"]
        other_outputs = [output for node_id, output in canonical_outputs.items() if node_id != "node-3"]
        
        # At least one other node should have different output
        assert any(node3_output != other_output for other_output in other_outputs)
    
    def test_divergence_detection_sequence_modification(self, verifier, sample_canonical_events):
        """Test divergence detection with sequence number modification"""
        correlation_id = "test-divergence-sequence"
        
        # Inject divergence by modifying sequence numbers in one node
        node_inputs = verifier.inject_divergence(
            base_events=sample_canonical_events,
            target_node="node-1",
            divergence_type="sequence"
        )
        
        # Verify divergence is detected
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=node_inputs
        )
        
        # Assert divergence detected
        assert divergence_report.consensus_result == ConsensusResult.DIVERGENCE
        assert divergence_report.has_divergence()
        assert "node-1" in divergence_report.divergent_nodes
    
    def test_deterministic_replay_across_nodes(self, verifier, sample_canonical_events):
        """Test that replay is deterministic across independent node executions"""
        correlation_id = "test-deterministic"
        
        # Run consensus verification multiple times with the same correlation_id
        reports = []
        for i in range(3):
            report = verifier.verify_consensus(
                canonical_events=sample_canonical_events,
                correlation_id=correlation_id  # Use same correlation_id for determinism
            )
            reports.append(report)
        
        # All runs should achieve consensus
        for i, report in enumerate(reports):
            assert report.consensus_result == ConsensusResult.CONSENSUS, f"Run {i+1} failed to achieve consensus"
        
        # Hashes should be identical across runs (deterministic)
        consensus_hashes = [list(set(report.node_hashes.values()))[0] for report in reports]
        assert len(set(consensus_hashes)) == 1, "Replay hashes are not deterministic across runs"
    
    def test_node_result_hash_verification(self, sample_canonical_events):
        """Test NodeResult hash verification"""
        correlation_id = "test-node-result"
        
        # Create a replay engine and run replay
        audit_store = {correlation_id: sample_canonical_events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        replay_report = replay_engine.replay_correlation(correlation_id)
        
        # Generate canonical output and hash
        canonical_output = canonical_json(replay_report.to_dict())
        output_hash = stable_hash(canonical_output)
        
        # Create NodeResult with correct hash
        node_result = NodeResult(
            node_id="test-node",
            correlation_id=correlation_id,
            replay_report=replay_report,
            canonical_output=canonical_output,
            output_hash=output_hash
        )
        
        # Should not raise exception
        assert node_result.output_hash == output_hash
        assert node_result.node_id == "test-node"
    
    def test_node_result_hash_mismatch_rejection(self, sample_canonical_events):
        """Test NodeResult rejects hash mismatch"""
        correlation_id = "test-node-result-mismatch"
        
        # Create a replay engine and run replay
        audit_store = {correlation_id: sample_canonical_events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        replay_report = replay_engine.replay_correlation(correlation_id)
        
        # Generate canonical output and wrong hash
        canonical_output = canonical_json(replay_report.to_dict())
        wrong_hash = "wrong_hash_value"
        
        # NodeResult should reject hash mismatch
        with pytest.raises(ValueError, match="Hash mismatch"):
            NodeResult(
                node_id="test-node",
                correlation_id=correlation_id,
                replay_report=replay_report,
                canonical_output=canonical_output,
                output_hash=wrong_hash
            )
    
    def test_divergence_report_structure(self, verifier, sample_canonical_events):
        """Test DivergenceReport structure and methods"""
        correlation_id = "test-report-structure"
        
        # Test consensus report structure
        consensus_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id
        )
        
        assert isinstance(consensus_report, DivergenceReport)
        assert hasattr(consensus_report, 'consensus_result')
        assert hasattr(consensus_report, 'node_hashes')
        assert hasattr(consensus_report, 'divergent_nodes')
        assert hasattr(consensus_report, 'canonical_outputs')
        assert hasattr(consensus_report, 'divergence_details')
        
        # Test consensus details
        assert "consensus_hash" in consensus_report.divergence_details
        
        # Test divergence report structure
        node_inputs = verifier.inject_divergence(
            base_events=sample_canonical_events,
            target_node="node-2",
            divergence_type="payload"
        )
        
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=node_inputs
        )
        
        # Verify divergence details structure
        details = divergence_report.divergence_details
        assert "majority_hash" in details
        assert "hash_distribution" in details
        assert "divergent_hash_count" in details
        assert "majority_node_count" in details
        assert "divergent_node_count" in details
    
    def test_inject_divergence_invalid_target_node(self, verifier, sample_canonical_events):
        """Test divergence injection with invalid target node"""
        with pytest.raises(ValueError, match="Target node invalid-node not found"):
            verifier.inject_divergence(
                base_events=sample_canonical_events,
                target_node="invalid-node",
                divergence_type="payload"
            )
    
    def test_verify_consensus_invalid_node_inputs(self, verifier, sample_canonical_events):
        """Test verify_consensus with invalid node_inputs structure"""
        correlation_id = "test-invalid-inputs"
        
        # Test wrong number of node inputs
        invalid_inputs = {"node-1": sample_canonical_events}  # Only 1 node, but verifier expects 3
        result = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=invalid_inputs
        )
        assert result.consensus_result == ConsensusResult.ERROR
        assert "node_inputs must have exactly 3 entries" in result.divergence_details["error"]
        
        # Test non-list inputs
        invalid_inputs = {
            "node-1": sample_canonical_events,
            "node-2": sample_canonical_events,
            "node-3": "not_a_list"  # Invalid
        }
        result = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=invalid_inputs
        )
        assert result.consensus_result == ConsensusResult.ERROR
        assert "node-3 inputs must be a list" in result.divergence_details["error"]
        
        # Test non-CanonicalEvent inputs
        invalid_inputs = {
            "node-1": sample_canonical_events,
            "node-2": sample_canonical_events,
            "node-3": ["not_a_canonical_event"]  # Invalid
        }
        result = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=invalid_inputs
        )
        assert result.consensus_result == ConsensusResult.ERROR
        assert "node-3 contains non-CanonicalEvent input" in result.divergence_details["error"]
    
    def test_empty_events_handling(self, verifier):
        """Test verifier behavior with empty events"""
        correlation_id = "test-empty-events"
        empty_events = []
        
        # Should handle empty events gracefully
        divergence_report = verifier.verify_consensus(
            canonical_events=empty_events,
            correlation_id=correlation_id
        )
        
        # All nodes should get the same result (failure due to no events)
        assert divergence_report.consensus_result == ConsensusResult.CONSENSUS
        assert not divergence_report.has_divergence()
        assert len(divergence_report.node_hashes) == verifier.node_count
    
    def test_multiple_divergent_nodes(self, verifier, sample_canonical_events):
        """Test handling of multiple divergent nodes"""
        correlation_id = "test-multiple-divergence"
        
        # Create inputs with two divergent nodes by modifying them separately
        node_inputs = verifier._generate_identical_inputs(sample_canonical_events)
        
        # Modify node-2 with payload divergence
        node2_events = []
        for event in node_inputs["node-2"]:
            event_dict = event.to_dict()
            if event_dict.get("payload"):
                payload = event_dict["payload"].copy()
                if isinstance(payload, dict):
                    payload["divergence_marker"] = "modified_for_node-2"
                    if "ref" in payload and isinstance(payload["ref"], dict):
                        payload["ref"]["divergence_injected"] = True
                    event_dict["payload"] = payload
                    event_dict["payload_hash"] = stable_hash(canonical_json(payload))
            event_dict["event_id"] = f"{event_dict['event_id']}_divergent_node-2"
            node2_events.append(CanonicalEvent(**event_dict))
        node_inputs["node-2"] = node2_events
        
        # Modify node-3 with event type divergence
        node3_events = []
        for event in node_inputs["node-3"]:
            event_dict = event.to_dict()
            if event_dict.get("event_type"):
                original_type = event_dict["event_type"]
                if original_type == "telemetry_ingested":
                    event_dict["event_type"] = "safety_gate_evaluated"
                elif original_type == "safety_gate_evaluated":
                    event_dict["event_type"] = "approval_requested"
                else:
                    event_dict["event_type"] = f"{original_type}_modified"
            event_dict["event_id"] = f"{event_dict['event_id']}_divergent_node-3"
            node3_events.append(CanonicalEvent(**event_dict))
        node_inputs["node-3"] = node3_events
        
        # Verify consensus analysis
        divergence_report = verifier.verify_consensus(
            canonical_events=sample_canonical_events,
            correlation_id=correlation_id,
            node_inputs=node_inputs
        )
        
        # Should detect divergence
        assert divergence_report.consensus_result == ConsensusResult.DIVERGENCE
        assert divergence_report.has_divergence()
        
        # Should identify both divergent nodes
        divergent_nodes = set(divergence_report.divergent_nodes)
        assert "node-2" in divergent_nodes
        assert "node-3" in divergent_nodes
        
        # Should have only one consensus node
        consensus_nodes = divergence_report.get_consensus_nodes()
        assert len(consensus_nodes) == 1
        assert "node-1" in consensus_nodes
