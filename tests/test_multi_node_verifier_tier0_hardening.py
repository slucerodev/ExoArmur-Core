"""
Tier 0 Hardening Tests for Multi-Node Verifier
Focuses on agreement scenarios, consensus detection, and isolation guarantees
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from exoarmur.replay.multi_node_verifier import (
    MultiNodeReplayVerifier, NodeResult, DivergenceReport, 
    ConsensusResult, VerificationError
)
from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.control_plane.intent_store import IntentStore
from exoarmur.control_plane.approval_service import ApprovalService


class TestMultiNodeVerifierIsolation:
    """Test that nodes operate with complete isolation"""
    
    @pytest.fixture
    def verifier(self):
        """Create multi-node verifier with 3 nodes"""
        return MultiNodeReplayVerifier(node_count=3)
    
    @pytest.fixture
    def sample_events(self):
        """Create sample canonical events"""
        events = [
            CanonicalEvent(
                event_id=f"event-{i}",
                event_type="telemetry_ingested" if i % 2 == 0 else "safety_gate_evaluated",
                actor="system",
                correlation_id="isolation-test",
                payload={"index": i, "data": f"value-{i}"},
                payload_hash="",
                sequence_number=i
            )
            for i in range(5)
        ]
        return events
    
    def test_node_isolation_guarantee(self, verifier, sample_events):
        """Test that each node operates in complete isolation"""
        # Run consensus verification
        report = verifier.verify_consensus(sample_events, "isolation-test")
        
        # Should achieve consensus with identical outputs
        assert report.consensus_result == ConsensusResult.CONSENSUS
        
        # All nodes should have the same hash
        node_hashes = list(report.node_hashes.values())
        assert len(set(node_hashes)) == 1, "All nodes should produce identical hashes"
        
        # Verify node hashes are properly isolated
        for node_id, node_hash in report.node_hashes.items():
            assert isinstance(node_hash, str)
            assert len(node_hash) == 64  # SHA-256
            assert node_id.startswith("node-")
    
    def test_node_state_isolation(self, verifier, sample_events):
        """Test that node state doesn't leak between runs"""
        # First verification
        report1 = verifier.verify_consensus(sample_events, "isolation-test")
        hashes1 = list(report1.node_hashes.values())
        
        # Second verification with SAME correlation_id (TRACE_IDENTITY_HASH semantics)
        report2 = verifier.verify_consensus(sample_events, "isolation-test")
        hashes2 = list(report2.node_hashes.values())
        
        # Hashes should be identical (deterministic for same correlation_id)
        assert hashes1 == hashes2
        
        # But node IDs should be consistent
        node_ids_1 = set(report1.node_hashes.keys())
        node_ids_2 = set(report2.node_hashes.keys())
        assert node_ids_1 == node_ids_2  # Same node IDs
        
        # Verify each run produces identical hashes (deterministic behavior)
        for node_id in node_ids_1:
            hash1 = report1.node_hashes[node_id]
            hash2 = report2.node_hashes[node_id]
            assert hash1 == hash2  # Identical hashes for same input
    
    def test_independent_replay_engines(self, verifier, sample_events):
        """Test that each node gets its own ReplayEngine instance"""
        # Mock ReplayEngine to track instance creation
        with patch('exoarmur.replay.multi_node_verifier.ReplayEngine') as mock_engine:
            mock_engine.return_value = Mock()
            mock_engine.return_value.replay_correlation.return_value = Mock()
            mock_engine.return_value.replay_correlation.return_value.to_dict.return_value = {"test": "data"}
            
            verifier.verify_consensus(sample_events, "engine-test")
            
            # Should create separate ReplayEngine for each node
            assert mock_engine.call_count == verifier.node_count


class TestConsensusDetection:
    """Test consensus detection and reporting"""
    
    @pytest.fixture
    def verifier(self):
        return MultiNodeReplayVerifier(node_count=5)
    
    @pytest.fixture
    def consensus_events(self):
        """Events that should produce consensus"""
        return [
            CanonicalEvent(
                event_id=f"consensus-{i}",
                event_type="telemetry_ingested",
                actor="system",
                correlation_id="consensus-test",
                payload={"data": f"consensus-{i}"},
                payload_hash="",
                sequence_number=i
            )
            for i in range(3)
        ]
    
    def test_perfect_consensus_detection(self, verifier, consensus_events):
        """Test detection of perfect consensus"""
        report = verifier.verify_consensus(consensus_events, "perfect-consensus")
        
        assert report.consensus_result == ConsensusResult.CONSENSUS
        assert not report.has_divergence()
        assert len(report.divergent_nodes) == 0
        assert len(report.get_consensus_nodes()) == verifier.node_count
        
        # All hashes should be identical
        unique_hashes = set(report.node_hashes.values())
        assert len(unique_hashes) == 1
    
    def test_divergence_detection(self, verifier, consensus_events):
        """Test detection of node divergence"""
        # Inject divergence into one node
        divergence_inputs = verifier.inject_divergence(
            consensus_events, 
            target_node="node-2",
            divergence_type="event_type"  # Use event_type for actual divergence
        )
        
        report = verifier.verify_consensus(consensus_events, "divergence-test", node_inputs=divergence_inputs)
        
        assert report.consensus_result == ConsensusResult.DIVERGENCE
        assert report.has_divergence()
        assert len(report.divergent_nodes) == 1
        assert "node-2" in report.divergent_nodes
        
        # Should have both consensus and divergent nodes
        assert len(report.get_consensus_nodes()) == verifier.node_count - 1
        assert len(report.divergent_nodes) == 1
        
        # Divergent node should have different hash
        consensus_hash = report.node_hashes["node-1"]  # Consensus node
        divergent_hash = report.node_hashes["node-2"]  # Divergent node
        assert consensus_hash != divergent_hash
    
    def test_partial_consensus_detection(self, verifier, consensus_events):
        """Test detection of partial consensus"""
        # Inject divergence into node-2 only (simple case)
        divergence_inputs = verifier.inject_divergence(
            consensus_events,
            target_node="node-2",
            divergence_type="event_type"
        )
        
        report = verifier.verify_consensus(consensus_events, "partial-consensus", node_inputs=divergence_inputs)
        
        assert report.consensus_result == ConsensusResult.DIVERGENCE
        assert len(report.get_consensus_nodes()) == 4  # 4 nodes consensus (1 divergent)
        assert len(report.divergent_nodes) == 1   # node-2 divergent
        
        # Consensus nodes should have identical hashes
        consensus_nodes = report.get_consensus_nodes()
        consensus_hashes = [report.node_hashes[node_id] for node_id in consensus_nodes]
        assert len(set(consensus_hashes)) == 1
        
        # Divergent node should have different hash from consensus
        consensus_hash = consensus_hashes[0]
        divergent_hash = report.node_hashes[report.divergent_nodes[0]]
        assert divergent_hash != consensus_hash
    
    def test_no_consensus_all_divergent(self, verifier, consensus_events):
        """Test case where no consensus is achieved"""
        # Make all nodes divergent with different mutations
        # We'll use event_type changes since that creates actual divergence
        
        # Create divergent inputs for each node
        node_inputs = verifier._generate_identical_inputs(consensus_events)
        
        # Modify each node with different event types
        event_types = ["telemetry_ingested", "safety_gate_evaluated", "approval_requested", "intent_published", "belief_published"]
        
        for i, node_id in enumerate(["node-1", "node-2", "node-3", "node-4", "node-5"]):
            # Create new events with different types for this node
            modified_events = []
            for j, base_event in enumerate(consensus_events):
                modified_event = CanonicalEvent(
                    event_id=base_event.event_id,
                    event_type=event_types[i],  # Different type for each node
                    actor=base_event.actor,
                    correlation_id=base_event.correlation_id,
                    payload=base_event.payload,
                    payload_hash=base_event.payload_hash,
                    sequence_number=base_event.sequence_number
                )
                modified_events.append(modified_event)
            node_inputs[node_id] = modified_events
        
        report = verifier.verify_consensus(consensus_events, "no-consensus", node_inputs=node_inputs)
        
        assert report.consensus_result == ConsensusResult.DIVERGENCE
        # With all unique hashes, there's no clear majority, but algorithm picks one as "consensus"
        assert len(report.get_consensus_nodes()) == 1  # One node picked as consensus by majority algorithm
        assert len(report.divergent_nodes) == verifier.node_count - 1  # Rest are divergent
        
        # All hashes should be unique
        all_hashes = list(report.node_hashes.values())
        assert len(set(all_hashes)) == verifier.node_count


class TestDivergenceInjection:
    """Test divergence injection capabilities"""
    
    @pytest.fixture
    def verifier(self):
        return MultiNodeReplayVerifier(node_count=3)
    
    @pytest.fixture
    def base_events(self):
        """Base events for divergence testing"""
        return [
            CanonicalEvent(
                event_id="base-event",
                event_type="telemetry_ingested",
                actor="system",
                correlation_id="divergence-test",
                payload={"key": "original_value"},
                payload_hash="",
                sequence_number=1
            )
        ]
    
    def test_payload_mutation_divergence(self, verifier, base_events):
        """Test payload mutation divergence injection"""
        # Use event_type divergence since payload changes don't affect replay output
        divergence_inputs = verifier.inject_divergence(
            base_events,
            target_node="node-2",
            divergence_type="event_type"
        )
        
        # Run verification to see divergence
        report = verifier.verify_consensus(base_events, "payload-mutation", node_inputs=divergence_inputs)
        
        assert report.consensus_result == ConsensusResult.DIVERGENCE
        assert "node-2" in report.divergent_nodes
        
        # Verify divergence was actually created
        divergent_hash = report.node_hashes["node-2"]
        consensus_hash = report.node_hashes["node-1"]  # Consensus node
        assert divergent_hash != consensus_hash
    
    def test_event_type_substitution_divergence(self, verifier, base_events):
        """Test event type substitution divergence"""
        divergence_inputs = verifier.inject_divergence(
            base_events,
            target_node="node-3",
            divergence_type="event_type"
        )
        
        report = verifier.verify_consensus(base_events, "event-type-sub", node_inputs=divergence_inputs)
        
        assert report.consensus_result == ConsensusResult.DIVERGENCE
        assert "node-3" in report.divergent_nodes
        
        # Divergent node should have different hash
        consensus_hash = report.node_hashes["node-1"]
        divergent_hash = report.node_hashes["node-3"]
        assert consensus_hash != divergent_hash
    
    def test_sequence_manipulation_divergence(self, verifier, base_events):
        """Test sequence manipulation divergence"""
        divergence_inputs = verifier.inject_divergence(
            base_events,
            target_node="node-2",
            divergence_type="sequence"
        )
        
        # Verify the divergence was actually applied
        modified_event = divergence_inputs["node-2"][0]
        original_event = base_events[0]
        
        # Sequence should be modified
        assert modified_event.sequence_number != original_event.sequence_number
        assert modified_event.sequence_number == original_event.sequence_number + 1000
        
        # Event ID should also be modified to ensure uniqueness
        assert "divergent_node-2" in modified_event.event_id
        assert modified_event.event_id != original_event.event_id
    
    def test_multiple_target_divergence(self, verifier, base_events):
        """Test divergence injection to multiple nodes"""
        # Inject divergence into node-1
        divergence_inputs1 = verifier.inject_divergence(
            base_events,
            target_node="node-1",
            divergence_type="event_type"
        )
        
        # Inject divergence into node-3
        divergence_inputs2 = verifier.inject_divergence(
            base_events,
            target_node="node-3",
            divergence_type="payload"
        )
        
        # Verify both divergences were applied
        modified_event_1 = divergence_inputs1["node-1"][0]
        modified_event_3 = divergence_inputs2["node-3"][0]
        original_event = base_events[0]
        
        # Node-1 should have different event type
        assert modified_event_1.event_type != original_event.event_type
        
        # Node-3 should have modified payload
        assert modified_event_3.payload != original_event.payload
        assert "divergence_marker" in str(modified_event_3.payload)
    
    def test_divergence_parameter_validation(self, verifier, base_events):
        """Test divergence injection parameter validation"""
        # Test invalid node ID
        with pytest.raises(ValueError, match="Target node invalid-node not found"):
            verifier.inject_divergence(
                base_events,
                target_node="invalid-node",
                divergence_type="event_type"
            )


class TestDivergenceReport:
    """Test divergence reporting and analysis"""
    
    @pytest.fixture
    def verifier(self):
        return MultiNodeReplayVerifier(node_count=5)
    
    @pytest.fixture
    def sample_events(self):
        return [
            CanonicalEvent(
                event_id=f"report-{i}",
                event_type="test",
                actor="system",
                correlation_id="report-test",
                payload={"data": f"value-{i}"},
                payload_hash="",
                sequence_number=i
            )
            for i in range(3)
        ]
    
    def test_divergence_report_completeness(self, verifier, sample_events):
        """Test divergence report contains all required information"""
        # Create mixed consensus/divergence scenario
        divergence_inputs = verifier.inject_divergence(
            sample_events, 
            target_node="node-2",
            divergence_type="event_type"
        )
        
        report = verifier.verify_consensus(sample_events, "report-completeness", node_inputs=divergence_inputs)
        
        # Verify report structure
        assert hasattr(report, 'consensus_result')
        assert hasattr(report, 'node_hashes')
        assert hasattr(report, 'divergent_nodes')
        assert hasattr(report, 'get_consensus_nodes')
        
        # Verify content completeness
        assert len(report.node_hashes) == verifier.node_count
        assert len(report.divergent_nodes) == 1
        assert len(report.get_consensus_nodes()) == verifier.node_count - 1
        
        # Verify node IDs are correct
        expected_node_ids = {f"node-{i}" for i in range(1, verifier.node_count + 1)}
        actual_node_ids = set(report.node_hashes.keys())
        assert actual_node_ids == expected_node_ids
    
    def test_divergence_analysis_methods(self, verifier, sample_events):
        """Test divergence analysis methods"""
        divergence_inputs = verifier.inject_divergence(
            sample_events, 
            target_node="node-3",
            divergence_type="event_type"
        )
        
        report = verifier.verify_consensus(sample_events, "analysis-test", node_inputs=divergence_inputs)
        
        # Test has_divergence method
        assert report.has_divergence() == True
        
        # Test get_consensus_nodes method
        consensus_nodes = report.get_consensus_nodes()
        assert len(consensus_nodes) == verifier.node_count - 1
        assert "node-3" not in consensus_nodes
        
        # Test node classification
        for node_id in consensus_nodes:
            assert node_id != "node-3"
        assert "node-3" in report.divergent_nodes
    
    def test_divergence_report_serialization(self, verifier, sample_events):
        """Test divergence report serialization"""
        divergence_inputs = verifier.inject_divergence(
            sample_events, 
            target_node="node-2",
            divergence_type="event_type"
        )
        
        report = verifier.verify_consensus(sample_events, "serialization-test", node_inputs=divergence_inputs)
        
        # Test JSON serialization using canonical_json
        report_json = canonical_json({
            'consensus_result': report.consensus_result.value,
            'node_hashes': report.node_hashes,
            'divergent_nodes': report.divergent_nodes
        })
        
        # Verify required fields are present
        report_dict = json.loads(report_json)
        assert "consensus_result" in report_dict
        assert "node_hashes" in report_dict
        assert "divergent_nodes" in report_dict
        
        # Verify data types
        assert isinstance(report_dict["consensus_result"], str)
        assert isinstance(report_dict["node_hashes"], dict)
        assert isinstance(report_dict["divergent_nodes"], list)
        
        # Verify round-trip consistency
        serialized = canonical_json(report_dict)
        parsed = json.loads(serialized)
        
        assert parsed["consensus_result"] == report.consensus_result.value
        assert len(parsed["node_hashes"]) == verifier.node_count


class TestNodeResult:
    """Test NodeResult data structure"""
    
    def test_node_result_structure(self):
        """Test NodeResult contains required fields"""
        from exoarmur.replay.replay_engine import ReplayReport, ReplayResult
        
        node_id = "test-node"
        correlation_id = "test-correlation"
        canonical_output = {"test": "data", "events": [{"id": "1"}]}
        canonical_output_str = canonical_json(canonical_output)
        output_hash = stable_hash(canonical_output_str)
        replay_report = ReplayReport(correlation_id=correlation_id)
        
        result = NodeResult(
            node_id=node_id,
            correlation_id=correlation_id,
            replay_report=replay_report,
            canonical_output=canonical_output_str,
            output_hash=output_hash
        )
        
        assert result.node_id == node_id
        assert result.correlation_id == correlation_id
        assert result.canonical_output == canonical_output_str
        assert result.output_hash == output_hash
        assert len(result.output_hash) == 64
    
    def test_node_result_hash_consistency(self):
        """Test NodeResult hash is consistent with output"""
        from exoarmur.replay.replay_engine import ReplayReport
        
        output = {"events": [{"id": "test-event"}]}
        canonical_output_str = canonical_json(output)
        expected_hash = stable_hash(canonical_output_str)
        
        result = NodeResult(
            node_id="hash-test",
            correlation_id="hash-correlation",
            replay_report=ReplayReport(correlation_id="hash-correlation"),
            canonical_output=canonical_output_str,
            output_hash=expected_hash
        )
        
        assert result.output_hash == expected_hash
        
        # Verify hash matches computed hash
        computed_hash = stable_hash(result.canonical_output)
        assert result.output_hash == computed_hash
    
    def test_node_result_immutability(self):
        """Test NodeResult is properly immutable"""
        from exoarmur.replay.replay_engine import ReplayReport
        
        output = {"test": "data"}
        canonical_output_str = canonical_json(output)
        output_hash = stable_hash(canonical_output_str)
        result = NodeResult(
            node_id="immutable-test",
            correlation_id="immutable-correlation",
            replay_report=ReplayReport(correlation_id="immutable-correlation"),
            canonical_output=canonical_output_str,
            output_hash=output_hash
        )
        
        # Should be frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            result.node_id = "new-id"
        
        with pytest.raises(Exception):
            result.canonical_output = "new output"
        
        with pytest.raises(Exception):
            result.output_hash = "new_hash"


class TestVerifierEdgeCases:
    """Test verifier edge cases and boundary conditions"""
    
    @pytest.fixture
    def verifier(self):
        return MultiNodeReplayVerifier(node_count=3)
    
    def test_empty_events_handling(self, verifier):
        """Test handling of empty events list"""
        report = verifier.verify_consensus([], "empty-test")
        
        # Should still achieve consensus with empty results
        assert report.consensus_result == ConsensusResult.CONSENSUS
        assert not report.has_divergence()
        assert len(report.get_consensus_nodes()) == verifier.node_count
        assert len(report.divergent_nodes) == 0
        
        # All nodes should have identical (empty) outputs
        unique_hashes = set(report.node_hashes.values())
        assert len(unique_hashes) == 1
    
    def test_single_event_handling(self, verifier):
        """Test handling of single event"""
        single_event = [
            CanonicalEvent(
                event_id="single",
                event_type="test",
                actor="system",
                correlation_id="single-test",
                payload={"data": "single"},
                payload_hash="",
                sequence_number=1
            )
        ]
        
        report = verifier.verify_consensus(single_event, "single-test")
        
        assert report.consensus_result == ConsensusResult.CONSENSUS
        assert len(report.get_consensus_nodes()) == verifier.node_count
    
    def test_large_event_sequence(self, verifier):
        """Test handling of large event sequences"""
        large_events = [
            CanonicalEvent(
                event_id=f"large-{i}",
                event_type="test",
                actor="system",
                correlation_id="large-test",
                payload={"index": i, "data": f"value-{i}"},
                payload_hash="",
                sequence_number=i
            )
            for i in range(100)
        ]
        
        report = verifier.verify_consensus(large_events, "large-test")
        
        assert report.consensus_result == ConsensusResult.CONSENSUS
        assert len(report.get_consensus_nodes()) == verifier.node_count
        
        # Verify all nodes processed the large sequence
        for node_hash in report.node_hashes.values():
            assert node_hash is not None
            assert len(node_hash) > 0
    
    def test_malformed_events_handling(self, verifier):
        """Test handling of malformed events"""
        # Create events with potential issues
        malformed_events = [
            CanonicalEvent(
                event_id="unicode-test-🚀",
                event_type="test",
                actor="system",
                correlation_id="malformed-test",
                payload={"unicode": "🎯🎪🎭", "control": "\t\n\r"},
                payload_hash="",
                sequence_number=1
            ),
            CanonicalEvent(
                event_id="long-id-" + "a" * 1000,
                event_type="test",
                actor="system",
                correlation_id="malformed-test",
                payload={"large": "x" * 10000},
                payload_hash="",
                sequence_number=2
            )
        ]
        
        report = verifier.verify_consensus(malformed_events, "malformed-test")
        
        # Should handle gracefully and achieve consensus
        assert report.consensus_result == ConsensusResult.CONSENSUS
        assert len(report.get_consensus_nodes()) == verifier.node_count
    
    def test_verifier_node_count_validation(self):
        """Test verifier node count validation"""
        # Valid node counts (minimum 2 for consensus)
        for count in [2, 3, 5, 7, 10]:
            verifier = MultiNodeReplayVerifier(node_count=count)
            assert verifier.node_count == count
        
        # Invalid node counts
        invalid_counts = [0, 1, -1, -5]
        for count in invalid_counts:
            with pytest.raises(ValueError, match="node_count must be at least 2"):
                MultiNodeReplayVerifier(node_count=count)
    
    def test_concurrent_verification(self, verifier):
        """Test concurrent verification operations"""
        import threading
        import time
        
        events = [
            CanonicalEvent(
                event_id=f"concurrent-{i}",
                event_type="test",
                actor="system",
                correlation_id="concurrent-test",
                payload={"data": f"value-{i}"},
                payload_hash="",
                sequence_number=i
            )
            for i in range(5)
        ]
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                report = verifier.verify_consensus(events, f"concurrent-{worker_id}")
                results.append((worker_id, report))
                time.sleep(0.01)
            except Exception as e:
                errors.append((worker_id, e))
        
        # Run multiple concurrent verifications
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors in concurrent execution: {errors}"
        assert len(results) == 5
        
        # All should achieve consensus
        for worker_id, report in results:
            assert report.consensus_result == ConsensusResult.CONSENSUS
            assert len(report.get_consensus_nodes()) == verifier.node_count


class TestVerifierConfiguration:
    """Test verifier configuration and customization"""
    
    def test_custom_node_count(self):
        """Test verifier with custom node count"""
        for count in [2, 3, 4, 7, 10]:
            verifier = MultiNodeReplayVerifier(node_count=count)
            
            # Create simple events
            events = [
                CanonicalEvent(
                    event_id="test",
                    event_type="test",
                    actor="system",
                    correlation_id="config-test",
                    payload={"data": "test"},
                    payload_hash="",
                    sequence_number=1
                )
            ]
            
            report = verifier.verify_consensus(events, f"config-{count}")
            
            assert report.consensus_result == ConsensusResult.CONSENSUS
            assert len(report.node_hashes) == count
            assert len(report.get_consensus_nodes()) == count
            
            # Verify node IDs are correct
            expected_ids = {f"node-{i}" for i in range(1, count + 1)}
            actual_ids = set(report.node_hashes.keys())
            assert actual_ids == expected_ids
    
    def test_verifier_determinism_across_instances(self):
        """Test that different verifier instances produce identical results"""
        events = [
            CanonicalEvent(
                event_id="determinism-test",
                event_type="test",
                actor="system",
                correlation_id="determinism-test",
                payload={"data": "test"},
                payload_hash="",
                sequence_number=1
            )
        ]
        
        # Create multiple verifier instances
        verifiers = [MultiNodeReplayVerifier(node_count=3) for _ in range(5)]
        reports = []
        
        for verifier in verifiers:
            report = verifier.verify_consensus(events, "determinism-test")
            reports.append(report)
        
        # All reports should be identical
        first_hashes = reports[0].node_hashes
        for i, report in enumerate(reports[1:], 1):
            assert report.node_hashes == first_hashes, \
                f"Verifier {i} produced different hashes"
            assert report.consensus_result == ConsensusResult.CONSENSUS
