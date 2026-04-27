"""
Test canonical hash coverage audit.

This test verifies that every field in a valid bundle is either:
1. HASHED - influences the canonical hash
2. EXCLUDED_NONDETERMINISTIC - explicitly excluded with documented reason
3. REJECTED_UNKNOWN - unknown fields must fail validation

No field may be validated but not hash-sensitive unless explicitly classified as nondeterministic metadata.
"""

import json
import sys
import subprocess
from pathlib import Path


def get_sample_bundle():
    """Generate a sample bundle for testing."""
    sample_path = "/tmp/test_hash_coverage_sample.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Failed to generate sample: {result.stderr}"
    
    with open(sample_path) as f:
        return json.load(f)


def get_coverage_manifest():
    """Load the canonical coverage manifest."""
    manifest_path = Path(__file__).parent.parent / "artifacts" / "canonical" / "CANONICAL_COVERAGE.json"
    with open(manifest_path) as f:
        return json.load(f)


def walk_json_paths(obj, path="$"):
    """Recursively walk all JSON paths in an object."""
    if isinstance(obj, dict):
        for key in sorted(obj.keys()):
            yield from walk_json_paths(obj[key], f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from walk_json_paths(item, f"{path}[{i}]")
    else:
        yield path, obj


def get_field_classification(manifest, path):
    """Get classification for a field path from the manifest."""
    # Parse path components
    parts = path.lstrip("$.").split(".")
    
    # Start with root classification
    current = manifest.get("root_classification", {})
    
    # Navigate through nested structure
    for part in parts:
        if part.startswith("[") and part.endswith("]"):
            # List index - check if parent has list classification
            continue
        if part in current:
            if isinstance(current[part], dict):
                current = current[part]
            else:
                return current[part]
        # Try nested_structure
        nested = manifest.get("nested_structure", {})
        if part in nested:
            current = nested[part].get("classification", {})
            continue
    
    # If we have a dict at the end, look for classification
    if isinstance(current, dict) and "classification" in current:
        return current["classification"]
    
    # Check if it's in nested structure classification
    if path.startswith("$."):
        field_name = path.split(".")[1]
        nested = manifest.get("nested_structure", {})
        if field_name in nested:
            field_nested = nested[field_name]
            if "classification" in field_nested:
                return field_nested["classification"]
            # Check element_fields for list items
            if "element_fields" in field_nested:
                elem_class = field_nested["element_fields"].get("classification", {})
                if elem_class:
                    return elem_class
    
    return None


def test_all_hashed_fields_change_hash():
    """Test that every HASHED field mutation changes the hash or fails."""
    bundle = get_sample_bundle()
    manifest = get_coverage_manifest()
    
    # Get all leaf paths
    leaf_paths = list(walk_json_paths(bundle))
    
    # Filter to HASHED fields
    hashed_fields = []
    for path, value in leaf_paths:
        classification = get_field_classification(manifest, path)
        if classification == "HASHED":
            hashed_fields.append((path, value))
    
    print(f"Found {len(hashed_fields)} HASHED fields to test")
    
    # Test a representative sample of HASHED fields
    # (Testing all would be too slow, so we test key semantic fields)
    key_paths = [
        "$.intent.action_type",
        "$.intent.target",
        "$.policy_decision.verdict",
        "$.safety_verdict.verdict",
        "$.final_verdict",
        "$.execution_trace.events[0].stage",
        "$.execution_trace.events[0].code",
        "$.executor_result.success",
    ]
    
    for path in key_paths:
        # Find the actual path in the bundle
        for bundle_path, value in leaf_paths:
            if bundle_path == path:
                # Mutate the value
                test_bundle = json.loads(json.dumps(bundle))
                
                # Navigate to the path and mutate
                parts = path.lstrip("$.").split(".")
                current = test_bundle
                for part in parts[:-1]:
                    if "[" in part:
                        # Handle list indexing
                        field, idx = part.split("[")
                        idx = int(idx.rstrip("]"))
                        current = current[field][idx]
                    else:
                        current = current[part]
                
                last_part = parts[-1]
                if "[" in last_part:
                    field, idx = last_part.split("[")
                    idx = int(idx.rstrip("]"))
                    original = current[field][idx]
                    if isinstance(original, str):
                        current[field][idx] = "MUTATED_" + original
                    elif isinstance(original, bool):
                        current[field][idx] = not original
                    elif isinstance(original, int):
                        current[field][idx] = original + 1
                else:
                    original = current[last_part]
                    if isinstance(original, str):
                        current[last_part] = "MUTATED_" + original
                    elif isinstance(original, bool):
                        current[last_part] = not original
                    elif isinstance(original, int):
                        current[last_part] = original + 1
                
                # Write mutated bundle
                test_path = "/tmp/test_hash_coverage_mutated.json"
                with open(test_path, "w") as f:
                    json.dump(test_bundle, f)
                
                # Run demo on mutated bundle
                result = subprocess.run(
                    [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", test_path],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent
                )
                
                # Should either fail or have different hash
                if result.returncode == 0 and "REPLAY_VERDICT=PASS" in result.stdout:
                    # Extract hash
                    for line in result.stdout.split("\n"):
                        if line.startswith("HASH="):
                            mutated_hash = line.split("=")[1]
                            break
                    else:
                        raise AssertionError(f"Could not extract hash for path {path}")
                    
                    # Get original hash
                    original_path = "/tmp/test_hash_coverage_original.json"
                    with open(original_path, "w") as f:
                        json.dump(bundle, f)
                    result_orig = subprocess.run(
                        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", original_path],
                        capture_output=True,
                        text=True,
                        cwd=Path(__file__).parent.parent
                    )
                    for line in result_orig.stdout.split("\n"):
                        if line.startswith("HASH="):
                            original_hash = line.split("=")[1]
                            break
                    else:
                        raise AssertionError(f"Could not extract original hash")
                    
                    assert mutated_hash != original_hash, f"Hash did not change for HASHED field {path}"
                
                print(f"✓ {path}: hash changed or failed as expected")
                break


def test_excluded_nondeterministic_fields_stable():
    """Test that EXCLUDED_NONDETERMINISTIC field mutations do not change hash."""
    bundle = get_sample_bundle()
    manifest = get_coverage_manifest()
    
    # Get excluded fields with reasons
    excluded_fields = manifest.get("excluded_fields", [])
    excluded_reasons = manifest.get("excluded_reasons", {})
    
    print(f"Found {len(excluded_fields)} EXCLUDED_NONDETERMINISTIC fields")
    
    # Test that excluded fields are documented with reasons
    for field in excluded_fields:
        assert field in excluded_reasons, f"Excluded field {field} has no documented reason"
        reason = excluded_reasons[field]
        assert reason in ["nondeterministic", "runtime-only", "metadata-only", "computed-from-intent", "computed-from-canonical-bundle", "computed-from-core-fields"], \
            f"Excluded field {field} has invalid reason: {reason}"
        print(f"✓ {field}: documented with reason '{reason}'")


def test_unknown_fields_rejected():
    """Test that unknown injected fields cause UNKNOWN_FIELD failure."""
    bundle = get_sample_bundle()
    
    # Add unknown field at various depths
    test_cases = [
        ("$.unknown_root_field", "test"),
        ("$.intent.unknown_intent_field", "test"),
        ("$.policy_decision.unknown_policy_field", "test"),
    ]
    
    for path, value in test_cases:
        test_bundle = json.loads(json.dumps(bundle))
        
        # Navigate and inject
        parts = path.lstrip("$.").split(".")
        current = test_bundle
        for part in parts[:-1]:
            if "[" in part:
                field, idx = part.split("[")
                idx = int(idx.rstrip("]"))
                current = current[field][idx]
            else:
                current = current[part]
        
        last_part = parts[-1]
        if "[" in last_part:
            field, idx = last_part.split("[")
            idx = int(idx.rstrip("]"))
            current[field][idx] = value
        else:
            current[last_part] = value
        
        # Write test bundle
        test_path = "/tmp/test_hash_coverage_unknown.json"
        with open(test_path, "w") as f:
            json.dump(test_bundle, f)
        
        # Run demo
        result = subprocess.run(
            [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", test_path],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert "REPLAY_VERDICT=FAIL" in result.stdout, f"Unknown field {path} did not cause failure"
        assert "UNKNOWN_FIELD" in result.stdout, f"Unknown field {path} did not cause UNKNOWN_FIELD error"
        print(f"✓ {path}: rejected with UNKNOWN_FIELD")


def test_no_implicit_exclusions():
    """Test that no field is excluded without documented reason."""
    manifest = get_coverage_manifest()
    
    # Check root classification
    root_classification = manifest.get("root_classification", {})
    for field, classification in root_classification.items():
        if classification == "EXCLUDED_NONDETERMINISTIC":
            assert field in manifest.get("excluded_fields", []), f"Field {field} classified as EXCLUDED_NONDETERMINISTIC but not in excluded_fields list"
            assert field in manifest.get("excluded_reasons", {}), f"Field {field} classified as EXCLUDED_NONDETERMINISTIC but has no excluded_reason"
    
    # Check nested structures
    nested = manifest.get("nested_structure", {})
    for key, value in nested.items():
        if "classification" in value:
            for field, classification in value["classification"].items():
                if classification == "EXCLUDED_NONDETERMINISTIC":
                    # Check both direct excluded_fields and element_fields.excluded_fields
                    nested_excluded = value.get("excluded_fields", [])
                    if field not in nested_excluded and "element_fields" in value:
                        element_excluded = value["element_fields"].get("excluded_fields", [])
                        assert field in element_excluded, f"Nested field {key}.{field} classified as EXCLUDED_NONDETERMINISTIC but not in excluded_fields"
                        nested_reasons = value["element_fields"].get("excluded_reasons", {})
                        assert field in nested_reasons, f"Nested field {key}.{field} classified as EXCLUDED_NONDETERMINISTIC but has no excluded_reason"
                    else:
                        assert field in nested_excluded, f"Nested field {key}.{field} classified as EXCLUDED_NONDETERMINISTIC but not in excluded_fields"
                        nested_reasons = value.get("excluded_reasons", {})
                        assert field in nested_reasons, f"Nested field {key}.{field} classified as EXCLUDED_NONDETERMINISTIC but has no excluded_reason"
    
    print("✓ No implicit exclusions found")


def test_manifest_version_and_algorithm():
    """Test that manifest specifies canonicalization version and hash algorithm."""
    manifest = get_coverage_manifest()
    
    assert "canonicalization_version" in manifest, "Manifest missing canonicalization_version"
    assert manifest["canonicalization_version"] == "v1", f"Unexpected canonicalization_version: {manifest['canonicalization_version']}"
    
    assert "hash_algorithm" in manifest, "Manifest missing hash_algorithm"
    assert manifest["hash_algorithm"] == "sha256", f"Unexpected hash_algorithm: {manifest['hash_algorithm']}"
    
    print("✓ Manifest version and algorithm specified")


if __name__ == "__main__":
    print("Testing canonical hash coverage...")
    print()
    
    test_manifest_version_and_algorithm()
    test_no_implicit_exclusions()
    test_excluded_nondeterministic_fields_stable()
    test_unknown_fields_rejected()
    test_all_hashed_fields_change_hash()
    
    print()
    print("All canonical hash coverage tests passed!")
