"""
Approval module initialization
"""

from .approval_gate import (
    ApprovalStatus,
    ActionType,
    ApprovalRequest,
    ApprovalDecision,
    ApprovalError,
    ApprovalGate,
    get_approval_gate,
    enforce_approval_gate,
    _approval_gate  # Export for testing
)

__all__ = [
    "ApprovalStatus",
    "ActionType",
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalError",
    "ApprovalGate",
    "get_approval_gate",
    "enforce_approval_gate",
    "_approval_gate"
]
