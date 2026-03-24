"""Deterministic ID derivation tests for core pipeline."""

from datetime import datetime, timezone

from exoarmur.analysis.facts_deriver import FactsDeriver
from exoarmur.beliefs.belief_generator import BeliefGenerator
from exoarmur.decision.local_decider import LocalDecider
from exoarmur.spec.contracts.models_v1 import TelemetryEventV1


def _make_event(event_id: str, correlation_id: str) -> TelemetryEventV1:
    return TelemetryEventV1(
        schema_version="1.0.0",
        event_id=event_id,
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        observed_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        received_at=datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        source={"kind": "edr", "name": "crowdstrike"},
        event_type="process_start",
        severity="high",
        attributes={"process_name": "evil.exe", "pid": 1337},
        entity_refs={"subject_type": "host", "subject_id": "host-123"},
        correlation_id=correlation_id,
        trace_id=f"trace-{correlation_id}",
    )


def test_ids_derive_from_inputs_and_are_stable():
    """Different inputs must produce different IDs while same input stays stable."""
    facts_deriver = FactsDeriver()
    decider = LocalDecider()
    belief_generator = BeliefGenerator()

    event_a = _make_event("01J4NR5X9Z8GABCDEF12345670", "corr-a")
    event_b = _make_event("01J4NR5X9Z8GABCDEF12345671", "corr-b")

    facts_a1 = facts_deriver.derive_facts(event_a)
    facts_a2 = facts_deriver.derive_facts(event_a)
    facts_b = facts_deriver.derive_facts(event_b)

    assert facts_a1.facts_id == facts_a2.facts_id
    assert facts_a1.facts_id != facts_b.facts_id

    decision_a1 = decider.decide(facts_a1)
    decision_a2 = decider.decide(facts_a2)
    decision_b = decider.decide(facts_b)

    assert decision_a1.decision_id == decision_a2.decision_id
    assert decision_a1.decision_id != decision_b.decision_id

    belief_a1 = belief_generator.generate_belief(decision_a1)
    belief_a2 = belief_generator.generate_belief(decision_a2)
    belief_b = belief_generator.generate_belief(decision_b)

    assert belief_a1.belief_id == belief_a2.belief_id
    assert belief_a1.belief_id != belief_b.belief_id
