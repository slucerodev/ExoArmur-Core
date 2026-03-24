"""Execution kernel audit emission tests."""

from types import SimpleNamespace

import pytest

from exoarmur.audit.audit_logger import AuditLogger
from exoarmur.execution.execution_kernel import ExecutionKernel
from exoarmur.spec.contracts.models_v1 import LocalDecisionV1


@pytest.mark.asyncio
async def test_execution_emits_audit_record(monkeypatch):
    """ExecutionKernel must emit an audit record when an intent is executed."""
    monkeypatch.setenv("EXOARMUR_FAIL_OPEN_KILL_SWITCH", "1")
    monkeypatch.delenv("EXOARMUR_TESTING_KILL_SWITCH", raising=False)

    audit_logger = AuditLogger()
    kernel = ExecutionKernel(audit_logger=audit_logger)

    decision = LocalDecisionV1(
        schema_version="1.0.0",
        decision_id="01J4NR5X9Z8GABCDEF12345690",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        subject={"subject_type": "host", "subject_id": "host-123"},
        classification="suspicious",
        severity="high",
        confidence=0.9,
        recommended_intents=[],
        evidence_refs={"event_ids": ["evt-1"], "belief_ids": [], "feature_hashes": []},
        correlation_id="corr-exec-audit-1",
        trace_id="trace-exec-audit-1",
    )

    safety_verdict = SimpleNamespace(verdict="allow", rationale="test")
    intent = kernel.create_execution_intent(
        local_decision=decision,
        safety_verdict=safety_verdict,
        idempotency_identifier="exec-idemp-1",
    )

    executed = await kernel.execute_intent(intent)
    assert executed is True

    records = audit_logger.get_audit_records(decision.correlation_id)
    assert any(
        r.event_kind == "execution_intent_executed" and r.payload_ref.get("intent_id") == intent.intent_id
        for r in records
    )
