"""
ExecutionDispatch model for execution governance boundary.

Execution dispatch tracking and status management.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from exoarmur.clock import utc_now
from exoarmur.ids import make_dispatch_id


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
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    dispatch_id: str = Field(description="Dispatch identifier (deterministic ULID)")
    intent_id: str = Field(description="Associated intent identifier")
    status: DispatchStatus = Field(description="Current dispatch status")
    created_at: datetime = Field(description="Dispatch creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional dispatch details")

    @classmethod
    def create(cls, intent_id: str, status: DispatchStatus = DispatchStatus.SUBMITTED,
               details: Optional[Dict[str, Any]] = None) -> "ExecutionDispatch":
        """Create ExecutionDispatch with deterministic ID and timestamps."""
        dispatch_id = make_dispatch_id(intent_id)
        now = utc_now()
        
        return cls(
            dispatch_id=dispatch_id,
            intent_id=intent_id,
            status=status,
            created_at=now,
            updated_at=now,
            details=details
        )
    
    def update_status(self, new_status: DispatchStatus, details: Optional[Dict[str, Any]] = None) -> None:
        """Update dispatch status and timestamp."""
        self.status = new_status
        self.updated_at = utc_now()
        if details is not None:
            self.details = details
