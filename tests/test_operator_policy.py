"""
Tests for the operator-approved policy mechanism.

Covers loading a versioned policy file verified against an
operator-pinned SHA-256 digest, rule matching, the
OperatorPolicyDecisionPoint, and end-to-end ProxyPipeline behavior with
the real SafetyGate. The pinned digest is always supplied explicitly in
tests — never auto-generated-and-trusted by the loader.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone

import pytest

from exoarmur.policy.operator_policy import (
    OperatorPolicy,
    OperatorPolicyDecisionPoint,
    PolicyRule,
    PolicyUnavailableError,
    PolicyVerificationError,
    load_operator_policy,
)
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import (
    ProxyPipeline,
    AuditEmitter,
    TrustedSafetyContext,
)
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.execution_dispatch import (
    ExecutionDispatch,
    DispatchStatus,
)
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyVerdict
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
from exoarmur.execution_boundary_v2.approvals.in_memory_store import InMemoryApprovalStore
from exoarmur.safety.safety_gate import SafetyGate
from exoarmur.safety.execution_gate import ExecutionGate
from exoarmur.collective_confidence.aggregator import CollectiveState
from spec.contracts.models_v1 import LocalDecisionV1


POLICY_DOC = {
    "version": 1,
    "rules": [
        {
            "tenant_id": "tenant-1",
            "principal_id": "agent-001",
            "operations": ["tool.read", "ingest.execute"],
            "action_classes": {
                "tool.read": "A0_observe",
                "ingest.execute": "A1_soft_containment",
            },
            "required_approval": "none",
        },
        {
            "tenant_id": "tenant-1",
            "principal_id": "agent-002",
            "operations": ["tool.write"],
            "action_classes": {"tool.write": "A2_hard_containment"},
            "required_approval": "quorum",
        },
    ],
}


def _write_policy(tmp_path, doc=None):
    doc = POLICY_DOC if doc is None else doc
    path = tmp_path / "operator_policy.json"
    raw = json.dumps(doc).encode("utf-8")
    path.write_bytes(raw)
    return str(path), hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- loader --


def test_load_verified_policy_succeeds(tmp_path):
    path, digest = _write_policy(tmp_path)
    policy = load_operator_policy(path, digest)

    assert isinstance(policy, OperatorPolicy)
    assert policy.version == 1
    assert len(policy.rules) == 2
    assert policy.sha256 == digest


def test_missing_path_denies(tmp_path):
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy("", "0" * 64)
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(None, "0" * 64)


def test_missing_file_denies(tmp_path):
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(str(tmp_path / "nonexistent.json"), "0" * 64)


def test_missing_pinned_digest_denies(tmp_path):
    path, _digest = _write_policy(tmp_path)
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(path, None)
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(path, "")


def test_incorrect_pinned_digest_denies(tmp_path):
    path, _digest = _write_policy(tmp_path)
    with pytest.raises(PolicyVerificationError):
        load_operator_policy(path, "f" * 64)


def test_altered_policy_denies(tmp_path):
    """Digest computed over original content; altered file must fail."""
    path, digest = _write_policy(tmp_path)
    doc = json.loads(open(path).read())
    doc["rules"][0]["required_approval"] = "none"  # tamper attempt
    # rewrite with different content but keep original digest
    altered = dict(doc)
    altered["rules"] = [dict(doc["rules"][0], principal_id="agent-999")]
    with open(path, "w") as f:
        json.dump(altered, f)
    with pytest.raises(PolicyVerificationError):
        load_operator_policy(path, digest)


def test_invalid_json_denies(tmp_path):
    path = tmp_path / "bad.json"
    raw = b"{not json"
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(str(path), digest)


def test_unsupported_version_denies(tmp_path):
    path, digest = _write_policy(tmp_path, {"version": 2, "rules": []})
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(path, digest)


@pytest.mark.parametrize("rule_patch", [
    {"tenant_id": ""},
    {"principal_id": None},
    {"operations": []},
    {"action_classes": {"op": "A9_bogus"}},
    {"default_action_class": "A9_bogus"},
    {"required_approval": "maybe"},
    {"required_approval": None},
])
def test_invalid_rule_schema_denies(tmp_path, rule_patch):
    doc = {
        "version": 1,
        "rules": [dict({
            "tenant_id": "t",
            "principal_id": "p",
            "operations": ["op"],
            "action_classes": {"op": "A0_observe"},
            "required_approval": "none",
        }, **rule_patch)],
    }
    path, digest = _write_policy(tmp_path, doc)
    with pytest.raises(PolicyUnavailableError):
        load_operator_policy(path, digest)


# ------------------------------------------------------------- matching --


def _policy():
    path_doc = POLICY_DOC
    # build OperatorPolicy directly from validated rules
    return OperatorPolicy(
        version=1,
        rules=(
            PolicyRule(
                tenant_id="tenant-1",
                principal_id="agent-001",
                operations=("tool.read", "ingest.execute"),
                action_classes={"tool.read": "A0_observe", "ingest.execute": "A1_soft_containment"},
                default_action_class=None,
                required_approval="none",
            ),
            PolicyRule(
                tenant_id="tenant-1",
                principal_id="agent-002",
                operations=("tool.write",),
                action_classes={"tool.write": "A2_hard_containment"},
                default_action_class=None,
                required_approval="quorum",
            ),
        ),
        source_path="test",
        sha256="0" * 64,
    )


def test_matching_rule_exact():
    policy = _policy()
    rule = policy.matching_rule("tenant-1", "agent-001", "tool.read")
    assert rule is not None and rule.required_approval == "none"


def test_matching_rule_denies_unmatched():
    policy = _policy()
    assert policy.matching_rule("tenant-2", "agent-001", "tool.read") is None
    assert policy.matching_rule("tenant-1", "agent-999", "tool.read") is None
    assert policy.matching_rule("tenant-1", "agent-001", "tool.delete") is None
    assert policy.matching_rule("tenant-1", "agent-001", None) is None
    assert policy.matching_rule(None, "agent-001", "tool.read") is None
    assert policy.matching_rule("tenant-1", None, "tool.read") is None


def test_resolve_action_class_from_rule():
    policy = _policy()
    rule = policy.matching_rule("tenant-1", "agent-001", "ingest.execute")
    assert rule.resolve_action_class("ingest.execute") == "A1_soft_containment"
    assert rule.resolve_action_class("unmapped") is None


# ------------------------------------------------------------------ PDP --


def _intent(tenant_id="tenant-1", actor_id="agent-001", action_type="tool.read", safety_context=None):
    return ActionIntent(
        intent_id="intent-policy-1",
        actor_id=actor_id,
        actor_type="agent",
        action_type=action_type,
        target="tool_execution",
        parameters={},
        safety_context=safety_context or {},
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        cell_id="cell-1",
    )


def test_pdp_denies_when_policy_unavailable():
    pdp = OperatorPolicyDecisionPoint(None)
    decision = pdp.evaluate(_intent())
    assert decision.verdict == PolicyVerdict.DENY


def test_pdp_denies_unmatched_tenant_principal_operation():
    pdp = OperatorPolicyDecisionPoint(_policy())
    assert pdp.evaluate(_intent(tenant_id="tenant-2")).verdict == PolicyVerdict.DENY
    assert pdp.evaluate(_intent(actor_id="agent-999")).verdict == PolicyVerdict.DENY
    assert pdp.evaluate(_intent(action_type="tool.delete")).verdict == PolicyVerdict.DENY


def test_pdp_allows_matched_rule():
    pdp = OperatorPolicyDecisionPoint(_policy())
    decision = pdp.evaluate(_intent())
    assert decision.verdict == PolicyVerdict.ALLOW
    assert decision.approval_required is False


def test_pdp_requires_approval_for_quorum_rule():
    pdp = OperatorPolicyDecisionPoint(_policy())
    decision = pdp.evaluate(_intent(actor_id="agent-002", action_type="tool.write"))
    assert decision.verdict == PolicyVerdict.REQUIRE_APPROVAL
    assert decision.approval_required is True


def test_pdp_approval_status_and_bypass():
    store = InMemoryApprovalStore()
    pdp = OperatorPolicyDecisionPoint(_policy(), approval_store=store)
    intent = _intent(actor_id="agent-002", action_type="tool.write")

    assert pdp.approval_status(intent.intent_id) == "pending"
    assert pdp.evaluate_with_approval_bypass(intent).verdict == PolicyVerdict.REQUIRE_APPROVAL

    # Simulate an approved record
    from exoarmur.execution_boundary_v2.approvals.approval_models import (
        ApprovalDecision,
        ApprovalRecord,
    )
    record = ApprovalRecord(
        intent_id=intent.intent_id,
        decision=ApprovalDecision.APPROVE,
        decided_by="operator-1",
        decided_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    store.record(record)

    assert pdp.approval_status(intent.intent_id) == "approved"
    assert pdp.evaluate_with_approval_bypass(intent).verdict == PolicyVerdict.ALLOW


# ------------------------------------------------- pipeline integration --


class CountingExecutor:
    def __init__(self):
        self.calls = 0

    def name(self) -> str:
        return "counting-executor"

    def capabilities(self) -> dict:
        return {"executor_name": "counting-executor", "version": "0.0.1",
                "capabilities": ["count"], "constraints": {}}

    def execute(self, intent: ActionIntent) -> ExecutorResult:
        self.calls += 1
        return ExecutorResult(success=True, output={"calls": self.calls})


def _local_decision(confidence=0.95):
    return LocalDecisionV1(
        schema_version="1.0.0",
        decision_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        tenant_id="tenant-1",
        cell_id="cell-1",
        subject={"subject_type": "agent", "subject_id": "agent-001"},
        classification="benign",
        severity="low",
        confidence=confidence,
        evidence_refs={},
        correlation_id="corr-1",
        trace_id="trace-1",
    )


def _trusted_context(action_classes=None, **overrides):
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
            action_classes if action_classes is not None
            else {"tool.read": "A0_observe", "ingest.execute": "A1_soft_containment"}
        ),
    )
    kwargs.update(overrides)
    return TrustedSafetyContext(**kwargs)


def _pipeline(policy, executor, trusted=None, gate=None):
    return ProxyPipeline(
        OperatorPolicyDecisionPoint(policy),
        SafetyGate(),
        executor,
        AuditEmitter(),
        execution_gate=gate,
        trusted_safety_context=trusted if trusted is not None else _trusted_context(),
    )


def test_approved_matching_policy_permits_execution():
    """Verified policy + matching rule + sufficient context -> one call."""
    executor = CountingExecutor()
    pipeline = _pipeline(_policy(), executor)

    result = pipeline.execute(_intent())

    assert executor.calls == 1
    assert getattr(result, "success", False) is True


def test_unmatched_policy_denies_before_executor():
    executor = CountingExecutor()
    pipeline = _pipeline(_policy(), executor)

    assert pipeline.execute(_intent(tenant_id="tenant-2")).error == "DENIED"
    assert pipeline.execute(_intent(actor_id="agent-999")).error == "DENIED"
    assert pipeline.execute(_intent(action_type="tool.delete")).error == "DENIED"
    assert executor.calls == 0


def test_unavailable_policy_denies_execution():
    executor = CountingExecutor()
    pipeline = _pipeline(None, executor)

    result = pipeline.execute(_intent())

    assert executor.calls == 0
    assert getattr(result, "error", None) == "DENIED"


def test_request_cannot_override_policy_or_class():
    """safety_context fields cannot substitute for policy-derived values."""
    executor = CountingExecutor()
    # Context maps tool.read -> A0 (allow); caller claims nothing extra.
    # An intent for an operation with no policy rule must deny even if the
    # caller supplies a permissive safety_context.
    pipeline = _pipeline(_policy(), executor)

    result = pipeline.execute(_intent(
        action_type="tool.delete",
        safety_context={"action_class": "A0_observe", "trust_score": 1.0},
    ))

    assert executor.calls == 0
    assert getattr(result, "error", None) == "DENIED"


def test_policy_approval_requirement_blocks_until_approved():
    executor = CountingExecutor()
    store = InMemoryApprovalStore()
    pdp = OperatorPolicyDecisionPoint(_policy(), approval_store=store)
    pipeline = ProxyPipeline(
        pdp, SafetyGate(), executor, AuditEmitter(),
        trusted_safety_context=_trusted_context(
            tenant_id="tenant-1", actor_id="agent-002",
            action_classes={"tool.write": "A2_hard_containment"},
            required_approval="quorum",
        ),
    )

    result = pipeline.execute(_intent(actor_id="agent-002", action_type="tool.write"))

    assert executor.calls == 0
    assert isinstance(result, ExecutionDispatch)
    assert result.status == DispatchStatus.APPROVAL_PENDING


class _MockKVStore:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.data = {}

    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Key {key} not found")

    async def put(self, key, value):
        self.data[key] = value.encode("utf-8") if isinstance(value, str) else value


class _MockJS:
    def __init__(self):
        self.stores = {}

    async def create_key_value(self, bucket, description=None):
        if bucket not in self.stores:
            self.stores[bucket] = _MockKVStore(bucket)
        return self.stores[bucket]


class _MockNATSClient:
    def __init__(self):
        self.js = _MockJS()

    async def publish(self, subject, data):
        pass


def _gate_with_tenant_switch(active=True):
    nats = _MockNATSClient()
    gate = ExecutionGate(nats_client=nats)
    asyncio.run(gate._ensure_kv_stores())
    asyncio.run(gate._global_kill_switch_kv.put("switch_all_execution", "inactive"))
    asyncio.run(
        gate._tenant_kill_switch_kv.put(
            "tenant-1_switch_all_execution", "active" if active else "inactive"
        )
    )
    return gate


@pytest.mark.usefixtures("kill_switch_test_mode")
def test_kill_switch_still_blocks_policy_allowed_intent():
    """An approved policy match cannot bypass the authoritative kill switch."""
    executor = CountingExecutor()
    pipeline = _pipeline(_policy(), executor, gate=_gate_with_tenant_switch(active=True))

    result, trace = pipeline.execute_with_trace(_intent())

    assert executor.calls == 0
    assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
    assert result.evidence["denial_reason"] == "tenant_kill_switch_active"


@pytest.mark.usefixtures("kill_switch_test_mode")
def test_kill_switch_inactive_allows_policy_permitted_intent():
    executor = CountingExecutor()
    pipeline = _pipeline(_policy(), executor, gate=_gate_with_tenant_switch(active=False))

    result = pipeline.execute(_intent())

    assert executor.calls == 1
    assert getattr(result, "success", False) is True
