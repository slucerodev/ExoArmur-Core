"""
Execution proof bundle model for deterministic replay verification.

This model provides a canonical, versioned representation of execution
artifacts that can be deterministically replayed and verified.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionProofBundle(BaseModel):
    """Canonical execution proof bundle for deterministic replay verification.
    
    Contains all execution artifacts needed to replay and verify an execution
    with full determinism and cryptographic integrity guarantees.
    """
    
    bundle_version: str = Field(default="v1", description="Bundle format version")
    intent: Dict[str, Any] = Field(description="Original intent (canonicalized)")
    policy_decision: Dict[str, Any] = Field(description="Policy decision (canonicalized)")
    approval_records: List[Dict[str, Any]] = Field(default_factory=list, description="Approval records (if any)")
    execution_trace: Dict[str, Any] = Field(description="Complete execution trace (canonicalized)")
    executor_result: Dict[str, Any] = Field(description="Executor result (canonicalized)")
    replay_hash: str = Field(description="SHA-256 hash of canonical bundle data")
    bundle_created_at: Optional[datetime] = Field(default=None, description="Bundle creation timestamp (optional for determinism)")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        str_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
