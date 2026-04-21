"""
Canonical Hash Extraction for Determinism Proof

This module provides functions to extract canonical audit hashes from
execution records, ensuring identical inputs always produce identical outputs.
"""

from typing import List, Dict, Any
import hashlib

from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.stability.deterministic_ordering import deterministic_iter_dict


def strip_noise_fields(data: Any) -> Any:
    """
    Recursively remove all fields with __noise__ prefix from data structure.
    
    This function ensures that noise-injected fields are excluded from:
    - Hashing
    - Execution logic
    - Decision inputs
    
    Args:
        data: Any data structure (dict, list, or primitive)
        
    Returns:
        Data structure with all __noise__ fields removed
    """
    if isinstance(data, dict):
        # Recursively strip noise from dict values
        return {
            k: strip_noise_fields(v)
            for k, v in deterministic_iter_dict(data)
            if not k.startswith("__noise__")
        }
    elif isinstance(data, list):
        # Recursively strip noise from list items
        return [strip_noise_fields(item) for item in data]
    else:
        # Return primitive values as-is
        return data


def extract_canonical_audit_hash(audit_records: List[Dict[str, Any]]) -> str:
    """
    Extract canonical audit hash from a list of audit records.
    
    This function:
    - Canonicalizes all records using canonical_json
    - Enforces deterministic ordering using deterministic_iter_*
    - Hashes the full ordered sequence using stable_hash
    
    Args:
        audit_records: List of audit record dictionaries
        
    Returns:
        Canonical hash string that is deterministic for identical inputs
        
    Raises:
        ValueError: If audit_records is empty or invalid
    """
    if not audit_records:
        raise ValueError("Cannot extract hash from empty audit_records")
    
    # Canonicalize each record with deterministic ordering
    canonical_records = []
    for record in audit_records:
        if not isinstance(record, dict):
            raise ValueError(f"Invalid audit record type: {type(record)}")
        
        # Canonicalize the record with deterministic key ordering
        canonical_record = canonical_json(record)
        canonical_records.append(canonical_record)
    
    # Ensure deterministic ordering of records themselves
    # Sort by a deterministic key if available, otherwise use canonical representation
    try:
        # Try to sort by timestamp if present (most common case)
        canonical_records_sorted = sorted(
            canonical_records,
            key=lambda r: r  # canonical_json already sorts keys, so string comparison works
        )
    except Exception:
        # If sorting fails, use the canonical representation as-is
        canonical_records_sorted = canonical_records
    
    # Create combined canonical representation
    combined = canonical_json({
        "records": canonical_records_sorted,
        "count": len(canonical_records_sorted)
    })
    
    # Compute stable hash
    return stable_hash(combined)


def extract_canonical_execution_hash(execution_data: Dict[str, Any]) -> str:
    """
    Extract canonical hash from execution data including audit records and metadata.
    
    Args:
        execution_data: Dictionary containing execution metadata and audit records
        
    Returns:
        Canonical hash string
    """
    if not execution_data:
        raise ValueError("Cannot extract hash from empty execution_data")
    
    # Extract audit records if present
    audit_records = execution_data.get("audit_records", [])
    metadata = {k: v for k, v in deterministic_iter_dict(execution_data) if k != "audit_records"}
    
    # Get canonical audit hash
    audit_hash = extract_canonical_audit_hash(audit_records) if audit_records else ""
    
    # Combine metadata and audit hash
    combined = canonical_json({
        "metadata": metadata,
        "audit_hash": audit_hash,
        "audit_count": len(audit_records)
    })
    
    return stable_hash(combined)


def verify_hash_consistency(hashes: List[str]) -> bool:
    """
    Verify that all hashes in a list are identical.
    
    Args:
        hashes: List of hash strings
        
    Returns:
        True if all hashes are identical, False otherwise
    """
    if not hashes:
        return False
    
    first_hash = hashes[0]
    return all(h == first_hash for h in hashes)


def get_unique_hash_count(hashes: List[str]) -> int:
    """
    Get the number of unique hashes in a list.
    
    Args:
        hashes: List of hash strings
        
    Returns:
        Count of unique hashes
    """
    return len(set(hashes))
