"""
Safety Module - Safety Gate and Arbitration

Evaluates SafetyGate verdict and applies arbitration precedence.
Phase 5: Added ExecutionGate for kill switch enforcement.
"""

from .safety_gate import SafetyGate
from .execution_gate import (
    ExecutionGate,
    ExecutionContext,
    GateResult,
    GateDecision,
    DenialReason,
    ExecutionActionType,
    get_execution_gate,
    enforce_execution_gate,
    _execution_gate  # Export for testing
)

__all__ = [
    'SafetyGate',
    'ExecutionGate',
    'ExecutionContext', 
    'GateResult',
    'GateDecision',
    'DenialReason',
    'ExecutionActionType',
    'get_execution_gate',
    'enforce_execution_gate',
    '_execution_gate'
]
