"""
Test --explain failure output mode.

This test verifies that the --explain CLI flag provides detailed failure explanations.
"""

import json
import sys
import subprocess
from pathlib import Path


def test_explain_flag_exists():
    """Test that --explain flag is accepted by the CLI."""
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, "Help command should succeed"
    assert "--explain" in result.stdout, "--explain flag should be documented in help"
    
    print("✓ --explain flag exists in CLI")


def test_explain_mode_outputs_explanation():
    """Test that --explain mode outputs detailed failure explanation."""
    # Generate a sample bundle
    sample_path = "/tmp/test_explain_sample.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, "Sample bundle generation should succeed"
    
    # Tamper with the bundle to cause a failure
    with open(sample_path) as f:
        bundle = json.load(f)
    bundle["evil_field"] = "malicious"
    tampered_path = "/tmp/test_explain_tampered.json"
    with open(tampered_path, "w") as f:
        json.dump(bundle, f, indent=2)
    
    # Run without --explain
    result_without = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", tampered_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Run with --explain
    result_with = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", tampered_path, "--explain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Both should fail
    assert "REPLAY_VERDICT=FAIL" in result_without.stdout, "Should fail without --explain"
    assert "REPLAY_VERDICT=FAIL" in result_with.stdout, "Should fail with --explain"
    
    # --explain should have additional output
    assert "EXPLANATION=" in result_with.stdout, "--explain should output EXPLANATION field"
    assert "DETAIL=" in result_with.stdout, "--explain should output DETAIL field"
    
    # Without --explain should not have these fields
    assert "EXPLANATION=" not in result_without.stdout, "Without --explain should not output EXPLANATION"
    
    print("✓ --explain mode outputs detailed explanation")


def test_explain_unknown_field():
    """Test that --explain provides details for UNKNOWN_FIELD errors."""
    # Generate a sample bundle
    sample_path = "/tmp/test_explain_unknown.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    # Add unknown field
    with open(sample_path) as f:
        bundle = json.load(f)
    bundle["unknown_field"] = "test"
    tampered_path = "/tmp/test_explain_unknown_tampered.json"
    with open(tampered_path, "w") as f:
        json.dump(bundle, f, indent=2)
    
    # Run with --explain
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", tampered_path, "--explain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert "REPLAY_VERDICT=FAIL" in result.stdout
    assert "UNKNOWN_FIELD" in result.stdout, "Should mention UNKNOWN_FIELD"
    assert "EXPLANATION=" in result.stdout
    assert "DETAIL=" in result.stdout
    assert "CANONICAL_COVERAGE.json" in result.stdout, "Should mention CANONICAL_COVERAGE.json"
    
    print("✓ --explain provides details for UNKNOWN_FIELD")


def test_explain_type_mismatch():
    """Test that --explain provides details for TYPE_MISMATCH errors."""
    # Generate a sample bundle
    sample_path = "/tmp/test_explain_type.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    # Change type of a field
    with open(sample_path) as f:
        bundle = json.load(f)
    bundle["execution_trace"]["events"][0]["ok"] = "true"  # String instead of bool
    tampered_path = "/tmp/test_explain_type_tampered.json"
    with open(tampered_path, "w") as f:
        json.dump(bundle, f, indent=2)
    
    # Run with --explain
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", tampered_path, "--explain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert "REPLAY_VERDICT=FAIL" in result.stdout
    assert "TYPE_MISMATCH" in result.stdout, "Should mention TYPE_MISMATCH"
    assert "EXPLANATION=" in result.stdout
    assert "DETAIL=" in result.stdout
    assert "Type coercion" in result.stdout, "Should mention type coercion"
    
    print("✓ --explain provides details for TYPE_MISMATCH")


def test_explain_missing_field():
    """Test that --explain provides details for MISSING_FIELD errors."""
    # Generate a sample bundle
    sample_path = "/tmp/test_explain_missing.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    # Remove required field
    with open(sample_path) as f:
        bundle = json.load(f)
    del bundle["intent"]["action_type"]
    tampered_path = "/tmp/test_explain_missing_tampered.json"
    with open(tampered_path, "w") as f:
        json.dump(bundle, f, indent=2)
    
    # Run with --explain
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", tampered_path, "--explain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert "REPLAY_VERDICT=FAIL" in result.stdout
    assert "MISSING_FIELD" in result.stdout, "Should mention MISSING_FIELD"
    assert "EXPLANATION=" in result.stdout
    assert "DETAIL=" in result.stdout
    assert "required field" in result.stdout.lower(), "Should mention required field"
    
    print("✓ --explain provides details for MISSING_FIELD")


def test_explain_not_shown_on_success():
    """Test that --explain does not add output on successful verification."""
    # Generate a sample bundle
    sample_path = "/tmp/test_explain_success.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    
    # Run without --explain
    result_without = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Run with --explain
    result_with = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--input", sample_path, "--explain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Both should succeed
    assert "REPLAY_VERDICT=PASS" in result_without.stdout
    assert "REPLAY_VERDICT=PASS" in result_with.stdout
    
    # --explain should not add extra output on success
    assert "EXPLANATION=" not in result_with.stdout, "--explain should not add output on success"
    assert "DETAIL=" not in result_with.stdout, "--explain should not add output on success"
    
    print("✓ --explain does not add output on success")


if __name__ == "__main__":
    print("Testing --explain failure output mode...")
    print()
    
    test_explain_flag_exists()
    test_explain_mode_outputs_explanation()
    test_explain_unknown_field()
    test_explain_type_mismatch()
    test_explain_missing_field()
    test_explain_not_shown_on_success()
    
    print()
    print("All --explain mode tests passed!")
