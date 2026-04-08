"""Deterministic replay regression tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from exoarmur.replay.canonical_utils import canonical_json, stable_hash, to_canonical_event
from exoarmur.replay.event_envelope import CanonicalEvent
from exoarmur.replay.replay_engine import ReplayEngine, ReplayResult
from exoarmur.spec.contracts.models_v1 import AuditRecordV1

CORRELATION_ID = "determinism-corr"


def _sample_records() -> list[AuditRecordV1]:
    base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return [
        AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345680",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=base_time,
            event_kind="telemetry_ingested",
            payload_ref={
                "kind": {
                    "ref": {
                        "event_id": "event-1",
                        "correlation_id": CORRELATION_ID,
                        "trace_id": "trace-1",
                        "tenant_id": "tenant-1",
                        "cell_id": "cell-1",
                    }
                }
            },
            hashes={"sha256": "hash1", "upstream_hashes": []},
            correlation_id=CORRELATION_ID,
            trace_id="trace-1",
        ),
        AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345681",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=base_time + timedelta(seconds=1),
            event_kind="safety_gate_evaluated",
            payload_ref={"kind": {"ref": {"verdict": "require_human", "rationale": "A3 action"}}},
            hashes={"sha256": "hash2", "upstream_hashes": []},
            correlation_id=CORRELATION_ID,
            trace_id="trace-1",
        ),
        AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345682",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=base_time + timedelta(seconds=2),
            event_kind="approval_requested",
            payload_ref={"kind": {"ref": {"approval_id": "approval-123"}}},
            hashes={"sha256": "hash3", "upstream_hashes": []},
            correlation_id=CORRELATION_ID,
            trace_id="trace-1",
        ),
    ]


def _run_replay(records: list[AuditRecordV1]):
    canonical = [CanonicalEvent(**to_canonical_event(r)) for r in records]
    engine = ReplayEngine({CORRELATION_ID: canonical})
    return engine.replay_correlation(CORRELATION_ID)


def _fingerprint(report) -> str:
    return stable_hash(canonical_json(report.to_dict()))


def test_identical_input_produces_identical_replay_output():
    first_report = _run_replay(_sample_records())
    second_report = _run_replay(_sample_records())

    assert first_report.to_dict() == second_report.to_dict()
    assert _fingerprint(first_report) == _fingerprint(second_report)


def test_replay_ordering_is_consistent_for_equivalent_data():
    forward_report = _run_replay(_sample_records())
    reverse_report = _run_replay(list(reversed(_sample_records())))

    assert forward_report.result == reverse_report.result == ReplayResult.SUCCESS
    assert forward_report.to_dict() == reverse_report.to_dict()
    assert _fingerprint(forward_report) == _fingerprint(reverse_report)
    assert forward_report.processed_events == reverse_report.processed_events == 3


def test_replay_report_hash_is_stable_across_runs():
    first_hash = _fingerprint(_run_replay(_sample_records()))
    second_hash = _fingerprint(_run_replay(_sample_records()))

    assert first_hash == second_hash
