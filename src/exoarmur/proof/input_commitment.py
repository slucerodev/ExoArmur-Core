"""
Input Commitment Module for Determinism Proof

This module provides functions for cryptographic binding of inputs to outputs
through canonical hashing, ensuring input reproducibility across runs.
"""

from typing import Dict, Any

from exoarmur.replay.canonical_utils import canonical_json
from exoarmur.replay.canonical_utils import stable_hash
from exoarmur.stability.deterministic_ordering import DeterminismViolationError


def compute_input_hash(payload: Dict[str, Any]) -> str:
    """
    Compute cryptographic hash of input payload for commitment.
    
    This function:
    - Canonicalizes the payload using canonical_json
    - Computes stable hash of the canonical representation
    
    Args:
        payload: Input payload dictionary representing scenario configuration
        
    Returns:
        Canonical hash string that is deterministic for identical inputs
        
    Raises:
        ValueError: If payload is empty or invalid
    """
    if not payload:
        raise ValueError("Cannot compute hash from empty payload")
    
    # Canonicalize the payload with deterministic key ordering
    canonical_payload = canonical_json(payload)
    
    # Compute stable hash
    return stable_hash(canonical_payload)


def validate_input_reproducibility(payload: Dict[str, Any], expected_hash: str) -> bool:
    """
    Validate that input payload produces expected hash.
    
    This function recomputes the input hash and asserts equality
    with the expected hash, validating input reproducibility.
    
    Args:
        payload: Input payload to validate
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches expected value
        
    Raises:
        DeterminismViolationError: If computed hash does not match expected hash
    """
    computed_hash = compute_input_hash(payload)
    
    if computed_hash != expected_hash:
        raise DeterminismViolationError(
            f"Input reproducibility violation: expected hash {expected_hash}, "
            f"but computed {computed_hash}"
        )
    
    return True


def verify_input_consistency(payloads: list[Dict[str, Any]]) -> bool:
    """
    Verify that all payloads produce identical input hashes.
    
    This is used to ensure that multiple runs receive identical inputs.
    
    Args:
        payloads: List of input payloads to verify
        
    Returns:
        True if all payloads produce identical hashes
        
    Raises:
        DeterminismViolationError: If any payload produces a different hash
    """
    if not payloads:
        raise ValueError("Cannot verify consistency of empty payload list")
    
    # Compute hash for first payload
    reference_hash = compute_input_hash(payloads[0])
    
    # Verify all other payloads produce the same hash
    for i, payload in enumerate(payloads[1:], start=1):
        computed_hash = compute_input_hash(payload)
        if computed_hash != reference_hash:
            raise DeterminismViolationError(
                f"Input inconsistency detected at payload {i}: "
                f"reference hash {reference_hash}, but computed {computed_hash}"
            )
    
    return True
