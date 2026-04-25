"""
Deterministic Ordering and Replay Stress Tests

These tests verify that deterministic ordering enforcement produces consistent results
across multiple runs with identical scenarios, including:
- 10x identical scenario execution
- Unordered collections handling
- Async load testing
- Cross-run hash consistency
"""

import pytest
from typing import Dict, Any, List
import hashlib
import json

from exoarmur.stability.deterministic_ordering import (
    deterministic_iter_dict,
    deterministic_iter_set,
    deterministic_sort_list,
    assert_deterministic_collection
)


class TestDeterministicOrdering:
    """Test deterministic ordering utilities"""

    def test_deterministic_iter_dict_consistency(self):
        """Verify dict iteration produces consistent ordering across multiple calls"""
        test_dict = {"z": 1, "a": 2, "m": 3, "b": 4, "c": 5}
        
        # Collect results from 10 iterations
        results = []
        for _ in range(10):
            iteration_result = list(deterministic_iter_dict(test_dict))
            results.append(iteration_result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Inconsistent dict iteration: {result} != {first_result}"

    def test_deterministic_iter_set_consistency(self):
        """Verify set iteration produces consistent ordering across multiple calls"""
        test_set = {"z", "a", "m", "b", "c"}
        
        # Collect results from 10 iterations
        results = []
        for _ in range(10):
            iteration_result = list(deterministic_iter_set(test_set))
            results.append(iteration_result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Inconsistent set iteration: {result} != {first_result}"

    def test_deterministic_sort_list_consistency(self):
        """Verify list sorting produces consistent results across multiple calls"""
        test_list = ["z", "a", "m", "b", "c"]
        
        # Collect results from 10 iterations
        results = []
        for _ in range(10):
            sorted_result = deterministic_sort_list(test_list)
            results.append(sorted_result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Inconsistent list sorting: {result} != {first_result}"

    def test_deterministic_iter_dict_with_nested_structures(self):
        """Verify dict iteration with nested structures is deterministic"""
        test_dict = {
            "outer1": {"inner_z": 1, "inner_a": 2},
            "outer2": {"inner_m": 3, "inner_b": 4}
        }
        
        # Collect results from 10 iterations
        results = []
        for _ in range(10):
            iteration_result = [(k, dict(deterministic_iter_dict(v))) for k, v in deterministic_iter_dict(test_dict)]
            results.append(iteration_result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Inconsistent nested dict iteration: {result} != {first_result}"

    def test_assert_deterministic_collection_passes(self):
        """Verify assert_deterministic_collection passes for deterministic collections"""
        test_dict = {"z": 1, "a": 2, "m": 3}
        
        # Should not raise
        assert_deterministic_collection(test_dict)

    def test_cross_run_hash_consistency(self):
        """Verify that identical scenarios produce identical hashes across runs"""
        scenario = {
            "events": [
                {"id": "z", "type": "A", "value": 1},
                {"id": "a", "type": "B", "value": 2},
                {"id": "m", "type": "C", "value": 3}
            ],
            "metadata": {"z": 1, "a": 2, "m": 3}
        }
        
        # Compute hash using deterministic ordering
        def compute_scenario_hash(scenario: Dict[str, Any]) -> str:
            ordered_events = [dict(deterministic_iter_dict(event)) for event in scenario["events"]]
            ordered_metadata = dict(deterministic_iter_dict(scenario["metadata"]))
            canonical = json.dumps({"events": ordered_events, "metadata": ordered_metadata}, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        
        # Collect hashes from 10 iterations
        hashes = []
        for _ in range(10):
            scenario_hash = compute_scenario_hash(scenario)
            hashes.append(scenario_hash)
        
        # All hashes should be identical
        first_hash = hashes[0]
        for scenario_hash in hashes[1:]:
            assert scenario_hash == first_hash, f"Inconsistent hash: {scenario_hash} != {first_hash}"


class TestReplayDeterminism:
    """Test replay determinism with stress scenarios"""

    def test_replay_hash_consistency_10x(self):
        """Verify replay hash consistency across 10 identical scenario executions"""
        scenario = {
            "intent_id": "test-intent-001",
            "actions": [
                {"action": "create", "resource": "z"},
                {"action": "update", "resource": "a"},
                {"action": "delete", "resource": "m"}
            ],
            "context": {"user": "test", "session": "abc123"}
        }
        
        def compute_replay_hash(scenario: Dict[str, Any]) -> str:
            ordered_actions = [dict(deterministic_iter_dict(action)) for action in scenario["actions"]]
            ordered_context = dict(deterministic_iter_dict(scenario["context"]))
            canonical = json.dumps({
                "intent_id": scenario["intent_id"],
                "actions": ordered_actions,
                "context": ordered_context
            }, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        
        # Collect hashes from 10 iterations
        hashes = []
        for i in range(10):
            scenario_hash = compute_replay_hash(scenario)
            hashes.append(scenario_hash)
        
        # All hashes should be identical
        first_hash = hashes[0]
        for i, scenario_hash in enumerate(hashes[1:], 1):
            assert scenario_hash == first_hash, f"Iteration {i+1} hash mismatch: {scenario_hash} != {first_hash}"

    def test_unordered_collections_determinism(self):
        """Verify unordered collections are handled deterministically"""
        unordered_data = {
            "set_values": {"z", "a", "m", "b", "c"},
            "dict_values": {"z": 1, "a": 2, "m": 3, "b": 4, "c": 5},
            "list_values": ["z", "a", "m", "b", "c"]
        }
        
        def process_unordered_data(data: Dict[str, Any]) -> str:
            ordered_set = list(deterministic_iter_set(data["set_values"]))
            ordered_dict = dict(deterministic_iter_dict(data["dict_values"]))
            ordered_list = deterministic_sort_list(data["list_values"])
            canonical = json.dumps({
                "set": ordered_set,
                "dict": ordered_dict,
                "list": ordered_list
            }, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        
        # Collect hashes from 10 iterations
        hashes = []
        for _ in range(10):
            data_hash = process_unordered_data(unordered_data)
            hashes.append(data_hash)
        
        # All hashes should be identical
        first_hash = hashes[0]
        for data_hash in hashes[1:]:
            assert data_hash == first_hash, f"Unordered collection hash mismatch: {data_hash} != {first_hash}"

    def test_async_load_determinism(self):
        """Verify determinism under simulated async load"""
        import asyncio
        
        async def process_async_batch(batch: List[Dict[str, Any]]) -> str:
            """Process a batch of events deterministically"""
            ordered_batch = [dict(deterministic_iter_dict(event)) for event in batch]
            canonical = json.dumps(ordered_batch, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        
        async def async_load_test():
            # Create 10 batches of events with identical data to verify determinism
            batches = []
            base_batch = [
                {"id": "z0", "value": 0},
                {"id": "a0", "value": 0},
                {"id": "m0", "value": 0}
            ]
            for i in range(10):
                batches.append(base_batch.copy())
            
            # Process all batches concurrently
            tasks = [process_async_batch(batch) for batch in batches]
            hashes = await asyncio.gather(*tasks)
            
            # All hashes should be identical (same data, same ordering)
            first_hash = hashes[0]
            for i, batch_hash in enumerate(hashes[1:], 1):
                assert batch_hash == first_hash, f"Batch {i+1} hash mismatch: {batch_hash} != {first_hash}"
            
            return True
        
        # Run async test
        result = asyncio.run(async_load_test())
        assert result, "Async load determinism test failed"

    def test_cross_run_comparison(self):
        """Verify cross-run comparison of identical scenarios"""
        scenarios = [
            {
                "scenario_id": "scenario-1",
                "events": [{"id": "z"}, {"id": "a"}, {"id": "m"}]
            },
            {
                "scenario_id": "scenario-2",
                "events": [{"id": "b"}, {"id": "c"}, {"id": "d"}]
            }
        ]
        
        def compute_scenario_signature(scenario: Dict[str, Any]) -> str:
            ordered_events = [dict(deterministic_iter_dict(event)) for event in scenario["events"]]
            canonical = json.dumps({
                "scenario_id": scenario["scenario_id"],
                "events": ordered_events
            }, sort_keys=True)
            return hashlib.sha256(canonical.encode()).hexdigest()
        
        # Compute signatures for each scenario across 10 runs
        scenario_signatures = {s["scenario_id"]: [] for s in scenarios}
        for run in range(10):
            for scenario in scenarios:
                signature = compute_scenario_signature(scenario)
                scenario_signatures[scenario["scenario_id"]].append(signature)
        
        # Verify each scenario has consistent signatures across runs
        for scenario_id, signatures in scenario_signatures.items():
            first_signature = signatures[0]
            for i, signature in enumerate(signatures[1:], 1):
                assert signature == first_signature, f"Scenario {scenario_id} run {i+1} signature mismatch"
        
        # Verify different scenarios produce different signatures
        scenario_1_signatures = scenario_signatures["scenario-1"]
        scenario_2_signatures = scenario_signatures["scenario-2"]
        assert scenario_1_signatures[0] != scenario_2_signatures[0], "Different scenarios should have different signatures"


class TestDeterminismEdgeCases:
    """Test edge cases for deterministic ordering"""

    def test_empty_collections(self):
        """Verify deterministic ordering handles empty collections"""
        assert list(deterministic_iter_dict({})) == []
        assert list(deterministic_iter_set(set())) == []
        assert deterministic_sort_list([]) == []

    def test_single_element_collections(self):
        """Verify deterministic ordering handles single-element collections"""
        assert list(deterministic_iter_dict({"a": 1})) == [("a", 1)]
        assert list(deterministic_iter_set({"a"})) == ["a"]
        assert deterministic_sort_list(["a"]) == ["a"]

    def test_unicode_keys(self):
        """Verify deterministic ordering handles unicode keys"""
        test_dict = {"α": 1, "β": 2, "γ": 3, "δ": 4}
        results = []
        for _ in range(10):
            iteration_result = list(deterministic_iter_dict(test_dict))
            results.append(iteration_result)
        
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Unicode key iteration inconsistent: {result} != {first_result}"

    def test_numeric_keys(self):
        """Verify deterministic ordering handles numeric keys"""
        test_dict = {3: "c", 1: "a", 2: "b", 5: "e", 4: "d"}
        results = []
        for _ in range(10):
            iteration_result = list(deterministic_iter_dict(test_dict))
            results.append(iteration_result)
        
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Numeric key iteration inconsistent: {result} != {first_result}"
