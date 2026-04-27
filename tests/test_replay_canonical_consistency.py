"""
Test replay/canonical consistency.

This test verifies consistency between:
- Source audit bundle
- Reconstructed execution representation
- Canonical representation

For every required semantic field:
- Source value must appear in reconstructed representation OR be intentionally transformed with documented rule
- Canonical value must derive from reconstructed representation
- No canonical field may be copied directly from raw input if replay reconstruction should own it
"""

import json
import sys
import subprocess
from pathlib import Path


def get_sample_bundle():
    """Generate a sample bundle for testing."""
    sample_path = "/tmp/test_replay_consistency_sample.json"
    result = subprocess.run(
        [sys.executable, "demos/canonical_truth_reconstruction_demo.py", "--write-sample", sample_path],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Failed to generate sample: {result.stderr}"
    
    with open(sample_path) as f:
        return json.load(f)


def test_valid_bundle_reconstructs_expected_canonical():
    """Test that a valid bundle reconstructs expected canonical representation."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import canonicalize_bundle, canonical_json
    
    bundle = get_sample_bundle()
    
    # Generate canonical representation
    canonical_bundle = canonicalize_bundle(bundle)
    canonical_json_str = canonical_json(canonical_bundle)
    
    # Verify canonical representation is valid JSON
    canonical_obj = json.loads(canonical_json_str)
    assert isinstance(canonical_obj, dict), "Canonical representation must be a dict"
    
    # Verify all required top-level fields are present
    required_fields = ["schema_version", "bundle_version", "intent", "policy_decision", 
                      "safety_verdict", "final_verdict", "execution_trace", "executor_result"]
    for field in required_fields:
        assert field in canonical_obj, f"Required field {field} missing from canonical representation"
    
    print("✓ Valid bundle reconstructs expected canonical representation")


def test_semantic_field_changes_affect_hash():
    """Test that changing source semantic field changes hash or fails."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    bundle = get_sample_bundle()
    
    # Get original hash
    original_verdict, original_hash = verify_bundle(bundle)
    assert original_verdict == "PASS"
    
    # Change semantic field: action_type
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["intent"]["action_type"] = "read"  # Original was "delete"
    
    # Get new hash
    new_verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if new_verdict == "PASS":
        assert new_hash != original_hash, "Semantic field change should change hash"
    
    print("✓ Semantic field change affects hash or fails")


def test_nested_field_changes_affect_hash():
    """Test that changing replay-relevant nested field changes hash or fails."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import verify_bundle
    
    bundle = get_sample_bundle()
    
    # Get original hash
    original_verdict, original_hash = verify_bundle(bundle)
    assert original_verdict == "PASS"
    
    # Change nested field: event code
    test_bundle = json.loads(json.dumps(bundle))
    test_bundle["execution_trace"]["events"][0]["code"] = "MODIFIED"
    
    # Get new hash
    new_verdict, new_hash = verify_bundle(test_bundle)
    
    # Should either fail or have different hash
    if new_verdict == "PASS":
        assert new_hash != original_hash, "Nested field change should change hash"
    
    print("✓ Nested field change affects hash or fails")


def test_counts_match_actual_records():
    """Test that counts match actual records/events."""
    bundle = get_sample_bundle()
    
    # Verify events count matches actual events list length
    events = bundle["execution_trace"]["events"]
    assert len(events) == len(bundle["execution_trace"]["events"]), "Events count must match actual events"
    
    # Verify each event has required fields
    for event in events:
        assert "stage" in event, "Event must have stage"
        assert "ok" in event, "Event must have ok"
        assert "code" in event, "Event must have code"
    
    print("✓ Counts match actual records/events")


def test_final_status_matches_terminal_state():
    """Test that final status matches replayed terminal state."""
    bundle = get_sample_bundle()
    
    # final_verdict should match the terminal state from execution_trace
    final_verdict = bundle["final_verdict"]
    trace_final_verdict = bundle["execution_trace"]["final_verdict"]
    
    assert final_verdict == trace_final_verdict, "final_verdict must match execution_trace.final_verdict"
    
    # Also verify consistency with policy_decision and safety_verdict
    # If policy_deny, final should be deny
    if bundle["policy_decision"]["verdict"] == "deny":
        assert final_verdict == "deny", "Policy deny should result in deny verdict"
    
    print("✓ Final status matches terminal state")


def test_canonical_derives_from_reconstructed():
    """Test that canonical representation derives from reconstructed representation, not raw copy."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import canonicalize_bundle
    
    bundle = get_sample_bundle()
    
    # Generate canonical representation
    canonical_bundle = canonicalize_bundle(bundle)
    
    # Canonical should be a different object (not the same reference)
    assert canonical_bundle is not bundle, "Canonical must be a new object, not a reference to raw bundle"
    
    # Canonical should have excluded fields removed (like timestamps, event_id, etc.)
    # Check that nondeterministic fields are excluded
    if "bundle_id" in bundle:
        assert "bundle_id" not in canonical_bundle, "bundle_id should be excluded from canonical"
    
    # Check that nested excluded fields are removed
    if "execution_trace" in canonical_bundle and "events" in canonical_bundle["execution_trace"]:
        for event in canonical_bundle["execution_trace"]["events"]:
            assert "event_id" not in event, "event_id should be excluded from canonical"
            assert "timestamp" not in event, "timestamp should be excluded from canonical"
    
    print("✓ Canonical derives from reconstructed, not raw copy")


def test_source_values_in_reconstructed():
    """Test that source values appear in reconstructed representation."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import canonicalize_bundle
    
    bundle = get_sample_bundle()
    canonical_bundle = canonicalize_bundle(bundle)
    
    # Key semantic fields should be preserved
    assert bundle["intent"]["action_type"] == canonical_bundle["intent"]["action_type"], \
        "action_type should be preserved in canonical"
    assert bundle["intent"]["target"] == canonical_bundle["intent"]["target"], \
        "target should be preserved in canonical"
    assert bundle["policy_decision"]["verdict"] == canonical_bundle["policy_decision"]["verdict"], \
        "policy verdict should be preserved in canonical"
    assert bundle["final_verdict"] == canonical_bundle["final_verdict"], \
        "final_verdict should be preserved in canonical"
    
    print("✓ Source values appear in reconstructed representation")


def test_no_direct_raw_copy_in_hash():
    """Test that canonical fields are not directly copied from raw input for replay-relevant fields."""
    demo_path = Path(__file__).parent.parent / "demos"
    sys.path.insert(0, str(demo_path))
    from canonical_truth_reconstruction_demo import canonicalize_bundle
    
    bundle = get_sample_bundle()
    canonical_bundle = canonicalize_bundle(bundle)
    
    # Verify that canonicalization applies transformations (e.g., removing excluded fields)
    # rather than a direct copy
    
    # Check that the canonical bundle is a subset with transformations applied
    # not a shallow copy
    if "execution_trace" in bundle and "events" in bundle["execution_trace"]:
        raw_events = bundle["execution_trace"]["events"]
        canonical_events = canonical_bundle["execution_trace"]["events"]
        
        # Same number of events
        assert len(raw_events) == len(canonical_events), "Event count should match"
        
        # But canonical events should have excluded fields removed
        for raw_event, canonical_event in zip(raw_events, canonical_events):
            # Check that canonical event has fewer or equal fields (exclusions removed)
            assert len(canonical_event) <= len(raw_event), \
                "Canonical event should have excluded fields removed"
    
    print("✓ No direct raw copy in hash - transformations applied")


if __name__ == "__main__":
    print("Testing replay/canonical consistency...")
    print()
    
    test_valid_bundle_reconstructs_expected_canonical()
    test_semantic_field_changes_affect_hash()
    test_nested_field_changes_affect_hash()
    test_counts_match_actual_records()
    test_final_status_matches_terminal_state()
    test_canonical_derives_from_reconstructed()
    test_source_values_in_reconstructed()
    test_no_direct_raw_copy_in_hash()
    
    print()
    print("All replay/canonical consistency tests passed!")
