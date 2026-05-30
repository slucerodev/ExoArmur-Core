"""
Canonical JSON hashing utilities for external effect evidence.

Core provides deterministic hashing without understanding provider specifics.
"""

import hashlib
import json
from typing import Dict, Any, List


class CanonicalizationError(Exception):
    """Error during canonicalization."""
    pass


def canonical_json_bytes(data: Any) -> bytes:
    """
    Convert data to canonical JSON bytes.
    
    Args:
        data: Data to canonicalize (must be JSON-serializable)
    
    Returns:
        Canonical JSON bytes
    
    Raises:
        CanonicalizationError: If data cannot be canonicalized
    """
    try:
        canonical = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False
        )
        return canonical.encode("utf-8")
    except (TypeError, ValueError) as e:
        raise CanonicalizationError(f"Failed to canonicalize data: {e}")


def canonical_hash(data: Any) -> str:
    """
    Compute SHA-256 hash of canonical JSON.
    
    Args:
        data: Data to hash (must be JSON-serializable)
    
    Returns:
        SHA-256 hash as hexadecimal string
    
    Raises:
        CanonicalizationError: If data cannot be canonicalized
    """
    try:
        canonical_bytes = canonical_json_bytes(data)
        return hashlib.sha256(canonical_bytes).hexdigest()
    except CanonicalizationError:
        raise


def validate_canonical_json_compatible(data: Any) -> bool:
    """
    Validate that data is compatible with canonical JSON.
    
    Args:
        data: Data to validate
    
    Returns:
        True if data is compatible, False otherwise
    """
    try:
        canonical_json_bytes(data)
        return True
    except CanonicalizationError:
        return False


def normalize_for_hashing(data: Dict[str, Any], fields_to_remove: List[str]) -> Dict[str, Any]:
    """
    Normalize data for hashing by removing non-deterministic fields.
    
    Args:
        data: Raw data to normalize
        fields_to_remove: List of field names to remove (e.g., timestamps, IDs)
    
    Returns:
        Normalized data suitable for hashing
    
    Note:
        This function removes specified fields but does NOT reorder
        semantically meaningful content (e.g., message arrays).
    """
    normalized = data.copy()
    for field in fields_to_remove:
        normalized.pop(field, None)
    return normalized
