# Counterfactual Replay Quickstart Demo

from datetime import datetime, timezone
from pathlib import Path
import sys

try:  # Prefer installed package; fallback to local src for repo checkout runs
    from exoarmur import ReplayEngine
    from exoarmur.counterfactual import CounterfactualEngine, Intervention
except ImportError:  # pragma: no cover - convenience for local example run
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root / "src"))
    sys.path.append(str(repo_root))  # for spec.contracts.*
    from exoarmur import ReplayEngine
    from exoarmur.counterfactual import CounterfactualEngine, Intervention

from spec.contracts.models_v1 import AuditRecordV1


def create_audit_record() -> AuditRecordV1:
    """Create a sample audit record for the demo."""
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
                    "actor_id": "agent-001",  # This will be our intervention target
                    "action": "read_file",
                    "target": "/sensitive/data.txt"
                }
            }
        },
        hashes={"sha256": "abc123", "upstream_hashes": []},
        correlation_id="corr-1",
        trace_id="trace-1",
    )


def main() -> None:
    """Run the counterfactual demo."""
    print("=" * 60)
    print("EXOARMUR COUNTERFACTUAL REPLAY DEMO")
    print("=" * 60)
    print()
    
    # Step 1: Create audit record and replay engine
    print("STEP 1: Creating audit record and replay engine...")
    record = create_audit_record()
    replay_engine = ReplayEngine(audit_store={"corr-1": [record]})
    print("✓ Created audit record with actor_id='agent-001'")
    print()
    
    # Step 2: Create counterfactual engine
    print("STEP 2: Creating counterfactual engine...")
    cf_engine = CounterfactualEngine(replay_engine)
    print("✓ Counterfactual engine ready")
    print()
    
    # Step 3: Define intervention
    print("STEP 3: Defining counterfactual intervention...")
    intervention = Intervention(
        field_path="payload_ref.kind.ref.actor_id",
        original_value="agent-001",
        counterfactual_value="unauthorized-actor",
        rationale="What if the actor was unauthorized instead of agent-001?"
    )
    print(f"✓ Intervention defined:")
    print(f"  - Field: {intervention.field_path}")
    print(f"  - Original: {intervention.original_value}")
    print(f"  - Counterfactual: {intervention.counterfactual_value}")
    print(f"  - Rationale: {intervention.rationale}")
    print()
    
    # Step 4: Run counterfactual experiment
    print("STEP 4: Running counterfactual experiment...")
    try:
        report = cf_engine.run_counterfactual("corr-1", intervention)
        print("✓ Counterfactual experiment completed")
        print()
        
        # Step 5: Display results
        print("STEP 5: COUNTERFACTUAL RESULTS")
        print("=" * 60)
        print()
        
        print("ORIGINAL EXECUTION:")
        print(f"  Actor: agent-001")
        print(f"  Result: {report.original_summary}")
        print()
        
        print("COUNTERFACTUAL EXECUTION:")
        print(f"  Actor: unauthorized-actor")
        print(f"  Result: {report.counterfactual_summary}")
        print()
        
        print("INTERVENTION ANALYSIS:")
        print(f"  Field Modified: {report.intervention.field_path}")
        print(f"  Change: {report.intervention.original_value} → {report.intervention.counterfactual_value}")
        print(f"  Outcome Changed: {'YES' if report.outcome_changed else 'NO'}")
        print()
        
        print("VERDICT:")
        print(f"  {report.verdict}")
        print()
        
        # Human-readable explanation
        print("HUMAN READABLE SUMMARY:")
        if report.verdict == "SAME_OUTCOME":
            print("  The policy decision was the same even with an unauthorized actor.")
            print("  This suggests the current policy may not be checking actor authorization.")
        elif report.verdict == "DIFFERENT_OUTCOME":
            print("  The policy decision changed when the actor became unauthorized.")
            print("  This indicates the policy is properly checking actor authorization.")
        else:  # INCONCLUSIVE
            print("  Both executions failed, so we cannot determine the policy difference.")
        print()
        
        print("=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Counterfactual experiment failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
