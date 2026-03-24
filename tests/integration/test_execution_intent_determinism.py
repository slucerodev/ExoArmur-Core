"""Execution intent determinism tests."""

from types import SimpleNamespace

from exoarmur.execution.execution_kernel import ExecutionKernel
from exoarmur.spec.contracts.models_v1 import LocalDecisionV1


def _make_decision(decision_id: str, correlation_id: str) -> LocalDecisionV1:
    return LocalDecisionV1(
        schema_version="1.0.0",
        decision_id=decision_id,
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        subject={"subject_type": "host", "subject_id": "host-123"},
        classification="suspicious",
        severity="high",
        confidence=0.9,
        recommended_intents=[],
        evidence_refs={"event_ids": ["evt-1"], "belief_ids": [], "feature_hashes": []},
        correlation_id=correlation_id,
        trace_id=f"trace-{correlation_id}",
    )


def test_execution_intent_ids_and_policy_context_are_deterministic():
    """Execution intent IDs and policy context must be deterministic and non-placeholder."""
    kernel = ExecutionKernel()
    safety_verdict = SimpleNamespace(verdict="allow", rationale="test")

    decision_a1 = _make_decision("01J4NR5X9Z8GABCDEF12345691", "corr-intent-a")
    decision_a2 = _make_decision("01J4NR5X9Z8GABCDEF12345691", "corr-intent-a")
    decision_b = _make_decision("01J4NR5X9Z8GABCDEF12345692", "corr-intent-b")

    intent_a1 = kernel.create_execution_intent(decision_a1, safety_verdict, "idem-1")
    intent_a2 = kernel.create_execution_intent(decision_a2, safety_verdict, "idem-1")
    intent_b = kernel.create_execution_intent(decision_b, safety_verdict, "idem-1")

    assert intent_a1.intent_id == intent_a2.intent_id
    assert intent_a1.intent_id != intent_b.intent_id

    bundle_hash = intent_a1.policy_context.get("bundle_hash_sha256")
    rule_ids = intent_a1.policy_context.get("rule_ids", [])

    assert bundle_hash not in (None, "", "abc123...")
    assert rule_ids and "rule-1" not in rule_ids
