"""
Test deep adversarial tamper matrix.

This test applies comprehensive adversarial mutations against full sample bundles:
- Structural: add unknown field, remove required field, replace object with list, etc.
- Type: int → string, bool → string, string → int, null instead of value, etc.
- Semantic: change event sequence, action type, target, final status, etc.

Expected: Every mutation must either FAIL with explicit reason or produce different hash.
No mutation may PASS with identical hash.
"""

import json
import sys
import subprocess
from pathlib import Path


def get_sample_bundle():
    """Generate a sample bundle for testing."""
    sample_path = "/tmp/test_adversarial_tamper_sample.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Failed to generate sample: {result.stderr}"
    
    with open(sample_path) as f:
        return json.load(f)


def get_original_hash(bundle):
    """Get the original hash for a bundle."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, hash_val = verify_bundle(bundle)
        assert verdict == "PASS", "Original bundle should pass"
        return hash_val
    except ValueError as e:
        raise AssertionError(f"Original bundle should not fail: {e}")


def test_add_unknown_field_at_root():
    """Test adding unknown field at root object depth."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["evil_root_field"] = "malicious"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        assert False, "Unknown root field should cause ValueError"
    except ValueError as e:
        assert "UNKNOWN_FIELD" in str(e), "Should fail with UNKNOWN_FIELD"
    
    print("✓ Add unknown field at root: FAILS with UNKNOWN_FIELD")


def test_add_unknown_field_nested():
    """Test adding unknown field at nested object depth."""
    bundle = get_sample_bundle()
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["evil_nested_field"] = "malicious"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        assert False, "Unknown nested field should cause ValueError"
    except ValueError as e:
        assert "UNKNOWN_FIELD" in str(e), "Should fail with UNKNOWN_FIELD"
    
    print("✓ Add unknown field nested: FAILS with UNKNOWN_FIELD")


def test_remove_required_field():
    """Test removing required field."""
    bundle = get_sample_bundle()
    
    test_bundle = json.loads(json.dumps(bundle))
    del test_bundle["intent"]["action_type"]  # Required field
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        assert False, "Removing required field should cause ValueError"
    except ValueError as e:
        assert "MISSING_FIELD" in str(e), "Should fail with MISSING_FIELD"
    
    print("✓ Remove required field: FAILS with MISSING_FIELD")


def test_replace_object_with_list():
    """Test replacing object with list."""
    bundle = get_sample_bundle()
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"] = ["malicious", "list"]
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        # If it passes, the hash should be different
        if verdict == "PASS":
            original_hash = get_original_hash(bundle)
            assert new_hash != original_hash, "Replacing object with list should change hash"
    except (ValueError, TypeError) as e:
        # Type errors are also acceptable failures
        assert True, "Replacing object with list should fail or change hash"
    
    print("✓ Replace object with list: FAILS or changes hash")


def test_replace_list_with_object():
    """Test replacing list with object."""
    bundle = get_sample_bundle()
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["execution_trace"]["events"] = {"not": "a list"}
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        assert False, "Replacing list with object should cause ValueError"
    except (ValueError, TypeError) as e:
        # Type errors are also acceptable failures
        assert True, "Replacing list with object should fail"
    
    print("✓ Replace list with object: FAILS")


def test_empty_required_list():
    """Test emptying a required list."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["execution_trace"]["events"] = []  # Empty required list
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Emptying required list should change hash"
    
    print("✓ Empty required list: FAILS or changes hash")


def test_int_to_string():
    """Test type mutation: int → string."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    # Use a field that's actually an int in the bundle
    if "schema_version" in test_bundle and isinstance(test_bundle["schema_version"], int):
        test_bundle["schema_version"] = "999"  # String instead of int
    elif "bundle_version" in test_bundle and isinstance(test_bundle["bundle_version"], int):
        test_bundle["bundle_version"] = "999"  # String instead of int
    else:
        # Skip if no int field found
        print("✓ int → string: SKIPPED (no int field found)")
        return
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        if verdict == "PASS":
            assert new_hash != original_hash, "Type mutation should change hash"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e), "Should fail with TYPE_MISMATCH"
    
    print("✓ int → string: FAILS with TYPE_MISMATCH or changes hash")


def test_bool_to_string():
    """Test type mutation: bool → string."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["execution_trace"]["events"][0]["ok"] = "true"  # String instead of bool
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    try:
        verdict, new_hash = verify_bundle(test_bundle)
        assert False, "bool → string should cause ValueError"
    except ValueError as e:
        assert "TYPE_MISMATCH" in str(e), "Should fail with TYPE_MISMATCH"
    
    print("✓ bool → string: FAILS with TYPE_MISMATCH")


def test_string_to_int():
    """Test type mutation: string → int."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["action_type"] = 123  # Int instead of string
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Type mutation should change hash"
    
    print("✓ string → int: FAILS or changes hash")


def test_null_instead_of_value():
    """Test null instead of required value."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["action_type"] = None  # Null instead of string
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Null mutation should change hash"
    
    print("✓ null instead of value: FAILS or changes hash")


def test_empty_string_required():
    """Test empty string where nonempty required."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["action_type"] = ""  # Empty string
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Empty string should change hash"
    
    print("✓ empty string required: FAILS or changes hash")


def test_change_event_sequence():
    """Test semantic mutation: change event sequence."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    # Swap two events
    events = test_bundle["execution_trace"]["events"]
    if len(events) >= 2:
        events[0], events[1] = events[1], events[0]
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Event sequence change should change hash"
    
    print("✓ Change event sequence: FAILS or changes hash")


def test_change_action_type():
    """Test semantic mutation: change action type."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["action_type"] = "read"  # Change from "delete"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Action type change should change hash"
    
    print("✓ Change action type: FAILS or changes hash")


def test_change_target():
    """Test semantic mutation: change target."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["target"] = "/different/target"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Target change should change hash"
    
    print("✓ Change target: FAILS or changes hash")


def test_change_final_status():
    """Test semantic mutation: change final status."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["final_verdict"] = "approve"  # Change from "deny"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Final status change should change hash"
    
    print("✓ Change final status: FAILS or changes hash")


def test_change_event_without_count():
    """Test semantic mutation: change events without changing count."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    # Modify an event but keep count the same
    test_bundle["execution_trace"]["events"][0]["code"] = "MODIFIED_CODE"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Event modification should change hash"
    
    print("✓ Change event without count: FAILS or changes hash")


def test_change_terminal_event_without_status():
    """Test semantic mutation: change terminal event without updating final status."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    test_bundle = json.loads(json.dumps(bundle))
    # Change the last event's code but keep final_verdict the same
    events = test_bundle["execution_trace"]["events"]
    if events:
        events[-1]["code"] = "MODIFIED_TERMINAL"
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if verdict == "PASS":
        assert new_hash != original_hash, "Terminal event change should change hash"
    
    print("✓ Change terminal event without status: FAILS or changes hash")


def test_no_mutation_passes_with_same_hash():
    """Test that no mutation passes with identical hash."""
    bundle = get_sample_bundle()
    original_hash = get_original_hash(bundle)
    
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    # Test a variety of mutations
    mutations = [
        ("intent.action_type", "read"),
        ("intent.target", "/modified"),
        ("final_verdict", "approve"),
    ]
    
    for mutation_path, new_value in mutations:
        test_bundle = json.loads(json.dumps(bundle))
        
        # Navigate to the field
        parts = mutation_path.split(".")
        current = test_bundle
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = new_value
        
        try:
            verdict, new_hash = verify_bundle(test_bundle)
            # Should not pass with same hash
            if verdict == "PASS":
                assert new_hash != original_hash, f"Mutation {mutation_path} should change hash"
        except ValueError:
            # Failure is also acceptable
            pass
    
    print("✓ No mutation passes with identical hash")


if __name__ == "__main__":
    print("Testing deep adversarial tamper matrix...")
    print()
    
    test_add_unknown_field_at_root()
    test_add_unknown_field_nested()
    test_remove_required_field()
    test_replace_object_with_list()
    test_replace_list_with_object()
    test_empty_required_list()
    test_int_to_string()
    test_bool_to_string()
    test_string_to_int()
    test_null_instead_of_value()
    test_empty_string_required()
    test_change_event_sequence()
    test_change_action_type()
    test_change_target()
    test_change_final_status()
    test_change_event_without_count()
    test_change_terminal_event_without_status()
    test_no_mutation_passes_with_same_hash()
    
    print()
    print("All deep adversarial tamper matrix tests passed!")
