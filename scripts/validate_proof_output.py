#!/usr/bin/env python3
"""
Proof Output Validation Script

Validates CLI output contains all required fields and consistent values.
Exits non-zero if any missing or inconsistent.
"""

import sys
import re
import subprocess


def run_proof_harness():
    """Run determinism proof harness and capture output."""
    cmd = [
        sys.executable, "-m", "exoarmur.cli",
        "prove-determinism", "--runs", "3", "--mode", "all", "--include-failure-demo"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def extract_field(output, pattern):
    """Extract field value from output using regex."""
    match = re.search(pattern, output)
    if not match:
        return None
    return match.group(1)


def validate_proof_output():
    """Validate proof output contains required fields and consistent values."""
    output = run_proof_harness()
    
    failures = []
    
    # Check for Input Hash
    if "Input Hash:" not in output:
        failures.append("Input Hash missing")
    
    # Check for Execution Hash
    if "Execution Hash:" not in output:
        failures.append("Execution Hash missing")
    
    # Check for Replay Verification
    replay_match = re.search(r"Replay Verification:\s*([✓✗])\s*(\w+)", output)
    if not replay_match:
        failures.append("Replay Verification missing")
    else:
        status = replay_match.group(2)
        if status != "MATCH":
            failures.append(f"Replay Verification status is {status}, expected MATCH")
    
    # Check for Unique Hashes = 1
    unique_hash_match = re.search(r"Unique Hashes Observed:\s*(\d+)", output)
    if not unique_hash_match:
        failures.append("Unique Hashes Observed missing")
    else:
        count = int(unique_hash_match.group(1))
        if count != 1:
            failures.append(f"Unique Hashes Observed is {count}, expected 1")
    
    # Check for Noise Injection
    noise_match = re.search(r"Noise Injection:\s*([✓✗])\s*(\w+)", output)
    if not noise_match:
        failures.append("Noise Injection missing")
    else:
        status = noise_match.group(2)
        if status != "IGNORED":
            failures.append(f"Noise Injection status is {status}, expected IGNORED")
    
    # Check for Failure Detection
    failure_match = re.search(r"Failure Detection:\s*([✓✗])\s*(\w+)", output)
    if not failure_match:
        failures.append("Failure Detection missing")
    else:
        status = failure_match.group(2)
        if status != "ENFORCED":
            failures.append(f"Failure Detection status is {status}, expected ENFORCED")
    
    # Check for STATUS: VERIFIED
    if "STATUS: VERIFIED" not in output:
        failures.append("STATUS: VERIFIED missing")
    
    # Report results
    if failures:
        print("❌ Proof output validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✓ Proof output validation passed")
        print("  ✓ Input Hash present")
        print("  ✓ Execution Hash present")
        print("  ✓ Replay Verification: MATCH")
        print("  ✓ Unique Hashes = 1")
        print("  ✓ Noise Injection: IGNORED")
        print("  ✓ Failure Detection: ENFORCED")
        print("  ✓ STATUS: VERIFIED")
        sys.exit(0)


if __name__ == "__main__":
    validate_proof_output()
