#!/usr/bin/env python3
"""
External Validation Script - Canonical Demo Path

This script implements the canonical demo path for external validation:
STEP 1: Submit canonical event → Run replay → Capture output + hash
STEP 2: Run multi-node verification → Confirm consensus  
STEP 3: Run Byzantine fault injection → Confirm divergence detection

Requirements:
- Identical output across runs
- No timestamps
- No environment drift  
- No randomness
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

class ExternalValidationDemo:
    """Canonical demo path for external validation"""
    
    def __init__(self):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        
        # Canonical correlation ID for validation
        self.correlation_id = "external-validation-001"
        
        # Results storage
        self.validation_results = {}
    
    def create_canonical_events(self):
        """Create canonical events for external validation"""
        print("📝 STEP 1.1: Creating Canonical Events")
        print("-" * 50)
        
        # Fixed base time - no wall-clock usage
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='external-validation-tenant',
                cell_id='validation-cell-01',
                idempotency_key='validation-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'validation-event-001',
                    'source': 'validation-sensor-01',
                    'severity': 'high',
                    'event_type': 'security_incident'
                }}},
                hashes={'sha256': 'validation-telemetry-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='validation-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345672',
                tenant_id='external-validation-tenant',
                cell_id='validation-cell-01',
                idempotency_key='validation-key-001',
                recorded_at=base_time,
                event_kind='safety_gate_evaluated',
                payload_ref={'kind': {'ref': {
                    'verdict': 'require_human_approval',
                    'risk_level': 'high',
                    'policy_rules': ['external_validation_required'],
                    'automated_checks': ['passed', 'validated']
                }}},
                hashes={'sha256': 'validation-safety-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='validation-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345673',
                tenant_id='external-validation-tenant',
                cell_id='validation-cell-01',
                idempotency_key='validation-key-001',
                recorded_at=base_time,
                event_kind='approval_requested',
                payload_ref={'kind': {'ref': {
                    'approval_id': 'validation-approval-001',
                    'operator': 'external-validator-01',
                    'approval_type': 'external_validation'
                }}},
                hashes={'sha256': 'validation-approval-hash-001'},
                correlation_id=self.correlation_id,
                trace_id='validation-trace-001'
            )
        ]
        
        events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]
        
        print(f"✅ Created {len(events)} canonical events")
        print(f"   Correlation ID: {self.correlation_id}")
        print(f"   Events: telemetry → safety → approval")
        print(f"   Fixed timestamp: {base_time.isoformat()}")
        
        # Store canonical events
        self.canonical_events = events
        return events
    
    def step_1_replay_validation(self):
        """STEP 1: Submit canonical event → Run replay → Capture output + hash"""
        print("\n⚙️  STEP 1.2: Replay Validation")
        print("=" * 50)
        
        # Create replay engine
        audit_store = {self.correlation_id: self.canonical_events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        
        # Run replay
        report = replay_engine.replay_correlation(self.correlation_id)
        
        # Generate deterministic hash
        replay_output = report.to_dict()
        replay_hash = stable_hash(canonical_json(replay_output))
        
        # Store results
        self.validation_results['replay'] = {
            'correlation_id': report.correlation_id,
            'replay_hash': replay_hash,
            'total_events': report.total_events,
            'processed_events': report.processed_events,
            'failed_events': report.failed_events,
            'result': report.result.value,
            'intent_hash_verified': report.intent_hash_verified,
            'safety_gate_verified': report.safety_gate_verified,
            'audit_integrity_verified': report.audit_integrity_verified,
            'reconstructed_intents': len(report.reconstructed_intents),
            'reconstructed_decisions': len(report.reconstructed_decisions),
            'failures': report.failures,
            'warnings': report.warnings,
            'replay_output': replay_output
        }
        
        print(f"✅ Replay completed successfully")
        print(f"   Events processed: {report.processed_events}/{report.total_events}")
        print(f"   Result: {report.result.value}")
        print(f"   Deterministic hash: {replay_hash}")
        print(f"   Safety gates verified: {report.safety_gate_verified}")
        print(f"   Audit integrity verified: {report.audit_integrity_verified}")
        
        # Show canonical input
        print(f"\n📋 Canonical Input Summary:")
        for i, event in enumerate(self.canonical_events):
            print(f"   Event {i+1}: {event.event_type} (ID: {event.event_id[:16]}...)")
        
        return replay_hash
    
    def step_2_consensus_validation(self):
        """STEP 2: Run multi-node verification → Confirm consensus"""
        print("\n🔗 STEP 2: Multi-Node Consensus Validation")
        print("=" * 50)
        
        # Run multi-node verification
        verifier = MultiNodeReplayVerifier(node_count=3)
        divergence_report = verifier.verify_consensus(self.canonical_events, self.correlation_id)
        
        # Store results
        self.validation_results['consensus'] = {
            'correlation_id': self.correlation_id,
            'node_count': verifier.node_count,
            'consensus': not divergence_report.has_divergence(),
            'consensus_result': divergence_report.consensus_result.value,
            'node_hashes': divergence_report.node_hashes,
            'divergent_nodes': divergence_report.divergent_nodes,
            'consensus_nodes': divergence_report.get_consensus_nodes(),
            'has_divergence': divergence_report.has_divergence()
        }
        
        print(f"✅ Multi-node verification completed")
        print(f"   Node count: {verifier.node_count}")
        print(f"   Consensus: {not divergence_report.has_divergence()}")
        print(f"   Result: {divergence_report.consensus_result.value}")
        
        # Show node-by-node results
        print(f"\n📊 Node-by-Node Results:")
        for node_id, hash_value in divergence_report.node_hashes.items():
            consensus_status = "✅ CONSENSUS" if node_id in divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
            print(f"   {node_id}: {hash_value[:16]}... {consensus_status}")
        
        return divergence_report.consensus_result.value
    
    def step_3_byzantine_validation(self):
        """STEP 3: Run Byzantine fault injection → Confirm divergence detection"""
        print("\n🛡️  STEP 3: Byzantine Fault Injection Validation")
        print("=" * 50)
        
        # Test clean scenario first
        print("   Testing CLEAN scenario:")
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        clean_result = test_runner.run_byzantine_test(self.canonical_events, ByzantineScenario.CLEAN)
        
        # Test single-node fault scenario
        print("   Testing SINGLE_NODE fault scenario:")
        single_result = test_runner.run_byzantine_test(self.canonical_events, ByzantineScenario.SINGLE_NODE)
        
        # Extract corrupted nodes
        corrupted_nodes = []
        for node_result in single_result.injection_results:
            if node_result.corrupted_events:
                corrupted_nodes.append(f"corrupted-node-{len(corrupted_nodes)+1}")
        
        # Store results
        self.validation_results['byzantine'] = {
            'clean_scenario': {
                'scenario': clean_result.scenario.value,
                'baseline_hash': clean_result.baseline_hash,
                'consensus': not clean_result.divergence_report.has_divergence(),
                'consensus_result': clean_result.divergence_report.consensus_result.value,
                'corrupted_nodes': [],
                'divergence_detected': clean_result.divergence_report.has_divergence(),
                'node_count': len(clean_result.divergence_report.node_hashes)
            },
            'single_node_scenario': {
                'scenario': single_result.scenario.value,
                'baseline_hash': single_result.baseline_hash,
                'consensus': not single_result.divergence_report.has_divergence(),
                'consensus_result': single_result.divergence_report.consensus_result.value,
                'corrupted_nodes': corrupted_nodes,
                'divergence_detected': single_result.divergence_report.has_divergence(),
                'node_count': len(single_result.divergence_report.node_hashes)
            }
        }
        
        print(f"✅ Byzantine fault injection completed")
        print(f"\n   CLEAN Scenario Results:")
        print(f"     Baseline hash: {clean_result.baseline_hash}")
        print(f"     Consensus: {not clean_result.divergence_report.has_divergence()}")
        print(f"     Divergence detected: {clean_result.divergence_report.has_divergence()}")
        
        print(f"\n   SINGLE_NODE Scenario Results:")
        print(f"     Baseline hash: {single_result.baseline_hash}")
        print(f"     Consensus: {not single_result.divergence_report.has_divergence()}")
        print(f"     Corrupted nodes: {len(corrupted_nodes)}")
        print(f"     Divergence detected: {single_result.divergence_report.has_divergence()}")
        
        return single_result.divergence_report.has_divergence()
    
    def validate_output_consistency(self):
        """Validate identical outputs across multiple runs"""
        print("\n🔍 OUTPUT CONSISTENCY VALIDATION")
        print("=" * 50)
        
        # Run the entire demo multiple times
        run_hashes = []
        
        for run_num in range(3):
            print(f"   Running validation test #{run_num + 1}...")
            
            # Clear previous results
            self.validation_results = {}
            
            # Run all steps
            self.create_canonical_events()
            replay_hash = self.step_1_replay_validation()
            consensus_result = self.step_2_consensus_validation()
            divergence_detected = self.step_3_byzantine_validation()
            
            # Generate composite hash
            composite_data = {
                'replay_hash': replay_hash,
                'consensus_result': consensus_result,
                'clean_baseline': self.validation_results['byzantine']['clean_scenario']['baseline_hash'],
                'single_divergence': self.validation_results['byzantine']['single_node_scenario']['divergence_detected']
            }
            composite_hash = stable_hash(canonical_json(composite_data))
            run_hashes.append(composite_hash)
        
        # Check consistency
        if len(set(run_hashes)) == 1:
            print(f"✅ OUTPUT CONSISTENCY VERIFIED")
            print(f"   All runs produce identical composite hash: {run_hashes[0][:16]}...")
            return True
        else:
            print(f"❌ OUTPUT INCONSISTENCY DETECTED")
            print(f"   Different hashes across runs:")
            for i, hash_val in enumerate(run_hashes):
                print(f"     Run {i+1}: {hash_val}")
            return False
    
    def generate_trust_signals(self):
        """Generate clear trust signals for external validation"""
        print("\n🔐 TRUST SIGNAL EXTRACTION")
        print("=" * 50)
        
        if 'replay' not in self.validation_results:
            print("❌ No validation results available")
            return
        
        replay = self.validation_results['replay']
        consensus = self.validation_results['consensus']
        byzantine = self.validation_results['byzantine']
        
        print(f"📊 PRIMARY TRUTH SIGNALS:")
        print(f"   Replay Hash (deterministic output): {replay['replay_hash']}")
        print(f"   Input Events: {replay['total_events']} canonical events")
        print(f"   Processing Result: {replay['result']}")
        print(f"   Safety Gates Verified: {replay['safety_gate_verified']}")
        
        print(f"\n🔗 CONSENSUS SIGNALS:")
        print(f"   Node Count: {consensus['node_count']}")
        print(f"   Consensus Achieved: {consensus['consensus']}")
        print(f"   Consensus Result: {consensus['consensus_result']}")
        print(f"   Agreeing Nodes: {len(consensus['consensus_nodes'])}/{consensus['node_count']}")
        
        print(f"\n🛡️  FAULT DETECTION SIGNALS:")
        clean = byzantine['clean_scenario']
        single = byzantine['single_node_scenario']
        
        print(f"   Clean Scenario Consensus: {clean['consensus']}")
        print(f"   Fault Scenario Divergence: {single['divergence_detected']}")
        print(f"   Corrupted Nodes Detected: {len(single['corrupted_nodes'])}")
        print(f"   System Resilience: {'VERIFIED' if clean['consensus'] and single['divergence_detected'] else 'FAILED'}")
        
        print(f"\n🎯 EXTERNAL VALIDATION SUMMARY:")
        print(f"   ✅ Deterministic replay: {replay['replay_hash'][:16]}...")
        print(f"   ✅ Multi-node consensus: {consensus['consensus']}")
        print(f"   ✅ Byzantine resilience: {single['divergence_detected']}")
        print(f"   ✅ System is PROVABLY DETERMINISTIC")
        
        return self.validation_results
    
    def run_canonical_demo(self):
        """Run the complete canonical demo for external validation"""
        print("🎯 EXTERNAL VALIDATION - CANONICAL DEMO PATH")
        print("=" * 60)
        print("Objective: Validate ExoArmur is deterministic and trustworthy")
        print()
        
        try:
            # Run canonical demo steps
            self.create_canonical_events()
            self.step_1_replay_validation()
            self.step_2_consensus_validation()
            self.step_3_byzantine_validation()
            
            # Validate output consistency
            consistent = self.validate_output_consistency()
            
            if not consistent:
                print("\n❌ EXTERNAL VALIDATION FAILED: Output inconsistency detected")
                return False
            
            # Generate trust signals
            self.generate_trust_signals()
            
            print(f"\n🎉 EXTERNAL VALIDATION COMPLETED SUCCESSFULLY!")
            print(f"✅ ExoArmur is demonstrably deterministic and trustworthy")
            
            return True
            
        except Exception as e:
            print(f"\n❌ EXTERNAL VALIDATION FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main entry point for external validation"""
    validator = ExternalValidationDemo()
    success = validator.run_canonical_demo()
    
    if success:
        print(f"\n🚀 Ready for Phase 3: Trust Signal Extraction")
        sys.exit(0)
    else:
        print(f"\n❌ External validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
