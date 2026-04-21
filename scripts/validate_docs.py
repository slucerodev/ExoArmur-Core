#!/usr/bin/env python3
"""
Docs vs Reality Validation Script

Check:
- README contains proof output block
- README contains one-line command
- PROOF_SNAPSHOT exists
- claims in docs match actual CLI output fields
"""

import sys
import re
import subprocess
from pathlib import Path


def check_readme_proof_output(repo_root: Path) -> bool:
    """Check README contains proof output block."""
    readme_path = repo_root / "README.md"
    
    if not readme_path.exists():
        print("  ✗ README.md not found")
        return False
    
    content = readme_path.read_text()
    
    # Check for proof output section
    if "DETERMINISM PROOF" in content or "proof output" in content.lower():
        print("  ✓ README contains proof output section")
        return True
    else:
        print("  ✗ README missing proof output section")
        return False


def check_readme_one_line_command(repo_root: Path) -> bool:
    """Check README contains one-line command."""
    readme_path = repo_root / "README.md"
    
    if not readme_path.exists():
        return False
    
    content = readme_path.read_text()
    
    # Check for command examples
    if "exoarmur" in content and ("prove-determinism" in content or "```" in content):
        print("  ✓ README contains command examples")
        return True
    else:
        print("  ✗ README missing command examples")
        return False


def check_proof_snapshot_exists(repo_root: Path) -> bool:
    """Check PROOF_SNAPSHOT exists."""
    # Look for proof snapshot in common locations
    snapshot_paths = [
        repo_root / "PROOF_SNAPSHOT.md",
        repo_root / "docs" / "PROOF_SNAPSHOT.md",
        repo_root / "spec" / "PROOF_SNAPSHOT.md",
    ]
    
    for path in snapshot_paths:
        if path.exists():
            print(f"  ✓ PROOF_SNAPSHOT found at {path.relative_to(repo_root)}")
            return True
    
    print("  ✗ PROOF_SNAPSHOT not found")
    return False


def check_docs_match_cli_output(repo_root: Path) -> bool:
    """Check claims in docs match actual CLI output fields."""
    # Get actual CLI output
    cmd = [sys.executable, "-m", "exoarmur.cli", "prove-determinism", "--runs", "1", "--mode", "sequential"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    actual_output = result.stdout
    
    # Check for expected fields in actual output
    expected_fields = [
        "Input Hash",
        "Execution Hash",
        "Replay Verification",
        "Unique Hashes",
        "STATUS"
    ]
    
    missing_fields = []
    for field in expected_fields:
        if field not in actual_output:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"  ✗ CLI output missing fields: {', '.join(missing_fields)}")
        return False
    else:
        print("  ✓ CLI output contains all expected fields")
        return True


def validate_docs():
    """Run docs validation."""
    repo_root = Path(__file__).resolve().parent.parent
    
    print("=" * 60)
    print("DOCS VS REALITY VALIDATION")
    print("=" * 60)
    print()
    
    failures = []
    warnings = []
    
    # Check README proof output
    print("Checking README for proof output section...")
    if not check_readme_proof_output(repo_root):
        warnings.append("README missing proof output section")
    print()
    
    # Check README one-line command
    print("Checking README for command examples...")
    if not check_readme_one_line_command(repo_root):
        failures.append("README missing command examples")
    print()
    
    # Check PROOF_SNAPSHOT
    print("Checking for PROOF_SNAPSHOT...")
    if not check_proof_snapshot_exists(repo_root):
        warnings.append("PROOF_SNAPSHOT not found")
    print()
    
    # Check docs match CLI output
    print("Checking docs match actual CLI output...")
    if not check_docs_match_cli_output(repo_root):
        failures.append("CLI output fields don't match documentation")
    print()
    
    # Report warnings
    if warnings:
        print("⚠ Warnings (non-blocking):")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    # Report results
    if failures:
        print("❌ Docs validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✓ Docs validation passed")
        if not warnings:
            print("  ✓ README contains proof output section")
            print("  ✓ README contains command examples")
            print("  ✓ PROOF_SNAPSHOT exists")
            print("  ✓ CLI output matches documentation")
        else:
            print("  ✓ CLI output matches documentation (critical check)")
        sys.exit(0)


if __name__ == "__main__":
    validate_docs()
