# Minimal deterministic replay quickstart

import hashlib
import json
from pathlib import Path
import sys

try:  # Prefer installed package; fallback to local src for repo checkout runs
    from exoarmur import ReplayEngine
    from exoarmur.replay.event_envelope import CanonicalEvent
except ImportError:  # pragma: no cover - convenience for local example run
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root / "src"))
    from exoarmur import ReplayEngine  # type: ignore
    from exoarmur.replay.event_envelope import CanonicalEvent  # type: ignore


def build_minimal_event() -> CanonicalEvent:
    """Construct the smallest valid CanonicalEvent instance."""
    payload = {"kind": "inline", "ref": {"event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"}}
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CanonicalEvent(
        event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        event_type="belief_creation_started",
        actor="quickstart_runner",
        correlation_id="corr-1",
        payload=payload,
        payload_hash=payload_hash,
    )


def main() -> None:
    event = build_minimal_event()
    engine = ReplayEngine(audit_store={"corr-1": [event]})
    report = engine.replay_correlation("corr-1")

    result_value = getattr(report.result, "value", report.result)
    print("Replay result:", result_value)
    print("Failures:", report.failures or "none")
    print("Warnings:", report.warnings or "none")


if __name__ == "__main__":
    main()
