"""
Test user-supplied input capability for proof demo.

Ensures that:
- Default demo still passes
- --write-sample creates valid JSON
- --input sample passes
- Repeated --input sample runs produce same hash
- Changing one semantic value fails or changes hash
- Adding unknown field fails
- Removing required field fails
- Malformed JSON fails cleanly
- Missing input file fails cleanly
- --input path does not bypass canonical validation
- Tamper modes work correctly (value, remove-field, add-field, reorder)
- Recursive validation detects MISSING_FIELD and UNKNOWN_FIELD errors
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))


def run_demo(*args) -> tuple[int, str, str]:
    """Run the demo script with given arguments."""
    cmd = [sys.executable, str(repo_root / "demos" / "canonical_truth_reconstruction_demo.py")] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
    return result.returncode, result.stdout, result.stderr


def test_default_demo_still_passes():
    """Test that default demo still passes."""
    returncode, stdout, stderr = run_demo()
    assert returncode == 0, f"Default demo failed: {stderr}"
    assert "REPLAY_VERDICT=PASS" in stdout
    assert "CANONICALIZATION_VERSION=v1" in stdout
    assert "HASH_ALGORITHM=sha256" in stdout
    assert "HASH=" in stdout


def test_write_sample_creates_valid_json():
    """Test that --write-sample creates valid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        assert "Sample bundle written to" in stdout
        
        # Verify file exists and is valid JSON
        sample_file = Path(sample_path)
        assert sample_file.exists()
        
        with open(sample_file) as f:
            bundle = json.load(f)
        
        # Verify bundle has required fields for full ExecutionProofBundle structure
        assert "schema_version" in bundle
        assert "bundle_version" in bundle
        assert "intent" in bundle
        assert "policy_decision" in bundle
        assert "safety_verdict" in bundle
        assert "final_verdict" in bundle
        assert "execution_trace" in bundle
        assert "executor_result" in bundle
        assert "intent" in bundle and "action_type" in bundle["intent"]
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_input_sample_passes():
    """Test that --input sample passes."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write sample first
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        
        # Then read it back
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0, f"Input sample failed: {stderr}"
        assert "REPLAY_VERDICT=PASS" in stdout
        assert "CANONICALIZATION_VERSION=v1" in stdout
        assert "HASH_ALGORITHM=sha256" in stdout
        assert "HASH=" in stdout
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_repeated_input_runs_produce_same_hash():
    """Test that repeated --input sample runs produce same hash."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write sample first
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        
        # Run input twice
        returncode1, stdout1, stderr1 = run_demo("--input", sample_path)
        returncode2, stdout2, stderr2 = run_demo("--input", sample_path)
        
        assert returncode1 == 0, f"First input run failed: {stderr1}"
        assert returncode2 == 0, f"Second input run failed: {stderr2}"
        
        # Extract hashes
        hash1 = [line for line in stdout1.split("\n") if line.startswith("HASH=")][0]
        hash2 = [line for line in stdout2.split("\n") if line.startswith("HASH=")][0]
        
        assert hash1 == hash2, f"Hashes differ: {hash1} != {hash2}"
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_changing_semantic_value_changes_hash():
    """Test that changing one semantic value changes hash."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write sample first
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        
        # Get original hash
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0, f"Input sample failed: {stderr}"
        original_hash = [line for line in stdout.split("\n") if line.startswith("HASH=")][0]
        
        # Modify the bundle - change action_type in nested intent
        with open(sample_path) as f:
            bundle = json.load(f)
        bundle["intent"]["action_type"] = "read"  # Change semantic value
        with open(sample_path, "w") as f:
            json.dump(bundle, f)
        
        # Get new hash
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0, f"Modified input failed: {stderr}"
        new_hash = [line for line in stdout.split("\n") if line.startswith("HASH=")][0]
        
        assert original_hash != new_hash, f"Hash should change: {original_hash} == {new_hash}"
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_adding_unknown_field_fails():
    """Test that adding unknown field fails."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write sample first
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        
        # Add unknown field at top level
        with open(sample_path) as f:
            bundle = json.load(f)
        bundle["unknown_field"] = "test"
        with open(sample_path, "w") as f:
            json.dump(bundle, f)
        
        # Should fail
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0  # Script exits cleanly
        assert "REPLAY_VERDICT=FAIL" in stdout
        assert "UNKNOWN_FIELD" in stdout
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_removing_required_field_fails():
    """Test that removing required field fails."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write sample first
        returncode, stdout, stderr = run_demo("--write-sample", sample_path)
        assert returncode == 0, f"Write-sample failed: {stderr}"
        
        # Remove required field from nested intent
        with open(sample_path) as f:
            bundle = json.load(f)
        del bundle["intent"]["action_type"]
        with open(sample_path, "w") as f:
            json.dump(bundle, f)
        
        # Should fail with MISSING_FIELD error
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0
        assert "REPLAY_VERDICT=FAIL" in stdout
        assert "MISSING_FIELD" in stdout
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_malformed_json_fails_cleanly():
    """Test that malformed JSON fails cleanly."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write malformed JSON
        with open(sample_path, "w") as f:
            f.write("{invalid json")
        
        # Should fail cleanly
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0
        assert "REPLAY_VERDICT=FAIL" in stdout
        assert "MALFORMED_JSON" in stdout
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_missing_input_file_fails_cleanly():
    """Test that missing input file fails cleanly."""
    returncode, stdout, stderr = run_demo("--input", "/nonexistent/path.json")
    assert returncode == 0
    assert "REPLAY_VERDICT=FAIL" in stdout
    assert "FILE_NOT_FOUND" in stdout


def test_input_path_does_not_bypass_validation():
    """Test that --input path does not bypass canonical validation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        sample_path = f.name
    
    try:
        # Write bundle with type mismatch in nested structure
        bundle = {
            "schema_version": "2.0",
            "bundle_version": "v1",
            "intent": {
                "intent_id": "test",
                "action_type": "delete",
                "target": "/tmp/test.txt",
                "parameters": {}
            },
            "policy_decision": {
                "verdict": "deny",
                "rationale": "test",
                "approval_required": False
            },
            "safety_verdict": {
                "verdict": "deny",
                "rationale": "test"
            },
            "final_verdict": "deny",
            "approval_records": [],
            "execution_trace": {
                "events": [],
                "final_verdict": "deny"
            },
            "executor_result": {
                "success": "false",  # String instead of bool
                "output": {},
                "error": None,
                "evidence": {}
            },
            "governance_evidence": {},
            "resolution_evidence": {},
            "executor_capabilities": {},
            "validation_evidence": {},
            "executor_failure_evidence": {}
        }
        with open(sample_path, "w") as f:
            json.dump(bundle, f)
        
        # Should fail due to type mismatch
        returncode, stdout, stderr = run_demo("--input", sample_path)
        assert returncode == 0
        assert "REPLAY_VERDICT=FAIL" in stdout
        assert "TYPE_MISMATCH" in stdout
    finally:
        Path(sample_path).unlink(missing_ok=True)


def test_tamper_value_mode():
    """Test that --tamper value mode fails with HASH_MISMATCH."""
    returncode, stdout, stderr = run_demo("--tamper", "value")
    assert returncode == 0
    assert "REPLAY_VERDICT=FAIL" in stdout
    assert "HASH_MISMATCH" in stdout


def test_tamper_remove_field_mode():
    """Test that --tamper remove-field mode fails with MISSING_FIELD."""
    returncode, stdout, stderr = run_demo("--tamper", "remove-field")
    assert returncode == 0
    assert "REPLAY_VERDICT=FAIL" in stdout
    assert "MISSING_FIELD" in stdout


def test_tamper_add_field_mode():
    """Test that --tamper add-field mode fails with UNKNOWN_FIELD."""
    returncode, stdout, stderr = run_demo("--tamper", "add-field")
    assert returncode == 0
    assert "REPLAY_VERDICT=FAIL" in stdout
    assert "UNKNOWN_FIELD" in stdout


def test_tamper_reorder_mode():
    """Test that --tamper reorder mode fails with HASH_MISMATCH."""
    returncode, stdout, stderr = run_demo("--tamper", "reorder")
    assert returncode == 0
    assert "REPLAY_VERDICT=FAIL" in stdout
    assert "HASH_MISMATCH" in stdout


if __name__ == "__main__":
    test_default_demo_still_passes()
    test_write_sample_creates_valid_json()
    test_input_sample_passes()
    test_repeated_input_runs_produce_same_hash()
    test_changing_semantic_value_changes_hash()
    test_adding_unknown_field_fails()
    test_removing_required_field_fails()
    test_malformed_json_fails_cleanly()
    test_missing_input_file_fails_cleanly()
    test_input_path_does_not_bypass_validation()
    test_tamper_value_mode()
    test_tamper_remove_field_mode()
    test_tamper_add_field_mode()
    test_tamper_reorder_mode()
    print("All proof demo user input tests passed")
