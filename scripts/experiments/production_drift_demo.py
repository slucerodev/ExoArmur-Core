#!/usr/bin/env python3
"""
Production Agent Drift Demo Harness

This script creates realistic production divergence in AI agent pipelines
by introducing subtle runtime noise: API latency variance, cache differences,
partial responses, retry behavior, and execution ordering drift.

GOAL: Show "Same agent. Same prompt. Different execution reality."
"""

import os
import sys
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.replay.event_envelope import CanonicalEvent
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.replay.canonical_utils import to_canonical_event

# Ensure deterministic environment for baseline
os.environ['PYTHONHASHSEED'] = '0'

class DivergenceType(Enum):
    """Classification of execution divergence types"""
    STEP_MISMATCH = "step_mismatch"
    ORDERING_DRIFT = "ordering_drift"
    SEMANTIC_DECISION_DRIFT = "semantic_decision_drift"
    TOOL_RESPONSE_INCONSISTENCY = "tool_response_inconsistency"

@dataclass
class ToolCall:
    """Represents a tool call in the agent pipeline"""
    tool_name: str
    call_id: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    execution_time_ms: int
    timestamp: datetime
    success: bool
    retry_count: int = 0

@dataclass
class ExecutionTrace:
    """Complete execution trace for an agent pipeline run"""
    run_id: str
    agent_task: str
    incident_report: Dict[str, Any]
    tool_calls: List[ToolCall]
    final_decision: Dict[str, Any]
    total_execution_time_ms: int
    divergence_points: List[str]

class ProductionNoiseInjector:
    """Injects realistic production noise into agent execution"""
    
    def __init__(self, noise_profile: str = "subtle"):
        self.noise_profile = noise_profile
        self.random_seed = 42  # For reproducible noise patterns
        
    def inject_api_latency_variance(self, base_latency_ms: int) -> int:
        """Inject realistic API latency variance"""
        if self.noise_profile == "baseline":
            return base_latency_ms
        
        # Production-like latency variance: ±30% with occasional spikes
        variance_factor = random.uniform(0.7, 1.3)
        if random.random() < 0.1:  # 10% chance of latency spike
            variance_factor *= random.uniform(1.5, 2.0)
        
        return int(base_latency_ms * variance_factor)
    
    def inject_partial_response(self, full_response: Dict[str, Any]) -> Dict[str, Any]:
        """Inject partial tool response (production reality)"""
        if self.noise_profile == "baseline" or random.random() > 0.15:  # 15% chance
            return full_response
        
        # Return partial response with missing fields
        partial_response = full_response.copy()
        if "events" in partial_response and isinstance(partial_response["events"], list):
            # Remove some events from the middle
            events = partial_response["events"]
            if len(events) > 3:
                partial_response["events"] = events[:1] + events[-2:]
                partial_response["partial"] = True
                partial_response["missing_count"] = len(events) - len(partial_response["events"])
        
        return partial_response
    
    def inject_cache_behavior(self, cache_hit_probability: float) -> bool:
        """Inject realistic cache hit/miss behavior"""
        if self.noise_profile == "baseline":
            return True  # Always cache hit for baseline
        
        # Production-like cache behavior with variance
        actual_probability = cache_hit_probability * random.uniform(0.8, 1.2)
        return random.random() < actual_probability
    
    def inject_retry_behavior(self, should_fail: bool = False) -> int:
        """Inject realistic retry behavior"""
        if self.noise_profile == "baseline" or not should_fail:
            return 0  # No retries for baseline
        
        # Production retry logic: 1-2 retries for transient failures
        if random.random() < 0.05:  # 5% chance of transient failure
            return random.randint(1, 2)
        
        return 0
    
    def inject_execution_ordering_drift(self, tool_sequence: List[str]) -> List[str]:
        """Inject subtle execution ordering drift"""
        if self.noise_profile == "baseline" or len(tool_sequence) <= 2:
            return tool_sequence
        
        # Production-like ordering drift: swap adjacent tools occasionally
        if random.random() < 0.1:  # 10% chance of ordering drift
            sequence = tool_sequence.copy()
            for i in range(len(sequence) - 1):
                if random.random() < 0.3:  # 30% chance per adjacent pair
                    sequence[i], sequence[i + 1] = sequence[i + 1], sequence[i]
            return sequence
        
        return tool_sequence

class SecurityIncidentAgent:
    """Simulates a security incident response AI agent"""
    
    def __init__(self, noise_injector: ProductionNoiseInjector):
        self.noise_injector = noise_injector
        self.cache = {}  # Simple cache simulation
        
    def process_incident(self, incident_report: Dict[str, Any], run_id: str) -> ExecutionTrace:
        """Process a security incident with realistic production behavior"""
        start_time = datetime.now(timezone.utc)
        tool_calls = []
        divergence_points = []
        
        # Step 1: Ingest incident report (always consistent)
        ingestion_time = self.noise_injector.inject_api_latency_variance(50)
        time.sleep(ingestion_time / 1000.0)  # Simulate processing time
        
        tool_calls.append(ToolCall(
            tool_name="incident_ingestion",
            call_id=f"{run_id}_ingest_001",
            input_data={"incident_id": incident_report["id"]},
            output_data={"status": "ingested", "timestamp": datetime.now(timezone.utc).isoformat()},
            execution_time_ms=ingestion_time,
            timestamp=datetime.now(timezone.utc),
            success=True
        ))
        
        # Step 2: Query logs tool (with cache behavior)
        cache_key = f"logs_{incident_report['id']}"
        cache_hit = self.noise_injector.inject_cache_behavior(0.7)  # 70% base cache hit
        
        logs_query_time = self.noise_injector.inject_api_latency_variance(200 if cache_hit else 800)
        time.sleep(logs_query_time / 1000.0)
        
        if cache_hit and cache_key in self.cache:
            logs_data = self.cache[cache_key]
            logs_data["cache_hit"] = True
        else:
            # Simulate logs API call
            logs_data = {
                "events": [
                    {"timestamp": "2024-03-30T19:00:00Z", "event": "login_failure", "user": "admin"},
                    {"timestamp": "2024-03-30T19:01:00Z", "event": "privilege_escalation", "user": "admin"},
                    {"timestamp": "2024-03-30T19:02:00Z", "event": "data_access", "user": "admin"}
                ],
                "total_events": 3,
                "cache_hit": False
            }
            self.cache[cache_key] = logs_data
        
        # Inject partial response possibility
        logs_data = self.noise_injector.inject_partial_response(logs_data)
        if "partial" in logs_data:
            divergence_points.append("logs_partial_response")
        
        tool_calls.append(ToolCall(
            tool_name="logs_query",
            call_id=f"{run_id}_logs_001",
            input_data={"incident_id": incident_report["id"], "time_range": "1h"},
            output_data=logs_data,
            execution_time_ms=logs_query_time,
            timestamp=datetime.now(timezone.utc),
            success=True
        ))
        
        # Step 3: Call enrichment API (with retry behavior)
        should_retry = self.noise_injector.noise_profile != "baseline"
        retry_count = self.noise_injector.inject_retry_behavior(should_retry)
        
        enrichment_time = self.noise_injector.inject_api_latency_variance(300)
        if retry_count > 0:
            enrichment_time += retry_count * 500  # Retry delay
            divergence_points.append("enrichment_retry")
        
        time.sleep(enrichment_time / 1000.0)
        
        enrichment_data = {
            "threat_score": 0.85,
            "confidence": 0.92,
            "indicators": ["privilege_escalation", "unusual_access_pattern"],
            "retry_count": retry_count
        }
        
        tool_calls.append(ToolCall(
            tool_name="threat_enrichment",
            call_id=f"{run_id}_enrich_001",
            input_data={"incident_id": incident_report["id"]},
            output_data=enrichment_data,
            execution_time_ms=enrichment_time,
            timestamp=datetime.now(timezone.utc),
            success=True,
            retry_count=retry_count
        ))
        
        # Step 4: Evaluate severity (deterministic but input-dependent)
        severity_time = self.noise_injector.inject_api_latency_variance(100)
        time.sleep(severity_time / 1000.0)
        
        # Severity evaluation depends on enriched data
        base_score = enrichment_data["threat_score"]
        if logs_data.get("total_events", 0) > 2:
            base_score += 0.1
        
        severity_level = "high" if base_score > 0.8 else "medium" if base_score > 0.6 else "low"
        
        tool_calls.append(ToolCall(
            tool_name="severity_evaluation",
            call_id=f"{run_id}_severity_001",
            input_data={"threat_score": base_score, "event_count": logs_data.get("total_events", 0)},
            output_data={"severity": severity_level, "score": base_score},
            execution_time_ms=severity_time,
            timestamp=datetime.now(timezone.utc),
            success=True
        ))
        
        # Step 5: Decide escalation action (semantic decision point)
        decision_time = self.noise_injector.inject_api_latency_variance(150)
        time.sleep(decision_time / 1000.0)
        
        # Decision logic with subtle divergence potential
        if severity_level == "high" and enrichment_data["confidence"] > 0.9:
            action = "escalate_to_human"
            reason = "High confidence threat with elevated severity"
        elif severity_level == "high":
            action = "auto_contain"
            reason = "High severity but confidence threshold not met"
        else:
            action = "monitor"
            reason = "Severity below escalation threshold"
        
        # Inject subtle decision drift based on execution path
        if retry_count > 0 and severity_level == "high":
            action = "escalate_to_human"  # Retry bias toward escalation
            divergence_points.append("decision_drift_from_retry")
        
        final_decision = {
            "action": action,
            "reason": reason,
            "severity": severity_level,
            "confidence": enrichment_data["confidence"],
            "execution_path": f"retry_{retry_count}" if retry_count > 0 else "normal"
        }
        
        tool_calls.append(ToolCall(
            tool_name="escalation_decision",
            call_id=f"{run_id}_decision_001",
            input_data={"severity": severity_level, "confidence": enrichment_data["confidence"]},
            output_data=final_decision,
            execution_time_ms=decision_time,
            timestamp=datetime.now(timezone.utc),
            success=True
        ))
        
        total_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return ExecutionTrace(
            run_id=run_id,
            agent_task="Incident response escalation decision",
            incident_report=incident_report,
            tool_calls=tool_calls,
            final_decision=final_decision,
            total_execution_time_ms=int(total_time),
            divergence_points=divergence_points
        )

class ExecutionTraceComparator:
    """Compares two execution traces and classifies divergence"""
    
    def compare_traces(self, trace_a: ExecutionTrace, trace_b: ExecutionTrace) -> Dict[str, Any]:
        """Compare two execution traces and identify divergence"""
        divergence_analysis = {
            "summary": {
                "identical_executions": False,
                "total_divergence_points": 0,
                "divergence_types": []
            },
            "step_mismatches": [],
            "ordering_drift": [],
            "semantic_decision_drift": [],
            "tool_response_inconsistency": [],
            "execution_metrics": {
                "run_a_time_ms": trace_a.total_execution_time_ms,
                "run_b_time_ms": trace_b.total_execution_time_ms,
                "time_variance_percent": abs(trace_a.total_execution_time_ms - trace_b.total_execution_time_ms) / max(trace_a.total_execution_time_ms, trace_b.total_execution_time_ms) * 100
            }
        }
        
        # Compare tool calls
        tool_calls_a = {tc.call_id: tc for tc in trace_a.tool_calls}
        tool_calls_b = {tc.call_id: tc for tc in trace_b.tool_calls}
        
        all_call_ids = set(tool_calls_a.keys()) | set(tool_calls_b.keys())
        
        for call_id in all_call_ids:
            if call_id not in tool_calls_a:
                divergence_analysis["step_mismatches"].append({
                    "type": "missing_in_a",
                    "call_id": call_id,
                    "tool_name": tool_calls_b[call_id].tool_name
                })
                divergence_analysis["summary"]["divergence_types"].append(DivergenceType.STEP_MISMATCH.value)
            elif call_id not in tool_calls_b:
                divergence_analysis["step_mismatches"].append({
                    "type": "missing_in_b", 
                    "call_id": call_id,
                    "tool_name": tool_calls_a[call_id].tool_name
                })
                divergence_analysis["summary"]["divergence_types"].append(DivergenceType.STEP_MISMATCH.value)
            else:
                tc_a = tool_calls_a[call_id]
                tc_b = tool_calls_b[call_id]
                
                # Compare execution times
                time_diff = abs(tc_a.execution_time_ms - tc_b.execution_time_ms)
                if time_diff > 100:  # More than 100ms difference
                    divergence_analysis["tool_response_inconsistency"].append({
                        "call_id": call_id,
                        "tool_name": tc_a.tool_name,
                        "time_a_ms": tc_a.execution_time_ms,
                        "time_b_ms": tc_b.execution_time_ms,
                        "variance_ms": time_diff
                    })
                    divergence_analysis["summary"]["divergence_types"].append(DivergenceType.TOOL_RESPONSE_INCONSISTENCY.value)
                
                # Compare outputs
                if tc_a.output_data != tc_b.output_data:
                    divergence_analysis["tool_response_inconsistency"].append({
                        "call_id": call_id,
                        "tool_name": tc_a.tool_name,
                        "type": "output_mismatch",
                        "output_a_differs": True,
                        "output_b_differs": True
                    })
                    divergence_analysis["summary"]["divergence_types"].append(DivergenceType.TOOL_RESPONSE_INCONSISTENCY.value)
                
                # Compare retry counts
                if tc_a.retry_count != tc_b.retry_count:
                    divergence_analysis["tool_response_inconsistency"].append({
                        "call_id": call_id,
                        "tool_name": tc_a.tool_name,
                        "type": "retry_mismatch",
                        "retry_a": tc_a.retry_count,
                        "retry_b": tc_b.retry_count
                    })
                    divergence_analysis["summary"]["divergence_types"].append(DivergenceType.TOOL_RESPONSE_INCONSISTENCY.value)
        
        # Compare final decisions
        if trace_a.final_decision != trace_b.final_decision:
            divergence_analysis["semantic_decision_drift"].append({
                "decision_a": trace_a.final_decision,
                "decision_b": trace_b.final_decision,
                "impact": "different_escalation_action"
            })
            divergence_analysis["summary"]["divergence_types"].append(DivergenceType.SEMANTIC_DECISION_DRIFT.value)
        
        # Compare execution ordering
        ordering_a = [tc.tool_name for tc in trace_a.tool_calls]
        ordering_b = [tc.tool_name for tc in trace_b.tool_calls]
        
        if ordering_a != ordering_b:
            divergence_analysis["ordering_drift"].append({
                "ordering_a": ordering_a,
                "ordering_b": ordering_b,
                "first_difference": self._find_first_ordering_diff(ordering_a, ordering_b)
            })
            divergence_analysis["summary"]["divergence_types"].append(DivergenceType.ORDERING_DRIFT.value)
        
        # Calculate summary
        divergence_analysis["summary"]["total_divergence_points"] = (
            len(divergence_analysis["step_mismatches"]) +
            len(divergence_analysis["ordering_drift"]) +
            len(divergence_analysis["semantic_decision_drift"]) +
            len(divergence_analysis["tool_response_inconsistency"])
        )
        
        divergence_analysis["summary"]["identical_executions"] = divergence_analysis["summary"]["total_divergence_points"] == 0
        
        return divergence_analysis
    
    def _find_first_ordering_diff(self, ordering_a: List[str], ordering_b: List[str]) -> int:
        """Find the first position where orderings differ"""
        for i, (a, b) in enumerate(zip(ordering_a, ordering_b)):
            if a != b:
                return i
        return -1

class ProductionDriftDemo:
    """Main demo harness for production agent drift demonstration"""
    
    def __init__(self):
        self.incident_report = {
            "id": "INC-2024-0330",
            "type": "security_incident",
            "severity": "unknown",
            "description": "Potential privilege escalation detected",
            "timestamp": "2024-03-30T19:00:00Z",
            "source": "security_monitoring"
        }
    
    def run_demo(self) -> Dict[str, Any]:
        """Run the complete production drift demo"""
        print("🎯 PRODUCTION AGENT DRIFT DEMO")
        print("=" * 60)
        print("Scenario: Security incident response escalation decision")
        print("Same agent. Same prompt. Different execution reality.")
        print()
        
        # Run A: Baseline execution
        print("🔄 RUNNING EXECUTION A (Baseline)")
        baseline_noise = ProductionNoiseInjector("baseline")
        agent_a = SecurityIncidentAgent(baseline_noise)
        trace_a = agent_a.process_incident(self.incident_report, "run_A")
        
        print(f"   ✅ Execution A completed")
        print(f"   📊 Total time: {trace_a.total_execution_time_ms}ms")
        print(f"   🎯 Final decision: {trace_a.final_decision['action']}")
        print()
        
        # Run B: Production noise execution
        print("🔄 RUNNING EXECUTION B (Production Noise)")
        production_noise = ProductionNoiseInjector("subtle")
        random.seed(42)  # Reproducible noise pattern
        agent_b = SecurityIncidentAgent(production_noise)
        trace_b = agent_b.process_incident(self.incident_report, "run_B")
        
        print(f"   ✅ Execution B completed")
        print(f"   📊 Total time: {trace_b.total_execution_time_ms}ms")
        print(f"   🎯 Final decision: {trace_b.final_decision['action']}")
        print()
        
        # Compare traces
        print("🔍 COMPARING EXECUTION TRACES")
        comparator = ExecutionTraceComparator()
        divergence_analysis = comparator.compare_traces(trace_a, trace_b)
        
        print(f"   📊 Divergence points: {divergence_analysis['summary']['total_divergence_points']}")
        print(f"   📊 Time variance: {divergence_analysis['execution_metrics']['time_variance_percent']:.1f}%")
        print(f"   📊 Identical executions: {divergence_analysis['summary']['identical_executions']}")
        print()
        
        # Display detailed divergence
        self._display_divergence_details(divergence_analysis, trace_a, trace_b)
        
        return {
            "trace_a": asdict(trace_a),
            "trace_b": asdict(trace_b),
            "divergence_analysis": divergence_analysis,
            "demo_summary": {
                "scenario": "Security incident response escalation",
                "identical_input": True,
                "divergent_execution": not divergence_analysis["summary"]["identical_executions"],
                "production_relevant": True
            }
        }
    
    def _display_divergence_details(self, analysis: Dict[str, Any], trace_a: ExecutionTrace, trace_b: ExecutionTrace):
        """Display detailed divergence analysis"""
        print("📈 DETAILED DIVERGENCE ANALYSIS")
        print("-" * 40)
        
        # Tool response inconsistencies
        if analysis["tool_response_inconsistency"]:
            print("🔧 TOOL RESPONSE INCONSISTENCIES:")
            for inconsistency in analysis["tool_response_inconsistency"]:
                if "time_a_ms" in inconsistency:
                    print(f"   {inconsistency['tool_name']} ({inconsistency['call_id']})")
                    print(f"     Time A: {inconsistency['time_a_ms']}ms")
                    print(f"     Time B: {inconsistency['time_b_ms']}ms")
                    print(f"     Variance: {inconsistency['variance_ms']}ms")
                elif "retry_a" in inconsistency:
                    print(f"   {inconsistency['tool_name']} ({inconsistency['call_id']})")
                    print(f"     Retries A: {inconsistency['retry_a']}")
                    print(f"     Retries B: {inconsistency['retry_b']}")
                elif "output_mismatch" in inconsistency:
                    print(f"   {inconsistency['tool_name']} ({inconsistency['call_id']})")
                    print(f"     Output differs between executions")
            print()
        
        # Semantic decision drift
        if analysis["semantic_decision_drift"]:
            print("🧠 SEMANTIC DECISION DRIFT:")
            for drift in analysis["semantic_decision_drift"]:
                print(f"   Decision A: {drift['decision_a']['action']}")
                print(f"   Decision B: {drift['decision_b']['action']}")
                print(f"   Impact: {drift['impact']}")
            print()
        
        # Execution metrics
        metrics = analysis["execution_metrics"]
        print("⏱️  EXECUTION METRICS:")
        print(f"   Run A time: {metrics['run_a_time_ms']}ms")
        print(f"   Run B time: {metrics['run_b_time_ms']}ms")
        print(f"   Time variance: {metrics['time_variance_percent']:.1f}%")
        print()
        
        # Final conclusion
        if not analysis["summary"]["identical_executions"]:
            print("🎯 CONCLUSION:")
            print("   Same agent. Same prompt. Different execution reality.")
            print("   This divergence occurs in production environments.")
            print("   Without execution trace verification, this class of failure is undetectable.")
        else:
            print("🎯 CONCLUSION:")
            print("   Executions were identical (baseline scenario).")

def main():
    """Main entry point"""
    demo = ProductionDriftDemo()
    results = demo.run_demo()
    
    print("🎉 PRODUCTION DRIFT DEMO COMPLETED")
    print("✅ Realistic execution divergence demonstrated")
    print("✅ Production-relevant noise patterns injected")
    print("✅ Execution trace comparison completed")
    
    return results

if __name__ == "__main__":
    main()
