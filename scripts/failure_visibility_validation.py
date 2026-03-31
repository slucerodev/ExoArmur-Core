#!/usr/bin/env python3
"""
Failure Visibility Validation Script

This script ensures that divergence is:
- clearly visible
- not masked
- not explained away
- not auto-corrected

User must be able to see: "System disagrees here"

DO NOT MODIFY CORE LOGIC - ONLY VALIDATE VISIBILITY
"""

import os
import sys
import json
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

class FailureVisibilityValidator:
    """Validate that system failures and divergence are clearly visible"""
    
    def __init__(self):
        # Ensure deterministic environment
        os.environ['PYTHONHASHSEED'] = '0'
        
        # Visibility checks
        self.visibility_checks = []
        self.masking_issues = []
        self.clarity_problems = []
    
    def check_divergence_visibility(self):
        """Check that divergence is clearly visible"""
        print("🔍 DIVERGENCE VISIBILITY VALIDATION")
        print("=" * 60)
        print("Ensuring system disagreements are clearly visible")
        print()
        
        # Create test events
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='visibility-tenant',
                cell_id='visibility-cell-01',
                idempotency_key='visibility-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'visibility-event-001',
                    'source': 'visibility-sensor-01',
                    'severity': 'critical',
                    'event_type': 'system_failure'
                }}},
                hashes={'sha256': 'visibility-telemetry-hash-001'},
                correlation_id='visibility-correlation-001',
                trace_id='visibility-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345672',
                tenant_id='visibility-tenant',
                cell_id='visibility-cell-01',
                idempotency_key='visibility-key-001',
                recorded_at=base_time,
                event_kind='safety_gate_evaluated',
                payload_ref={'kind': {'ref': {
                    'verdict': 'require_emergency_shutdown',
                    'risk_level': 'critical',
                    'policy_rules': ['immediate_action_required'],
                    'automated_checks': ['failed', 'critical_failure']
                }}},
                hashes={'sha256': 'visibility-safety-hash-001'},
                correlation_id='visibility-correlation-001',
                trace_id='visibility-trace-001'
            )
        ]
        
        events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]
        
        # STEP 1: Test clean scenario for baseline
        print("📊 STEP 1: Clean Scenario Baseline")
        print("-" * 40)
        
        verifier = MultiNodeReplayVerifier(node_count=3)
        clean_report = verifier.verify_consensus(events, "visibility-correlation-001")
        
        print(f"Clean Results:")
        print(f"   Node Count: {verifier.node_count}")
        print(f"   Consensus: {not clean_report.has_divergence()}")
        print(f"   Node Hashes:")
        
        for node_id, hash_value in clean_report.node_hashes.items():
            print(f"     {node_id}: {hash_value[:16]}... ✅ CONSENSUS")
        
        print()
        
        # STEP 2: Test fault scenario for divergence
        print("🚨 STEP 2: Fault Scenario Divergence")
        print("-" * 40)
        
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        fault_result = test_runner.run_byzantine_test(events, ByzantineScenario.SINGLE_NODE)
        
        print(f"Fault Results:")
        print(f"   Scenario: {fault_result.scenario.value}")
        print(f"   Consensus: {not fault_result.divergence_report.has_divergence()}")
        print(f"   Divergence Detected: {fault_result.divergence_report.has_divergence()}")
        print(f"   Node Hashes:")
        
        for node_id, hash_value in fault_result.divergence_report.node_hashes.items():
            consensus_status = "✅ CONSENSUS" if node_id in fault_result.divergence_report.get_consensus_nodes() else "❌ DIVERGENT"
            print(f"     {node_id}: {hash_value[:16]}... {consensus_status}")
        
        print()
        
        # STEP 3: Validate divergence visibility
        print("🔍 STEP 3: Divergence Visibility Analysis")
        print("-" * 40)
        
        divergence_detected = fault_result.divergence_report.has_divergence()
        divergent_nodes = fault_result.divergence_report.divergent_nodes
        consensus_nodes = fault_result.divergence_report.get_consensus_nodes()
        
        print(f"DIVERGENCE VISIBILITY CHECK:")
        print(f"   ✅ Divergence Detected: {divergence_detected}")
        print(f"   ✅ Divergent Nodes: {len(divergent_nodes)}")
        print(f"   ✅ Consensus Nodes: {len(consensus_nodes)}")
        print(f"   ✅ System Disagreement: {'VISIBLE' if divergence_detected else 'NOT VISIBLE'}")
        print()
        
        # Check if disagreement is clearly visible
        if divergence_detected:
            print("🎯 SYSTEM DISAGREEMENT IS CLEARLY VISIBLE:")
            print(f"   \"System disagrees here: {len(divergent_nodes)} of {verifier.node_count} nodes disagree\"")
            print(f"   Divergent node IDs: {divergent_nodes}")
            print(f"   Consensus node IDs: {consensus_nodes}")
            
            # Show actual hash differences
            print(f"   Hash Differences:")
            consensus_hash = fault_result.divergence_report.node_hashes[consensus_nodes[0]] if consensus_nodes else "none"
            for node_id in divergent_nodes:
                divergent_hash = fault_result.divergence_report.node_hashes[node_id]
                print(f"     {node_id}: {divergent_hash[:16]}... ❌ (vs consensus {consensus_hash[:16]}...)")
            
            self.visibility_checks.append("✅ Divergence clearly visible")
        else:
            print("❌ SYSTEM DISAGREEMENT NOT VISIBLE")
            self.masking_issues.append("❌ Divergence not detected")
        
        print()
        
        return divergence_detected
    
    def check_failure_masking(self):
        """Check that failures are not masked or explained away"""
        print("🚨 FAILURE MASKING VALIDATION")
        print("=" * 60)
        print("Ensuring failures are not masked or auto-corrected")
        print()
        
        # Test with multiple failure scenarios
        failure_scenarios = [
            ("Single Node Fault", ByzantineScenario.SINGLE_NODE),
            ("Clean Scenario", ByzantineScenario.CLEAN),
        ]
        
        for scenario_name, scenario_type in failure_scenarios:
            print(f"📊 Testing {scenario_name}:")
            print("-" * 30)
            
            # Create test events
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            
            records = [
                AuditRecordV1(
                    schema_version='1.0.0',
                    audit_id='01J4NR5X9Z8GABCDEF12345671',
                    tenant_id='masking-tenant',
                    cell_id='masking-cell-01',
                    idempotency_key='masking-key-001',
                    recorded_at=base_time,
                    event_kind='telemetry_ingested',
                    payload_ref={'kind': {'ref': {
                        'event_id': 'masking-event-001',
                        'source': 'masking-sensor-01',
                        'severity': 'critical',
                        'event_type': 'system_compromise'
                    }}},
                    hashes={'sha256': 'masking-telemetry-hash-001'},
                    correlation_id='masking-correlation-001',
                    trace_id='masking-trace-001'
                )
            ]
            
            events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                    for i, record in enumerate(records)]
            
            # Run Byzantine test
            test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
            result = test_runner.run_byzantine_test(events, scenario_type)
            
            # Check for masking
            divergence_detected = result.divergence_report.has_divergence()
            corrupted_nodes = []
            
            for node_result in result.injection_results:
                if node_result.corrupted_events:
                    corrupted_nodes.append(node_result.node_id)
            
            print(f"   Divergence Detected: {divergence_detected}")
            print(f"   Corrupted Nodes: {len(corrupted_nodes)}")
            print(f"   Result: {result.divergence_report.consensus_result.value}")
            
            # Validate no masking
            if len(corrupted_nodes) > 0 and not divergence_detected:
                print(f"   ❌ MASKING DETECTED: {len(corrupted_nodes)} corrupted nodes but no divergence")
                self.masking_issues.append(f"❌ {scenario_name}: Failure masked")
            elif len(corrupted_nodes) > 0 and divergence_detected:
                print(f"   ✅ FAILURE VISIBLE: {len(corrupted_nodes)} corrupted nodes detected")
                self.visibility_checks.append(f"✅ {scenario_name}: Failure visible")
            else:
                print(f"   ℹ️  No failures injected")
            
            print()
    
    def check_auto_correction(self):
        """Check that failures are not auto-corrected"""
        print("🔧 AUTO-CORRECTION VALIDATION")
        print("=" * 60)
        print("Ensuring failures are not auto-corrected")
        print()
        
        # Test with events that might trigger auto-correction
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='autocorrect-tenant',
                cell_id='autocorrect-cell-01',
                idempotency_key='autocorrect-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'autocorrect-event-001',
                    'source': 'autocorrect-sensor-01',
                    'severity': 'critical',
                    'event_type': 'data_corruption_detected'
                }}},
                hashes={'sha256': 'autocorrect-telemetry-hash-001'},
                correlation_id='autocorrect-correlation-001',
                trace_id='autocorrect-trace-001'
            ),
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345672',
                tenant_id='autocorrect-tenant',
                cell_id='autocorrect-cell-01',
                idempotency_key='autocorrect-key-001',
                recorded_at=base_time,
                event_kind='safety_gate_evaluated',
                payload_ref={'kind': {'ref': {
                    'verdict': 'system_compromised',
                    'risk_level': 'critical',
                    'policy_rules': ['immediate_shutdown_required'],
                    'automated_checks': ['corruption_detected', 'integrity_failed']
                }}},
                hashes={'sha256': 'autocorrect-safety-hash-001'},
                correlation_id='autocorrect-correlation-001',
                trace_id='autocorrect-trace-001'
            )
        ]
        
        events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]
        
        # Run replay to check for auto-correction
        audit_store = {"autocorrect-correlation-001": events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        report = replay_engine.replay_correlation("autocorrect-correlation-001")
        
        print(f"REPLAY RESULTS:")
        print(f"   Total Events: {report.total_events}")
        print(f"   Processed Events: {report.processed_events}")
        print(f"   Failed Events: {report.failed_events}")
        print(f"   Result: {report.result.value}")
        print(f"   Failures: {report.failures}")
        print(f"   Warnings: {report.warnings}")
        
        # Check for auto-correction signs
        if report.result.value == 'success' and 'critical' in str(report.failures).lower():
            print(f"   ❌ AUTO-CORRECTION SUSPECTED: Critical events but success result")
            self.masking_issues.append("❌ Auto-correction detected")
        elif report.result.value == 'failure':
            print(f"   ✅ FAILURE PRESERVED: Critical events properly resulted in failure")
            self.visibility_checks.append("✅ No auto-correction")
        else:
            print(f"   ℹ️  Result: {report.result.value}")
        
        print()
        
        # Run Byzantine test to check divergence preservation
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        fault_result = test_runner.run_byzantine_test(events, ByzantineScenario.SINGLE_NODE)
        
        print(f"BYZANTINE RESULTS:")
        print(f"   Divergence Detected: {fault_result.divergence_report.has_divergence()}")
        print(f"   Consensus Result: {fault_result.divergence_report.consensus_result.value}")
        
        if fault_result.divergence_report.has_divergence():
            print(f"   ✅ DIVERGENCE PRESERVED: System properly detects disagreement")
            self.visibility_checks.append("✅ Divergence preserved in Byzantine test")
        else:
            print(f"   ❌ DIVERGENCE MASKED: System should detect disagreement but doesn't")
            self.masking_issues.append("❌ Divergence masked in Byzantine test")
        
        print()
    
    def check_clarity_of_failure_reporting(self):
        """Check that failure reporting is clear and unambiguous"""
        print("📋 FAILURE REPORTING CLARITY")
        print("=" * 60)
        print("Ensuring failure reporting is clear and unambiguous")
        print()
        
        # Test various failure scenarios
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version='1.0.0',
                audit_id='01J4NR5X9Z8GABCDEF12345671',
                tenant_id='clarity-tenant',
                cell_id='clarity-cell-01',
                idempotency_key='clarity-key-001',
                recorded_at=base_time,
                event_kind='telemetry_ingested',
                payload_ref={'kind': {'ref': {
                    'event_id': 'clarity-event-001',
                    'source': 'clarity-sensor-01',
                    'severity': 'critical',
                    'event_type': 'security_breach_detected'
                }}},
                hashes={'sha256': 'clarity-telemetry-hash-001'},
                correlation_id='clarity-correlation-001',
                trace_id='clarity-trace-001'
            )
        ]
        
        events = [CanonicalEvent(**to_canonical_event(record, sequence_number=i)) 
                for i, record in enumerate(records)]
        
        # Test multi-node verification clarity
        verifier = MultiNodeReplayVerifier(node_count=3)
        divergence_report = verifier.verify_consensus(events, "clarity-correlation-001")
        
        print(f"CLARITY CHECK:")
        print(f"   Consensus Result: {divergence_report.consensus_result.value}")
        print(f"   Has Divergence: {divergence_report.has_divergence()}")
        print(f"   Node Count: {verifier.node_count}")
        print(f"   Consensus Nodes: {len(divergence_report.get_consensus_nodes())}")
        print(f"   Divergent Nodes: {len(divergence_report.divergent_nodes)}")
        
        # Check reporting clarity
        if divergence_report.has_divergence():
            print(f"   ✅ CLEAR REPORTING: Divergence clearly reported")
            print(f"   ✅ SPECIFIC NODES: {divergence_report.divergent_nodes} identified")
            print(f"   ✅ HASH DIFFERENCES: Visible in node_hashes")
            self.visibility_checks.append("✅ Clear divergence reporting")
        else:
            print(f"   ℹ️  No divergence to report")
        
        # Test Byzantine reporting clarity
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        fault_result = test_runner.run_byzantine_test(events, ByzantineScenario.SINGLE_NODE)
        
        print(f"\nBYZANTINE CLARITY CHECK:")
        print(f"   Scenario: {fault_result.scenario.value}")
        print(f"   Baseline Hash: {fault_result.baseline_hash}")
        print(f"   Consensus: {not fault_result.divergence_report.has_divergence()}")
        print(f"   Divergence Detected: {fault_result.divergence_report.has_divergence()}")
        
        # Count corrupted nodes
        corrupted_count = 0
        for node_result in fault_result.injection_results:
            if node_result.corrupted_events:
                corrupted_count += 1
        
        print(f"   Corrupted Nodes: {corrupted_count}")
        
        if fault_result.divergence_report.has_divergence() and corrupted_count > 0:
            print(f"   ✅ CLEAR BYZANTINE REPORTING: Fault and divergence both reported")
            self.visibility_checks.append("✅ Clear Byzantine reporting")
        else:
            print(f"   ❌ UNCLEAR BYZANTINE REPORTING: Expected fault and divergence")
            self.clarity_problems.append("❌ Unclear Byzantine reporting")
        
        print()
    
    def generate_visibility_report(self):
        """Generate comprehensive visibility report"""
        print("📊 FAILURE VISIBILITY REPORT")
        print("=" * 60)
        
        print(f"✅ VISIBILITY CHECKS PASSED: {len(self.visibility_checks)}")
        for check in self.visibility_checks:
            print(f"   {check}")
        
        print(f"\n❌ MASKING ISSUES FOUND: {len(self.masking_issues)}")
        for issue in self.masking_issues:
            print(f"   {issue}")
        
        print(f"\n⚠️  CLARITY PROBLEMS: {len(self.clarity_problems)}")
        for problem in self.clarity_problems:
            print(f"   {problem}")
        
        # Overall assessment
        total_issues = len(self.masking_issues) + len(self.clarity_problems)
        
        print(f"\n🎯 OVERALL VISIBILITY ASSESSMENT:")
        if total_issues == 0:
            print(f"   ✅ EXCELLENT: All failures clearly visible")
            print(f"   ✅ No masking or auto-correction detected")
            print(f"   ✅ Clear and unambiguous reporting")
            print(f"   ✅ User can see \"System disagrees here\"")
        elif total_issues <= 2:
            print(f"   ⚠️  ACCEPTABLE: Minor visibility issues")
            print(f"   ⚠️  Most failures are clearly visible")
            print(f"   ⚠️  Some improvements needed")
        else:
            print(f"   ❌ POOR: Significant visibility problems")
            print(f"   ❌ Failures may be masked or unclear")
            print(f"   ❌ User may not see system disagreements")
        
        print()
        
        return total_issues == 0
    
    def run_validation(self):
        """Run complete failure visibility validation"""
        print("🎯 FAILURE VISIBILITY VALIDATION STARTED")
        print("=" * 60)
        print("Objective: Ensure divergence is clearly visible and not masked")
        print("DO NOT modify core logic - only validate visibility")
        print()
        
        # Run all visibility checks
        self.check_divergence_visibility()
        self.check_failure_masking()
        self.check_auto_correction()
        self.check_clarity_of_failure_reporting()
        
        # Generate report
        success = self.generate_visibility_report()
        
        print("🎉 FAILURE VISIBILITY VALIDATION COMPLETED")
        if success:
            print("✅ All failures are clearly visible")
            print("✅ No masking or auto-correction detected")
            print("✅ Users can see \"System disagrees here\"")
        else:
            print("⚠️  Some visibility issues identified")
            print("⚠️  Review masking issues and clarity problems")
        
        print("✅ No core system behavior modified")
        
        return success

def main():
    """Main entry point"""
    validator = FailureVisibilityValidator()
    success = validator.run_validation()
    
    if success:
        print("\n🚀 Ready for Phase 7: Output Consistency Check")
        sys.exit(0)
    else:
        print("\n❌ Visibility validation failed - address issues before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()
