#!/usr/bin/env python3
"""
Minimal LangChain Integration - ExoArmur Governance Boundary

Demonstrates: External agent call → ExoArmur enforcement → decision → replay trace
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.replay.replay_engine import ReplayEngine
from exoarmur.replay.event_envelope import CanonicalEvent
from exoarmur.replay.canonical_utils import to_canonical_event
import json

# Fixed timestamp for deterministic output
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

class LangChainAgent:
    """Minimal agent that attempts file operations"""
    
    def __init__(self):
        self.agent_id = "langchain-agent-001"
    
    def attempt_file_delete(self, target_path: str) -> dict:
        """Agent attempts to delete a file"""
        return {
            "agent_id": self.agent_id,
            "action": "delete_file",
            "target": target_path,
            "timestamp": FIXED_TIMESTAMP.isoformat(),
            "rationale": "Clean up temporary files"
        }

class ExoArmurPolicy:
    """Policy that denies deletes outside authorized directory"""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        authorized_root = "/tmp/authorized"
        
        if intent.action_type == "delete_file":
            if not intent.target.startswith(authorized_root):
                return PolicyDecision(
                    verdict=PolicyVerdict.DENY,
                    rationale="Delete target outside authorized boundary",
                    evidence={"target": intent.target, "authorized_root": authorized_root},
                    confidence=1.0,
                    approval_required=False,
                    policy_version="1.0",
                    metadata={}
                )
        
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale="Action within authorized boundary",
            evidence={},
            confidence=1.0,
            approval_required=False,
            policy_version="1.0",
            metadata={}
        )

class MockExecutor:
    """Mock executor that would perform the action"""
    
    def execute(self, intent: ActionIntent):
        return {"status": "would_execute", "target": intent.target}

class AuditEmitter:
    """Collects audit events for replay"""
    
    def __init__(self):
        self.events = []
    
    def emit_audit_record(self, intent_id, event_type, outcome, details, recorded_at=None, tenant_id="test", cell_id="test"):
        event = {
            "event_id": f"event-{len(self.events)}",
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details,
            "recorded_at": (recorded_at or FIXED_TIMESTAMP).isoformat(),
            "tenant_id": tenant_id,
            "cell_id": cell_id
        }
        self.events.append(event)
        return event
    
    def get_events(self):
        return self.events

def main():
    print("LangChain + ExoArmur Integration Demo")
    print("=" * 50)
    
    # Step 1: External agent request
    agent = LangChainAgent()
    external_request = agent.attempt_file_delete("/tmp/unauthorized/secret.txt")
    
    print(f"External Request: {external_request['agent_id']} wants to {external_request['action']} {external_request['target']}")
    print(f"Rationale: {external_request['rationale']}")
    print()
    
    # Step 2: Convert to ExoArmur intent
    intent = ActionIntent(
        intent_id="langchain-integration-001",
        actor_id=external_request["agent_id"],
        actor_type="agent",
        action_type=external_request["action"],
        target=external_request["target"],
        parameters={"operation": "delete"},
        safety_context={"risk_level": "medium"},
        timestamp=FIXED_TIMESTAMP,
        tenant_id="integration-test",
        cell_id="langchain-demo"
    )
    
    # Step 3: ExoArmur governance decision
    policy = ExoArmurPolicy()
    
    # Use the same pattern as canonical demo - simple direct implementation
    class MockSafetyGate:
        def evaluate(self, intent):
            return {"verdict": "allow", "confidence": 1.0}
    
    class MockPDP:
        def __init__(self, policy):
            self.policy = policy
        
        def evaluate(self, intent):
            return self.policy.evaluate(intent)
    
    class MockExecutor:
        def execute(self, intent):
            return {"status": "would_execute", "target": intent.target}
    
    # Create minimal pipeline components
    from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import AuditEmitter, ProxyPipeline
    
    # Override the audit emitter to use our custom one
    class CustomAuditEmitter(AuditEmitter):
        def __init__(self):
            self.events = []
        
        def emit_audit_record(self, intent_id, event_type, outcome, details, recorded_at=None, tenant_id="test", cell_id="test"):
            event = {
                "event_id": f"event-{len(self.events)}",
                "intent_id": intent_id,
                "event_type": event_type,
                "outcome": outcome,
                "details": details,
                "recorded_at": (recorded_at or FIXED_TIMESTAMP).isoformat(),
                "tenant_id": tenant_id,
                "cell_id": cell_id
            }
            self.events.append(event)
            return event
        
        def get_events(self):
            return self.events
    
    custom_audit_emitter = CustomAuditEmitter()
    
    # Create pipeline with minimal components
    pipeline = ProxyPipeline(
        pdp=MockPDP(policy),
        safety_gate=MockSafetyGate(),
        executor=MockExecutor(),
        audit_emitter=custom_audit_emitter
    )
    
    # Step 4: Execute through governance boundary
    executor_result, trace = pipeline.execute_with_trace(intent)
    
    # Step 5: Extract governance decision
    governance_decision = "DENIED" if trace.final_status in ["POLICY_DENIED", "DENIED"] else "ALLOWED"
    
    print(f"ExoArmur Governance Decision: {governance_decision}")
    print(f"Final Status: {trace.final_status}")
    print()
    
    # Step 6: Replay verification
    audit_events = custom_audit_emitter.get_events()
    try:
        canonical_events = [CanonicalEvent(**to_canonical_event(event)) for event in audit_events if isinstance(event, dict) and 'event_id' in event]
        if canonical_events:
            replay_engine = ReplayEngine(audit_store={intent.intent_id: canonical_events})
            replay_report = replay_engine.replay_correlation(intent.intent_id)
            
            replay_result = getattr(replay_report.result, 'value', replay_report.result)
            replay_verdict = "PASS" if replay_result == "success" else "FAIL"
        else:
            replay_verdict = "FAIL"
    except Exception as e:
        replay_verdict = "FAIL"
    
    print(f"REPLAY_VERDICT={replay_verdict}")
    print()
    
    # Summary
    print("Integration Summary:")
    print(f"- External agent: {external_request['agent_id']}")
    print(f"- Requested action: {external_request['action']} {external_request['target']}")
    print(f"- ExoArmur decision: {governance_decision}")
    print(f"- Replay verification: {replay_verdict}")
    print(f"- Audit events: {len(audit_events)}")
    
    return {
        "external_agent": external_request['agent_id'],
        "governance_decision": governance_decision,
        "replay_verdict": replay_verdict,
        "audit_events_count": len(audit_events)
    }

if __name__ == "__main__":
    main()
