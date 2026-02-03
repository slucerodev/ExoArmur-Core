"""Integration tests for Core ↔ DPO boundary."""

from datetime import datetime, timezone

from spec.contracts.models_v1 import AuditRecordV1


def test_core_can_emit_dpo_verifiable_evidence_bundle(tmp_path):
    """
    Integration invariant:
    ExoArmur-Core must be able to emit a deterministic evidence bundle
    that ExoArmur-DPO can ingest and verify WITHOUT modifying Core V1 contracts.
    """
    audit_record = AuditRecordV1(
        schema_version="1.0.0",
        audit_id="01J4NR5X9Z8GABCDEF12345678",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        idempotency_key="idemp-demo-1",
        recorded_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        event_kind="telemetry_ingested",
        payload_ref={"kind": "inline", "ref": {"event_id": "evt-1"}},
        hashes={"sha256": "deadbeef"},
        correlation_id="corr-demo-1",
        trace_id="trace-demo-1",
    )

    output_dir = tmp_path / "bundle"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Core-side DPO integration should exist; it does not yet.
    from exoarmur.integration.dpo import export_evidence_bundle  # noqa: F401

    # DPO verification path should accept the bundle output once exporter exists.
    from exoarmur_dpo.verify import verify_bundle  # noqa: F401

    result_path = export_evidence_bundle(audit_record, output_dir)
    assert result_path is not None
    assert result_path.exists()


def test_core_bundle_verification_round_trip(tmp_path):
    """Core bundle should verify as VALID once policy/bundle metadata is wired."""
    audit_record = AuditRecordV1(
        schema_version="1.0.0",
        audit_id="01J4NR5X9Z8GABCDEF12345679",
        tenant_id="tenant-demo",
        cell_id="cell-demo-01",
        idempotency_key="idemp-demo-2",
        recorded_at=datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        event_kind="telemetry_ingested",
        payload_ref={"kind": "inline", "ref": {"event_id": "evt-2"}},
        hashes={"sha256": "deadbeef"},
        correlation_id="corr-demo-2",
        trace_id="trace-demo-2",
    )

    output_dir = tmp_path / "bundle"
    output_dir.mkdir(parents=True, exist_ok=True)

    from exoarmur.integration.dpo import export_evidence_bundle
    from exoarmur_dpo.verify import verify_bundle

    result_path = export_evidence_bundle(audit_record, output_dir)
    assert result_path is not None
    assert result_path.exists()
    result = verify_bundle(output_dir, audit_record.audit_id)

    # Expect VALID once policy bundle and evidence inputs are populated.
    assert result["status"] == "VALID"
