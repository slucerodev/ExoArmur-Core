"""
Canonical serialization and stable hashing utilities
Ensures deterministic representation for replay verification
"""

import json
import hashlib
import logging
from typing import Any, Dict, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def canonical_json(data: Union[Dict[str, Any], list, str, int, float, bool, None]) -> str:
    """
    Convert data to canonical JSON representation
    
    Rules:
    - Sort object keys alphabetically
    - Use compact separators (no whitespace)
    - Normalize numeric types
    - Normalize datetime to ISO format UTC
    - Ensure consistent floating point representation
    
    Args:
        data: Data to canonicalize
        
    Returns:
        Canonical JSON string
    """
    def _canonicalize(value):
        if isinstance(value, dict):
            # Sort keys and canonicalize values
            return {k: _canonicalize(v) for k, v in sorted(value.items())}
        elif isinstance(value, list):
            # Canonicalize list elements
            return [_canonicalize(item) for item in value]
        elif isinstance(value, datetime):
            # Normalize datetime to UTC ISO format
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat().replace('+00:00', 'Z')
        elif isinstance(value, float):
            # Ensure consistent float representation
            if value != value:  # NaN
                return "null"
            if value == float('inf'):
                return "null"
            if value == float('-inf'):
                return "null"
            # Round to avoid floating point precision issues
            return round(value, 12)
        elif isinstance(value, (str, int, bool)) or value is None:
            return value
        else:
            raise ValueError(f"Unsupported type for canonicalization: {type(value)}")
    
    try:
        canonical_data = _canonicalize(data)
        return json.dumps(canonical_data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to canonicalize data: {e}")
        raise ValueError(f"Canonicalization failed: {e}") from e


def stable_hash(data: str) -> str:
    """
    Generate stable SHA-256 hash of canonical data
    
    Args:
        data: Canonical string data to hash
        
    Returns:
        Hexadecimal SHA-256 hash
    """
    if not isinstance(data, str):
        raise ValueError(f"Data must be string, got {type(data)}")
    
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def verify_canonical_hash(original_data: Any, expected_hash: str) -> bool:
    """
    Verify that data canonicalizes to expected hash
    
    Args:
        original_data: Original data to verify
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches, False otherwise
    """
    try:
        canonical = canonical_json(original_data)
        computed_hash = stable_hash(canonical)
        return computed_hash == expected_hash
    except Exception as e:
        logger.error(f"Hash verification failed: {e}")
        return False


class CanonicalHashError(Exception):
    """Raised when canonicalization or hashing fails"""
    pass
