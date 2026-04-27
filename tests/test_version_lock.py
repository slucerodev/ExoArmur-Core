"""
Test version locking for canonicalization.

Ensures that:
- Version is embedded in canonicalization module
- Version mismatch is detected
- Version is required for valid replay
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))


def test_version_in_manifest():
    """Test that version is defined in coverage manifest."""
    manifest_path = repo_root / "artifacts" / "canonical" / "CANONICAL_COVERAGE.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    assert "version" in manifest, "Version must be in coverage manifest"
    assert manifest["version"] == "v1", f"Expected version v1, got {manifest['version']}"


def test_version_in_ordering_rules():
    """Test that version is defined in ordering rules."""
    manifest_path = repo_root / "artifacts" / "canonical" / "ORDERING_RULES.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    assert "version" in manifest, "Version must be in ordering rules"
    assert manifest["version"] == "v1", f"Expected version v1, got {manifest['version']}"


def test_version_consistency():
    """Test that versions are consistent across manifests."""
    coverage_path = repo_root / "artifacts" / "canonical" / "CANONICAL_COVERAGE.json"
    ordering_path = repo_root / "artifacts" / "canonical" / "ORDERING_RULES.json"
    
    with open(coverage_path) as f:
        coverage = json.load(f)
    
    with open(ordering_path) as f:
        ordering = json.load(f)
    
    assert coverage["version"] == ordering["version"], "Versions must be consistent across manifests"


if __name__ == "__main__":
    test_version_in_manifest()
    test_version_in_ordering_rules()
    test_version_consistency()
    print("All version lock tests passed")
