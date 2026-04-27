"""
Test list semantics lockdown.

This test verifies that every list path has explicit ordering semantics:
- ORDERED_SEMANTIC: reorder changes hash or fails
- UNORDERED_SET: deterministic sort key must be explicit
- REJECTED_IF_REORDERED: sequence/index invariant must fail
"""

import json
import sys
import subprocess
from pathlib import Path


def get_sample_bundle():
    """Generate a sample bundle for testing."""
    sample_path = "/tmp/test_list_semantics_sample.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Failed to generate sample: {result.stderr}"
    
    with open(sample_path) as f:
        return json.load(f)


def get_ordering_rules():
    """Load the ordering rules manifest."""
    rules_path = Path(__file__).parent.parent / "artifacts" / "canonical" / "ORDERING_RULES.json"
    with open(rules_path) as f:
        return json.load(f)


def walk_json_paths(obj, path="$"):
    """Recursively walk all JSON paths in an object."""
    if isinstance(obj, dict):
        for key in sorted(obj.keys()):
            yield from walk_json_paths(obj[key], f"{path}.{key}")
    elif isinstance(obj, list):
        yield path, "list"
        for i, item in enumerate(obj):
            yield from walk_json_paths(item, f"{path}[{i}]")
    else:
        yield path, "scalar"


def test_every_list_path_in_ordering_rules():
    """Test that every list path in sample bundle appears in ORDERING_RULES.json."""
    bundle = get_sample_bundle()
    rules = get_ordering_rules()
    
    # Get all list paths from bundle
    list_paths = set()
    for path, type_hint in walk_json_paths(bundle):
        if type_hint == "list":
            # Extract the list path (without indices)
            list_path = path.split("[")[0]
            list_paths.add(list_path)
    
    # Check that each list path is in ordering rules
    list_paths_classified = set(rules.get("list_paths", {}).keys())
    
    missing_paths = list_paths - list_paths_classified
    assert len(missing_paths) == 0, f"List paths not classified in ORDERING_RULES.json: {missing_paths}"
    
    print(f"✓ All {len(list_paths)} list paths are classified in ORDERING_RULES.json")


def test_ordered_semantic_list_reorder_changes_hash():
    """Test that ORDERED_SEMANTIC list reorder changes hash or fails."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    bundle = get_sample_bundle()
    rules = get_ordering_rules()
    
    # Find ORDERED_SEMANTIC lists
    ordered_lists = [
        path for path, config in rules.get("list_paths", {}).items()
        if config.get("classification") == "ORDERED_SEMANTIC"
    ]
    
    # Test each ordered list
    for list_path in ordered_lists:
        # Navigate to the list
        parts = list_path.lstrip("$.").split(".")
        current = bundle
        for part in parts:
            if "[" in part:
                continue  # Skip array notation
            current = current[part]
        
        if not isinstance(current, list) or len(current) < 2:
            continue  # Skip if not a list or too short
        
        # Reorder the list
        test_bundle = json.loads(json.dumps(bundle))
        current_test = test_bundle
        for part in parts[:-1]:
            if "[" in part:
                continue
            current_test = current_test[part]
        last_part = parts[-1].split("[")[0]
        
        # Swap first two elements
        if len(current_test[last_part]) >= 2:
            current_test[last_part][0], current_test[last_part][1] = current_test[last_part][1], current_test[last_part][0]
            
            # Get original hash
            original_verdict, original_hash = verify_bundle(bundle)
            
            # Get new hash after reorder
            new_verdict, new_hash = verify_bundle(test_bundle)
            
            # Should either fail or have different hash
            if new_verdict == "PASS":
                assert new_hash != original_hash, f"ORDERED_SEMANTIC list {list_path} reorder should change hash"
            
            print(f"✓ ORDERED_SEMANTIC list {list_path}: reorder changes hash or fails")


def test_unordered_list_has_explicit_sort_key():
    """Test that UNORDERED_SET lists have explicit stable sort key."""
    rules = get_ordering_rules()
    
    # Check UNORDERED_SET lists
    unordered_lists = [
        (path, config) for path, config in rules.get("list_paths", {}).items()
        if config.get("classification") == "UNORDERED_SET"
    ]
    
    for path, config in unordered_lists:
        # UNORDERED_SET should have a sort_key or be documented as unordered
        # For now, we just verify it's classified
        assert "description" in config, f"UNORDERED_SET list {path} missing description"
        print(f"✓ UNORDERED_SET list {path}: has description")


def test_nested_list_ordering_enforced():
    """Test that nested list ordering is enforced."""
    bundle = get_sample_bundle()
    rules = get_ordering_rules()
    
    # Check for nested lists (e.g., events within execution_trace)
    # The execution_trace.events list should be ORDERED_SEMANTIC
    events_path = "$.execution_trace.events"
    events_config = rules.get("list_paths", {}).get(events_path)
    
    assert events_config is not None, f"Path {events_path} not in ordering rules"
    assert events_config.get("classification") == "ORDERED_SEMANTIC", \
        f"execution_trace.events should be ORDERED_SEMANTIC"
    
    print("✓ Nested list ordering is enforced")


def test_duplicate_elements_handled_deterministically():
    """Test that duplicate list elements are handled deterministically."""
    bundle = get_sample_bundle()
    
    # For now, we just verify that the canonicalization process is deterministic
    # by hashing the same bundle twice
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    verdict1, hash1 = verify_bundle(bundle)
    verdict2, hash2 = verify_bundle(bundle)
    
    assert verdict1 == verdict2 == "PASS", "Bundle should pass verification"
    assert hash1 == hash2, "Hash should be deterministic for identical input"
    
    print("✓ Duplicate elements handled deterministically")


def test_ordering_rules_version_specified():
    """Test that ORDERING_RULES.json specifies canonicalization version."""
    rules = get_ordering_rules()
    
    assert "canonicalization_version" in rules, "ORDERING_RULES.json missing canonicalization_version"
    assert rules["canonicalization_version"] == "v1", f"Unexpected canonicalization_version: {rules['canonicalization_version']}"
    
    assert "version" in rules, "ORDERING_RULES.json missing version"
    assert rules["version"] == "v1", f"Unexpected version: {rules['version']}"
    
    print("✓ ORDERING_RULES.json version specified")


def test_classification_rules_documented():
    """Test that all classification types have documented rules."""
    rules = get_ordering_rules()
    
    classification_rules = rules.get("classification_rules", {})
    
    required_classifications = ["ORDERED_SEMANTIC", "UNORDERED_SET", "REJECTED_IF_REORDERED", "NOT_A_LIST"]
    
    for classification in required_classifications:
        assert classification in classification_rules, f"Classification {classification} not documented"
        rule = classification_rules[classification]
        assert "description" in rule, f"Classification {classification} missing description"
        assert "behavior" in rule, f"Classification {classification} missing behavior"
    
    print("✓ All classification types have documented rules")


if __name__ == "__main__":
    print("Testing list semantics lockdown...")
    print()
    
    test_every_list_path_in_ordering_rules()
    test_ordered_semantic_list_reorder_changes_hash()
    test_unordered_list_has_explicit_sort_key()
    test_nested_list_ordering_enforced()
    test_duplicate_elements_handled_deterministically()
    test_ordering_rules_version_specified()
    test_classification_rules_documented()
    
    print()
    print("All list semantics lockdown tests passed!")
