"""
Tests for Kernel IDs Module

These tests verify that the ID generation provides deterministic,
collision-resistant identifiers for governance entities.
"""

import pytest
from datetime import datetime, timezone
from exoarmur.kernel.ids import (
    make_intent_id,
    make_decision_id,
    make_audit_id,
    make_trace_id,
    make_id,
    IDFactory,
    get_id_factory,
    set_id_factory
)


class TestIDFactory:
    """Test IDFactory class for deterministic ID generation."""
    
    def test_id_factory_initialization(self):
        """Test that IDFactory initializes correctly."""
        factory = IDFactory()
        
        assert factory is not None
        assert factory._seed == "exoarmur-default"
    
    def test_id_factory_with_custom_seed(self):
        """Test that IDFactory accepts custom seed."""
        factory = IDFactory(seed="custom-seed")
        
        assert factory._seed == "custom-seed"
    
    def test_id_factory_make_id(self):
        """Test that IDFactory generates IDs."""
        factory = IDFactory()
        
        id1 = factory.make_id("test", {"key": "value"})
        id2 = factory.make_id("test", {"key": "value"})
        
        assert isinstance(id1, str)
        assert id1 == id2  # Deterministic
    
    def test_id_factory_make_id_with_different_payloads(self):
        """Test that different payloads produce different IDs."""
        factory = IDFactory()
        
        id1 = factory.make_id("test", {"key": "value1"})
        id2 = factory.make_id("test", {"key": "value2"})
        
        assert id1 != id2
    
    def test_id_factory_make_intent_id(self):
        """Test that IDFactory generates intent IDs."""
        factory = IDFactory()
        
        intent_id = factory.make_intent_id("actor", "action", "target")
        
        assert isinstance(intent_id, str)
        assert len(intent_id) > 0
    
    def test_id_factory_make_intent_id_deterministic(self):
        """Test that intent ID generation is deterministic."""
        factory = IDFactory()
        
        id1 = factory.make_intent_id("actor", "action", "target")
        id2 = factory.make_intent_id("actor", "action", "target")
        
        assert id1 == id2
    
    def test_id_factory_make_decision_id(self):
        """Test that IDFactory generates decision IDs."""
        factory = IDFactory()
        
        decision_id = factory.make_decision_id("intent1")
        
        assert isinstance(decision_id, str)
        assert len(decision_id) > 0
    
    def test_id_factory_make_trace_id(self):
        """Test that IDFactory generates trace IDs."""
        factory = IDFactory()
        
        trace_id = factory.make_trace_id("intent1")
        
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0
    
    def test_id_factory_make_audit_id(self):
        """Test that IDFactory generates audit IDs."""
        factory = IDFactory()
        
        audit_id = factory.make_audit_id("intent1", "event_type", "outcome")
        
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0


class TestGlobalIDFactory:
    """Test global ID factory functions."""
    
    def test_get_id_factory(self):
        """Test that get_id_factory returns IDFactory instance."""
        factory = get_id_factory()
        
        assert isinstance(factory, IDFactory)
    
    def test_set_id_factory(self):
        """Test that set_id_factory sets global factory."""
        custom_factory = IDFactory(seed="custom")
        set_id_factory(custom_factory)
        
        factory = get_id_factory()
        assert factory._seed == "custom"
        
        # Reset to default
        set_id_factory(IDFactory())
    
    def test_make_id_global(self):
        """Test that make_id uses global factory."""
        id1 = make_id("test", {"key": "value"})
        id2 = make_id("test", {"key": "value"})
        
        assert id1 == id2  # Deterministic


class TestIntentIDGeneration:
    """Test intent ID generation for governance intents."""
    
    def test_make_intent_id_returns_string(self):
        """Test that make_intent_id returns a string."""
        intent_id = make_intent_id("actor1", "action1", "target1")
        
        assert isinstance(intent_id, str)
    
    def test_make_intent_id_is_deterministic(self):
        """Test that intent ID generation is deterministic."""
        id1 = make_intent_id("actor1", "action1", "target1")
        id2 = make_intent_id("actor1", "action1", "target1")
        
        assert id1 == id2
    
    def test_make_intent_id_is_unique_for_different_inputs(self):
        """Test that different inputs produce different IDs."""
        id1 = make_intent_id("actor1", "action1", "target1")
        id2 = make_intent_id("actor2", "action1", "target1")
        id3 = make_intent_id("actor1", "action2", "target1")
        id4 = make_intent_id("actor1", "action1", "target2")
        
        assert id1 != id2
        assert id1 != id3
        assert id1 != id4
    
    def test_make_intent_id_with_timestamp(self):
        """Test intent ID generation with timestamp."""
        custom_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        intent_id = make_intent_id("actor1", "action1", "target1", custom_time)
        
        assert isinstance(intent_id, str)


class TestDecisionIDGeneration:
    """Test decision ID generation for governance decisions."""
    
    def test_make_decision_id_returns_string(self):
        """Test that make_decision_id returns a string."""
        decision_id = make_decision_id("intent1")
        
        assert isinstance(decision_id, str)
    
    def test_make_decision_id_is_deterministic(self):
        """Test that decision ID generation is deterministic."""
        id1 = make_decision_id("intent1", "action1")
        id2 = make_decision_id("intent1", "action1")
        
        assert id1 == id2
    
    def test_make_decision_id_is_unique_for_different_inputs(self):
        """Test that different inputs produce different IDs."""
        id1 = make_decision_id("intent1", "action1")
        id2 = make_decision_id("intent2", "action1")
        id3 = make_decision_id("intent1", "action2")
        
        assert id1 != id2
        assert id1 != id3


class TestAuditIDGeneration:
    """Test audit ID generation for audit records."""
    
    def test_make_audit_id_returns_string(self):
        """Test that make_audit_id returns a string."""
        audit_id = make_audit_id("intent1", "event_type", "outcome")
        
        assert isinstance(audit_id, str)
    
    def test_make_audit_id_is_deterministic(self):
        """Test that audit ID generation is deterministic."""
        id1 = make_audit_id("trace1", "event_type", "outcome")
        id2 = make_audit_id("trace1", "event_type", "outcome")
        
        assert id1 == id2
    
    def test_make_audit_id_with_different_outcomes(self):
        """Test that different outcomes produce different IDs."""
        id1 = make_audit_id("trace1", "event_type", "outcome1")
        id2 = make_audit_id("trace1", "event_type", "outcome2")
        
        assert id1 != id2


class TestTraceIDGeneration:
    """Test trace ID generation for execution traces."""
    
    def test_make_trace_id_returns_string(self):
        """Test that make_trace_id returns a string."""
        trace_id = make_trace_id("intent1")
        
        assert isinstance(trace_id, str)
    
    def test_make_trace_id_is_unique(self):
        """Test that trace IDs are unique."""
        id1 = make_trace_id("intent1")
        id2 = make_trace_id("intent2")
        
        assert id1 != id2


class TestIDCollisionResistance:
    """Test ID collision resistance properties."""
    
    def test_high_volume_id_generation(self):
        """Test ID generation under high volume."""
        ids = set()
        iterations = 10000
        
        for i in range(iterations):
            intent_id = make_intent_id(f"actor{i}", f"action{i}", f"target{i}")
            ids.add(intent_id)
        
        # All IDs should be unique
        assert len(ids) == iterations
    
    def test_concurrent_id_generation(self):
        """Test ID generation under concurrent scenarios."""
        import threading
        
        ids = set()
        lock = threading.Lock()
        
        def generate_ids(thread_id):
            for i in range(100):
                # Use thread_id to ensure different inputs
                intent_id = make_intent_id(f"actor{thread_id}_{i}", f"action{i}", f"target{i}")
                with lock:
                    ids.add(intent_id)
        
        threads = [threading.Thread(target=generate_ids, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All IDs should be unique
        assert len(ids) == 1000


class TestIDFormatValidation:
    """Test ID format and structure."""
    
    def test_intent_id_format(self):
        """Test that intent IDs have expected format."""
        intent_id = make_intent_id("actor1", "action1", "target1")
        
        # Intent IDs should be ULID-based strings
        assert len(intent_id) == 26  # ULID string length
    
    def test_decision_id_format(self):
        """Test that decision IDs have expected format."""
        decision_id = make_decision_id("intent1", "action1")
        
        # Decision IDs should be ULID-based strings
        assert len(decision_id) == 26


class TestIDPerformance:
    """Test ID generation performance."""
    
    def test_intent_id_generation_performance(self):
        """Test that intent ID generation is performant."""
        import time
        
        iterations = 10000
        start = time.perf_counter()
        
        for i in range(iterations):
            make_intent_id(f"actor{i}", f"action{i}", f"target{i}")
        
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 1 second for 10k calls)
        assert (end - start) < 1.0


class TestIDEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_make_intent_id_with_special_characters(self):
        """Test intent ID generation with special characters."""
        intent_id = make_intent_id("actor-1", "action@1", "target#1")
        
        assert isinstance(intent_id, str)
    
    def test_make_intent_id_with_unicode(self):
        """Test intent ID generation with unicode characters."""
        intent_id = make_intent_id("actor🚀", "action🎯", "target🎯")
        
        assert isinstance(intent_id, str)
    
    def test_make_intent_id_with_very_long_strings(self):
        """Test intent ID generation with very long strings."""
        long_string = "a" * 10000
        intent_id = make_intent_id(long_string, long_string, long_string)
        
        assert isinstance(intent_id, str)
