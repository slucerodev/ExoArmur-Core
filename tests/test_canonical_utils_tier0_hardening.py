"""
Tier 0 Hardening Tests for Canonical Utils
Focuses on canonicalization invariants, hash stability, and determinism
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from unittest.mock import patch

from exoarmur.replay.canonical_utils import (
    canonical_json, stable_hash, verify_canonical_hash, 
    CanonicalHashError, to_canonical_event
)


class TestCanonicalJsonDeterminism:
    """Test canonical_json deterministic behavior"""
    
    def test_key_ordering_is_alphabetical(self):
        """Test that keys are always sorted alphabetically"""
        test_cases = [
            {"z": 1, "a": 2, "m": 3},
            {"banana": 1, "apple": 2, "cherry": 3},
            {"Z": 1, "a": 2, "M": 3},  # Mixed case
            {"_private": 1, "public": 2, "__magic__": 3},  # Underscores
            {"key_with_numbers_123": 1, "key_with_456": 2, "key_789": 3}
        ]
        
        for data in test_cases:
            result = canonical_json(data)
            
            # Parse to verify key order
            parsed = json.loads(result)
            keys = list(parsed.keys())
            
            # Keys should be in alphabetical order
            assert keys == sorted(keys), f"Keys not sorted: {keys}"
            
            # Verify specific expected order for first test case
            if data == {"z": 1, "a": 2, "m": 3}:
                assert result == '{"a":2,"m":3,"z":1}'
    
    def test_nested_key_ordering(self):
        """Test that nested object keys are also sorted"""
        data = {
            "outer_z": {
                "inner_z": 1,
                "inner_a": 2,
                "inner_m": 3
            },
            "outer_a": {
                "nested_z": 4,
                "nested_a": 5
            },
            "outer_m": "simple_value"
        }
        
        result = canonical_json(data)
        parsed = json.loads(result)
        
        # Outer keys should be sorted
        outer_keys = list(parsed.keys())
        assert outer_keys == ["outer_a", "outer_m", "outer_z"]
        
        # Inner keys should be sorted
        assert list(parsed["outer_a"].keys()) == ["nested_a", "nested_z"]
        assert list(parsed["outer_z"].keys()) == ["inner_a", "inner_m", "inner_z"]
    
    def test_canonical_json_output_is_byte_stable(self):
        """Test that canonical_json produces identical output across runs"""
        complex_data = {
            "nested": {
                "arrays": [3, 1, 2, 5, 4],
                "objects": {"z": 1, "a": 2, "m": 3},
                "mixed": {
                    "string": "value",
                    "number": 42,
                    "boolean": True,
                    "null": None
                }
            },
            "unicode": "🚀🎯🎪",
            "special_chars": "quotes'and\"double",
            "empty": {}
        }
        
        # Generate output multiple times
        outputs = [canonical_json(complex_data) for _ in range(10)]
        
        # All outputs should be identical
        for i, output in enumerate(outputs[1:], 1):
            assert output == outputs[0], f"Output {i} differs from first"
        
        # Verify no whitespace except required separators
        assert outputs[0].count(" ") == 0  # No spaces
        assert outputs[0].count("\n") == 0  # No newlines
        assert outputs[0].count("\t") == 0  # No tabs
    
    def test_canonical_json_with_permuted_input(self):
        """Test canonical_json produces same output regardless of input key order"""
        # Same data, different key insertion order
        data1 = {}
        data1["z"] = 1
        data1["a"] = 2
        data1["m"] = 3
        
        data2 = {}
        data2["a"] = 2
        data2["z"] = 1
        data2["m"] = 3
        
        data3 = {}
        data3["m"] = 3
        data3["a"] = 2
        data3["z"] = 1
        
        # All should produce identical canonical output
        output1 = canonical_json(data1)
        output2 = canonical_json(data2)
        output3 = canonical_json(data3)
        
        assert output1 == output2 == output3
        assert output1 == '{"a":2,"m":3,"z":1}'


class TestCanonicalJsonTypeHandling:
    """Test canonical_json handling of different data types"""
    
    def test_datetime_normalization(self):
        """Test datetime normalization to UTC ISO format"""
        # UTC datetime
        utc_dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        data = {"time": utc_dt}
        result = canonical_json(data)
        expected = '{"time":"2023-01-01T12:30:45Z"}'
        assert result == expected
        
        # Naive datetime (should be treated as UTC)
        naive_dt = datetime(2023, 1, 1, 12, 30, 45)
        data = {"time": naive_dt}
        result = canonical_json(data)
        expected = '{"time":"2023-01-01T12:30:45Z"}'
        assert result == expected
        
        # Non-UTC timezone (should be converted)
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=est)
        data = {"time": est_dt}
        result = canonical_json(data)
        # EST 12:30 should become UTC 17:30
        expected = '{"time":"2023-01-01T17:30:45Z"}'
        assert result == expected
    
    def test_float_normalization(self):
        """Test float normalization and precision handling"""
        test_cases = [
            (1.23456789012345, 1.234567890123),  # Rounded to 12 decimal places
            (1.0, 1.0),  # Integer-like float
            (0.0, 0.0),  # Zero
            (-1.23456789012345, -1.234567890123),  # Negative float
            (3.14159265358979, 3.14159265359),  # Pi rounded
        ]
        
        for input_float, expected_output in test_cases:
            data = {"value": input_float}
            result = canonical_json(data)
            parsed = json.loads(result)
            assert parsed["value"] == expected_output, \
                f"Float {input_float} should normalize to {expected_output}"
    
    def test_special_float_values(self):
        """Test handling of special float values (NaN, infinity)"""
        special_floats = [
            float('nan'),
            float('inf'),
            float('-inf')
        ]
        
        for special_float in special_floats:
            data = {"value": special_float}
            result = canonical_json(data)
            parsed = json.loads(result)
            
            # Special floats should be converted to string "null"
            assert parsed["value"] == "null"
            
            # Verify the actual JSON contains "null"
            assert '"value":"null"' in result
    
    def test_basic_types(self):
        """Test handling of basic JSON types"""
        test_cases = [
            ({"string": "value"}, '{"string":"value"}'),
            ({"integer": 42}, '{"integer":42}'),
            ({"boolean_true": True}, '{"boolean_true":true}'),
            ({"boolean_false": False}, '{"boolean_false":false}'),
            ({"null_value": None}, '{"null_value":null}'),
            ({"empty_string": ""}, '{"empty_string":""}'),
            ({"empty_array": []}, '{"empty_array":[]}'),
            ({"empty_object": {}}, '{"empty_object":{}}')
        ]
        
        for data, expected in test_cases:
            result = canonical_json(data)
            assert result == expected
    
    def test_array_handling(self):
        """Test array canonicalization"""
        data = {
            "array": [3, 1, 2, "z", "a", "m"]
        }
        
        result = canonical_json(data)
        parsed = json.loads(result)
        
        # Arrays should preserve order, but elements should be canonicalized
        assert parsed["array"] == [3, 1, 2, "z", "a", "m"]
        
        # Nested arrays with objects
        nested_data = {
            "nested": [
                {"z": 1, "a": 2},
                {"m": 3, "b": 4}
            ]
        }
        
        result = canonical_json(nested_data)
        parsed = json.loads(result)
        
        # Objects in arrays should have sorted keys
        assert list(parsed["nested"][0].keys()) == ["a", "z"]
        assert list(parsed["nested"][1].keys()) == ["b", "m"]
    
    def test_unicode_handling(self):
        """Test proper handling of unicode characters"""
        unicode_data = {
            "emoji": "🚀🎯🎪🎭",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "russian": "Привет мир",
            "special": "café naïve résumé"
        }
        
        result = canonical_json(unicode_data)
        parsed = json.loads(result)
        
        # Unicode should be preserved
        assert parsed["emoji"] == "🚀🎯🎪🎭"
        assert parsed["chinese"] == "你好世界"
        assert parsed["arabic"] == "مرحبا بالعالم"
        assert parsed["russian"] == "Привет мир"
        assert parsed["special"] == "café naïve résumé"
        
        # Verify ensure_ascii=False is working
        assert "🚀" in result
        assert "你好" in result


class TestStableHashDeterminism:
    """Test stable_hash deterministic behavior"""
    
    def test_hash_consistency(self):
        """Test that hash is consistent for same input"""
        data = {"test": "value", "number": 42}
        
        hash1 = stable_hash(canonical_json(data))
        hash2 = stable_hash(canonical_json(data))
        hash3 = stable_hash(canonical_json(data))
        
        assert hash1 == hash2 == hash3
        assert len(hash1) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in hash1)  # Hex characters only
    
    def test_hash_uniqueness(self):
        """Test that different inputs produce different hashes"""
        data_sets = [
            {"test": "value"},
            {"test": "value", "extra": "field"},
            {"test": "different_value"},
            {"different_key": "value"},
            {"number": 42},
            {"string": "42"}
        ]
        
        hashes = []
        for data in data_sets:
            hash_val = stable_hash(canonical_json(data))
            assert hash_val not in hashes, f"Hash collision detected for {data}"
            hashes.append(hash_val)
    
    def test_hash_stability_across_permutations(self):
        """Test hash stability with permuted but equivalent data"""
        # Same logical data, different representation
        data1 = {"z": 1, "a": 2, "m": 3}
        data2 = {"a": 2, "m": 3, "z": 1}
        
        hash1 = stable_hash(canonical_json(data1))
        hash2 = stable_hash(canonical_json(data2))
        
        assert hash1 == hash2, "Hashes should be identical for equivalent data"
    
    def test_hash_input_validation(self):
        """Test hash input validation"""
        # Valid string input
        valid_input = '{"test": "value"}'
        hash_val = stable_hash(valid_input)
        assert len(hash_val) == 64
        
        # Invalid inputs should raise ValueError
        invalid_inputs = [
            123,
            None,
            {"not": "a string"},
            [],
            object()
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError, match="Data must be string"):
                stable_hash(invalid_input)


class TestHashVerification:
    """Test verify_canonical_hash function"""
    
    def test_verification_success(self):
        """Test successful hash verification"""
        data = {"test": "value", "nested": {"key": "data"}}
        expected_hash = stable_hash(canonical_json(data))
        
        result = verify_canonical_hash(data, expected_hash)
        assert result is True
    
    def test_verification_failure(self):
        """Test hash verification failure"""
        data = {"test": "value"}
        wrong_hash = "wrong_hash_value"
        
        result = verify_canonical_hash(data, wrong_hash)
        assert result is False
    
    def test_verification_with_modified_data(self):
        """Test verification fails when data is modified"""
        original_data = {"test": "value", "number": 42}
        expected_hash = stable_hash(canonical_json(original_data))
        
        # Modify data
        modified_data = original_data.copy()
        modified_data["modified"] = True
        
        result = verify_canonical_hash(modified_data, expected_hash)
        assert result is False
    
    def test_verification_error_handling(self):
        """Test verification handles errors gracefully"""
        # Test with data that can't be canonicalized
        invalid_data = {"bad": set([1, 2, 3])}  # Sets can't be JSON serialized
        
        result = verify_canonical_hash(invalid_data, "any_hash")
        assert result is False


class TestToCanonicalEvent:
    """Test to_canonical_event function"""
    
    def test_canonical_event_projection_strips_wall_clock(self):
        """Test canonical projection removes wall-clock fields"""
        from exoarmur.spec.contracts.models_v1 import AuditRecordV1
        
        record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345670",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),  # Wall clock field
            event_kind="telemetry_ingested",
            payload_ref={"kind": {"ref": {"event_id": "event-1"}}},
            hashes={"sha256": "hash0", "upstream_hashes": []},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical = to_canonical_event(record)
        
        # Wall-clock fields should be stripped
        assert "recorded_at" not in canonical
        assert "timestamp" not in canonical
        
        # Other fields should be preserved
        assert canonical["event_id"] == "01J4NR5X9Z8GABCDEF12345670"
        assert canonical["event_type"] == "telemetry_ingested"
        assert canonical["correlation_id"] == "test-corr"
        assert canonical["trace_id"] == "trace-1"
    
    def test_canonical_event_payload_extraction(self):
        """Test payload extraction from different reference formats"""
        from exoarmur.spec.contracts.models_v1 import AuditRecordV1
        
        # Test with kind.ref format
        record1 = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01KN4ZXCF4PRHFJNMMQSBKYX71",  # Valid ULID
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="test_event",
            payload_ref={"kind": {"ref": {"key": "value"}}},
            hashes={"sha256": "hash1"},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical1 = to_canonical_event(record1)
        assert canonical1["payload"]["kind"]["ref"]["key"] == "value"
        
        # Test with direct ref format
        record2 = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01KN4ZXCF4PRHFJNMMQSBKYX72",  # Valid ULID
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="test_event",
            payload_ref={"ref": {"key": "value"}},
            hashes={"sha256": "hash2"},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical2 = to_canonical_event(record2)
        assert canonical2["payload"]["ref"]["key"] == "value"
        
        # Test with string ref format
        record3 = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01KN4ZXCF4PRHFJNMMQSBKYX73",  # Valid ULID
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="test_event",
            payload_ref={"ref": '{"key": "value"}'},
            hashes={"sha256": "hash3"},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical3 = to_canonical_event(record3)
        # String ref format preserves the structure as-is
        assert canonical3["payload"]["ref"] == '{"key": "value"}'
    
    def test_canonical_event_payload_hash_computation(self):
        """Test payload hash is computed correctly"""
        from exoarmur.spec.contracts.models_v1 import AuditRecordV1
        
        record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01KN4ZXCF4PRHFJNMMQSBKYX69",  # Valid ULID
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="test_event",
            payload_ref={"kind": {"ref": {"key": "value"}}},
            hashes={"sha256": "hash0"},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical = to_canonical_event(record)
        
        # Payload hash should be computed
        assert "payload_hash" in canonical
        assert len(canonical["payload_hash"]) == 64
        
        # Hash should be verifiable
        payload = canonical["payload"]
        expected_hash = stable_hash(canonical_json(payload))
        assert canonical["payload_hash"] == expected_hash
    
    def test_canonical_event_field_fallbacks(self):
        """Test field extraction with fallbacks"""
        from exoarmur.spec.contracts.models_v1 import AuditRecordV1
        
        record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01KN4ZXCF4PRHFJNMMQSBKYX70",  # Valid ULID
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="test_event",
            payload_ref={"kind": {"ref": {"key": "value"}}},
            hashes={"sha256": "hash0"},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        canonical = to_canonical_event(record)
        
        # Test field fallbacks
        assert canonical["actor"] == "system"  # Default actor
        assert canonical["sequence_number"] is None  # Not provided
        assert canonical["parent_event_id"] is None  # Not provided


class TestCanonicalUtilsEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_extremely_nested_structures(self):
        """Test canonicalization of extremely nested structures"""
        # Create deeply nested structure
        deep_data = {}
        current = deep_data
        for i in range(100):
            current[f"level_{i}"] = {"data": f"value_{i}"}
            current = current[f"level_{i}"]
        
        # Should handle deep nesting without issues
        result = canonical_json(deep_data)
        parsed = json.loads(result)
        
        assert "level_0" in parsed
        assert "level_99" in parsed["level_0"]["level_1"]["level_2"]["level_3"]["level_4"]["level_5"]["level_6"]["level_7"]["level_8"]["level_9"]["level_10"]["level_11"]["level_12"]["level_13"]["level_14"]["level_15"]["level_16"]["level_17"]["level_18"]["level_19"]["level_20"]["level_21"]["level_22"]["level_23"]["level_24"]["level_25"]["level_26"]["level_27"]["level_28"]["level_29"]["level_30"]["level_31"]["level_32"]["level_33"]["level_34"]["level_35"]["level_36"]["level_37"]["level_38"]["level_39"]["level_40"]["level_41"]["level_42"]["level_43"]["level_44"]["level_45"]["level_46"]["level_47"]["level_48"]["level_49"]["level_50"]["level_51"]["level_52"]["level_53"]["level_54"]["level_55"]["level_56"]["level_57"]["level_58"]["level_59"]["level_60"]["level_61"]["level_62"]["level_63"]["level_64"]["level_65"]["level_66"]["level_67"]["level_68"]["level_69"]["level_70"]["level_71"]["level_72"]["level_73"]["level_74"]["level_75"]["level_76"]["level_77"]["level_78"]["level_79"]["level_80"]["level_81"]["level_82"]["level_83"]["level_84"]["level_85"]["level_86"]["level_87"]["level_88"]["level_89"]["level_90"]["level_91"]["level_92"]["level_93"]["level_94"]["level_95"]["level_96"]["level_97"]["level_98"]
    
    def test_large_data_structures(self):
        """Test canonicalization of large data structures"""
        # Large array
        large_array = list(range(10000))
        data = {"large_array": large_array}
        
        result = canonical_json(data)
        parsed = json.loads(result)
        
        assert len(parsed["large_array"]) == 10000
        assert parsed["large_array"][0] == 0
        assert parsed["large_array"][-1] == 9999
        
        # Large object
        large_object = {f"key_{i}": f"value_{i}" for i in range(1000)}
        data = {"large_object": large_object}
        
        result = canonical_json(data)
        parsed = json.loads(result)
        
        assert len(parsed["large_object"]) == 1000
        assert "key_0" in parsed["large_object"]
        assert "key_999" in parsed["large_object"]
        
        # Keys should be sorted
        keys = list(parsed["large_object"].keys())
        assert keys == sorted(keys)
    
    def test_unicode_edge_cases(self):
        """Test unicode edge cases"""
        unicode_edge_cases = {
            "zero_width": "\u200b\u200c\u200d",  # Zero-width characters
            "high_surrogate": "\ud83d",  # High surrogate (incomplete emoji)
            "low_surrogate": "\udc42",  # Low surrogate
            "combined": "café\u0301",  # Combined characters
            "bidi": "مرحبا Hello",  # Bidirectional text
            "control": "value\t\n\r",  # Control characters
            "emoji_variations": ["👨‍👩‍👧‍👦", "🇺🇸", "🏳️‍🌈"]  # Complex emoji
        }
        
        data = {"unicode_tests": unicode_edge_cases}
        result = canonical_json(data)
        parsed = json.loads(result)
        
        # Unicode should be preserved
        assert parsed["unicode_tests"]["zero_width"] == "\u200b\u200c\u200d"
        assert parsed["unicode_tests"]["combined"] == "café\u0301"
        assert parsed["unicode_tests"]["bidi"] == "مرحبا Hello"
        
        # Verify in JSON output
        assert "مرحبا" in result
        assert "café" in result
    
    def test_numeric_edge_cases(self):
        """Test numeric edge cases"""
        numeric_cases = {
            "very_large_int": 2**63,  # Large 64-bit integer
            "very_small_float": 1e-20,  # Very small float
            "very_large_float": 1e20,  # Very large float
            "negative_zero": -0.0,  # Negative zero
            "infinity_like": 1e308,  # Near infinity
            "precision_edge": 1.2345678901234567  # Beyond 12 decimal places
        }
        
        data = {"numeric_tests": numeric_cases}
        result = canonical_json(data)
        parsed = json.loads(result)
        
        # Floats should be rounded to 12 decimal places, but very small numbers may become 0
        assert parsed["numeric_tests"]["precision_edge"] == 1.234567890123
        
        # Large numbers should be preserved
        assert parsed["numeric_tests"]["very_large_int"] == 2**63
        # Very small floats may round to 0 due to precision limits
        assert parsed["numeric_tests"]["very_small_float"] == 0.0  # Expected behavior for 1e-20
        assert parsed["numeric_tests"]["very_large_float"] == 1e20
    
    def test_concurrent_canonicalization(self):
        """Test thread safety of canonicalization"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(100):
                    data = {"thread_id": i, "data": f"value_{i}"}
                    canonical = canonical_json(data)
                    hash_val = stable_hash(canonical)
                    results.append((i, canonical, hash_val))
                    time.sleep(0.001)  # Small delay
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
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all results are consistent
        assert len(results) == 1000  # 10 threads * 100 operations
        
        # Same thread_id should produce same canonical output
        thread_results = {}
        for thread_id, canonical, hash_val in results:
            if thread_id not in thread_results:
                thread_results[thread_id] = []
            thread_results[thread_id].append((canonical, hash_val))
        
        for thread_id, outputs in thread_results.items():
            # All outputs for same thread_id should be identical
            canonicals = [output[0] for output in outputs]
            hashes = [output[1] for output in outputs]
            
            assert all(c == canonicals[0] for c in canonicals), \
                f"Thread {thread_id} produced different canonical outputs"
            assert all(h == hashes[0] for h in hashes), \
                f"Thread {thread_id} produced different hashes"
