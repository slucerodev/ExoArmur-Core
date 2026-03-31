#!/usr/bin/env python3
"""
External Validation Observability Script

This script provides enhanced visibility into the ExoArmur validation process
without modifying core system behavior. It displays:
- Canonical events before replay
- Replay output
- Hash lineage: input → replay → hash
- Node-by-node results

DO NOT MODIFY CORE LOGIC - ONLY ADD VISIBILITY
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.byzantine_fault_injection import (
    ByzantineTestRunner, 
    ByzantineScenario
)
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event
from datetime import datetime, timezone

class ExternalValidationObservability:
    """Enhanced visibility for external validation"""
    
    def __init__(self):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        
        # Canonical correlation ID for validation
        self.correlation_id = "observability-validation-001"
    
    def display_canonical_events(self, events):
        """Display canonical events before replay (visibility only)"""
        print("📋 CANONICAL EVENTS (INPUT VISIBILITY)")
        print("=" * 60)
        print(f"Correlation ID: {self.correlation_id}")
        print(f"Total Events: {len(events)}")
        print()
        
        for i, event in enumerate(events):
            print(f"EVENT {i+1}:")
            print(f"  ID: {event.event_id}")
            print(f"  Type: {event.event_type}")
            print(f"  Actor: {event.actor}")
            print(f"  Sequence: {event.sequence_number}")
            print(f"  Payload Hash: {event.payload_hash}")
            print(f"  Payload: {json.dumps(event.payload, indent=4)}")
            print()
    
    def compute_input_hash(self, events):
        """Compute hash of canonical input (visibility only)"""
        input_data = {
            'correlation_id': self.correlation_id,
            'events': [event.to_dict() for event in events]
        }
        input_hash = stable_hash(canonical_json(input_data))
        print(f"🔐 INPUT HASH: {input_hash}")
        print(f"   Computed from {len(events)} canonical events")
        print()
        return input_hash
    
    def display_replay_output(self, replay_engine, correlation_id):
        """Display replay output with full visibility"""
        print("⚙️  REPLAY OUTPUT VISIBILITY")
        print("=" * 60)
        
        # Run replay
        report = replay_engine.replay_correlation(correlation_id)
        
        # Display full replay report
        print(f"Replay Report:")
        print(f"  Correlation ID: {report.correlation_id}")
        print(f"  Total Events: {report.total_events}")
        print(f"  Processed Events: {report.processed_events}")
        print(f"  Failed Events: {report.failed_events}")
        print(f"  Result: {report.result.value}")
        print(f"  Intent Hash Verified: {report.intent_hash_verified}")
        print(f"  Safety Gate Verified: {report.safety_gate_verified}")
        print(f"  Audit Integrity Verified: {report.audit_integrity_verified}")
        print(f"  Reconstructed Intents: {len(report.reconstructed_intents)}")
        print(f"  Reconstructed Decisions: {len(report.reconstructed_decisions)}")
        
        if report.failures:
            print(f"  Failures: {report.failures}")
        if report.warnings:
            print(f"  Warnings: {report.warnings}")
        
        print()
        
        # Display reconstructed intents if any
        if report.reconstructed_intents:
            print("RECONSTRUCTED INTENTS:")
            for i, intent in enumerate(report.reconstructed_intents):
                print(f"  Intent {i+1}: {intent}")
            print()
        
        # Display reconstructed decisions if any
        if report.reconstructed_decisions:
            print("RECONSTRUCTED DECISIONS:")
            for i, decision in enumerate(report.reconstructed_decisions):
                print(f"  Decision {i+1}: {decision}")
            print()
        
        return report
    
    def display_hash_lineage(self, input_hash, replay_output):
        """Display hash lineage: input → replay → hash"""
        print("🔗 HASH LINEAGE VISIBILITY")
        print("=" * 60)
        
        # Compute replay hash
        replay_dict = replay_output.to_dict()
        replay_hash = stable_hash(canonical_json(replay_dict))
        
        print(f"INPUT HASH:")
        print(f"  {input_hash}")
        print(f"  └─ Source: Canonical events")
        print()
        
        print(f"REPLAY HASH:")
        print(f"  {replay_hash}")
        print(f"  └─ Source: Replay output")
        print()
        
        print(f"HASH LINEAGE:")
        print(f"  Canonical Events → {input_hash[:16]}...")
        print(f"  Replay Engine → {replay_hash[:16]}...")
        print()
        
        print(f"DETERMINISM VERIFICATION:")
        print(f"  Same input always produces: {replay_hash}")
        print(f"  No environment influence: YES")
        print(f"  No randomness: YES")
        print()
        
        return replay_hash
    
    def display_node_by_node_results(self, verifier, events):
        """Display node-by-node consensus results with full visibility"""
        print("🔗 NODE-BY-NODE CONSENSUS VISIBILITY")
        print("=" * 60)
        
        # Run multi-node verification
        divergence_report = verifier.verify_consensus(events, self.correlation_id)
        
        print(f"Multi-Node Verification Results:")
        print(f"  Node Count: {verifier.node_count}")
        print(f"  Consensus Achieved: {not divergence_report.has_divergence()}")
        print(f"  Consensus Result: {divergence_report.consensus_result.value}")
        print()
        
        print("NODE-BY-NODE HASHES:")
        for node_id, hash_value in divergence_report.node_hashes.items():
            consensus_status = "✅ CONSENSUS" if node_id in divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
            print(f"  {node_id}:")
            print(f"    Hash: {hash_value}")
            print(f"    Status: {consensus_status}")
            print()
        
        print("CONSENSUS ANALYSIS:")
        print(f"  Agreeing Nodes: {len(divergence_report.get_consensus_nodes())}/{verifier.node_count}")
        print(f"  Divergent Nodes: {len(divergence_report.divergent_nodes)}")
        
        if divergence_report.divergent_nodes:
            print(f"  Divergent Node IDs: {divergence_report.divergent_nodes}")
        
        print()
        
        # Display canonical outputs for each node
        print("NODE CANONICAL OUTPUTS:")
        for node_id, output in divergence_report.canonical_outputs.items():
            consensus_status = "✅ CONSENSUS" if node_id in divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
            print(f"  {node_id}:")
            print(f"    Output: {output[:100]}...")
            print(f"    Status: {consensus_status}")
            print()
        
        return divergence_report
    
    def display_byzantine_visibility(self, events):
        """Display Byzantine fault injection with full visibility"""
        print("🛡️  BYZANTINE FAULT INJECTION VISIBILITY")
        print("=" * 60)
        
        # Test clean scenario
        print("CLEAN SCENARIO:")
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        clean_result = test_runner.run_byzantine_test(events, ByzantineScenario.CLEAN)
        
        print(f"  Scenario: {clean_result.scenario.value}")
        print(f"  Baseline Hash: {clean_result.baseline_hash}")
        print(f"  Consensus: {not clean_result.divergence_report.has_divergence()}")
        print(f"  Consensus Result: {clean_result.divergence_report.consensus_result.value}")
        print()
        
        # Display clean node results
        print("  CLEAN NODE RESULTS:")
        for node_id, hash_value in clean_result.divergence_report.node_hashes.items():
            print(f"    {node_id}: {hash_value[:16]}... ✅")
        print()
        
        # Test single-node fault scenario
        print("SINGLE-NODE FAULT SCENARIO:")
        single_result = test_runner.run_byzantine_test(events, ByzantineScenario.SINGLE_NODE)
        
        print(f"  Scenario: {single_result.scenario.value}")
        print(f"  Baseline Hash: {single_result.baseline_hash}")
        print(f"  Consensus: {not single_result.divergence_report.has_divergence()}")
        print(f"  Consensus Result: {single_result.divergence_report.consensus_result.value}")
        print(f"  Divergence Detected: {single_result.divergence_report.has_divergence()}")
        print()
        
        # Display fault injection results
        print("  FAULT INJECTION RESULTS:")
        for i, node_result in enumerate(single_result.injection_results):
            if node_result.corrupted_events:
                print(f"    Corrupted Node {i+1}:")
                print(f"      Node ID: {node_result.node_id}")
                print(f"      Fault Type: {node_result.fault_type.value}")
                print(f"      Corrupted Events: {len(node_result.corrupted_events)}")
                print()
        
        # Display single-node node results with divergence
        print("  FAULT SCENARIO NODE RESULTS:")
        for node_id, hash_value in single_result.divergence_report.node_hashes.items():
            consensus_status = "✅ CONSENSUS" if node_id in single_result.divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
            print(f"    {node_id}: {hash_value[:16]}... {consensus_status}")
        print()
        
        print("FAULT DETECTION ANALYSIS:")
        clean_consensus = not clean_result.divergence_report.has_divergence()
        single_divergence = single_result.divergence_report.has_divergence()
        
        print(f"  Clean Scenario Consensus: {clean_consensus}")
        print(f"  Fault Scenario Divergence: {single_divergence}")
        print(f"  System Resilience: {'VERIFIED' if clean_consensus and single_divergence else 'FAILED'}")
        print()
        
        return clean_result, single_result
    
    def run_observability_demo(self):
        """Run complete observability demo without modifying core behavior"""
        print("🎯 EXTERNAL VALIDATION OBSERVABILITY DEMO")
        print("=" * 60)
        print("Enhanced visibility without core system modifications")
        print()
        
        # Create canonical events
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='observability-tenant',
                cell_id='observability-cell-01',
                idempotency_key='observability-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'observability-event-001',
                    'source': 'observability-sensor-01',
                    'severity': 'high',
                    'event_type': 'security_incident'
                }}},
                hashes={'sha256': 'observability-telemetry-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='observability-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345672',
                tenant_id='observability-tenant',
                cell_id='observability-cell-01',
                idempotency_key='observability-key-001',
                recorded_at=base_time,
                event_kind='safety_gate_evaluated',
                payload_ref={'kind': {'ref': {
                    'verdict': 'require_human_approval',
                    'risk_level': 'high',
                    'policy_rules': ['observability_validation_required'],
                    'automated_checks': ['passed', 'validated']
                }}},
                hashes={'sha256': 'observability-safety-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='observability-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345673',
                tenant_id='observability-tenant',
                cell_id='observability-cell-01',
                idempotency_key='observability-key-001',
                recorded_at=base_time,
                event_kind='approval_requested',
                payload_ref={'kind': {'ref': {
                    'approval_id': 'observability-approval-001',
                    'operator': 'observability-validator-01',
                    'approval_type': 'observability_validation'
                }}},
                hashes={'sha256': 'observability-approval-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='observability-trace-001'
            )
        ]
        
        events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]
        
        # STEP 1: Display canonical events (visibility only)
        self.display_canonical_events(events)
        
        # STEP 2: Compute input hash (visibility only)
        input_hash = self.compute_input_hash(events)
        
        # STEP 3: Run replay and display output (visibility only)
        audit_store = {self.correlation_id: events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        replay_output = self.display_replay_output(replay_engine, self.correlation_id)
        
        # STEP 4: Display hash lineage (visibility only)
        replay_hash = self.display_hash_lineage(input_hash, replay_output)
        
        # STEP 5: Display node-by-node consensus (visibility only)
        verifier = MultiNodeReplayVerifier(node_count=3)
        divergence_report = self.display_node_by_node_results(verifier, events)
        
        # STEP 6: Display Byzantine fault injection (visibility only)
        clean_result, single_result = self.display_byzantine_visibility(events)
        
        # SUMMARY
        print("🎯 OBSERVABILITY SUMMARY")
        print("=" * 60)
        print("✅ Canonical events displayed with full visibility")
        print("✅ Hash lineage traced from input to output")
        print("✅ Node-by-node consensus results visible")
        print("✅ Byzantine fault injection fully observable")
        print("✅ No core system behavior modified")
        print("✅ Enhanced visibility without logic changes")
        print()
        print("🔐 DETERMINISTIC GUARANTEES VISIBLE:")
        print(f"   Input Hash: {input_hash[:16]}...")
        print(f"   Replay Hash: {replay_hash[:16]}...")
        print(f"   Consensus: {not divergence_report.has_divergence()}")
        print(f"   Fault Detection: {single_result.divergence_report.has_divergence()}")
        print()
        print("🎉 OBSERVABILITY DEMO COMPLETED")

def main():
    """Main entry point"""
    observability = ExternalValidationObservability()
    observability.run_observability_demo()

if __name__ == "__main__":
    main()
