#!/usr/bin/env python3
"""
Golden Artifact Generator for ExoArmur

This script generates deterministic golden artifacts that serve as
truth anchors for the system. These artifacts are committed to the
repository and used for regression testing.

Generated artifacts:
- demo_canonical_events.json: Sample canonical events
- demo_replay_output.json: Deterministic replay output
- demo_multi_node_hashes.json: Multi-node consensus hashes
- demo_byzantine_results.json: Byzantine fault injection results
- golden_manifest.json: Hash manifest of all artifacts
"""

import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.byzantine_fault_injection import (
    ByzantineTestRunner, 
    ByzantineScenario,
    FaultType,
    FaultConfig
)
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event

def create_sample_canonical_events() -> List[CanonicalEvent]:
    """Create deterministic sample canonical events for testing"""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    records = [
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345671',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='telemetry_ingested',
            payload_ref={'kind': {'ref': {'event_id': 'demo-event-001', 'source': 'test'}}},
            hashes={'sha256': 'demo-hash-001'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        ),
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345672',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='safety_gate_evaluated',
            payload_ref={'kind': {'ref': {'verdict': 'require_human', 'risk_score': 'medium'}}},
            hashes={'sha256': 'demo-hash-002'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        ),
        AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345673',
            tenant_id='demo-tenant',
            cell_id='demo-cell-01',
            idempotency_key='demo-key-001',
            recorded_at=base_time,
            event_kind='approval_requested',
            payload_ref={'kind': {'ref': {'approval_id': 'demo-approval-001', 'operator': 'demo-operator'}}},
            hashes={'sha256': 'demo-hash-003'},
            correlation_id='demo-correlation-001',
            trace_id='demo-trace-001'
        )
    ]
    
    return [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
            for i, record in enumerate(records)]

def generate_replay_output(events: List[CanonicalEvent]) -> Dict[str, Any]:
    """Generate deterministic replay output"""
    audit_store = {"demo-correlation-001": events}
    replay_engine = ReplayEngine(audit_store=audit_store)
    
    report = replay_engine.replay_correlation("demo-correlation-001")
    
    return {
        "correlation_id": report.correlation_id,
        "replay_timestamp": report.replay_timestamp.isoformat(),
        "result": report.result.value,
        "total_events": report.total_events,
        "processed_events": report.processed_events,
        "failed_events": report.failed_events,
        "intent_hash_verified": report.intent_hash_verified,
        "safety_gate_verified": report.safety_gate_verified,
        "audit_integrity_verified": report.audit_integrity_verified,
        "reconstructed_intents": len(report.reconstructed_intents),
        "reconstructed_decisions": len(report.reconstructed_decisions),
        "safety_gate_verdicts": len(report.safety_gate_verdicts),
        "failures": report.failures,
        "warnings": report.warnings
    }

def generate_multi_node_hashes(events: List[CanonicalEvent]) -> Dict[str, Any]:
    """Generate multi-node consensus hashes"""
    verifier = MultiNodeReplayVerifier(node_count=3)
    
    divergence_report = verifier.verify_consensus(events, "demo-correlation-001")
    
    return {
        "node_count": verifier.node_count,
        "consensus_result": divergence_report.consensus_result.value,
        "has_divergence": divergence_report.has_divergence(),
        "node_hashes": divergence_report.node_hashes,
        "divergent_nodes": divergence_report.divergent_nodes,
        "consensus_nodes": divergence_report.get_consensus_nodes()
    }

def generate_byzantine_results(events: List[CanonicalEvent]) -> Dict[str, Any]:
    """Generate Byzantine fault injection results"""
    test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
    
    results = {}
    for scenario in [ByzantineScenario.CLEAN, ByzantineScenario.SINGLE_NODE]:
        result = test_runner.run_byzantine_test(events, scenario)
        results[scenario.value] = {
            "scenario": result.scenario.value,
            "baseline_hash": result.baseline_hash,
            "consensus_result": result.divergence_report.consensus_result.value,
            "has_divergence": result.divergence_report.has_divergence(),
            "node_count": len(result.divergence_report.node_hashes),
            "divergent_nodes": len(result.divergence_report.divergent_nodes)
        }
    
    return results

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    """Generate all golden artifacts"""
    print("🏺 GENERATING GOLDEN ARTIFACTS")
    print("=" * 50)
    
    # Ensure deterministic environment
    os.environ['PYTHONHASHSEED'] = '0'
    
    # Create artifacts directory
    artifacts_dir = Path("tests/artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    
    print("📝 Creating sample canonical events...")
    events = create_sample_canonical_events()
    
    # Save canonical events
    events_file = artifacts_dir / "demo_canonical_events.json"
    events_data = [event.to_dict() for event in events]
    with open(events_file, 'w') as f:
        json.dump(events_data, f, indent=2, sort_keys=True)
    
    print("⚙️  Generating replay output...")
    replay_output = generate_replay_output(events)
    replay_file = artifacts_dir / "demo_replay_output.json"
    with open(replay_file, 'w') as f:
        json.dump(replay_output, f, indent=2, sort_keys=True)
    
    print("🔗 Generating multi-node hashes...")
    multi_node_hashes = generate_multi_node_hashes(events)
    hashes_file = artifacts_dir / "demo_multi_node_hashes.json"
    with open(hashes_file, 'w') as f:
        json.dump(multi_node_hashes, f, indent=2, sort_keys=True)
    
    print("🛡️  Generating Byzantine results...")
    byzantine_results = generate_byzantine_results(events)
    byzantine_file = artifacts_dir / "demo_byzantine_results.json"
    with open(byzantine_file, 'w') as f:
        json.dump(byzantine_results, f, indent=2, sort_keys=True)
    
    print("📋 Creating manifest...")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_hash_seed": "0",
        "version": "1.0.0",
        "artifacts": {}
    }
    
    # Compute hashes for all artifacts
    for artifact_file in [events_file, replay_file, hashes_file, byzantine_file]:
        file_hash = compute_file_hash(artifact_file)
        manifest["artifacts"][artifact_file.name] = {
            "file_path": str(artifact_file),
            "sha256": file_hash,
            "size": artifact_file.stat().st_size
        }
    
    # Save manifest
    manifest_file = artifacts_dir / "golden_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    
    print(f"\n✅ Golden artifacts generated successfully!")
    print(f"📁 Location: {artifacts_dir}")
    print(f"📄 Files created:")
    for artifact_file in [events_file, replay_file, hashes_file, byzantine_file, manifest_file]:
        size = artifact_file.stat().st_size
        print(f"   - {artifact_file.name} ({size} bytes)")
    
    print(f"\n🔐 Manifest hash: {compute_file_hash(manifest_file)}")
    print("\n💡 These artifacts serve as deterministic truth anchors.")
    print("   Any changes to core logic will cause hash mismatches in CI.")

if __name__ == "__main__":
    main()
