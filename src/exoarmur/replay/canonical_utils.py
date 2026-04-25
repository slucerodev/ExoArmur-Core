"""
Canonical serialization and stable hashing utilities
Ensures deterministic representation for replay verification
"""

import json
import hashlib
import logging
from typing import Any, Dict, Optional, Union
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
    def _canonicalize(value, visited=None):
        if visited is None:
            visited = set()
        
        # Track object identity to prevent infinite recursion
        value_id = id(value)
        if value_id in visited:
            return "[CIRCULAR_REFERENCE]"
        visited.add(value_id)
        
        try:
            if isinstance(value, dict):
                # Sort keys and canonicalize values
                return {k: _canonicalize(v, visited) for k, v in sorted(value.items())}
            elif isinstance(value, list):
                # Canonicalize list elements
                return [_canonicalize(item, visited) for item in value]
            elif isinstance(value, datetime):
                # Normalize datetime to UTC ISO format
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                else:
                    value = value.astimezone(timezone.utc)
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
            elif hasattr(value, 'value') and not isinstance(value, (str, bytes, int, float, bool)):
                # Handle enum objects (has .value attribute but is not a primitive)
                return _canonicalize(value.value, visited)
            elif hasattr(value, '__dict__'):
                # Handle objects with __dict__ (convert to dict and canonicalize)
                # Filter out non-serializable attributes (methods, functions, descriptors, etc.)
                obj_dict = {}
                for k, v in value.__dict__.items():
                    # Skip callable attributes (methods, functions)
                    if callable(v):
                        continue
                    # Skip descriptor types
                    if type(v).__name__ in ('getset_descriptor', 'member_descriptor', 'method_descriptor', 'wrapper_descriptor', 'builtin_function_or_method'):
                        continue
                    obj_dict[k] = v
                return _canonicalize(obj_dict, visited)
            elif type(value).__name__ == 'mappingproxy':
                # Handle mappingproxy (read-only dict proxy, used for class __dict__)
                return _canonicalize(dict(value), visited)
            elif type(value).__name__ in ('getset_descriptor', 'member_descriptor', 'method_descriptor', 'wrapper_descriptor'):
                # Skip Python descriptor types (not data)
                return f"[{type(value).__name__}]"
            elif isinstance(value, (str, int, bool)) or value is None:
                return value
            else:
                raise ValueError(f"Unsupported type for canonicalization: {type(value)}")
        finally:
            visited.remove(value_id)
    
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


def _extract_record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def to_canonical_event(audit_record: Any, sequence_number: Optional[int] = None) -> Dict[str, Any]:
    """Project an audit record into a canonical replay event.

    The projection intentionally excludes wall-clock metadata such as
    ``recorded_at`` so replay output stays byte-for-byte stable across runs.
    """

    payload = _extract_record_value(audit_record, "payload_ref", _extract_record_value(audit_record, "payload", {}))
    if payload is None:
        payload = {}

    if isinstance(payload, (dict, list)):
        canonical_payload = json.loads(canonical_json(payload))
    else:
        canonical_payload = payload

    event_id = _extract_record_value(audit_record, "audit_id", _extract_record_value(audit_record, "event_id", ""))
    event_type = _extract_record_value(audit_record, "event_kind", _extract_record_value(audit_record, "event_type", ""))
    actor = _extract_record_value(audit_record, "actor", "system") or "system"

    return {
        "event_id": event_id,
        "event_type": event_type,
        "actor": actor,
        "correlation_id": _extract_record_value(audit_record, "correlation_id", ""),
        "payload": canonical_payload,
        "payload_hash": stable_hash(canonical_json(canonical_payload)),
        "sequence_number": sequence_number,
        "parent_event_id": _extract_record_value(audit_record, "parent_event_id", None),
        "cell_id": _extract_record_value(audit_record, "cell_id", ""),
        "tenant_id": _extract_record_value(audit_record, "tenant_id", ""),
        "trace_id": _extract_record_value(audit_record, "trace_id", ""),
    }


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
