# Minimal deterministic replay quickstart

from datetime import datetime, timezone
from pathlib import Path
import sys

try:  # Prefer installed package; fallback to local src for repo checkout runs
    from exoarmur import ReplayEngine
except ImportError:  # pragma: no cover - convenience for local example run
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root / "src"))
    sys.path.append(str(repo_root))  # for spec.contracts.*
    from exoarmur import ReplayEngine  # type: ignore

from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event
from exoarmur.replay.event_envelope import CanonicalEvent


def build_minimal_record() -> AuditRecordV1:
    """Construct the smallest valid AuditRecordV1 instance."""
    return AuditRecordV1(
        schema_version="1.0.0",
        audit_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Valid ULID format
        tenant_id="tenant-1",
        cell_id="cell-1",
        idempotency_key="idem-1",
        recorded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        event_kind="telemetry_ingested",
        payload_ref={
            "kind": {
                "ref": {
                    "event_id": "event-1",
                    "correlation_id": "corr-1",
                    "trace_id": "trace-1",
                }
            }
        },
        hashes={"sha256": "abc123", "upstream_hashes": []},
        correlation_id="corr-1",
        trace_id="trace-1",
    )


def main() -> None:
    record = build_minimal_record()
    canonical_event = CanonicalEvent(**to_canonical_event(record))
    engine = ReplayEngine(audit_store={"corr-1": [canonical_event]})
    report = engine.replay_correlation("corr-1")

    result_value = getattr(report.result, "value", report.result)
    print("Replay result:", result_value)
    print("Failures:", report.failures or "none")
    print("Warnings:", report.warnings or "none")


if __name__ == "__main__":
    main()
