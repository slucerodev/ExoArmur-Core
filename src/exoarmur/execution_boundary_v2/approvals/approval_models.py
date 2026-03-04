"""
Approval models for execution governance boundary.

Defines approval decision types and record structures.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    """Approval decision types."""
    APPROVE = "APPROVE"
    DENY = "DENY"


class ApprovalRecord(BaseModel):
    """Record of an approval decision for an intent."""
    
    intent_id: str = Field(description="Intent identifier requiring approval")
    decision: ApprovalDecision = Field(description="Approval decision")
    decided_by: str = Field(description="Identifier of the approver")
    decided_at: datetime = Field(description="When the decision was made")
    reason: Optional[str] = Field(default=None, description="Reason for the decision")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        str_strip_whitespace = True