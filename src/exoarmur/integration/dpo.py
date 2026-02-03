"""Core ↔ DPO integration utilities (offline-only)."""

from __future__ import annotations

from pathlib import Path
import hashlib

from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import canonical_json, stable_hash


def _audit_record_hash(audit_record: AuditRecordV1) -> str:
    """Compute deterministic hash for an audit record payload."""
    payload = audit_record.model_dump(mode="json")
    return stable_hash(canonical_json(payload))


def _write_policy_bundle(policy_archive: Path, audit_record: AuditRecordV1, bundle_kind: str) -> str:
    """Write a deterministic policy bundle file and return its digest."""
    payload = {
        "bundle_kind": bundle_kind,
        "audit_id": audit_record.audit_id,
        "correlation_id": audit_record.correlation_id,
        "trace_id": audit_record.trace_id,
        "recorded_at": audit_record.recorded_at,
    }
    bundle_bytes = canonical_json(payload).encode("utf-8")
    digest = hashlib.sha256(bundle_bytes).hexdigest()
    bundle_path = policy_archive / f"{digest}.bundle"

    if bundle_path.exists():
        existing = bundle_path.read_bytes()
        if existing != bundle_bytes:
            raise ValueError(f"Policy bundle digest collision for {bundle_kind}")
    else:
        bundle_path.write_bytes(bundle_bytes)

    return digest


def export_evidence_bundle(audit_record: AuditRecordV1, output_dir: Path) -> Path:
    """
    Export a deterministic DPO evidence bundle rooted at output_dir.

    Produces a DPOEvidence JSON stored via DPO's content-addressed store and
    an append-only index entry linking audit_record_id → dpo_id.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from exoarmur_dpo.canonical import CANON_VERSION
        from exoarmur_dpo.models import DPOEvidence, DPOInputs, DPOOutputs
        from exoarmur_dpo.storage import compute_dpo_id, store_dpo_file, append_index_entry
    except ModuleNotFoundError as exc:  # pragma: no cover - surfaced in integration tests
        raise ModuleNotFoundError(
            "exoarmur_dpo is required for export_evidence_bundle; install ExoArmur-DPO"
        ) from exc

    audit_hash = _audit_record_hash(audit_record)

    policy_archive = output_dir / "policy_archive"
    policy_archive.mkdir(parents=True, exist_ok=True)
    policy_version = _write_policy_bundle(policy_archive, audit_record, "policy")
    arbitration_version = _write_policy_bundle(policy_archive, audit_record, "arbitration")
    safety_gate_version = _write_policy_bundle(policy_archive, audit_record, "safety")

    dpo = DPOEvidence(
        schema_version="1.0.0",
        canonicalization_version=CANON_VERSION,
        dpo_id="",  # populated after hash computation
        correlation_id=audit_record.correlation_id,
        trace_id=audit_record.trace_id,
        tenant_id=audit_record.tenant_id,
        cell_id=audit_record.cell_id,
        decision_recorded_at=audit_record.recorded_at,
        policy_version=policy_version,
        arbitration_version=arbitration_version,
        safety_gate_version=safety_gate_version,
        rule_trigger_ids=[],
        feature_flags_snapshot={},
        inputs=DPOInputs(
            telemetry_hash=None,
            signal_facts_hash=None,
            local_decision_hash=None,
            belief_hash=None,
            collective_state_hash=None,
            safety_verdict_hash=None,
        ),
        outputs=DPOOutputs(
            execution_intent_hash=None,
            audit_record_hash=audit_hash,
        ),
        provenance={
            "source": "exoarmur-core",
            "audit_id": audit_record.audit_id,
        },
    )

    dpo_id = compute_dpo_id(dpo)
    dpo = dpo.model_copy(update={"dpo_id": dpo_id})

    store_path = store_dpo_file(dpo, output_dir)
    append_index_entry(audit_record.audit_id, dpo_id, output_dir)

    return store_path
