"""
Tests for ProxyPipeline integration with the real V1 SafetyGate.

Uses the real SimplePolicyDecisionPoint, ProxyPipeline, SafetyGate, and
AuditEmitter with a counting executor that has no external side effects.
Safety evaluation context is supplied via TrustedSafetyContext (operator
configuration), never via caller-controlled intent fields.
"""

from datetime import datetime, timezone

import pytest

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import (
    ProxyPipeline,
    AuditEmitter,
    TrustedSafetyContext,
)
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.execution_dispatch import ExecutionDispatch, DispatchStatus
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyVerdict
from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
from exoarmur.safety.safety_gate import SafetyGate
from exoarmur.collective_confidence.aggregator import CollectiveState
from spec.contracts.models_v1 import LocalDecisionV1


class CountingExecutor:
    """ExecutorPlugin test double that only counts invocations."""

    def __init__(self):
        self.calls = 0
        self.intents = []

    def name(self) -> str:
        return "counting-executor"

    def capabilities(self) -> dict:
        return {
            "executor_name": "counting-executor",
            "version": "0.0.1",
            "capabilities": ["count"],
            "constraints": {},
        }

    def execute(self, intent: ActionIntent) -> ExecutorResult:
        self.calls += 1
        self.intents.append(intent)
        return ExecutorResult(success=True, output={"calls": self.calls})


def _local_decision(classification="benign", confidence=0.95):
    return LocalDecisionV1(
        schema_version="1.0.0",
        decision_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        tenant_id="test-tenant",
        cell_id="test-cell",
        subject={"subject_type": "agent", "subject_id": "agent-001"},
        classification=classification,
        severity="low",
        confidence=confidence,
        evidence_refs={},
        correlation_id="corr-1",
        trace_id="trace-1",
    )


def _trusted_context(action_classes=None, **overrides):
    """Operator-supplied trusted context; wildcard maps every action_type to A1."""
    kwargs = dict(
        local_decision=_local_decision(),
        tenant_id="tenant-1",
        actor_id="agent-001",
        trust_score=0.9,
        collective_state=CollectiveState(
            aggregate_score=0.0, quorum_count=0, conflict_detected=False
        ),
        policy_verified=True,
        kill_switch_global=False,
        kill_switch_tenant=False,
        required_approval="none",
        degraded_mode=False,
        action_classes=(
            action_classes if action_classes is not None else {"*": "A1_soft_containment"}
        ),
    )
    kwargs.update(overrides)
    return TrustedSafetyContext(**kwargs)


def _intent(action_type="http_request", method="GET", target="https://api.example.com/health", safety_context=None):
    return ActionIntent(
        intent_id="intent-real-gate-1",
        actor_id="agent-001",
        actor_type="agent",
        action_type=action_type,
        target=target,
        parameters={"method": method},
        safety_context=safety_context or {},
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        tenant_id="tenant-1",
        cell_id="cell-1",
    )


def _pipeline(rules, executor, trusted=None):
    pdp = SimplePolicyDecisionPoint(rules)
    return ProxyPipeline(
        pdp,
        SafetyGate(),
        executor,
        AuditEmitter(),
        trusted_safety_context=trusted if trusted is not None else _trusted_context(),
    )


ALLOW_RULE = PolicyRule(
    rule_id="allow-read",
    description="Allow GET on api.example.com",
    allowed_domains=["api.example.com"],
    allowed_methods=["GET"],
    require_approval=False,
)


def test_supported_permitted_action_executes_once():
    """A1-class action allowed by policy and safety gate executes exactly once."""
    executor = CountingExecutor()
    pipeline = _pipeline([ALLOW_RULE], executor)

    result = pipeline.execute(_intent())

    assert executor.calls == 1
    assert getattr(result, "success", False) is True


def test_policy_denied_action_never_executes():
    """A policy DENY verdict must not reach the safety gate or executor."""
    executor = CountingExecutor()
    pipeline = _pipeline([ALLOW_RULE], executor)

    # POST does not match the GET-only rule -> no matching rule -> DENY
    result = pipeline.execute(_intent(method="POST"))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "DENIED"


def test_safety_gate_denial_never_executes():
    """A real SafetyGate non-allow verdict (A3 -> require_human) blocks execution."""
    executor = CountingExecutor()
    trusted = _trusted_context(action_classes={"irreversible_action": "A3_irreversible"})
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent(action_type="irreversible_action"))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result, "evidence", {}).get("safety_verdict") == "require_human"


def test_approval_required_action_stays_pending():
    """A REQUIRE_APPROVAL verdict returns a pending dispatch; executor never runs."""
    executor = CountingExecutor()
    approval_rule = PolicyRule(
        rule_id="needs-approval",
        description="Require approval for GET on api.example.com",
        allowed_domains=["api.example.com"],
        allowed_methods=["GET"],
        require_approval=True,
    )
    pipeline = _pipeline([approval_rule], executor)

    result = pipeline.execute(_intent())

    assert executor.calls == 0
    assert isinstance(result, ExecutionDispatch)
    assert result.status == DispatchStatus.APPROVAL_PENDING


def test_missing_trusted_context_fails_closed():
    """No TrustedSafetyContext -> explicit block, not fabricated permissive defaults."""
    executor = CountingExecutor()
    pdp = SimplePolicyDecisionPoint([ALLOW_RULE])
    pipeline = ProxyPipeline(pdp, SafetyGate(), executor, AuditEmitter())

    result = pipeline.execute(_intent())

    assert executor.calls == 0
    assert getattr(result, "success", True) is False
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"


def test_unmapped_action_type_fails_closed():
    """An action_type with no operator mapping is an explicit block."""
    executor = CountingExecutor()
    trusted = _trusted_context(action_classes={"known_action": "A1_soft_containment"})
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent(action_type="unknown_action"))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"


def test_caller_cannot_downgrade_mapped_action_class():
    """Caller-declared A0_observe cannot override the operator-mapped class."""
    executor = CountingExecutor()
    # Operator maps http_request -> A1; caller claims A0_observe in safety_context.
    # A1 with confidence 0.5 fails the gate's 0.80 threshold -> deny.
    trusted = _trusted_context(
        action_classes={"http_request": "A1_soft_containment"},
        local_decision=_local_decision(confidence=0.5),
    )
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent(safety_context={"action_class": "A0_observe"}))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result, "evidence", {}).get("safety_verdict") == "deny"


def test_caller_cannot_override_trusted_confidence_or_trust():
    """Caller-supplied trust/confidence in safety_context are ignored."""
    executor = CountingExecutor()
    # Trusted trust_score 0.4 is below the A2 quorum floor (<0.50 -> require_quorum,
    # but above the 0.35 human floor). Caller claims perfect trust/confidence;
    # the real gate must still escalate.
    trusted = _trusted_context(
        action_classes={"http_request": "A2_hard_containment"},
        trust_score=0.4,
        local_decision=_local_decision(confidence=0.99),
    )
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent(safety_context={"trust_score": 1.0, "confidence": 1.0}))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result, "evidence", {}).get("safety_verdict") == "require_quorum"


def test_insufficient_trusted_confidence_blocks():
    """Real gate denial from low trusted confidence produces no executor call."""
    executor = CountingExecutor()
    trusted = _trusted_context(local_decision=_local_decision(confidence=0.5))
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent())

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result, "evidence", {}).get("safety_verdict") == "deny"


def test_tenant_mismatch_cannot_use_trusted_context():
    """An intent for a different tenant is rejected before reaching the gate."""
    executor = CountingExecutor()
    pipeline = _pipeline([ALLOW_RULE], executor)  # ctx bound to tenant-1/agent-001

    result = pipeline.execute(_intent())
    # sanity: bound intent executes
    assert executor.calls == 1

    foreign = _intent()
    foreign.tenant_id = "tenant-EVIL"
    result2 = pipeline.execute(foreign)

    assert executor.calls == 1
    assert getattr(result2, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result2, "evidence", {}).get("safety_verdict") == "deny"


def test_actor_mismatch_cannot_use_trusted_context():
    """An intent from a different actor cannot borrow the bound trust."""
    executor = CountingExecutor()
    pipeline = _pipeline([ALLOW_RULE], executor)

    foreign = _intent()
    foreign.actor_id = "agent-EVIL"
    result = pipeline.execute(foreign)

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"


def test_unavailable_trust_blocks_explicitly():
    """trust_score=None (unconfigured) is an explicit block, not a default."""
    executor = CountingExecutor()
    trusted = _trusted_context(trust_score=None)
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    result = pipeline.execute(_intent())

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
    assert getattr(result, "evidence", {}).get("safety_verdict") == "deny"


def test_caller_cannot_supply_trust_via_request():
    """Request parameters cannot substitute for configured operator trust."""
    executor = CountingExecutor()
    trusted = _trusted_context(trust_score=None)
    pipeline = _pipeline([ALLOW_RULE], executor, trusted=trusted)

    # Caller tries to inject trust through intent fields
    result = pipeline.execute(_intent(safety_context={
        "trust_score": 1.0,
        "emitter_trust_score": 1.0,
        "confidence": 1.0,
        "action_class": "A0_observe",
    }))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "SAFETY_GATE_BLOCKED"
