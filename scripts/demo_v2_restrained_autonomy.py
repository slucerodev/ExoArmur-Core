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
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

from models_v1 import TelemetryEventV1
from v2_restrained_autonomy import (
    RestrainedAutonomyPipeline, 
    RestrainedAutonomyConfig,
    MockActionExecutor
)
from feature_flags import FeatureFlagContext, get_feature_flags
from audit.audit_logger import AuditLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    config = RestrainedAutonomyConfig(
        enabled=True,
        require_approval_for_A3=True,
        deterministic_seed="demo-seed-12345"
    )
    
    pipeline = RestrainedAutonomyPipeline(config=config)
    audit_logger = pipeline.audit_logger
    
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
    
    outcome = await pipeline.process_event_to_action(
        event=event,
        operator_decision=operator_decision,
        operator_id=operator_id
    )
    
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
        approval_details = pipeline.approval_service.get_approval_details(outcome.approval_id)
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
        execution_record = pipeline.action_executor.get_execution_record(outcome.execution_id)
        if execution_record:
            print("⚙️  Execution Details:")
            print(f"   Action Type: {execution_record['action_type']}")
            print(f"   Endpoint ID: {execution_record['endpoint_id']}")
            print(f"   Status: {execution_record['status']}")
            print(f"   Mock: {execution_record['mock']}")
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
            "timestamp": outcome.timestamp.isoformat()
        }
    }


def replay_audit_stream(audit_stream_id: str):
    """Replay and display audit stream"""
    print("🔍 ExoArmur V2 Audit Stream Replay")
    print("=" * 50)
    print(f"📋 Audit Stream ID: {audit_stream_id}")
    print()
    
    # Initialize pipeline to access replay functionality
    config = RestrainedAutonomyConfig(
        enabled=True,
        deterministic_seed="demo-seed-12345"
    )
    pipeline = RestrainedAutonomyPipeline(config=config)
    
    # Replay the audit stream
    replay_result = pipeline.replay_audit_stream(audit_stream_id)
    
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
    if replay_result['final_outcome'] and replay_result['total_events'] > 0:
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
        print(f"💾 To replay this audit stream, run:")
        print(f"   python {__file__} --replay {audit_stream_id}")
        print()
    
    print("🎯 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
