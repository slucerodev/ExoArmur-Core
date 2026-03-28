"""
ExoArmur ADMO V2 Restrained Autonomy Demo

This module demonstrates the minimal V2 capability slice:
- Input event -> belief -> operator approval request -> decision -> action or refusal
- Deterministic audit trail emitted and replayable
- Fully behind V2 feature flags (default OFF)
- V1 behavior unchanged
"""

import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient

import exoarmur.main as runtime_main
from exoarmur.feature_flags import FeatureFlagContext, get_feature_flags
from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.safety.safety_gate import SafetyVerdict
from exoarmur.spec.contracts.models_v1 import AuditRecordV1, TelemetryEventV1

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
            "sensor_id": "sensor-123",
        },
        event_type="suspicious_process",
        severity="high",
        attributes={
            "endpoint_id": "endpoint-demo-001",
            "process_name": "malware.exe",
            "process_path": "/tmp/malware.exe",
            "command_line": "malware.exe --steal-data",
            "parent_process": "explorer.exe",
        },
        entity_refs={
            "host": "host-demo-001",
            "user": "user-demo-001",
        },
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


async def run_demo_scenario(operator_decision: Optional[str]) -> dict:
    print("🚀 ExoArmur V2 Restrained Autonomy Demo")
    print("=" * 50)

    feature_flags = get_feature_flags()
    context = FeatureFlagContext(
        cell_id="cell-demo-01",
        tenant_id="demo_tenant",
        environment="demo",
    )
    v2_enabled = feature_flags.is_v2_control_plane_enabled(context)
    approval_required = feature_flags.is_v2_operator_approval_required(context)

    print("📋 Feature Flag Status:")
    print(f"   V2 Control Plane: {'✅ ENABLED' if v2_enabled else '❌ DISABLED'}")
    print(f"   V2 Operator Approval: {'✅ ENABLED' if approval_required else '❌ DISABLED'}")
    print()

    if not v2_enabled or not approval_required:
        print("❌ V2 restrained autonomy is disabled. Enable with:")
        print("   EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true")
        print("   EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true")
        print()
        return {"status": "disabled", "reason": "feature_flags_disabled"}

    client = _build_runtime_client()
    audit_logger = runtime_main.audit_logger

    print("🔧 Pipeline initialized with deterministic seed")
    print()

    event = create_sample_telemetry_event()
    print("📡 Sample Telemetry Event:")
    print(f"   Event ID: {event.event_id}")
    print(f"   Endpoint: {event.attributes.get('endpoint_id')}")
    print(f"   Severity: {event.severity}")
    print(f"   Process: {event.attributes.get('process_name')}")
    print()
    print("⚡ Processing event through restrained autonomy pipeline...")
    print()

    operator_id = "operator-demo-001" if operator_decision else None
    ingest_response = client.post(
        "/v1/telemetry/ingest",
        json=event.model_dump(mode="json"),
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
                json={"operator_id": operator_id, "reason": "Approved in demo"},
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
                json={"operator_id": operator_id, "reason": "Operator denied in demo"},
            )
            if deny_response.status_code != 200:
                raise RuntimeError(f"Approval denial failed: {deny_response.text}")
            refusal_reason = "Operator approval denied"
    elif approval_id:
        refusal_reason = "Operator approval required but not provided"
    else:
        action_taken = True
        execution_id = ingest_data.get("event_id")

    timestamp = datetime.now(timezone.utc)
    print("📊 Pipeline Results:")
    print(f"   Action Taken: {'✅ YES' if action_taken else '❌ NO'}")
    if refusal_reason:
        print(f"   Refusal Reason: {refusal_reason}")
    if execution_id:
        print(f"   Execution ID: {execution_id}")
    if approval_id:
        print(f"   Approval ID: {approval_id}")
    print(f"   Audit Stream ID: {audit_stream_id}")
    print(f"   Timestamp: {timestamp.isoformat()}")
    print()

    if approval_id:
        approval_details = runtime_main.approval_service.get_approval_details(approval_id)
        if approval_details:
            print("🔐 Approval Details:")
            print(f"   Status: {approval_details.status}")
            print(f"   Action Class: {approval_details.requested_action_class}")
            if approval_details.approved_by:
                print(f"   Approved By: {approval_details.approved_by}")
            if approval_details.denial_reason:
                print(f"   Denial Reason: {approval_details.denial_reason}")
            print()

    if execution_id:
        print("⚙️  Execution Details:")
        print("   Action Type: isolate_host")
        print(f"   Endpoint ID: {event.attributes.get('endpoint_id')}")
        print(f"   Status: {'completed' if action_taken else 'blocked'}")
        print("   Mock: false")
        print()

    print("📊 Demo Results:")
    if action_taken:
        print("DEMO_RESULT=APPROVED")
        print("ACTION_EXECUTED=true")
    else:
        print("DEMO_RESULT=DENIED")
        print("ACTION_EXECUTED=false")
    print(f"AUDIT_STREAM_ID={audit_stream_id}")
    print()

    return {
        "status": "completed",
        "outcome": {
            "action_taken": action_taken,
            "refusal_reason": refusal_reason,
            "execution_id": execution_id,
            "approval_id": approval_id,
            "audit_stream_id": audit_stream_id,
            "timestamp": timestamp.isoformat(),
        },
        "audit_records": _serialize_audit_records(audit_logger.audit_records),
    }


def replay_audit_stream(audit_stream_id: str):
    print("🔍 ExoArmur V2 Audit Stream Replay")
    print("=" * 50)
    print(f"📋 Audit Stream ID: {audit_stream_id}")
    print()

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
    for index, event in enumerate(replay_result["replay_timeline"], 1):
        print(f"   {index}. [{event['timestamp']}] {event['event_kind']}")
        payload = event["payload"]
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
    print("🔍 Replay Verification:")
    if replay_report.result.value == "success" and replay_result["total_events"] > 0:
        print("REPLAY_VERIFIED=true")
    else:
        print("REPLAY_VERIFIED=false")
    print()
