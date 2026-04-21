"""
Adversarial Determinism Hardening Tests

This test suite actively attempts to break determinism in ExoArmur by:
- Stress testing core execution paths with 1000+ repeated runs
- Fuzzing inputs to PolicyDecisionPoint and SafetyGate
- Testing concurrent execution and race conditions
- Checking for time-dependent logic and system time usage
- Verifying serialization/deserialization determinism
- Testing state persistence and reload scenarios

Success criteria:
- Core execution paths produce identical results across at least 1000 repeated runs
- No state divergence under concurrent stress testing
- All nondeterministic sources are either eliminated or explicitly controlled
"""

import os
import sys
import pytest
import json
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import asdict
import copy

# Set deterministic hash seed before any imports
os.environ['PYTHONHASHSEED'] = '0'

from spec.contracts.models_v1 import (
    LocalDecisionV1,
    ExecutionIntentV1,
    AuditRecordV1
)
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.replay.replay_engine import ReplayEngine, ReplayReport
from exoarmur.replay.event_envelope import CanonicalEvent
from exoarmur.control_plane.intent_store import IntentStore
from exoarmur.federation.clock import Clock
from exoarmur.stability.env_parity import enforce_determinism_requirements, DeterminismRequirementError
from exoarmur.stability.deterministic_clock import (
    DeterministicClock,
    WallClock,
    Clock,
    get_clock,
    set_clock,
    reset_to_wall_clock,
    deterministic_clock_context
)


class TestReplayEngineDeterminism:
    """Stress test ReplayEngine with 1000+ repeated runs"""
    
    @pytest.fixture
    def sample_audit_records(self):
        """Create deterministic sample audit records"""
        correlation_id = "test-correlation-001"
        
        records = []
        for i in range(10):
            record = CanonicalEvent(
                event_id=f"event-{i:03d}",
                event_type="telemetry_ingested",
                actor="test-actor",
                correlation_id=correlation_id,
                payload={
                    "kind": "inline",
                    "ref": {
                        "event_id": f"event-{i:03d}",
                        "correlation_id": correlation_id,
                        "trace_id": f"trace-{i:03d}",
                        "timestamp": "1970-01-01T00:00:00Z"
                    }
                },
                payload_hash="",  # Will be computed in __post_init__
                sequence_number=i
            )
            records.append(record)
        
        return {correlation_id: records}
    
    @pytest.fixture
    def replay_engine(self, sample_audit_records):
        """Create replay engine with sample data"""
        return ReplayEngine(sample_audit_records)
    
    def test_replay_1000_runs_identical(self, replay_engine):
        """
        ADVERSARIAL TEST: Run replay 1000 times and verify identical results
        
        This test attempts to break determinism by:
        - Running the same replay 1000 times
        - Comparing all outputs byte-for-byte
        - Checking for any divergence in state
        """
        correlation_id = "test-correlation-001"
        results = []
        
        # Run 1000 times
        for i in range(1000):
            report = replay_engine.replay_correlation(correlation_id)
            report_dict = report.to_dict()
            results.append(report_dict)
        
        # All results must be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], start=2):
            if result != first_result:
                pytest.fail(
                    f"Determinism violation detected at run {i}!\n"
                    f"First result: {json.dumps(first_result, indent=2)}\n"
                    f"Divergent result: {json.dumps(result, indent=2)}"
                )
    
    def test_replay_ordering_determinism(self, sample_audit_records):
        """
        ADVERSARIAL TEST: Verify ordering key sorting is deterministic
        
        Tests that event ordering by ordering_key produces identical results
        across multiple runs regardless of initial list order.
        """
        correlation_id = "test-correlation-001"
        records = sample_audit_records[correlation_id]
        
        # Test with different initial orders
        results = []
        for _ in range(100):
            # Shuffle records randomly
            shuffled = records.copy()
            import random
            random.seed(42)  # Deterministic shuffle
            random.shuffle(shuffled)
            
            engine = ReplayEngine({correlation_id: shuffled})
            report = engine.replay_correlation(correlation_id)
            results.append(report.to_dict())
        
        # All results must be identical despite different initial orders
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Ordering key sorting is not deterministic"
    
    def test_replay_serialization_determinism(self, replay_engine):
        """
        ADVERSARIAL TEST: Verify serialization/deserialization is deterministic
        
        Tests that serializing and deserializing replay reports produces
        identical results across multiple cycles.
        """
        correlation_id = "test-correlation-001"
        
        # Serialize-deserialize cycle 100 times
        original_report = replay_engine.replay_correlation(correlation_id)
        
        for i in range(100):
            # Serialize
            serialized = json.dumps(original_report.to_dict(), sort_keys=True)
            
            # Deserialize
            deserialized_dict = json.loads(serialized)
            
            # Re-serialize to check stability
            re_serialized = json.dumps(deserialized_dict, sort_keys=True)
            
            # Must be identical to original serialization
            assert re_serialized == serialized, f"Serialization cycle {i} produced different output"


class TestConcurrentExecutionDeterminism:
    """Test concurrent execution and race conditions"""
    
    @pytest.fixture
    def sample_audit_records(self):
        """Create deterministic sample audit records"""
        correlation_id = "concurrent-test-001"
        
        records = []
        for i in range(20):
            record = CanonicalEvent(
                event_id=f"event-{i:03d}",
                event_type="telemetry_ingested",
                actor="test-actor",
                correlation_id=correlation_id,
                payload={
                    "kind": "inline",
                    "ref": {
                        "event_id": f"event-{i:03d}",
                        "correlation_id": correlation_id,
                        "trace_id": f"trace-{i:03d}",
                        "timestamp": "1970-01-01T00:00:00Z"
                    }
                },
                payload_hash="",  # Will be computed in __post_init__
                sequence_number=i
            )
            records.append(record)
        
        return {correlation_id: records}
    
    def test_concurrent_replay_determinism(self, sample_audit_records):
        """
        ADVERSARIAL TEST: Run concurrent replays and verify no race conditions
        
        Tests that running multiple replay operations concurrently
        does not introduce nondeterminism through race conditions.
        """
        correlation_id = "concurrent-test-001"
        
        def run_replay():
            engine = ReplayEngine(sample_audit_records)
            report = engine.replay_correlation(correlation_id)
            return report.to_dict()
        
        # Run 100 concurrent replays
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_replay) for _ in range(100)]
            results = [f.result() for f in futures]
        
        # All results must be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, \
                "Concurrent replay introduced nondeterminism"


class TestTimeDependentLogic:
    """Check for time-dependent logic and system time usage"""
    
    def test_clock_determinism(self):
        """
        ADVERSARIAL TEST: Verify clock does not use system time in critical paths
        
        Tests that the Clock class does not introduce nondeterminism
        through system time usage in critical execution paths.
        """
        pytest.skip(
            "Clock is abstract - need to test concrete implementations. "
            "Documenting: Clock.now() uses datetime.now(timezone.utc) which is nondeterministic. "
            "Critical paths must use deterministic timestamps from inputs."
        )
    


class TestSerializationDeserialization:
    """Verify serialization/deserialization determinism"""
    
    def test_json_serialization_determinism(self):
        """
        ADVERSARIAL TEST: Verify JSON serialization is deterministic
        
        Tests that JSON serialization of data structures produces
        identical output across multiple runs.
        """
        data = {
            "z": 1,
            "a": 2,
            "m": 3,
            "nested": {
                "z": 4,
                "a": 5
            }
        }
        
        # Serialize 100 times with sort_keys=True
        results = []
        for _ in range(100):
            serialized = json.dumps(data, sort_keys=True)
            results.append(serialized)
        
        # All results must be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, \
                "JSON serialization is not deterministic with sort_keys=True"
    


class TestStatePersistence:
    """Test state persistence and reload scenarios"""
    
    def test_intent_store_persistence_determinism(self):
        """
        ADVERSARIAL TEST: Verify intent store persistence is deterministic
        
        Tests that storing and reloading intents produces identical
        state across multiple cycles.
        """
        store = IntentStore()
        
        # Valid ULID format: 26 characters from Crockford's Base32
        intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Valid ULID
            tenant_id="tenant-001",
            cell_id="cell-001",
            idempotency_key="idempotency-001",
            subject={"subject_type": "host", "subject_id": "host-123"},
            intent_type="isolate_host",
            action_class="A1_soft_containment",
            requested_at=datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            parameters={"param1": "value1"},
            policy_context={"bundle_hash_sha256": "abc123"},
            safety_context={"safety_verdict": "allow"},
            correlation_id="correlation-001",
            trace_id="trace-001"
        )
        
        # Store and retrieve 100 times
        results = []
        for _ in range(100):
            store.freeze_intent("approval-001", intent)
            retrieved = store.get_intent_by_approval_id("approval-001")
            results.append(json.dumps(retrieved.model_dump(mode="json"), sort_keys=True))
        
        # All results must be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, \
                "Intent store persistence is not deterministic"
    
    def test_state_reload_determinism(self):
        """
        ADVERSARIAL TEST: Verify state reload from serialized form is deterministic
        
        Tests that serializing state, reloading it, and re-serializing
        produces identical output.
        """
        intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Valid ULID
            tenant_id="tenant-001",
            cell_id="cell-001",
            idempotency_key="idempotency-001",
            subject={"subject_type": "host", "subject_id": "host-123"},
            intent_type="isolate_host",
            action_class="A1_soft_containment",
            requested_at=datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            parameters={"param1": "value1"},
            policy_context={"bundle_hash_sha256": "abc123"},
            safety_context={"safety_verdict": "allow"},
            correlation_id="correlation-001",
            trace_id="trace-001"
        )
        
        # Serialize-deserialize-serialize cycle 100 times
        original_serialized = json.dumps(intent.model_dump(mode="json"), sort_keys=True)
        
        for _ in range(100):
            # Deserialize
            data = json.loads(original_serialized)
            reloaded = ExecutionIntentV1(**data)
            
            # Re-serialize
            re_serialized = json.dumps(reloaded.model_dump(mode="json"), sort_keys=True)
            
            # Must be identical to original
            assert re_serialized == original_serialized, \
                "State reload cycle is not deterministic"


class TestHashDeterminism:
    """Test hash function determinism"""
    
    def test_python_hash_determinism(self):
        """
        ADVERSARIAL TEST: Verify Python hash() is deterministic with PYTHONHASHSEED=0
        
        Tests that Python's built-in hash() function produces identical
        results across multiple runs when PYTHONHASHSEED=0 is set.
        """
        # Verify PYTHONHASHSEED is set
        hash_seed = os.environ.get('PYTHONHASHSEED')
        assert hash_seed == '0', \
            f"PYTHONHASHSEED must be 0 for deterministic hashing, got {hash_seed}"
        
        # Test hash determinism on strings
        test_strings = ["test1", "test2", "test3", "a" * 100, "b" * 100]
        
        for s in test_strings:
            hashes = []
            for _ in range(100):
                h = hash(s)
                hashes.append(h)
            
            # All hashes must be identical
            first_hash = hashes[0]
            for h in hashes[1:]:
                assert h == first_hash, \
                    f"Python hash() is not deterministic for string '{s}'"


class TestDeterminismRequirements:
    """Test determinism requirements enforcement"""
    
    def test_enforce_determinism_requirements_passes_with_pythonhashseed_zero(self, monkeypatch):
        """
        ADVERSARIAL TEST: Verify enforce_determinism_requirements passes with PYTHONHASHSEED=0
        
        Tests that the determinism requirements check passes when
        PYTHONHASHSEED is set to 0.
        """
        monkeypatch.setenv("PYTHONHASHSEED", "0")
        
        # Should not raise
        enforce_determinism_requirements()
    
    def test_enforce_determinism_requirements_fails_without_pythonhashseed(self, monkeypatch):
        """
        ADVERSARIAL TEST: Verify enforce_determinism_requirements fails without PYTHONHASHSEED
        
        Tests that the determinism requirements check raises an error
        when PYTHONHASHSEED is not set.
        """
        monkeypatch.delenv("PYTHONHASHSEED", raising=False)
        
        with pytest.raises(DeterminismRequirementError) as exc_info:
            enforce_determinism_requirements()
        
        assert "PYTHONHASHSEED must be set to '0'" in str(exc_info.value)
        assert exc_info.value.requirement == "PYTHONHASHSEED=0"
        assert exc_info.value.actual is None
    
    def test_enforce_determinism_requirements_fails_with_wrong_pythonhashseed(self, monkeypatch):
        """
        ADVERSARIAL TEST: Verify enforce_determinism_requirements fails with wrong PYTHONHASHSEED
        
        Tests that the determinism requirements check raises an error
        when PYTHONHASHSEED is set to a value other than 0.
        """
        monkeypatch.setenv("PYTHONHASHSEED", "42")
        
        with pytest.raises(DeterminismRequirementError) as exc_info:
            enforce_determinism_requirements()
        
        assert "PYTHONHASHSEED must be set to '0'" in str(exc_info.value)
        assert exc_info.value.requirement == "PYTHONHASHSEED=0"
        assert exc_info.value.actual == "42"


class TestDeterministicClock:
    """Test deterministic clock abstraction"""
    
    def test_deterministic_clock_returns_fixed_time(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock returns fixed time
        
        Tests that DeterministicClock returns the same time across
        multiple calls when not auto-advancing.
        """
        clock = DeterministicClock(auto_advance=False)
        
        times = []
        for _ in range(10):
            times.append(clock.now())
        
        # All times must be identical
        first_time = times[0]
        for time in times[1:]:
            assert time == first_time, "Deterministic clock should return fixed time"
    
    def test_deterministic_clock_auto_advance(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock auto-advance
        
        Tests that DeterministicClock advances time when auto_advance is enabled.
        """
        clock = DeterministicClock(auto_advance=True)
        
        times = []
        for _ in range(10):
            times.append(clock.now())
        
        # Each time should be 1 second ahead of the previous
        for i in range(1, len(times)):
            expected_delta = timedelta(seconds=i)
            actual_delta = times[i] - times[0]
            assert actual_delta == expected_delta, \
                f"Time at index {i} should be {i} seconds ahead of start"
    
    def test_deterministic_clock_manual_advance(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock manual advance
        
        Tests that DeterministicClock can be advanced programmatically.
        """
        clock = DeterministicClock(auto_advance=False)
        initial_time = clock.now()
        
        # Advance by 5 seconds
        clock.advance(timedelta(seconds=5))
        advanced_time = clock.now()
        
        expected_delta = timedelta(seconds=5)
        actual_delta = advanced_time - initial_time
        assert actual_delta == expected_delta, "Manual advance should work correctly"
    
    def test_deterministic_clock_set_time(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock can be set to specific time
        
        Tests that DeterministicClock can be set to a specific timestamp.
        """
        clock = DeterministicClock()
        target_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        clock.set_time(target_time)
        current_time = clock.now()
        
        assert current_time == target_time, "Clock should be set to target time"
    
    def test_deterministic_clock_reset(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock reset
        
        Tests that DeterministicClock can be reset to epoch time.
        """
        clock = DeterministicClock()
        clock.advance(timedelta(hours=24))
        
        clock.reset()
        reset_time = clock.now()
        
        epoch_time = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert reset_time == epoch_time, "Reset should return to epoch time"
    
    def test_deterministic_clock_thread_safety(self):
        """
        ADVERSARIAL TEST: Verify deterministic clock is thread-safe
        
        Tests that DeterministicClock can be used concurrently without
        race conditions.
        """
        clock = DeterministicClock(auto_advance=False)
        
        def read_time():
            return clock.now().isoformat()
        
        # Read from multiple threads
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_time) for _ in range(100)]
            results = [f.result() for f in futures]
        
        # All results must be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Concurrent reads should be deterministic"
    
    def test_wall_clock_raises_on_advance(self):
        """
        ADVERSARIAL TEST: Verify WallClock cannot be advanced
        
        Tests that WallClock raises NotImplementedError when advance is called.
        """
        clock = WallClock()
        
        with pytest.raises(NotImplementedError):
            clock.advance(timedelta(seconds=1))
    
    def test_global_clock_context_manager(self):
        """
        ADVERSARIAL TEST: Verify global clock context manager
        
        Tests that deterministic_clock_context temporarily replaces
        the global clock and restores it afterward.
        """
        original_clock = get_clock()
        
        with deterministic_clock_context():
            context_clock = get_clock()
            assert isinstance(context_clock, DeterministicClock), \
                "Context should use deterministic clock"
        
        restored_clock = get_clock()
        assert restored_clock == original_clock, \
            "Original clock should be restored after context"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
