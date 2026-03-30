"""
Execution trace models for execution governance boundary.

Provides deterministic execution tracing and evidence collection.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class TraceStage(str, Enum):
    """Execution trace stage enumeration."""
    INTENT_RECEIVED = "intent_received"
    POLICY_EVALUATED = "policy_evaluated"
    APPROVAL_CHECKED = "approval_checked"
    SAFETY_EVALUATED = "safety_evaluated"
    EXECUTOR_DISPATCHED = "executor_dispatched"
    COMPLETED = "completed"


class TraceEvent(BaseModel):
    """Single event in execution trace."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stage: TraceStage = Field(description="Trace stage identifier")
    ok: bool = Field(description="Whether the stage succeeded")
    code: str = Field(description="Stage-specific status code")
    details: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific details")


class ExecutionTrace(BaseModel):
    """Complete execution trace for an intent."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intent_id: str = Field(description="Intent identifier being traced")
    trace_version: str = Field(default="v1", description="Trace format version")
    events: List[TraceEvent] = Field(description="Ordered list of trace events")
    final_status: str = Field(description="Final execution status (DENIED, APPROVAL_PENDING, SAFETY_BLOCKED, EXECUTED, FAILED)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Audit-friendly summary (no secrets)")
