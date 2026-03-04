"""
PolicyDecisionPoint interface for execution governance boundary.

Interface for policy evaluation and approval status tracking.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol

from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision


class ApprovalStatus(Enum):
    """Approval status enumeration."""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class PolicyDecisionPoint(Protocol):
    """Interface for policy decision evaluation."""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """Evaluate an intent against policy rules.
        
        Args:
            intent: The action intent to evaluate
            
        Returns:
            Policy decision with verdict and rationale
        """
        ...
    
    def approval_status(self, intent_id: str) -> ApprovalStatus:
        """Check approval status for a pending decision.
        
        Args:
            intent_id: Intent identifier
            
        Returns:
            Current approval status
        """
        ...
