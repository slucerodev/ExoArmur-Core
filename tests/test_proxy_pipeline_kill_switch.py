"""
Tests for ProxyPipeline kill-switch enforcement before executor dispatch.

Exercises the real ExecutionGate fail-closed logic against controlled
in-memory KV storage. The conftest FAIL_OPEN override is neutralized via
EXOARMUR_TESTING_KILL_SWITCH=1 so the durable read path is actually used.
"""

import asyncio
from datetime import datetime, timezone

import pytest

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter, TrustedSafetyContext
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.execution_dispatch import ExecutionDispatch, DispatchStatus
from exoarmur.execution_boundary_v2.models.execution_trace import TraceStage
from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
from exoarmur.execution_boundary_v2.approvals.approval_models import ApprovalDecision, ApprovalRecord
from exoarmur.execution_boundary_v2.approvals.in_memory_store import InMemoryApprovalStore
from exoarmur.safety.safety_gate import SafetyGate
from exoarmur.safety.execution_gate import ExecutionGate
from exoarmur.collective_confidence.aggregator import CollectiveState
from spec.contracts.models_v1 import LocalDecisionV1


class MockKVStore:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.data = {}

    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(f"Key {key} not found")

    async def put(self, key, value):
        self.data[key] = value.encode("utf-8") if isinstance(value, str) else value


class MockJS:
    def __init__(self):
        self.stores = {}

    async def create_key_value(self, bucket, description=None):
        if bucket not in self.stores:
            self.stores[bucket] = MockKVStore(bucket)
        return self.stores[bucket]


class MockNATSClient:
    def __init__(self):
        self.js = MockJS()
        self.published = []

    async def publish(self, subject, data):
        self.published.append({"subject": subject, "data": data})


class CountingExecutor:
    def __init__(self):
        self.calls = 0

    def name(self) -> str:
        return "counting-executor"

    def capabilities(self) -> dict:
        return {"executor_name": "counting-executor", "version": "0.0.1", "capabilities": ["count"], "constraints": {}}

    def execute(self, intent: ActionIntent) -> ExecutorResult:
        self.calls += 1
        return ExecutorResult(success=True, output={"calls": self.calls})


ALLOW_RULE = PolicyRule(
    rule_id="allow-read",
    description="Allow GET on api.example.com",
    allowed_domains=["api.example.com"],
    allowed_methods=["GET"],
    require_approval=False,
)

APPROVAL_RULE = PolicyRule(
    rule_id="needs-approval",
    description="Require approval for GET on api.example.com",
    allowed_domains=["api.example.com"],
    allowed_methods=["GET"],
    require_approval=True,
)


def _trusted_context(**overrides):
    """Operator-supplied trusted context; wildcard maps every action_type to A1."""
    decision = LocalDecisionV1(
        schema_version="1.0.0",
        decision_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        tenant_id="test-tenant",
        cell_id="test-cell",
        subject={"subject_type": "agent", "subject_id": "agent-001"},
        classification="benign",
        severity="low",
        confidence=0.95,
        evidence_refs={},
        correlation_id="corr-1",
        trace_id="trace-1",
    )
    kwargs = dict(
        local_decision=decision,
        tenant_id="tenant-1",
        actor_id="agent-001",
        trust_score=0.9,
        collective_state=CollectiveState(aggregate_score=0.0, quorum_count=0, conflict_detected=False),
        policy_verified=True,
        kill_switch_global=False,
        kill_switch_tenant=False,
        required_approval="none",
        degraded_mode=False,
        action_classes={"*": "A1_soft_containment"},
    )
    kwargs.update(overrides)
    return TrustedSafetyContext(**kwargs)


def _intent(intent_id="intent-ks-1", tenant_id="tenant-1"):
    return ActionIntent(
        intent_id=intent_id,
        actor_id="agent-001",
        actor_type="agent",
        action_type="http_request",
        target="https://api.example.com/health",
        parameters={"method": "GET"},
        safety_context={"action_class": "A1_soft_containment"},
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        cell_id="cell-1",
    )


def _make_gate(global_status="inactive", tenant_status="inactive", tenant_id="tenant-1", with_storage=True):
    """Build an ExecutionGate backed by controlled mock KV storage."""
    nats = MockNATSClient() if with_storage else None
    gate = ExecutionGate(nats_client=nats)
    asyncio.run(gate._ensure_kv_stores())
    if with_storage:
        asyncio.run(gate._global_kill_switch_kv.put("switch_all_execution", global_status))
        asyncio.run(gate._tenant_kill_switch_kv.put(f"{tenant_id}_switch_all_execution", tenant_status))
    return gate


def _pipeline(rules, executor, gate):
    return ProxyPipeline(
        SimplePolicyDecisionPoint(rules),
        SafetyGate(),
        executor,
        AuditEmitter(),
        execution_gate=gate,
        trusted_safety_context=_trusted_context(),
    )


@pytest.mark.usefixtures("kill_switch_test_mode")
class TestKillSwitchEnforcement:
    def test_global_switch_active_blocks_execution(self):
        executor = CountingExecutor()
        emitter = AuditEmitter()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, emitter,
            execution_gate=_make_gate(global_status="active"),
            trusted_safety_context=_trusted_context(),
        )

        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result.evidence["denial_reason"] == "global_kill_switch_active"
        assert trace.final_status == "KILL_SWITCH_BLOCKED"
        ks_events = [e for e in trace.events if e.stage == TraceStage.KILL_SWITCH_CHECKED]
        assert len(ks_events) == 1 and ks_events[0].ok is False
        assert ks_events[0].details["denial_reason"] == "global_kill_switch_active"
        assert any(r.event_kind == "kill_switch_block" for r in emitter.audit_records)

    def test_tenant_switch_active_blocks_execution(self):
        executor = CountingExecutor()
        pipeline = _pipeline([ALLOW_RULE], executor, _make_gate(global_status="inactive", tenant_status="active"))

        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result.evidence["denial_reason"] == "tenant_kill_switch_active"
        assert trace.final_status == "KILL_SWITCH_BLOCKED"

    def test_missing_tenant_context_blocks_execution(self):
        executor = CountingExecutor()
        pipeline = _pipeline([ALLOW_RULE], executor, _make_gate())
        pipeline.trusted_safety_context = _trusted_context(tenant_id="")

        result, trace = pipeline.execute_with_trace(_intent(tenant_id=""))

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result.evidence["denial_reason"] == "missing_tenant_context"

    def test_unavailable_switch_storage_blocks_execution(self):
        """No NATS-backed storage -> fail closed, not fail open."""
        executor = CountingExecutor()
        pipeline = _pipeline([ALLOW_RULE], executor, _make_gate(with_storage=False))

        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"

    def test_failed_state_read_blocks_execution(self):
        """A KV read error must surface as an explicit block."""
        class FailingKV(MockKVStore):
            async def get(self, key):
                raise RuntimeError("kv unavailable")

        class FailingJS(MockJS):
            async def create_key_value(self, bucket, description=None):
                return FailingKV(bucket)

        nats = MockNATSClient()
        nats.js = FailingJS()
        gate = ExecutionGate(nats_client=nats)
        executor = CountingExecutor()
        pipeline = _pipeline([ALLOW_RULE], executor, gate)

        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"

    def test_both_switches_inactive_executes_once(self):
        executor = CountingExecutor()
        emitter = AuditEmitter()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, emitter,
            execution_gate=_make_gate(),
            trusted_safety_context=_trusted_context(),
        )

        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 1
        assert getattr(result, "success", False) is True
        assert trace.final_status == "EXECUTED"
        ks_events = [e for e in trace.events if e.stage == TraceStage.KILL_SWITCH_CHECKED]
        assert len(ks_events) == 1 and ks_events[0].ok is True

    def test_switch_activated_after_approval_still_blocks(self):
        """Approval is not a kill-switch override: state is re-read at dispatch."""
        executor = CountingExecutor()
        approval_store = InMemoryApprovalStore()
        approval_store.record(ApprovalRecord(
            intent_id="intent-ks-approved",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-1",
            decided_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            reason="approved earlier",
        ))
        pdp = SimplePolicyDecisionPoint([APPROVAL_RULE], approval_store=approval_store)
        gate = _make_gate(global_status="inactive", tenant_status="inactive")
        pipeline = ProxyPipeline(pdp, SafetyGate(), executor, AuditEmitter(), execution_gate=gate, trusted_safety_context=_trusted_context())

        # Switch activated after the approval was granted
        asyncio.run(gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "active"))

        result, trace = pipeline.check_approval_and_execute(_intent(intent_id="intent-ks-approved"))

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result.evidence["denial_reason"] == "tenant_kill_switch_active"
        assert trace.final_status == "KILL_SWITCH_BLOCKED"

    def test_approved_execution_with_inactive_switches_executes(self):
        executor = CountingExecutor()
        approval_store = InMemoryApprovalStore()
        approval_store.record(ApprovalRecord(
            intent_id="intent-ks-approved-2",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-1",
            decided_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        pdp = SimplePolicyDecisionPoint([APPROVAL_RULE], approval_store=approval_store)
        pipeline = ProxyPipeline(
            pdp, SafetyGate(), executor, AuditEmitter(),
            execution_gate=_make_gate(),
            trusted_safety_context=_trusted_context(),
        )

        result, trace = pipeline.check_approval_and_execute(_intent(intent_id="intent-ks-approved-2"))

        assert executor.calls == 1
        assert getattr(result, "success", False) is True
        assert trace.final_status == "EXECUTED"


class LoopBoundKVStore(MockKVStore):
    """KV double bound to a specific event loop; rejects cross-loop access."""

    def __init__(self, bucket_name, owner_loop):
        super().__init__(bucket_name)
        self._owner_loop = owner_loop

    def _check_loop(self):
        if asyncio.get_running_loop() is not self._owner_loop:
            raise RuntimeError("cross-loop KV access")

    async def get(self, key):
        self._check_loop()
        return await super().get(key)

    async def put(self, key, value):
        self._check_loop()
        return await super().put(key, value)


class LoopBoundJS(MockJS):
    """Creates KV stores bound to the loop on which they are created."""

    async def create_key_value(self, bucket, description=None):
        loop = asyncio.get_running_loop()
        if bucket not in self.stores:
            self.stores[bucket] = LoopBoundKVStore(bucket, loop)
        return self.stores[bucket]


def _loop_bound_gate(global_status="inactive", tenant_status="inactive", tenant_id="tenant-1"):
    """Gate whose KV stores only work on the application event loop."""
    nats = MockNATSClient()
    nats.js = LoopBoundJS()
    return ExecutionGate(nats_client=nats)


@pytest.mark.usefixtures("kill_switch_test_mode")
class TestAsyncKillSwitchPath:
    """Async entry points must evaluate kill-switch state on the caller's loop."""

    async def test_async_allowed_execution_on_app_loop(self):
        executor = CountingExecutor()
        emitter = AuditEmitter()
        gate = _loop_bound_gate()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, emitter,
            execution_gate=gate,
            trusted_safety_context=_trusted_context(),
        )
        # Pre-create KV stores on this (application) loop and mark switches inactive
        await gate._ensure_kv_stores()
        await gate._global_kill_switch_kv.put("switch_all_execution", "inactive")
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "inactive")

        result, trace = await pipeline.execute_with_trace_async(_intent())

        assert executor.calls == 1
        assert getattr(result, "success", False) is True
        assert trace.final_status == "EXECUTED"

    async def test_async_global_switch_denial_on_app_loop(self):
        executor = CountingExecutor()
        gate = _loop_bound_gate()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, AuditEmitter(),
            execution_gate=gate,
            trusted_safety_context=_trusted_context(),
        )
        await gate._ensure_kv_stores()
        await gate._global_kill_switch_kv.put("switch_all_execution", "active")
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "inactive")

        result, trace = await pipeline.execute_with_trace_async(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result.evidence["denial_reason"] == "global_kill_switch_active"

    async def test_async_resumed_approval_rechecks_state(self):
        executor = CountingExecutor()
        approval_store = InMemoryApprovalStore()
        approval_store.record(ApprovalRecord(
            intent_id="intent-async-approved",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-1",
            decided_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        pdp = SimplePolicyDecisionPoint([APPROVAL_RULE], approval_store=approval_store)
        gate = _loop_bound_gate()
        pipeline = ProxyPipeline(pdp, SafetyGate(), executor, AuditEmitter(), execution_gate=gate, trusted_safety_context=_trusted_context())
        await gate._ensure_kv_stores()
        await gate._global_kill_switch_kv.put("switch_all_execution", "inactive")
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "inactive")

        # First resume: allowed
        result, _ = await pipeline.check_approval_and_execute_async(_intent(intent_id="intent-async-approved"))
        assert executor.calls == 1
        assert getattr(result, "success", False) is True

        # Activate tenant switch, then resume again: must re-read and block
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "active")
        result2, trace2 = await pipeline.check_approval_and_execute_async(_intent(intent_id="intent-async-approved"))

        assert executor.calls == 1  # unchanged
        assert getattr(result2, "error", None) == "KILL_SWITCH_BLOCKED"
        assert result2.evidence["denial_reason"] == "tenant_kill_switch_active"
        assert trace2.final_status == "KILL_SWITCH_BLOCKED"

    async def test_repeated_async_calls_create_no_worker_threads(self):
        import threading
        import exoarmur.execution_boundary_v2.pipeline.proxy_pipeline as pp

        executor = CountingExecutor()
        gate = _loop_bound_gate()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, AuditEmitter(),
            execution_gate=gate,
            trusted_safety_context=_trusted_context(),
        )
        await gate._ensure_kv_stores()
        await gate._global_kill_switch_kv.put("switch_all_execution", "inactive")
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "inactive")

        threads_before = threading.active_count()
        bridge_before = pp._bridge_loop
        for i in range(3):
            intent = _intent(intent_id=f"intent-async-{i}")
            result, _ = await pipeline.execute_with_trace_async(intent)
            assert getattr(result, "success", False) is True

        assert executor.calls == 3
        assert threading.active_count() == threads_before
        assert pp._bridge_loop is bridge_before  # bridge loop never started

    async def test_sync_bridge_with_loop_bound_storage_fails_closed(self):
        """Sync entry point inside a running loop cannot use loop-bound storage;
        the gate fails closed rather than bypassing the check."""
        executor = CountingExecutor()
        gate = _loop_bound_gate()
        pipeline = ProxyPipeline(
            SimplePolicyDecisionPoint([ALLOW_RULE]), SafetyGate(), executor, AuditEmitter(),
            execution_gate=gate,
            trusted_safety_context=_trusted_context(),
        )
        await gate._ensure_kv_stores()
        await gate._global_kill_switch_kv.put("switch_all_execution", "inactive")
        await gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "inactive")

        # Switches are inactive, but the sync bridge runs on a different loop
        # so the loop-bound KV raises; the gate must deny (fail closed).
        result, trace = pipeline.execute_with_trace(_intent())

        assert executor.calls == 0
        assert getattr(result, "error", None) == "KILL_SWITCH_BLOCKED"
