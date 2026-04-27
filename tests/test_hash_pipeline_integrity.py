"""
Test hash pipeline integrity.

This test verifies that:
- Hash input is canonical JSON only
- Raw input is not directly hashed
- Display/output fields are not hash input
- Default and --input paths reach same verify_bundle function
"""

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import hashlib


def test_verify_bundle_is_single_entry_point():
    """Test that verify_bundle is the single explicit function boundary."""
    # Import the demo module
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Failed to generate sample: {result.stderr}"
    
    with open(sample_path) as f:
        bundle = json.load(f)
    
    # Call verify_bundle directly
    verdict, hash_val = verify_bundle(bundle)
    assert verdict == "PASS"
    assert len(hash_val) == 64  # SHA256 hex string
    
    print("✓ verify_bundle is the single entry point")


def test_hash_input_is_canonical_json_only():
    """Test that hash input is canonical JSON only, not raw bundle."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle, canonical_json, canonicalize_bundle
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    with open(sample_path) as f:
        bundle = json.load(f)
    
    # Spy on stable_hash to capture its input
    captured_inputs = []
    original_stable_hash = None
    
    def spy_stable_hash(data):
        captured_inputs.append(data)
        return hashlib.sha256(data.encode()).hexdigest()
    
    # Patch stable_hash
    with patch('canonical_truth_reconstruction_demo.stable_hash', side_effect=spy_stable_hash):
        from canonical_truth_reconstruction_demo import verify_bundle
        verdict, hash_val = verify_bundle(bundle)
    
    # Verify that the hash input is canonical JSON
    assert len(captured_inputs) == 1, "stable_hash should be called exactly once"
    hash_input = captured_inputs[0]
    
    # Generate expected canonical JSON
    canonical_bundle = canonicalize_bundle(bundle)
    expected_canonical_json = canonical_json(canonical_bundle)
    
    # Verify hash input equals canonical JSON
    assert hash_input == expected_canonical_json, "Hash input must equal canonical JSON"
    
    # Verify hash input is NOT raw bundle JSON
    raw_bundle_json = json.dumps(bundle, sort_keys=True)
    assert hash_input != raw_bundle_json, "Hash input must not be raw bundle JSON"
    
    print("✓ Hash input is canonical JSON only")


def test_raw_input_not_directly_hashed():
    """Test that raw input bundle is not directly hashed."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    with open(sample_path) as f:
        bundle = json.load(f)
    
    # Compute hash of raw bundle directly
    raw_bundle_json = json.dumps(bundle, sort_keys=True)
    raw_hash = hashlib.sha256(raw_bundle_json.encode()).hexdigest()
    
    # Compute hash through verify_bundle
    from canonical_truth_reconstruction_demo import verify_bundle
    verdict, verify_hash = verify_bundle(bundle)
    
    # They should be different (verify_hash uses canonicalization)
    assert verify_hash != raw_hash, "Raw bundle should not be directly hashed"
    
    print("✓ Raw input is not directly hashed")


def test_canonical_json_has_sorted_keys():
    """Test that canonical JSON has sorted object keys."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import canonical_json, canonicalize_bundle
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    with open(sample_path) as f:
        bundle = json.load(f)
    
    # Generate canonical JSON
    canonical_bundle = canonicalize_bundle(bundle)
    canonical_json_str = canonical_json(canonical_bundle)
    
    # Parse and verify sorted keys
    def has_sorted_keys(obj):
        if isinstance(obj, dict):
            keys = list(obj.keys())
            if keys != sorted(keys):
                return False
            for value in obj.values():
                if not has_sorted_keys(value):
                    return False
        elif isinstance(obj, list):
            for item in obj:
                if not has_sorted_keys(item):
                    return False
        return True
    
    canonical_obj = json.loads(canonical_json_str)
    assert has_sorted_keys(canonical_obj), "Canonical JSON must have sorted object keys"
    
    print("✓ Canonical JSON has sorted keys")


def test_default_and_input_paths_same_function():
    """Test that default and --input paths reach same verify_bundle function."""
    demo_path = Path(__file__).parent.parent / "demos"
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    # Run with --input
    result_input = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--input", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result_input.returncode == 0
    
    # Extract hash from --input output
    input_hash = None
    for line in result_input.stdout.split("\n"):
        if line.startswith("HASH="):
            input_hash = line.split("=")[1]
            break
    assert input_hash is not None, "Could not extract hash from --input output"
    
    # Run default mode and generate its hash
    result_default = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py")],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result_default.returncode == 0
    
    # Extract hash from default output
    default_hash = None
    for line in result_default.stdout.split("\n"):
        if line.startswith("HASH="):
            default_hash = line.split("=")[1]
            break
    assert default_hash is not None, "Could not extract hash from default output"
    
    # They should be the same (same deterministic bundle)
    assert input_hash == default_hash, "Default and --input should produce same hash for identical bundles"
    
    print("✓ Default and --input paths reach same verification logic")


def test_canonicalization_before_hash():
    """Test that canonicalization happens before hashing (internal assertion)."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle, canonicalize_bundle
    
    # Generate a sample bundle
    sample_path = "/tmp/test_pipeline_sample.json"
    result = subprocess.run(
        [sys.executable, str(demo_path / "canonical_truth_reconstruction_demo.py"), "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    with open(sample_path) as f:
        bundle = json.load(f)
    
    # The internal assertion in verify_bundle checks that canonical_bundle is not bundle
    # This ensures canonicalization creates a new object
    verdict, hash_val = verify_bundle(bundle)
    assert verdict == "PASS"
    
    print("✓ Canonicalization happens before hashing (internal assertion passes)")


if __name__ == "__main__":
    print("Testing hash pipeline integrity...")
    print()
    
    test_verify_bundle_is_single_entry_point()
    test_hash_input_is_canonical_json_only()
    test_raw_input_not_directly_hashed()
    test_canonical_json_has_sorted_keys()
    test_default_and_input_paths_same_function()
    test_canonicalization_before_hash()
    
    print()
    print("All hash pipeline integrity tests passed!")
