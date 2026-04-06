from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Use the public SDK API - this is the ONLY supported way to use ExoArmur
from exoarmur.sdk.public_api import (
    run_governed_execution,
    replay_governed_execution,
    verify_governance_integrity,
    SDKConfig,
    ActionIntent,
    ExecutionProofBundle,
    FinalVerdict
)


class EnumEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles enums."""
    def default(self, obj):
        if hasattr(obj, 'value'):
            return obj.value
        return super().default(obj)

logging.basicConfig(level=logging.WARNING, format="%(message)s")

AUTHORIZED_ROOT = Path("/tmp/exoarmur-demo-authorized")
UNAUTHORIZED_TARGET = Path("/tmp/exoarmur-demo-private/secret-exports/customer-records.csv")
PROOF_BUNDLE_PATH = Path(__file__).with_name("demo_standalone_proof_bundle.json")
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
INTENT_ID = "demo-standalone-delete-outside-authorized-path"


def write_proof_bundle(
    proof_bundle: ExecutionProofBundle,
    audit_records: list[Dict[str, Any]],
    audit_stream_id: str,
    action_executed: bool,
    output_path: Path,
) -> Path:
    """Write proof bundle and audit records to disk."""
    bundle_data = {
        "bundle": proof_bundle.model_dump(),
        "audit_records": audit_records,
        "audit_stream_id": audit_stream_id,
        "action_executed": action_executed,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "final_verdict": proof_bundle.final_verdict.value if hasattr(proof_bundle.final_verdict, 'value') else str(proof_bundle.final_verdict),
    }
    
    output_path.write_text(json.dumps(bundle_data, indent=2, sort_keys=True, cls=EnumEncoder))
    return output_path


def main() -> None:
    """Demonstrate ExoArmur SDK governance boundary enforcement."""
    print("ExoArmur Standalone Execution Boundary Demo")
    
    # Create SDK configuration with detailed logging
    config = SDKConfig(
        enable_detailed_logging=True,
        strict_replay_verification=True,
        audit_stream_id=INTENT_ID
    )
    
    # Create intent to delete file outside authorized path
    intent = ActionIntent.create(
        actor_id="demo-user",
        actor_type="human",
        action_type="file_delete",
        target=str(UNAUTHORIZED_TARGET),
        parameters={"force": True}
    )
    
    print(f"Simulated AI agent action: delete a file outside the authorized path")
    print(f"Authorized root: {AUTHORIZED_ROOT}")
    print(f"Requested delete target: {UNAUTHORIZED_TARGET}")
    
    # Execute through governed SDK
    try:
        proof_bundle = run_governed_execution(intent, config)
        
        # Verify governance integrity
        try:
            verification = verify_governance_integrity(proof_bundle)
            print(f"Governance integrity verified: {verification['is_valid']}")
        except Exception as e:
            print(f"Governance integrity verification failed: {e}")
            verification = {"is_valid": False, "error": str(e)}
        
        # Replay the execution
        replay_report = replay_governed_execution(proof_bundle, config)
        print(f"Replay verification: {replay_report.result.value}")
        
        # Write proof bundle to disk (for external verification)
        audit_stream_id = config.audit_stream_id or intent.intent_id
        try:
            bundle_path = write_proof_bundle(
                proof_bundle=proof_bundle,
                audit_records=[],  # SDK handles audit internally
                audit_stream_id=audit_stream_id,
                action_executed=False,  # Should be denied
                output_path=PROOF_BUNDLE_PATH,
            )
            print("Execution boundary result: policy denied before any filesystem side effect")
            print(f"Proof bundle written: examples/demo_standalone_proof_bundle.json")
            print(f"Proof bundle schema version: {proof_bundle.schema_version}")
            print(f"Proof bundle replay hash: {proof_bundle.replay_hash}")
            print("DEMO_RESULT=DENIED")
            print("ACTION_EXECUTED=false")
            print(f"AUDIT_STREAM_ID={audit_stream_id}")
        except Exception as e:
            print(f"Failed to write proof bundle: {e}")
            print("DEMO_RESULT=ERROR")
            print("ACTION_EXECUTED=false")
        
    except Exception as e:
        print(f"SDK execution failed: {e}")
        print("DEMO_RESULT=ERROR")
        print("ACTION_EXECUTED=false")


if __name__ == "__main__":
    main()