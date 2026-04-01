"""
Tier 0 Hardening Tests for Event Envelope
Focuses on serialization correctness, deterministic ordering, and invariants
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from unittest.mock import patch

from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import (
    CanonicalEvent, AuditEventEnvelope, EventTypePriority, 
    EnvelopeValidationError
)


class TestCanonicalEventSerialization:
    """Test CanonicalEvent serialization and determinism"""
    
    def test_canonical_event_to_dict_is_deterministic(self):
        """Test that CanonicalEvent.to_dict() produces deterministic output"""
        event = CanonicalEvent(
            event_id="test-event-123",
            event_type="safety_gate_evaluated",
            actor="system-operator",
            correlation_id="corr-456",
            payload={"nested": {"data": "value", "number": 42}},
            payload_hash="hash123",
            sequence_number=5,
            parent_event_id="parent-789",
            cell_id="cell-alpha",
            tenant_id="tenant-beta",
            trace_id="trace-gamma"
        )
        
        # Call to_dict multiple times
        outputs = [event.to_dict() for _ in range(10)]
        
        # All outputs should be identical
        for i, output in enumerate(outputs[1:], 1):
            assert output == outputs[0], f"Output {i} differs from first output"
        
        # Verify serialization is byte-stable
        serialized = canonical_json(outputs[0])
        hash_val = stable_hash(serialized)
        
        # Re-serialize and verify hash stability
        for output in outputs[1:]:
            re_serialized = canonical_json(output)
            re_hash = stable_hash(re_serialized)
            assert re_hash == hash_val
    
    def test_canonical_event_ordering_key_stability(self):
        """Test that ordering key is stable and deterministic"""
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        event = CanonicalEvent(
            event_id="ordering-test-event",
            event_type="approval_requested",
            actor="system",
            correlation_id="ordering-test",
            payload={"test": "data"},
            payload_hash="",
            sequence_number=42,
            parent_event_id="parent-event",
            cell_id="cell-1",
            tenant_id="tenant-1",
            trace_id="trace-1"
        )
        
        # Get ordering key multiple times
        ordering_keys = [event.ordering_key for _ in range(10)]
        
        # All ordering keys should be identical
        for i, key in enumerate(ordering_keys[1:], 1):
            assert key == ordering_keys[0], f"Ordering key {i} differs from first"
        
        # Verify ordering key structure
        expected_structure = (EventTypePriority.APPROVAL_REQUESTED.value, "ordering-test-event", 42)
        assert ordering_keys[0] == expected_structure
    
    def test_canonical_event_payload_hash_computation(self):
        """Test payload hash computation and verification"""
        payloads = [
            {"simple": "data"},
            {"nested": {"level1": {"level2": "deep"}}},
            {"array": [1, 2, 3, "four"]},
            {"mixed": {"str": "value", "num": 42, "bool": True, "null": None}},
            {"unicode": {"emoji": "🚀", "chinese": "你好", "arabic": "مرحبا"}},
            {}
        ]
        
        for payload in payloads:
            event = CanonicalEvent(
                event_id="hash-test-event",
                event_type="telemetry_ingested",
                actor="system",
                correlation_id="hash-test",
                payload=payload,
                payload_hash=""  # Will be computed
            )
            
            # Verify hash was computed
            assert event.payload_hash != ""
            assert len(event.payload_hash) == 64  # SHA-256 hex length
            
            # Verify payload integrity
            assert event.verify_payload_integrity() is True
            
            # Tamper with payload and verify failure
            tampered_payload = payload.copy() if payload else {}
            tampered_payload["tampered"] = True
            
            # Create new event with tampered payload but original hash
            tampered_event = CanonicalEvent(
                event_id="tampered-event",
                event_type="telemetry_ingested",
                actor="system",
                correlation_id="hash-test",
                payload=tampered_payload,
                payload_hash=event.payload_hash  # Original hash
            )
            
            assert tampered_event.verify_payload_integrity() is False
    
    def test_canonical_event_serialization_roundtrip(self):
        """Test that CanonicalEvent can survive serialization roundtrip"""
        original_event = CanonicalEvent(
            event_id="roundtrip-test",
            event_type="intent_executed",
            actor="human-operator",
            correlation_id="roundtrip-corr",
            payload={
                "complex": {
                    "nested": {
                        "arrays": [1, 2, 3],
                        "objects": {"key": "value"},
                        "primitives": True
                    }
                },
                "unicode": "🎯🎪🎭",
                "numbers": {"int": 42, "float": 3.14159, "neg": -100}
            },
            payload_hash="",
            sequence_number=10,
            parent_event_id="parent-roundtrip",
            cell_id="cell-roundtrip",
            tenant_id="tenant-roundtrip",
            trace_id="trace-roundtrip"
        )
        
        # Serialize to dict
        serialized = original_event.to_dict()
        
        # Reconstruct from dict
        reconstructed_event = CanonicalEvent(**serialized)
        
        # Verify all fields match
        assert reconstructed_event.event_id == original_event.event_id
        assert reconstructed_event.event_type == original_event.event_type
        assert reconstructed_event.actor == original_event.actor
        assert reconstructed_event.correlation_id == original_event.correlation_id
        assert reconstructed_event.payload == original_event.payload
        assert reconstructed_event.sequence_number == original_event.sequence_number
        assert reconstructed_event.parent_event_id == original_event.parent_event_id
        assert reconstructed_event.cell_id == original_event.cell_id
        assert reconstructed_event.tenant_id == original_event.tenant_id
        assert reconstructed_event.trace_id == original_event.trace_id
        
        # Verify hash is recomputed correctly
        assert reconstructed_event.verify_payload_integrity() is True


class TestAuditEventEnvelopeSerialization:
    """Test AuditEventEnvelope serialization and timestamp handling"""
    
    def test_audit_envelope_timestamp_normalization(self):
        """Test timestamp normalization to UTC"""
        # Test with UTC timestamp
        utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        envelope_utc = AuditEventEnvelope(
            event_id="utc-test",
            timestamp=utc_time,
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="utc-test",
            payload={"test": "data"},
            payload_hash=""
        )
        
        assert envelope_utc.timestamp.tzinfo == timezone.utc
        assert envelope_utc.timestamp == utc_time
        
        # Test with naive timestamp (should be converted to UTC)
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        envelope_naive = AuditEventEnvelope(
            event_id="naive-test",
            timestamp=naive_time,
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="naive-test",
            payload={"test": "data"},
            payload_hash=""
        )
        
        assert envelope_naive.timestamp.tzinfo == timezone.utc
        assert envelope_naive.timestamp.hour == 12  # Should remain 12, not be offset
        
        # Test with non-UTC timezone (should be converted)
        est_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        envelope_est = AuditEventEnvelope(
            event_id="est-test",
            timestamp=est_time,
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="est-test",
            payload={"test": "data"},
            payload_hash=""
        )
        
        assert envelope_est.timestamp.tzinfo == timezone.utc
        # EST time (12:00) should become UTC time (17:00)
        assert envelope_est.timestamp.hour == 17
    
    def test_audit_envelope_to_dict_serialization(self):
        """Test AuditEventEnvelope.to_dict() serialization format"""
        timestamp = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        envelope = AuditEventEnvelope(
            event_id="serialization-test",
            timestamp=timestamp,
            event_type="safety_gate_evaluated",
            actor="operator-1",
            correlation_id="serial-corr",
            payload={"verdict": "allow", "rationale": "Safe to proceed"},
            payload_hash="computed_hash",
            sequence_number=15,
            parent_event_id="parent-123",
            cell_id="cell-prod",
            tenant_id="tenant-main",
            trace_id="trace-abc123"
        )
        
        result = envelope.to_dict()
        
        # Verify all fields are present and correctly formatted
        assert result["event_id"] == "serialization-test"
        assert result["timestamp"] == "2023-01-01T12:30:45Z"  # ISO format with Z suffix
        assert result["event_type"] == "safety_gate_evaluated"
        assert result["actor"] == "operator-1"
        assert result["correlation_id"] == "serial-corr"
        assert result["payload"] == {"verdict": "allow", "rationale": "Safe to proceed"}
        assert result["payload_hash"] == "computed_hash"
        assert result["sequence_number"] == 15
        assert result["parent_event_id"] == "parent-123"
        assert result["cell_id"] == "cell-prod"
        assert result["tenant_id"] == "tenant-main"
        assert result["trace_id"] == "trace-abc123"
    
    def test_audit_envelope_ordering_key_includes_timestamp(self):
        """Test that AuditEventEnvelope ordering key includes timestamp"""
        timestamp1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamp2 = datetime(2023, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
        
        envelope1 = AuditEventEnvelope(
            event_id="event-1",
            timestamp=timestamp1,
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="ordering-test",
            payload={"test": "data"},
            payload_hash=""
        )
        
        envelope2 = AuditEventEnvelope(
            event_id="event-2",
            timestamp=timestamp2,
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="ordering-test",
            payload={"test": "data"},
            payload_hash=""
        )
        
        key1 = envelope1.ordering_key
        key2 = envelope2.ordering_key
        
        # Ordering key should be (timestamp, priority, event_id, sequence_number)
        assert len(key1) == 4
        assert len(key2) == 4
        
        # Timestamp should be first element and drive ordering
        assert key1[0] == timestamp1
        assert key2[0] == timestamp2
        assert key1[0] < key2[0]  # Earlier timestamp should come first
        
        # Priority should be second
        assert key1[1] == EventTypePriority.TELEMETRY_INGESTED.value
        assert key2[1] == EventTypePriority.TELEMETRY_INGESTED.value
        
        # Event ID should be third
        assert key1[2] == "event-1"
        assert key2[2] == "event-2"
        
        # Sequence number should be fourth
        assert key1[3] == 0  # default
        assert key2[3] == 0  # default


class TestEventTypePriorityDeterminism:
    """Test EventTypePriority deterministic behavior"""
    
    def test_event_type_priority_consistency(self):
        """Test that event type priorities are consistent"""
        # Test all known event types
        known_types = [
            ("telemetry_ingested", EventTypePriority.TELEMETRY_INGESTED.value),
            ("safety_gate_evaluated", EventTypePriority.SAFETY_GATE_EVALUATED.value),
            ("approval_requested", EventTypePriority.APPROVAL_REQUESTED.value),
            ("approval_bound_to_intent", EventTypePriority.APPROVAL_BOUND_TO_INTENT.value),
            ("intent_denied", EventTypePriority.INTENT_DENIED.value),
            ("intent_executed", EventTypePriority.INTENT_EXECUTED.value),
            ("approval_approved", EventTypePriority.APPROVAL_APPROVED.value),
            ("approval_denied", EventTypePriority.APPROVAL_DENIED.value),
        ]
        
        for event_type, expected_priority in known_types:
            priority = EventTypePriority.get_priority(event_type)
            assert priority == expected_priority, \
                f"Expected {expected_priority} for {event_type}, got {priority}"
    
    def test_unknown_event_type_priority(self):
        """Test priority for unknown event types"""
        unknown_types = [
            "unknown_event",
            "custom_type",
            "random_action",
            "",
            "123_invalid",
            "event-with-dashes"
        ]
        
        for unknown_type in unknown_types:
            priority = EventTypePriority.get_priority(unknown_type)
            assert priority == 999, \
                f"Expected 999 for unknown type {unknown_type}, got {priority}"
    
    def test_priority_case_insensitive_lookup(self):
        """Test that priority lookup is case insensitive"""
        test_cases = [
            ("TELEMETRY_INGESTED", EventTypePriority.TELEMETRY_INGESTED.value),
            ("telemetry_ingested", EventTypePriority.TELEMETRY_INGESTED.value),
            ("Telemetry_Ingested", EventTypePriority.TELEMETRY_INGESTED.value),
            ("Telemetry_Ingested".upper(), EventTypePriority.TELEMETRY_INGESTED.value),
            ("Telemetry_Ingested".lower(), EventTypePriority.TELEMETRY_INGESTED.value),
        ]
        
        for event_type, expected_priority in test_cases:
            priority = EventTypePriority.get_priority(event_type)
            assert priority == expected_priority, \
                f"Expected {expected_priority} for {event_type}, got {priority}"


class TestEnvelopeIntegrityVerification:
    """Test envelope integrity verification and validation"""
    
    def test_payload_integrity_verification_across_payload_types(self):
        """Test payload integrity verification with various payload types"""
        payload_types = [
            {"simple": "string"},
            {"number": 42},
            {"float": 3.14159},
            {"boolean": True},
            {"null_value": None},
            {"array": [1, 2, 3, "four"]},
            {"nested": {"level1": {"level2": {"level3": "deep"}}}},
            {"mixed": {"str": "value", "num": 42, "bool": True, "null": None, "arr": [1, 2]}},
            {"unicode": {"emoji": "🚀", "chinese": "你好", "arabic": "مرحبا"}},
            {"empty": {}},
            {"large": "x" * 10000}
        ]
        
        for payload in payload_types:
            # Create envelope with auto-computed hash
            envelope = CanonicalEvent(
                event_id="integrity-test",
                event_type="test_type",
                actor="system",
                correlation_id="integrity-test",
                payload=payload,
                payload_hash=""  # Will be computed
            )
            
            # Verify integrity passes
            assert envelope.verify_payload_integrity() is True, \
                f"Integrity check failed for payload type: {type(payload)}"
            
            # Tamper with payload and verify failure
            if isinstance(payload, dict):
                tampered_payload = payload.copy()
                tampered_payload["tampered"] = True
            elif isinstance(payload, list):
                tampered_payload = payload + ["tampered"]
            elif isinstance(payload, str):
                tampered_payload = payload + "tampered"
            else:
                tampered_payload = str(payload) + "tampered"
            
            # Create envelope with tampered payload but original hash
            tampered_envelope = CanonicalEvent(
                event_id="tampered-integrity-test",
                event_type="test_type",
                actor="system",
                correlation_id="integrity-test",
                payload=tampered_payload,
                payload_hash=envelope.payload_hash  # Original hash
            )
            
            assert tampered_envelope.verify_payload_integrity() is False, \
                f"Integrity check should have failed for tampered payload: {type(payload)}"
    
    def test_payload_hash_recomputation_on_modification(self):
        """Test that payload hash is recomputed when payload changes"""
        original_payload = {"data": "original", "value": 42}
        
        # Create event with original payload
        event = CanonicalEvent(
            event_id="hash-recompute-test",
            event_type="test_type",
            actor="system",
            correlation_id="hash-test",
            payload=original_payload,
            payload_hash=""  # Will be computed
        )
        
        original_hash = event.payload_hash
        assert original_hash != ""
        
        # Create new event with modified payload
        modified_payload = original_payload.copy()
        modified_payload["modified"] = True
        
        modified_event = CanonicalEvent(
            event_id="hash-recompute-test",
            event_type="test_type",
            actor="system",
            correlation_id="hash-test",
            payload=modified_payload,
            payload_hash=""  # Will be recomputed
        )
        
        # Hash should be different
        assert modified_event.payload_hash != original_hash
        
        # Both should verify their own integrity
        assert event.verify_payload_integrity() is True
        assert modified_event.verify_payload_integrity() is True
    
    def test_envelope_frozen_properties(self):
        """Test that envelope properties are properly frozen"""
        event = CanonicalEvent(
            event_id="frozen-test",
            event_type="test_type",
            actor="system",
            correlation_id="frozen-test",
            payload={"data": "value"},
            payload_hash=""
        )
        
        # Verify dataclass is frozen
        with pytest.raises(Exception):  # Should raise dataclass.FrozenInstanceError or similar
            event.event_id = "new-id"
        
        with pytest.raises(Exception):
            event.payload = {"new": "data"}


class TestEnvelopeEdgeCases:
    """Test envelope edge cases and boundary conditions"""
    
    def test_empty_and_null_payloads(self):
        """Test handling of empty and null payloads"""
        # Test empty dict
        empty_event = CanonicalEvent(
            event_id="empty-payload",
            event_type="test_type",
            actor="system",
            correlation_id="empty-test",
            payload={},
            payload_hash=""
        )
        
        assert empty_event.verify_payload_integrity() is True
        assert empty_event.payload_hash != ""
        
        # Test None payload
        none_event = CanonicalEvent(
            event_id="none-payload",
            event_type="test_type",
            actor="system",
            correlation_id="none-test",
            payload=None,
            payload_hash=""
        )
        
        # None payload should be handled gracefully
        assert none_event.payload is None
        assert none_event.verify_payload_integrity() is True  # Should handle None
    
    def test_extremely_long_field_values(self):
        """Test handling of extremely long field values"""
        long_string = "x" * 10000
        long_id = "id-" + "a" * 1000
        
        event = CanonicalEvent(
            event_id=long_id,
            event_type="test_type",
            actor="system",
            correlation_id="long-test",
            payload={"long_field": long_string},
            payload_hash=""
        )
        
        # Should handle long fields without issues
        assert event.verify_payload_integrity() is True
        assert len(event.event_id) > 1000
        
        # Serialization should work
        serialized = event.to_dict()
        assert serialized["event_id"] == long_id
        assert serialized["payload"]["long_field"] == long_string
    
    def test_special_characters_in_fields(self):
        """Test handling of special characters in fields"""
        special_chars = {
            "quotes": '"single" and "double"',
            "apostrophes": "single' and'double'",
            "newlines": "line1\nline2\rline3",
            "tabs": "col1\tcol2\tcol3",
            "backslashes": "path\\to\\file",
            "unicode": "🚀🎯🎪🎭",
            "html": "<script>alert('xss')</script>",
            "json": "{\"nested\": \"json\"}",
            "sql": "SELECT * FROM users WHERE '1'='1'"
        }
        
        event = CanonicalEvent(
            event_id="special-chars-test",
            event_type="test_type",
            actor="system",
            correlation_id="special-test",
            payload=special_chars,
            payload_hash=""
        )
        
        # Should handle special characters
        assert event.verify_payload_integrity() is True
        
        # Serialization should preserve special characters
        serialized = event.to_dict()
        assert serialized["payload"] == special_chars
        
        # Round-trip should work
        reconstructed = CanonicalEvent(**serialized)
        assert reconstructed.payload == special_chars
    
    def test_maximum_nesting_depth(self):
        """Test handling of deeply nested payloads"""
        # Create deeply nested structure
        deep_payload = {}
        current = deep_payload
        for i in range(100):  # 100 levels deep
            current[f"level_{i}"] = {"data": f"value_{i}"}
            current = current[f"level_{i}"]
        
        event = CanonicalEvent(
            event_id="deep-nesting-test",
            event_type="test_type",
            actor="system",
            correlation_id="deep-test",
            payload=deep_payload,
            payload_hash=""
        )
        
        # Should handle deep nesting
        assert event.verify_payload_integrity() is True
        
        # Serialization should work
        serialized = event.to_dict()
        assert "level_0" in serialized["payload"]
        assert "level_99" in serialized["payload"]["level_0"]["level_1"]["level_2"]["level_3"]["level_4"]["level_5"]["level_6"]["level_7"]["level_8"]["level_9"]["level_10"]["level_11"]["level_12"]["level_13"]["level_14"]["level_15"]["level_16"]["level_17"]["level_18"]["level_19"]["level_20"]["level_21"]["level_22"]["level_23"]["level_24"]["level_25"]["level_26"]["level_27"]["level_28"]["level_29"]["level_30"]["level_31"]["level_32"]["level_33"]["level_34"]["level_35"]["level_36"]["level_37"]["level_38"]["level_39"]["level_40"]["level_41"]["level_42"]["level_43"]["level_44"]["level_45"]["level_46"]["level_47"]["level_48"]["level_49"]["level_50"]["level_51"]["level_52"]["level_53"]["level_54"]["level_55"]["level_56"]["level_57"]["level_58"]["level_59"]["level_60"]["level_61"]["level_62"]["level_63"]["level_64"]["level_65"]["level_66"]["level_67"]["level_68"]["level_69"]["level_70"]["level_71"]["level_72"]["level_73"]["level_74"]["level_75"]["level_76"]["level_77"]["level_78"]["level_79"]["level_80"]["level_81"]["level_82"]["level_83"]["level_84"]["level_85"]["level_86"]["level_87"]["level_88"]["level_89"]["level_90"]["level_91"]["level_92"]["level_93"]["level_94"]["level_95"]["level_96"]["level_97"]["level_98"]
    
    def test_concurrent_access_thread_safety(self):
        """Test that envelope operations are thread-safe"""
        import threading
        import time
        
        # Shared event
        event = CanonicalEvent(
            event_id="concurrent-test",
            event_type="test_type",
            actor="system",
            correlation_id="concurrent-test",
            payload={"counter": 0},
            payload_hash=""
        )
        
        results = []
        errors = []
        
        def worker():
            try:
                # Perform multiple operations
                for _ in range(100):
                    # Verify integrity (read-only operation)
                    result = event.verify_payload_integrity()
                    results.append(result)
                    
                    # Serialize (read-only operation)
                    serialized = event.to_dict()
                    results.append(len(serialized))
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all operations returned expected results
        assert len(results) == 2000  # 10 threads * 100 operations * 2 checks per operation
        assert all(result is True for result in results[::2])  # All integrity checks should pass
        assert all(isinstance(count, int) and count > 0 for count in results[1::2])  # All serializations should return dict size
