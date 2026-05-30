"""
Tests for canonical JSON hashing utilities.

These tests verify that Core's canonicalization is strict and deterministic.
"""

import pytest
from exoarmur.kernel.canonicalization import (
    canonical_json_bytes,
    canonical_hash,
    validate_canonical_json_compatible,
    normalize_for_hashing,
    CanonicalizationError
)


def test_canonical_json_bytes_simple():
    """Test canonical JSON bytes conversion for simple data."""
    data = {"field": "value", "number": 42}
    bytes_result = canonical_json_bytes(data)
    
    # Should be valid UTF-8
    assert isinstance(bytes_result, bytes)
    assert b"field" in bytes_result
    assert b"value" in bytes_result


def test_canonical_json_bytes_sorted_keys():
    """Test that canonical JSON sorts keys."""
    data = {"z": 1, "a": 2, "m": 3}
    bytes_result = canonical_json_bytes(data)
    
    # Keys should be sorted: a, m, z
    assert bytes_result.index(b'"a"') < bytes_result.index(b'"m"') < bytes_result.index(b'"z"')


def test_canonical_json_bytes_no_whitespace():
    """Test that canonical JSON has no whitespace."""
    data = {"field": "value"}
    bytes_result = canonical_json_bytes(data)
    
    # Should not contain spaces or newlines
    assert b" " not in bytes_result
    assert b"\n" not in bytes_result


def test_canonical_json_bytes_no_nan():
    """Test that canonical JSON rejects NaN."""
    data = {"field": float('nan')}
    
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes(data)


def test_canonical_json_bytes_no_infinity():
    """Test that canonical JSON rejects Infinity."""
    data = {"field": float('inf')}
    
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes(data)


def test_canonical_hash_determinism():
    """Test that canonical hashing is deterministic."""
    data = {"field": "value", "number": 42}
    
    hash1 = canonical_hash(data)
    hash2 = canonical_hash(data)
    
    # Should be identical
    assert hash1 == hash2


def test_canonical_hash_different_data():
    """Test that canonical hashing produces different hashes for different data."""
    data1 = {"field": "value1"}
    data2 = {"field": "value2"}
    
    hash1 = canonical_hash(data1)
    hash2 = canonical_hash(data2)
    
    # Should be different
    assert hash1 != hash2


def test_canonical_hash_preserves_order():
    """Test that canonical hashing preserves semantically meaningful order."""
    # Message order is semantically meaningful
    data = {"messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]}
    
    hash1 = canonical_hash(data)
    hash2 = canonical_hash(data)
    
    # Should be identical (order preserved)
    assert hash1 == hash2


def test_canonical_hash_reversed_order():
    """Test that canonical hashing detects reversed order."""
    data1 = {"messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]}
    data2 = {"messages": [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "hello"}]}
    
    hash1 = canonical_hash(data1)
    hash2 = canonical_hash(data2)
    
    # Should be different (order matters)
    assert hash1 != hash2


def test_validate_canonical_json_compatible_valid():
    """Test validation with compatible data."""
    data = {"field": "value", "number": 42}
    
    assert validate_canonical_json_compatible(data) is True


def test_validate_canonical_json_compatible_invalid():
    """Test validation with incompatible data."""
    data = {"field": float('nan')}
    
    assert validate_canonical_json_compatible(data) is False


def test_normalize_for_hashing():
    """Test that normalization removes specified fields."""
    data = {
        "field": "value",
        "timestamp": "2024-01-01T00:00:00",
        "request_id": "req-123"
    }
    
    normalized = normalize_for_hashing(data, ["timestamp", "request_id"])
    
    assert "field" in normalized
    assert "timestamp" not in normalized
    assert "request_id" not in normalized


def test_normalize_for_hashing_preserves_other_fields():
    """Test that normalization preserves non-specified fields."""
    data = {
        "field": "value",
        "other": "data",
        "timestamp": "2024-01-01T00:00:00"
    }
    
    normalized = normalize_for_hashing(data, ["timestamp"])
    
    assert "field" in normalized
    assert "other" in normalized
    assert "timestamp" not in normalized


def test_normalize_for_hashing_preserves_list_order():
    """Test that normalization does not reorder lists."""
    data = {
        "messages": ["first", "second", "third"],
        "timestamp": "2024-01-01T00:00:00"
    }
    
    normalized = normalize_for_hashing(data, ["timestamp"])
    
    # List order should be preserved
    assert normalized["messages"] == ["first", "second", "third"]
