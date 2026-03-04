"""
PolicyDecision model for execution governance boundary.

Policy evaluation results and verdicts for intent authorization.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PolicyVerdict(Enum):
    """Policy verdict enumeration."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    DEFER = "defer"


class PolicyDecision(BaseModel):
    """Policy decision result for intent evaluation."""
    
    verdict: PolicyVerdict = Field(description="Policy verdict")
    rationale: Optional[str] = Field(default=None, description="Decision rationale")
    confidence: Optional[float] = Field(default=None, description="Decision confidence (0.0-1.0)")
    approval_required: bool = Field(default=False, description="Human approval required")
    policy_version: Optional[str] = Field(default=None, description="Policy version used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")
    
    class Config:
        extra = "forbid"
        str_strip_whitespace = True
