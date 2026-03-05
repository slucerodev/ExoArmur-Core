"""
Canonicalization utilities for execution proof bundles.

Provides deterministic JSON serialization and hash computation
for execution artifacts to enable verifiable replay.
"""

import hashlib
import json
from typing import Any, Dict, List, Union

from pydantic import BaseModel

from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision
from ..models.execution_trace import ExecutionTrace


def to_canonical_dict(obj: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Pydantic model or dict to canonical dictionary representation.
    
    Ensures deterministic JSON serialization with:
    - Sorted keys for reproducible output
    - Consistent data types
    - No NaN or None values in final output
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True, mode='json')
    elif isinstance(obj, dict):
        # Remove None values and sort keys for determinism
        cleaned = {k: v for k, v in obj.items() if v is not None}
        return dict(sorted(cleaned.items()))
    else:
        raise TypeError(f"Cannot canonicalize object of type {type(obj)}")


def canonical_json(data: Dict[str, Any]) -> bytes:
    """Generate canonical JSON bytes with deterministic serialization.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        UTF-8 encoded JSON bytes with sorted keys and consistent formatting
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode('utf-8')


def compute_replay_hash(data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of canonical data for replay verification.
    
    Args:
        data: Dictionary to hash
        
    Returns:
        Hexadecimal SHA-256 hash
    """
    canonical_bytes = canonical_json(data)
    return hashlib.sha256(canonical_bytes).hexdigest()


def bundle_inputs_hash(intent: ActionIntent, 
                   policy_decision: PolicyDecision,
                   approval_records: List[Dict[str, Any]],
                   execution_trace: ExecutionTrace,
                   executor_result: Dict[str, Any]) -> str:
    """Compute deterministic hash of all bundle inputs.
    
    Args:
        intent: Original action intent
        policy_decision: Policy decision result
        approval_records: List of approval records
        execution_trace: Complete execution trace
        executor_result: Executor output
        
    Returns:
        SHA-256 hash of canonicalized inputs
    """
    bundle_data = {
        "bundle_version": "v1",
        "intent": to_canonical_dict(intent),
        "policy_decision": to_canonical_dict(policy_decision),
        "approval_records": [to_canonical_dict(record) for record in approval_records],
        "execution_trace": to_canonical_dict(execution_trace),
        "executor_result": to_canonical_dict(executor_result)
    }
    
    return compute_replay_hash(bundle_data)
