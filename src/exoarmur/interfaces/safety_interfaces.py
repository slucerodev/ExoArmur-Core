"""Dependency-free safety interface contracts."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ActionIntentLike(Protocol):
    intent_id: str
    actor_id: str
    actor_type: str
    action_type: str
    target: str
    parameters: Dict[str, Any]
    safety_context: Dict[str, Any]
    timestamp: Any
    tenant_id: str
    cell_id: str


@runtime_checkable
class PolicyDecisionLike(Protocol):
    verdict: Any
    rationale: str
    confidence: float
    approval_required: bool
    policy_version: str


@runtime_checkable
class ExecutorResultLike(Protocol):
    success: bool
    output: Dict[str, Any]
    evidence: Dict[str, Any]
