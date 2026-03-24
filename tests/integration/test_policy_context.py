"""Policy context integrity tests for belief generation."""

from datetime import datetime, timezone

from exoarmur.analysis.facts_deriver import FactsDeriver
from exoarmur.beliefs.belief_generator import BeliefGenerator
from exoarmur.decision.local_decider import LocalDecider
from exoarmur.spec.contracts.models_v1 import TelemetryEventV1


def test_belief_policy_context_is_real_and_not_placeholder():
    """Belief policy_context must be populated from real bundle metadata, not placeholders."""
    event = TelemetryEventV1(
        schema_version="1.0.0",
        event_id="01J4NR5X9Z8GABCDEF12345672",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        observed_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        received_at=datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        source={"kind": "edr", "name": "crowdstrike"},
        event_type="process_start",
        severity="high",
        attributes={"process_name": "evil.exe", "pid": 1337},
        entity_refs={"subject_type": "host", "subject_id": "host-123"},
        correlation_id="corr-policy-1",
        trace_id="trace-corr-policy-1",
    )

    facts = FactsDeriver().derive_facts(event)
    decision = LocalDecider().decide(facts)
    belief = BeliefGenerator().generate_belief(decision)

    bundle_hash = belief.policy_context.get("bundle_hash_sha256")
    rule_ids = belief.policy_context.get("rule_ids", [])

    assert bundle_hash not in (None, "", "demo-bundle-hash")
    assert rule_ids and "rule-demo-001" not in rule_ids
