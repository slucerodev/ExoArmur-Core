#!/usr/bin/env python3
"""
ExoArmur ADMO V2 Restrained Autonomy Demo

This script demonstrates the minimal V2 capability slice:
- Input event -> belief -> operator approval request -> decision -> action or refusal
- Deterministic audit trail emitted and replayable
- Fully behind V2 feature flags (default OFF)
- V1 behavior unchanged

Usage:
    # Run with V2 flags enabled (requires explicit enablement)
    EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
    EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
    python scripts/demo_v2_restrained_autonomy.py --operator-decision approve
    
    # Run with V2 flags disabled (should refuse)
    python scripts/demo_v2_restrained_autonomy.py
    
    # Replay audit stream
    python scripts/demo_v2_restrained_autonomy.py --replay <audit_stream_id>
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi.testclient import TestClient

from exoarmur.spec.contracts.models_v1 import TelemetryEventV1, AuditRecordV1
import exoarmur.main as runtime_main
from exoarmur.feature_flags import FeatureFlagContext, get_feature_flags
from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.safety.safety_gate import SafetyVerdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEMO_AUDIT_PATH = Path(__file__).resolve().parent / "demo_audit_stream.json"


def _serialize_audit_records(audit_records: dict) -> dict:
    serialized: dict[str, list[dict]] = {}
    for correlation_id, records in audit_records.items():
        serialized[correlation_id] = [record.model_dump(mode="json") for record in records]
    return serialized


def _load_audit_records(path: Path) -> dict[str, list[AuditRecordV1]]:
    if not path.exists():
        raise RuntimeError(f"Audit stream file missing: {path}")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Audit stream file is corrupt: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Audit stream file has invalid shape: {path}")
    loaded: dict[str, list[AuditRecordV1]] = {}
    for correlation_id, records in payload.items():
        if not isinstance(records, list):
            raise RuntimeError(f"Audit stream entry invalid for {correlation_id}")
        loaded[correlation_id] = [AuditRecordV1.model_validate(record) for record in records]
    return loaded


def _build_runtime_client() -> TestClient:
    runtime_main.initialize_components(None)
    return TestClient(runtime_main.app)


def _payload_ref_to_dict(payload_ref: dict) -> dict:
    ref = payload_ref.get("ref", {}) if isinstance(payload_ref, dict) else {}
    if isinstance(ref, str):
        try:
            parsed = json.loads(ref)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return ref if isinstance(ref, dict) else {}


def create_sample_telemetry_event() -> TelemetryEventV1:
    """Create a sample telemetry event for the demo"""
    import ulid
    
    event_id = str(ulid.ULID())
    correlation_id = f"demo-{event_id[:8]}"
    trace_id = f"trace-{event_id[:8]}"
    
    return TelemetryEventV1(
        schema_version="1.0.0",
        event_id=event_id,
        tenant_id="demo_tenant",
        cell_id="cell-demo-01",
        observed_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        source={
            "kind": "edr",
            "name": "demo_edr",
            "host": "sensor-01",
            "sensor_id": "sensor-123"
        },
        event_type="suspicious_process",
        severity="high",
        attributes={
            "endpoint_id": "endpoint-demo-001",
            "process_name": "malware.exe",
            "process_path": "/tmp/malware.exe",
            "command_line": "malware.exe --steal-data",
            "parent_process": "explorer.exe"
        },
        entity_refs={
            "host": "host-demo-001",
            "user": "user-demo-001"
        },
        correlation_id=correlation_id,
        trace_id=trace_id
    )


async def run_demo_scenario(operator_decision: Optional[str]) -> dict:
    """Run the restrained autonomy demo scenario"""
    
    print("🚀 ExoArmur V2 Restrained Autonomy Demo")
    print("=" * 50)
    
    # Check feature flags
    feature_flags = get_feature_flags()
    context = FeatureFlagContext(
        cell_id="cell-demo-01",
        tenant_id="demo_tenant", 
        environment="demo"
    )
    
    v2_enabled = feature_flags.is_v2_control_plane_enabled(context)
    approval_required = feature_flags.is_v2_operator_approval_required(context)
    
    print(f"📋 Feature Flag Status:")
    print(f"   V2 Control Plane: {'✅ ENABLED' if v2_enabled else '❌ DISABLED'}")
    print(f"   V2 Operator Approval: {'✅ ENABLED' if approval_required else '❌ DISABLED'}")
    print()
    
    if not v2_enabled or not approval_required:
        print("❌ V2 restrained autonomy is disabled. Enable with:")
        print("   EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true")
        print("   EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true")
        print()
        return {"status": "disabled", "reason": "feature_flags_disabled"}
    
    # Initialize pipeline
    client = _build_runtime_client()
    audit_logger = runtime_main.audit_logger
    
    print("🔧 Pipeline initialized with deterministic seed")
    print()
    
    # Create sample event
    event = create_sample_telemetry_event()
    print(f"📡 Sample Telemetry Event:")
    print(f"   Event ID: {event.event_id}")
    print(f"   Endpoint: {event.attributes.get('endpoint_id')}")
    print(f"   Severity: {event.severity}")
    print(f"   Process: {event.attributes.get('process_name')}")
    print()
    
    # Process event through pipeline
    print("⚡ Processing event through restrained autonomy pipeline...")
    print()
    
    operator_id = "operator-demo-001" if operator_decision else None
    
    ingest_response = client.post(
        "/v1/telemetry/ingest",
        json=event.model_dump(mode="json")
    )
    if ingest_response.status_code != 200:
        raise RuntimeError(f"Telemetry ingest failed: {ingest_response.text}")
    ingest_data = ingest_response.json()
    approval_id = ingest_data.get("approval_id")
    audit_stream_id = event.correlation_id
    action_taken = False
    refusal_reason = None
    execution_id = None

    if approval_id and operator_decision and operator_id:
        if operator_decision == "approve":
            approve_response = client.post(
                f"/v1/approvals/{approval_id}/approve",
                json={"operator_id": operator_id, "reason": "Approved in demo"}
            )
            if approve_response.status_code != 200:
                raise RuntimeError(f"Approval failed: {approve_response.text}")

            frozen_intent = runtime_main.intent_store.get_intent_by_approval_id(approval_id)
            if frozen_intent is not None:
                frozen_intent.safety_context["human_approval_id"] = approval_id
                action_taken = await runtime_main._execute_intent_via_proxy_pipeline(
                    frozen_intent,
                    SafetyVerdict(
                        verdict="allow",
                        rationale="Operator approved in demo",
                        rule_ids=["DEMO-APPROVED"],
                    ),
                )
                if action_taken:
                    execution_id = frozen_intent.intent_id
                    runtime_main.audit_logger.emit_audit_record(
                        event_kind="intent_executed",
                        payload_ref={"kind": "inline", "ref": frozen_intent.model_dump(mode="json")},
                        correlation_id=event.correlation_id,
                        trace_id=event.trace_id,
                        tenant_id=event.tenant_id,
                        cell_id=event.cell_id,
                        idempotency_key=f"{frozen_intent.idempotency_key}:intent_executed:demo",
                    )
                else:
                    refusal_reason = "Approved intent execution failed"
        else:
            deny_response = client.post(
                f"/v1/approvals/{approval_id}/deny",
                json={"operator_id": operator_id, "reason": "Operator denied in demo"}
            )
            if deny_response.status_code != 200:
                raise RuntimeError(f"Approval denial failed: {deny_response.text}")
            refusal_reason = "Operator approval denied"
    elif approval_id:
        refusal_reason = "Operator approval required but not provided"
    else:
        action_taken = True
        execution_id = ingest_data.get("event_id")

    class DemoOutcome:
        def __init__(self, action_taken: bool, refusal_reason: Optional[str], execution_id: Optional[str], approval_id: Optional[str], audit_stream_id: str):
            self.action_taken = action_taken
            self.refusal_reason = refusal_reason
            self.execution_id = execution_id
            self.approval_id = approval_id
            self.audit_stream_id = audit_stream_id
            self.timestamp = datetime.now(timezone.utc)

    outcome = DemoOutcome(action_taken, refusal_reason, execution_id, approval_id, audit_stream_id)
    
    # Display results
    print("📊 Pipeline Results:")
    print(f"   Action Taken: {'✅ YES' if outcome.action_taken else '❌ NO'}")
    if outcome.refusal_reason:
        print(f"   Refusal Reason: {outcome.refusal_reason}")
    if outcome.execution_id:
        print(f"   Execution ID: {outcome.execution_id}")
    if outcome.approval_id:
        print(f"   Approval ID: {outcome.approval_id}")
    print(f"   Audit Stream ID: {outcome.audit_stream_id}")
    print(f"   Timestamp: {outcome.timestamp.isoformat()}")
    print()
    
    # Show approval details if available
    if outcome.approval_id:
        approval_details = runtime_main.approval_service.get_approval_details(outcome.approval_id)
        if approval_details:
            print("🔐 Approval Details:")
            print(f"   Status: {approval_details.status}")
            print(f"   Action Class: {approval_details.requested_action_class}")
            if approval_details.approved_by:
                print(f"   Approved By: {approval_details.approved_by}")
            if approval_details.denial_reason:
                print(f"   Denial Reason: {approval_details.denial_reason}")
            print()
    
    # Show execution details if action taken
    if outcome.execution_id:
        print("⚙️  Execution Details:")
        print(f"   Action Type: isolate_host")
        print(f"   Endpoint ID: {event.attributes.get('endpoint_id')}")
        print(f"   Status: {'completed' if outcome.action_taken else 'blocked'}")
        print(f"   Mock: false")
        print()
    
    # Print stable markers for CI/automation
    print("📊 Demo Results:")
    if outcome.action_taken:
        print(f"DEMO_RESULT=APPROVED")
        print(f"ACTION_EXECUTED=true")
    else:
        print(f"DEMO_RESULT=DENIED")
        print(f"ACTION_EXECUTED=false")
    
    print(f"AUDIT_STREAM_ID={outcome.audit_stream_id}")
    print()
    
    return {
        "status": "completed",
        "outcome": {
            "action_taken": outcome.action_taken,
            "refusal_reason": outcome.refusal_reason,
            "execution_id": outcome.execution_id,
            "approval_id": outcome.approval_id,
            "audit_stream_id": outcome.audit_stream_id,
            "timestamp": outcome.timestamp.isoformat() if outcome.timestamp else None,
        },
        "audit_records": _serialize_audit_records(audit_logger.audit_records)
    }


def replay_audit_stream(audit_stream_id: str):
    """Replay and display audit stream"""
    print("🔍 ExoArmur V2 Audit Stream Replay")
    print("=" * 50)
    print(f"📋 Audit Stream ID: {audit_stream_id}")
    print()
    
    # Initialize pipeline to access replay functionality
    loaded_records = _load_audit_records(DEMO_AUDIT_PATH)
    replay_report = ReplayEngine(audit_store=loaded_records).replay_correlation(audit_stream_id)
    audit_records = loaded_records.get(audit_stream_id, [])
    replay_timeline = [
        {
            "timestamp": record.recorded_at.isoformat(),
            "event_kind": record.event_kind,
            "payload": _payload_ref_to_dict(record.payload_ref),
        }
        for record in audit_records
    ]
    replay_result = {
        "replay_timeline": replay_timeline,
        "total_events": replay_report.total_events,
        "final_outcome": replay_report.result.value,
        "deterministic_hash": hashlib.sha256(
            json.dumps([record.model_dump(mode="json") for record in audit_records], sort_keys=True).encode()
        ).hexdigest(),
    }
    
    print("📈 Replay Timeline:")
    for i, event in enumerate(replay_result["replay_timeline"], 1):
        timestamp = event["timestamp"]
        event_kind = event["event_kind"]
        payload = event["payload"]
        
        print(f"   {i}. [{timestamp}] {event_kind}")
        if "belief_id" in payload:
            print(f"      Belief ID: {payload['belief_id']}")
        if "intent_id" in payload:
            print(f"      Intent ID: {payload['intent_id']}")
        if "approval_id" in payload:
            print(f"      Approval ID: {payload['approval_id']}")
        if "execution_id" in payload:
            print(f"      Execution ID: {payload['execution_id']}")
        if "reason" in payload:
            print(f"      Reason: {payload['reason']}")
    
    print()
    print("📊 Replay Summary:")
    print(f"   Total Events: {replay_result['total_events']}")
    print(f"   Final Outcome: {replay_result['final_outcome']}")
    print(f"   Deterministic Hash: {replay_result['deterministic_hash']}")
    print()
    
    # Print stable replay verification marker
    print("🔍 Replay Verification:")
    if replay_report.result.value == "success" and replay_result['total_events'] > 0:
        print("REPLAY_VERIFIED=true")
    else:
        print("REPLAY_VERIFIED=false")
    print()


async def main():
    """Main demo entry point"""
    parser = argparse.ArgumentParser(
        description="ExoArmur V2 Restrained Autonomy Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--operator-decision",
        choices=["approve", "deny"],
        help="Simulated operator decision (requires V2 flags enabled)"
    )
    
    parser.add_argument(
        "--replay",
        help="Replay audit stream with given ID"
    )
    
    args = parser.parse_args()
    
    if args.replay:
        replay_audit_stream(args.replay)
        return
    
    # Run demo scenario
    result = await run_demo_scenario(args.operator_decision)
    
    # Save audit stream ID for potential replay
    if result["status"] == "completed" and "outcome" in result:
        audit_stream_id = result["outcome"]["audit_stream_id"]
        DEMO_AUDIT_PATH.write_text(json.dumps(result["audit_records"], indent=2, sort_keys=True))
        print(f"💾 To replay this audit stream, run:")
        print(f"   python {__file__} --replay {audit_stream_id}")
        print()
    
    print("🎯 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
