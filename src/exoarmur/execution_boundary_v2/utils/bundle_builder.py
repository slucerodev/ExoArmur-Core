"""
Execution proof bundle builder for deterministic replay verification.

Builds verifiable bundles from execution artifacts with canonical
serialization and cryptographic hash computation.
"""

from typing import Any, Dict, List, Optional

from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision
from ..models.execution_trace import ExecutionTrace
from ..models.execution_proof_bundle import ExecutionProofBundle
from ..utils.canonicalization import bundle_inputs_hash, to_canonical_dict


def build_execution_proof_bundle(
    intent: ActionIntent,
    policy_decision: Optional[PolicyDecision] = None,
    approval_records: Optional[List[Dict[str, Any]]] = None,
    execution_trace: Optional[ExecutionTrace] = None,
    executor_result: Optional[Dict[str, Any]] = None
) -> ExecutionProofBundle:
    """Build a deterministic execution proof bundle from execution artifacts.
    
    Args:
        intent: Original action intent
        policy_decision: Policy decision result (optional)
        approval_records: Approval records (optional)
        execution_trace: Complete execution trace (optional)
        executor_result: Executor output (optional)
        
    Returns:
        ExecutionProofBundle with all artifacts and replay hash
    """
    # Use empty defaults for optional fields
    canonical_policy_decision = to_canonical_dict(policy_decision) if policy_decision else {}
    canonical_approval_records = [to_canonical_dict(record) for record in approval_records] if approval_records else []
    canonical_execution_trace = to_canonical_dict(execution_trace) if execution_trace else {}
    canonical_executor_result = to_canonical_dict(executor_result) if executor_result else {}
    
    # Compute deterministic hash of all inputs
    replay_hash = bundle_inputs_hash(
        intent=intent,
        policy_decision=canonical_policy_decision,
        approval_records=canonical_approval_records,
        execution_trace=canonical_execution_trace,
        executor_result=canonical_executor_result
    )
    
    return ExecutionProofBundle(
        bundle_version="v1",
        intent=to_canonical_dict(intent),
        policy_decision=canonical_policy_decision,
        approval_records=canonical_approval_records,
        execution_trace=canonical_execution_trace,
        executor_result=canonical_executor_result,
        replay_hash=replay_hash
    )
