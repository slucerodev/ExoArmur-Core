#!/usr/bin/env python3
"""
Inject known scenario for reality testing
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from nats_client import ExoArmurNATSClient, NATSConfig
from audit.audit_logger import AuditLogger


async def inject_scenario(nats_url: str, stream_name: str, output_file: str):
    """Inject known audit scenario"""
    print(f"Injecting scenario to {stream_name} via {nats_url}")
    
    # Connect to NATS
    config = NATSConfig()
    config.url = nats_url
    nats_client = ExoArmurNATSClient(config)
    
    try:
        await nats_client.connect()
        
        # Ensure stream exists
        from nats.js.api import StreamConfig
        stream_config = StreamConfig(
            name=stream_name,
            subjects=["exoarmur.audit.append.v1"],
            retention="limits",
            max_age=365 * 24 * 3600,
            max_bytes=10 * 1024 * 1024 * 1024,
            storage="file"
        )
        await nats_client.js.add_stream(stream_config)
        
        # Initialize audit logger
        audit_logger = AuditLogger(nats_client)
        
        # Inject known test scenario
        test_scenarios = [
            {
                "event_kind": "TELEMETRY_INGESTED",
                "payload_ref": {
                    "test": "gate3_replay",
                    "scenario": "telemetry_batch",
                    "batch_id": "batch_001",
                    "records": 10
                },
                "correlation_id": "gate3_test_001",
                "trace_id": "trace_gate3_001",
                "tenant_id": "tenant_001",
                "cell_id": "cell_001",
                "idempotency_key": "EXOARMUR_GATE3_SCENARIO_001_NOT_REAL"
            },
            {
                "event_kind": "SAFETY_CHECK",
                "payload_ref": {
                    "test": "gate3_replay",
                    "scenario": "safety_verification",
                    "check_type": "boundary_validation",
                    "result": "passed"
                },
                "correlation_id": "gate3_test_001",
                "trace_id": "trace_gate3_002",
                "tenant_id": "tenant_001",
                "cell_id": "cell_001",
                "idempotency_key": "EXOARMUR_GATE3_SCENARIO_002_NOT_REAL"
            },
            {
                "event_kind": "DECISION_MADE",
                "payload_ref": {
                    "test": "gate3_replay",
                    "scenario": "autonomous_decision",
                    "decision_type": "allow",
                    "confidence": 0.95,
                    "reason": "within_safe_parameters"
                },
                "correlation_id": "gate3_test_002",
                "trace_id": "trace_gate3_003",
                "tenant_id": "tenant_001",
                "cell_id": "cell_001",
                "idempotency_key": "EXOARMUR_GATE3_SCENARIO_003_NOT_REAL"
            }
        ]
        
        injected_records = []
        
        for scenario in test_scenarios:
            print(f"Injecting: {scenario['event_kind']}")
            
            record = await audit_logger.emit_audit_record_async(
                event_kind=scenario["event_kind"],
                payload_ref=scenario["payload_ref"],
                correlation_id=scenario["correlation_id"],
                trace_id=scenario["trace_id"],
                tenant_id=scenario["tenant_id"],
                cell_id=scenario["cell_id"],
                idempotency_key=scenario["idempotency_key"]
            )
            
            injected_records.append(record.model_dump())
        
        # Wait for persistence
        await asyncio.sleep(1)
        
        # Get final stream state
        stream_info = await nats_client.js.stream_info(stream_name)
        print(f"Final stream state: {stream_info.state.messages} messages")
        
        # Write injection record
        injection_record = {
            "injected_at_utc": datetime.now(timezone.utc).isoformat(),
            "nats_url": nats_url,
            "stream_name": stream_name,
            "scenarios_injected": len(test_scenarios),
            "final_stream_messages": stream_info.state.messages,
            "final_stream_bytes": stream_info.state.bytes,
            "injected_records": injected_records
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(injection_record, f, indent=2)
        
        print(f"Injection record written to: {output_path}")
        return len(injected_records)
        
    except Exception as e:
        print(f"Injection failed: {e}")
        return 0
    
    finally:
        await nats_client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Inject known scenario for reality testing')
    parser.add_argument('--nats', default='nats://127.0.0.1:4222', help='NATS server URL')
    parser.add_argument('--stream', default='EXOARMUR_AUDIT_V1', help='Stream name')
    parser.add_argument('--out', required=True, help='Output injection record file')
    
    args = parser.parse_args()
    
    count = asyncio.run(inject_scenario(args.nats, args.stream, args.out))
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
