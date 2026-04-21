"""
Deterministic Ordering Enforcement

Provides deterministic iteration over unordered data structures (dict, set).
Ensures consistent ordering across runs for hash inputs and iteration patterns.

Usage:
- deterministic_iter_dict(d) → yields items sorted by canonical_json(key)
- deterministic_iter_set(s) → yields items sorted by canonical_json(item)
- deterministic_sort_list(lst) → returns sorted copy using canonical_json(item)
- assert_deterministic_collection(obj) → raises if unordered structure is iterated without deterministic wrapper
"""

import json
from typing import Dict, Set, List, Iterable, Tuple, Any, Union
from collections.abc import KeysView, ValuesView, ItemsView

from exoarmur.replay.canonical_utils import canonical_json


def deterministic_iter_dict(d: Dict) -> Iterable[Tuple[Any, Any]]:
    """
    Iterate over dictionary items in deterministic order.
    
    Yields items sorted by canonical_json(key) to ensure consistent ordering
    across runs regardless of hash seed or insertion order.
    
    Args:
        d: Dictionary to iterate over
        
    Returns:
        Iterable of (key, value) tuples in deterministic order
    """
    if not isinstance(d, dict):
        raise TypeError(f"Expected dict, got {type(d).__name__}")
    
    # Sort keys by their canonical JSON representation
    sorted_keys = sorted(d.keys(), key=lambda k: canonical_json(k))
    
    for key in sorted_keys:
        yield (key, d[key])


def deterministic_iter_set(s: Set) -> Iterable[Any]:
    """
    Iterate over set items in deterministic order.
    
    Yields items sorted by canonical_json(item) to ensure consistent ordering
    across runs regardless of hash seed or insertion order.
    
    Args:
        s: Set to iterate over
        
    Returns:
        Iterable of items in deterministic order
    """
    if not isinstance(s, set):
        raise TypeError(f"Expected set, got {type(s).__name__}")
    
    # Sort items by their canonical JSON representation
    sorted_items = sorted(s, key=lambda item: canonical_json(item))
    
    for item in sorted_items:
        yield item


def deterministic_sort_list(lst: List) -> List:
    """
    Return a sorted copy of a list using canonical_json for comparison.
    
    Ensures consistent sorting across runs for complex objects that may
    have different string representations but identical canonical forms.
    
    Args:
        lst: List to sort
        
    Returns:
        New list sorted in deterministic order
    """
    if not isinstance(lst, list):
        raise TypeError(f"Expected list, got {type(lst).__name__}")
    
    return sorted(lst, key=lambda item: canonical_json(item))


class DeterministicCollectionError(Exception):
    """Raised when an unordered collection is iterated without deterministic wrapper"""
    pass


class DeterminismViolationError(Exception):
    """Raised when determinism is violated in execution"""
    pass


def assert_deterministic_collection(obj: Any):
    """
    Assert that an unordered structure is iterated with deterministic wrapper.
    
    This is a runtime guard that can be used in protected modules to ensure
    that dict/set iteration is done through deterministic_iter_dict/set.
    
    Args:
        obj: Object to check
        
    Raises:
        DeterministicCollectionError: If obj is an unordered collection
    """
    if isinstance(obj, dict):
        # Check if it's a view (dict.keys(), dict.items(), dict.values())
        if isinstance(obj, (KeysView, ItemsView, ValuesView)):
            raise DeterministicCollectionError(
                f"Direct iteration over dict.{obj.__class__.__name__} is nondeterministic. "
                f"Use deterministic_iter_dict() instead."
            )
    elif isinstance(obj, set):
        raise DeterministicCollectionError(
            f"Direct set iteration is nondeterministic. "
            f"Use deterministic_iter_set() instead."
        )


def get_deterministic_dict_items(d: Dict) -> List[Tuple[Any, Any]]:
    """
    Get dictionary items as a list in deterministic order.
    
    Convenience function that returns a list instead of an iterator.
    
    Args:
        d: Dictionary to get items from
        
    Returns:
        List of (key, value) tuples in deterministic order
    """
    return list(deterministic_iter_dict(d))


def get_deterministic_set_items(s: Set) -> List[Any]:
    """
    Get set items as a list in deterministic order.
    
    Convenience function that returns a list instead of an iterator.
    
    Args:
        s: Set to get items from
        
    Returns:
        List of items in deterministic order
    """
    return list(deterministic_iter_set(s))


def deterministic_dict_to_list(d: Dict) -> List[Tuple[Any, Any]]:
    """
    Convert dictionary to list of tuples in deterministic order.
    
    Alias for get_deterministic_dict_items for semantic clarity.
    
    Args:
        d: Dictionary to convert
        
    Returns:
        List of (key, value) tuples in deterministic order
    """
    return get_deterministic_dict_items(d)


def deterministic_set_to_list(s: Set) -> List[Any]:
    """
    Convert set to list in deterministic order.
    
    Alias for get_deterministic_set_items for semantic clarity.
    
    Args:
        s: Set to convert
        
    Returns:
        List of items in deterministic order
    """
    return get_deterministic_set_items(s)


# Context manager for temporarily disabling deterministic collection checks
from contextlib import contextmanager

@contextmanager
def allow_nondeterministic_iteration():
    """
    Context manager to temporarily allow nondeterministic iteration.
    
    Use sparingly and only for:
    - Test fixtures that intentionally use nondeterministic patterns
    - Legacy code paths being refactored
    - Non-critical utility functions
    
    DO NOT use in production critical paths.
    """
    # This is a placeholder for future implementation
    # Currently, deterministic iteration is enforced by code review and static analysis
    # Runtime enforcement would require monkey-patching dict/set.__iter__
    yield


# Helper for hashing collections deterministically
def deterministic_hash_dict(d: Dict) -> str:
    """
    Compute deterministic hash of dictionary contents.
    
    Uses canonical_json to ensure hash is consistent across runs
    regardless of insertion order or hash seed.
    
    Args:
        d: Dictionary to hash
        
    Returns:
        Stable hash string
    """
    from exoarmur.replay.canonical_utils import stable_hash
    items = get_deterministic_dict_items(d)
    return stable_hash(canonical_json(items))


def deterministic_hash_set(s: Set) -> str:
    """
    Compute deterministic hash of set contents.
    
    Uses canonical_json to ensure hash is consistent across runs
    regardless of insertion order or hash seed.
    
    Args:
        s: Set to hash
        
    Returns:
        Stable hash string
    """
    from exoarmur.replay.canonical_utils import stable_hash
    items = get_deterministic_set_items(s)
    return stable_hash(canonical_json(items))


def deterministic_hash_list(lst: List) -> str:
    """
    Compute deterministic hash of list contents.
    
    Sorts list using canonical_json before hashing to ensure
    hash is consistent across runs regardless of initial order.
    
    Args:
        lst: List to hash
        
    Returns:
        Stable hash string
    """
    from exoarmur.replay.canonical_utils import stable_hash
    sorted_lst = deterministic_sort_list(lst)
    return stable_hash(canonical_json(sorted_lst))
