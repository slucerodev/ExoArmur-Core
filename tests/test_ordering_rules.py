"""
Test ordering rules enforcement.

Ensures that:
- Object key reorder produces same hash (unordered)
- List reorder produces different hash when ordered
- List reorder produces same hash when unordered
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))

from exoarmur.replay.canonical_utils import canonical_json, stable_hash


def test_key_reorder_same_hash():
    """Test that object key reorder produces same hash (unordered)."""
    bundle1 = {
        "intent_id": "test",
        "action_type": "delete",
        "target": "/tmp/test.txt",
    }
    
    bundle2 = {
        "target": "/tmp/test.txt",
        "action_type": "delete",
        "intent_id": "test",
    }
    
    canonical1 = canonical_json(bundle1)
    canonical2 = canonical_json(bundle2)
    
    hash1 = stable_hash(canonical1)
    hash2 = stable_hash(canonical2)
    
    assert hash1 == hash2, f"Key reorder should produce same hash: {hash1} != {hash2}"


def test_ordered_list_reorder_different_hash():
    """Test that ordered list reorder produces different hash."""
    bundle1 = {
        "intent_id": "test",
        "action_type": "delete",
        "ordered_list": ["a", "b", "c"],
    }
    
    bundle2 = {
        "intent_id": "test",
        "action_type": "delete",
        "ordered_list": ["c", "b", "a"],
    }
    
    canonical1 = canonical_json(bundle1)
    canonical2 = canonical_json(bundle2)
    
    hash1 = stable_hash(canonical1)
    hash2 = stable_hash(canonical2)
    
    assert hash1 != hash2, f"Ordered list reorder should produce different hash: {hash1} == {hash2}"


def test_unordered_list_reorder_same_hash():
    """Test that unordered list reorder produces same hash (after sorting)."""
    bundle1 = {
        "intent_id": "test",
        "action_type": "delete",
        "unordered_list": ["c", "a", "b"],
    }
    
    bundle2 = {
        "intent_id": "test",
        "action_type": "delete",
        "unordered_list": ["a", "b", "c"],
    }
    
    # Sort unordered lists before canonicalization
    bundle1["unordered_list"] = sorted(bundle1["unordered_list"])
    bundle2["unordered_list"] = sorted(bundle2["unordered_list"])
    
    canonical1 = canonical_json(bundle1)
    canonical2 = canonical_json(bundle2)
    
    hash1 = stable_hash(canonical1)
    hash2 = stable_hash(canonical2)
    
    assert hash1 == hash2, f"Sorted unordered list reorder should produce same hash: {hash1} != {hash2}"


if __name__ == "__main__":
    test_key_reorder_same_hash()
    test_ordered_list_reorder_different_hash()
    test_unordered_list_reorder_same_hash()
    print("All ordering rules tests passed")
