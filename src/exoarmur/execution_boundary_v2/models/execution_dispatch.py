"""
ExecutionDispatch model for execution governance boundary.

Execution dispatch tracking and status management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DispatchStatus(Enum):
    """Execution dispatch status enumeration."""
    SUBMITTED = "submitted"
    EVALUATING = "evaluating"
    BLOCKED = "blocked"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    EXECUTED = "executed"
    FAILED = "failed"


class ExecutionDispatch(BaseModel):
    """Execution dispatch tracking record."""
    
    intent_id: str = Field(description="Associated intent identifier")
    status: DispatchStatus = Field(description="Current dispatch status")
    created_at: datetime = Field(description="Dispatch creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional dispatch details")
    
    class Config:
        extra = "forbid"
        str_strip_whitespace = True
