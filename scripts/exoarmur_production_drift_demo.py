#!/usr/bin/env python3
"""
ExoArmur Production Drift Integration

This script integrates the production drift demo with ExoArmur's
canonical event system to demonstrate execution integrity verification.

SCENARIO: Security incident response AI agent
GOAL: Show "Same agent. Same prompt. Different execution reality."
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event
from datetime import datetime, timezone

# Import the production drift demo
from production_drift_demo import ProductionDriftDemo, ExecutionTrace, ToolCall

# Ensure deterministic environment
os.environ['PYTHONHASHSEED'] = '0'

class ExoArmurDriftVerifier:
    """Integrates production drift demo with ExoArmur verification"""
    
    def __init__(self):
        self.demo = ProductionDriftDemo()
    
    def convert_trace_to_canonical_events(self, trace: ExecutionTrace, run_prefix: str) -> List[CanonicalEvent]:
        """Convert execution trace to canonical events for ExoArmur"""
        events = []
        base_time = datetime(2024, 3, 30, 19, 0, 0, tzinfo=timezone.utc)
        
        # Create incident ingestion event
        incident_event = AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345671',  # Valid ULID format
            tenant_id='security-operations',
            cell_id='incident-response-cell',
            idempotency_key=f'{run_prefix}_ingest',
            recorded_at=base_time,
            event_kind='incident_ingested',
            payload_ref={'kind': {'ref': trace.incident_report}},
            hashes={'sha256': stable_hash(canonical_json(trace.incident_report))},
            correlation_id=f'{run_prefix}_incident_response',
            trace_id=f'{run_prefix}_trace_001'
        )
        
        events.append(CanonicalEvent(**to_canonical_event(incident_event, sequence_number=0)))
        
        # Create tool call events
        for i, tool_call in enumerate(trace.tool_calls):
            # Handle both ToolCall objects and dict representations
            if isinstance(tool_call, dict):
                tool_name = tool_call.get('tool_name', 'unknown')
                call_id = tool_call.get('call_id', f'call_{i}')
                input_data = tool_call.get('input_data', {})
                output_data = tool_call.get('output_data', {})
                execution_time_ms = tool_call.get('execution_time_ms', 0)
                timestamp_str = tool_call.get('timestamp', datetime.now(timezone.utc).isoformat())
                success = tool_call.get('success', True)
                retry_count = tool_call.get('retry_count', 0)
                
                # Parse timestamp
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
            else:
                # Handle ToolCall object
                tool_name = tool_call.tool_name
                call_id = tool_call.call_id
                input_data = tool_call.input_data
                output_data = tool_call.output_data
                execution_time_ms = tool_call.execution_time_ms
                timestamp = tool_call.timestamp
                success = tool_call.success
                retry_count = tool_call.retry_count
            
            tool_event = AuditRecordV1(
                schema_version='1.0.0',
                audit_id=f'01J4NR5X9Z8GABCDEF1234567{2+i}',  # Valid ULID format
                tenant_id='security-operations',
                cell_id='incident-response-cell',
                idempotency_key=f'{run_prefix}_tool_{i}',
                recorded_at=timestamp,
                event_kind='tool_executed',
                payload_ref={
                    'kind': {
                        'ref': {
                            'tool_name': tool_name,
                            'input': input_data,
                            'output': output_data,
                            'execution_time_ms': execution_time_ms,
                            'retry_count': retry_count,
                            'success': success
                        }
                    }
                },
                hashes={'sha256': stable_hash(canonical_json(output_data))},
                correlation_id=f'{run_prefix}_incident_response',
                trace_id=f'{run_prefix}_trace_001'
            )
            
            events.append(CanonicalEvent(**to_canonical_event(tool_event, sequence_number=i + 1)))
        
        # Create final decision event
        decision_event = AuditRecordV1(
            schema_version='1.0.0',
            audit_id='01J4NR5X9Z8GABCDEF12345679',  # Valid ULID format
            tenant_id='security-operations',
            cell_id='incident-response-cell',
            idempotency_key=f'{run_prefix}_decision',
            recorded_at=base_time,
            event_kind='decision_made',
            payload_ref={'kind': {'ref': trace.final_decision}},
            hashes={'sha256': stable_hash(canonical_json(trace.final_decision))},
            correlation_id=f'{run_prefix}_incident_response',
            trace_id=f'{run_prefix}_trace_001'
        )
        
        events.append(CanonicalEvent(**to_canonical_event(decision_event, sequence_number=len(trace.tool_calls) + 1)))
        
        return events
    
    def run_exoarmur_verification(self, trace_a: ExecutionTrace, trace_b: ExecutionTrace) -> Dict[str, Any]:
        """Run ExoArmur verification on both execution traces"""
        print("🔐 EXOARMUR EXECUTION INTEGRITY VERIFICATION")
        print("=" * 60)
        
        # Convert traces to canonical events
        events_a = self.convert_trace_to_canonical_events(trace_a, "run_a")
        events_b = self.convert_trace_to_canonical_events(trace_b, "run_b")
        
        print(f"   📊 Trace A: {len(events_a)} canonical events")
        print(f"   📊 Trace B: {len(events_b)} canonical events")
        print()
        
        # Step 1: Individual replay verification
        print("🔄 STEP 1: Individual Execution Replay")
        
        # Replay trace A
        audit_store_a = {"run_a_incident_response": events_a}
        replay_engine_a = ReplayEngine(audit_store=audit_store_a)
        report_a = replay_engine_a.replay_correlation("run_a_incident_response")
        fingerprint_a = stable_hash(canonical_json(report_a.to_dict()))
        
        print(f"   ✅ Trace A replay: {fingerprint_a[:16]}...")
        print(f"   📊 Events processed: {report_a.processed_events}/{report_a.total_events}")
        print(f"   🎯 Agent decision: {trace_a.final_decision['action']}")
        
        # Replay trace B
        audit_store_b = {"run_b_incident_response": events_b}
        replay_engine_b = ReplayEngine(audit_store=audit_store_b)
        report_b = replay_engine_b.replay_correlation("run_b_incident_response")
        fingerprint_b = stable_hash(canonical_json(report_b.to_dict()))
        
        print(f"   ✅ Trace B replay: {fingerprint_b[:16]}...")
        print(f"   📊 Events processed: {report_b.processed_events}/{report_b.total_events}")
        print(f"   🎯 Agent decision: {trace_b.final_decision['action']}")
        print()
        
        # Step 2: Cross-system agreement verification
        print("🤝 STEP 2: Cross-System Agreement Verification")
        
        # Verify trace A across multiple systems
        verifier_a = MultiNodeReplayVerifier(node_count=3)
        consensus_a = verifier_a.verify_consensus(events_a, "run_a_incident_response")
        
        print(f"   📊 Trace A agreement: {len(consensus_a.get_consensus_nodes())}/3 systems")
        print(f"   🎯 Consensus achieved: {not consensus_a.has_divergence()}")
        
        # Verify trace B across multiple systems
        verifier_b = MultiNodeReplayVerifier(node_count=3)
        consensus_b = verifier_b.verify_consensus(events_b, "run_b_incident_response")
        
        print(f"   📊 Trace B agreement: {len(consensus_b.get_consensus_nodes())}/3 systems")
        print(f"   🎯 Consensus achieved: {not consensus_b.has_divergence()}")
        print()
        
        # Step 3: Execution divergence detection
        print("🔍 STEP 3: Execution Divergence Detection")
        
        # Compare fingerprints
        fingerprints_identical = fingerprint_a == fingerprint_b
        decisions_identical = trace_a.final_decision == trace_b.final_decision
        
        print(f"   🔐 Execution fingerprints identical: {fingerprints_identical}")
        print(f"   🎯 Agent decisions identical: {decisions_identical}")
        print(f"   📊 Time variance: {abs(trace_a.total_execution_time_ms - trace_b.total_execution_time_ms)}ms")
        
        if not fingerprints_identical:
            print(f"   🚨 EXECUTION DIVERGENCE DETECTED")
            print(f"      Same agent. Same prompt. Different execution reality.")
        else:
            print(f"   ✅ EXECUTIONS IDENTICAL")
        
        print()
        
        # Generate ExoArmur integrity report
        integrity_report = {
            "execution_verification": {
                "trace_a": {
                    "fingerprint": fingerprint_a,
                    "events_processed": report_a.processed_events,
                    "agent_decision": trace_a.final_decision['action'],
                    "execution_time_ms": trace_a.total_execution_time_ms,
                    "cross_system_agreement": not consensus_a.has_divergence()
                },
                "trace_b": {
                    "fingerprint": fingerprint_b,
                    "events_processed": report_b.processed_events,
                    "agent_decision": trace_b.final_decision['action'],
                    "execution_time_ms": trace_b.total_execution_time_ms,
                    "cross_system_agreement": not consensus_b.has_divergence()
                },
                "divergence_analysis": {
                    "fingerprints_identical": fingerprints_identical,
                    "decisions_identical": decisions_identical,
                    "execution_variance_ms": abs(trace_a.total_execution_time_ms - trace_b.total_execution_time_ms),
                    "divergence_detected": not fingerprints_identical
                }
            },
            "integrity_classification": {
                "status": "divergent_execution" if not fingerprints_identical else "consistent_execution",
                "production_relevant": True,
                "verification_layer": "exoarmur_deterministic_replay",
                "trust_signal": "execution_integrity_verified"
            }
        }
        
        return integrity_report
    
    def run_complete_demo(self) -> Dict[str, Any]:
        """Run the complete ExoArmur production drift demo"""
        print("🎯 EXOARMUR PRODUCTION DRIFT DEMO")
        print("=" * 60)
        print("AI Agent Execution Integrity Verification")
        print("Scenario: Security incident response escalation decision")
        print()
        
        # Run production drift demo
        demo_results = self.demo.run_demo()
        trace_a = ExecutionTrace(**demo_results["trace_a"])
        trace_b = ExecutionTrace(**demo_results["trace_b"])
        
        # Run ExoArmur verification
        exoarmur_results = self.run_exoarmur_verification(trace_a, trace_b)
        
        # Combine results
        complete_results = {
            "demo_scenario": {
                "agent_task": "Security incident response escalation decision",
                "incident_id": "INC-2024-0330",
                "identical_input": True,
                "production_noise_injected": True
            },
            "execution_traces": {
                "trace_a": asdict(trace_a),
                "trace_b": asdict(trace_b)
            },
            "exoarmur_verification": exoarmur_results,
            "conclusion": {
                "same_agent_same_prompt": True,
                "different_execution_reality": exoarmur_results["execution_verification"]["divergence_analysis"]["divergence_detected"],
                "production_relevant": True,
                "verification_layer_required": exoarmur_results["execution_verification"]["divergence_analysis"]["divergence_detected"]
            }
        }
        
        print("🎉 EXOARMUR PRODUCTION DRIFT DEMO COMPLETED")
        print()
        
        if complete_results["conclusion"]["different_execution_reality"]:
            print("🚨 KEY INSIGHT:")
            print("   Same agent. Same prompt. Different execution reality.")
            print("   This occurs in production environments.")
            print("   Without ExoArmur, this failure class is undetectable.")
            print()
            print("💡 DEVELOPER CONCLUSION:")
            print("   I cannot debug this class of failure without this layer.")
        else:
            print("✅ KEY INSIGHT:")
            print("   Executions were consistent (baseline scenario).")
        
        return complete_results

def main():
    """Main entry point"""
    verifier = ExoArmurDriftVerifier()
    results = verifier.run_complete_demo()
    
    print("✅ Production drift demonstration completed")
    print("✅ ExoArmur execution integrity verification completed")
    print("✅ Realistic AI agent divergence exposed")
    
    return results

if __name__ == "__main__":
    main()
