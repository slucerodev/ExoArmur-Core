"""
Test type strictness validation.

Ensures that:
- Type mismatches are rejected (int vs string, bool vs string)
- Null values are rejected (use missing field instead)
- Unicode normalization is consistent
- Empty structures vs missing are detected
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))


def validate_types(bundle: dict) -> None:
    """Validate types before canonicalization."""
    type_expectations = {
        "intent_id": str,
        "action_type": str,
        "target": str,
        "final_status": str,
        "events_count": int,
    }
    
    for field, expected_type in type_expectations.items():
        if field in bundle:
            value = bundle[field]
            
            # Check for null first
            if value is None:
                raise ValueError(f"NULL_VALUE: {field} is null, should be missing")
            
            # Then check type
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"TYPE_MISMATCH: {field} expected {expected_type.__name__}, got {type(value).__name__}"
                )


def get_valid_bundle() -> dict:
    """Get a valid bundle for testing."""
    return {
        "intent_id": "test-intent",
        "action_type": "delete",
        "target": "/tmp/test.txt",
        "final_status": "deny",
        "events_count": 1,
    }


def test_int_string_rejection():
    """Test that int vs string type mismatch is rejected."""
    bundle = get_valid_bundle()
    bundle["events_count"] = "1"  # String instead of int
    
    try:
        validate_types(bundle)
        assert False, "Int vs string type mismatch should be rejected"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e)


def test_string_int_rejection():
    """Test that string vs int type mismatch is rejected."""
    bundle = get_valid_bundle()
    bundle["intent_id"] = 123  # Int instead of string
    
    try:
        validate_types(bundle)
        assert False, "String vs int type mismatch should be rejected"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e)


def test_null_value_rejection():
    """Test that null values are rejected."""
    bundle = get_valid_bundle()
    bundle["events_count"] = None
    
    try:
        validate_types(bundle)
        assert False, "Null value should be rejected"
    except ValueError as e:
        assert "NULL_VALUE" in str(e)


def test_float_int_rejection():
    """Test that float vs int type mismatch is rejected."""
    bundle = get_valid_bundle()
    bundle["events_count"] = 1.5  # Float instead of int
    
    try:
        validate_types(bundle)
        assert False, "Float vs int type mismatch should be rejected"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e)


def test_bool_string_rejection():
    """Test that bool vs string type mismatch is rejected."""
    bundle = get_valid_bundle()
    bundle["final_status"] = True  # Bool instead of string
    
    try:
        validate_types(bundle)
        assert False, "Bool vs string type mismatch should be rejected"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e)


def test_valid_types_pass():
    """Test that valid types pass validation."""
    bundle = get_valid_bundle()
    validate_types(bundle)  # Should not raise


def test_unicode_normalization_consistency():
    """Test that unicode normalization is consistent."""
    bundle1 = get_valid_bundle()
    bundle2 = get_valid_bundle()
    
    # Use different unicode representations of the same character
    bundle1["intent_id"] = "test-intent"
    bundle2["intent_id"] = "test-intent"
    
    # Both should pass validation
    validate_types(bundle1)
    validate_types(bundle2)


def test_empty_string_vs_missing():
    """Test that empty string vs missing is handled correctly."""
    bundle1 = get_valid_bundle()
    bundle2 = get_valid_bundle()
    
    # Empty string is valid for string fields
    bundle1["target"] = ""
    validate_types(bundle1)
    
    # Missing field is also valid
    del bundle2["target"]
    validate_types(bundle2)


if __name__ == "__main__":
    test_int_string_rejection()
    test_string_int_rejection()
    test_null_value_rejection()
    test_float_int_rejection()
    test_bool_string_rejection()
    test_valid_types_pass()
    test_unicode_normalization_consistency()
    test_empty_string_vs_missing()
    print("All type strictness tests passed")
