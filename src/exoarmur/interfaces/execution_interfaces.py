"""Dependency-free execution interface contracts."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ExecutionRequestLike(Protocol):
    module_id: Any
    execution_context: Any
    action_data: Dict[str, Any]
    approval_id: str | None
    correlation_id: str | None


@runtime_checkable
class ExecutionResultLike(Protocol):
    success: bool
    result_data: Dict[str, Any]
    execution_id: str
    audit_trail_id: str
    error: str | None
