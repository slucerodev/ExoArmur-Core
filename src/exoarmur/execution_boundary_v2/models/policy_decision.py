"""
PolicyDecision model for execution governance boundary.

Policy evaluation results and verdicts for intent authorization.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from exoarmur.ids import make_decision_id


class PolicyVerdict(Enum):
    """Policy verdict enumeration with precedence ordering.
    
    Precedence (highest to lowest):
    - DENY: Absolute rejection, overrides all other verdicts
    - REQUIRE_APPROVAL: Conditional approval, requires human intervention
    - DEFER: Temporary block, may be retried later
    - ALLOW: Unconditional approval
    """
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    DEFER = "defer"
    ALLOW = "allow"
    
    @classmethod
    def precedence_rank(cls, verdict: "PolicyVerdict") -> int:
        """Get precedence rank for verdict resolution (lower = higher precedence)."""
        precedence = {
            cls.DENY: 0,
            cls.REQUIRE_APPROVAL: 1,
            cls.DEFER: 2,
            cls.ALLOW: 3
        }
        return precedence.get(verdict, 0)  # Default to highest precedence (DENY)


class PolicyDecision(BaseModel):
    """Policy decision result for intent evaluation."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    decision_id: str = Field(description="Decision identifier (deterministic ULID)")
    verdict: PolicyVerdict = Field(description="Policy verdict")
    rationale: Optional[str] = Field(default=None, description="Decision rationale")
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Decision evidence")
    confidence: Optional[float] = Field(default=None, description="Decision confidence (0.0-1.0)")
    approval_required: bool = Field(default=False, description="Human approval required")
    policy_version: Optional[str] = Field(default=None, description="Policy version used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")
    
    @classmethod
    def create(cls, intent_id: str, verdict: PolicyVerdict, 
               rationale: Optional[str] = None,
               evidence: Optional[Dict[str, Any]] = None,
               confidence: Optional[float] = None,
               approval_required: bool = False,
               policy_version: Optional[str] = None,
               metadata: Optional[Dict[str, Any]] = None) -> "PolicyDecision":
        """Create PolicyDecision with deterministic ID."""
        if evidence is None:
            evidence = {}
        if metadata is None:
            metadata = {}
        
        decision_id = make_decision_id(intent_id, policy_version)
        
        return cls(
            decision_id=decision_id,
            verdict=verdict,
            rationale=rationale,
            evidence=evidence,
            confidence=confidence,
            approval_required=approval_required,
            policy_version=policy_version,
            metadata=metadata
        )
