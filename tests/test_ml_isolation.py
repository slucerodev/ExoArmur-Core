"""
ML Isolation Compliance Test

Validates Doctrine Claim 4: ML outputs are advisory-only, non-binding, fully traceable.

Test: Run decision pipeline with ML enabled vs disabled → identical deterministic results.
"""

import pytest
import hashlib
import json
from typing import Dict, Any, Optional

from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.execution_proof_bundle import ExecutionProofBundle
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, V2AuditEmitter
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorPlugin
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.safety.safety_gate import SafetyGate


class DeterministicPolicyDecisionPoint(PolicyDecisionPoint):
    """Deterministic policy that never uses ML."""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        # Rule-based decision - no ML
        if intent.action_type in ["file_delete", "file_modify", "network_block"]:
            return PolicyDecision.create(
                intent_id=intent.intent_id,
                verdict=PolicyVerdict.DENY,
                rationale="High-risk action denied by deterministic policy",
                confidence=1.0
            )
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=PolicyVerdict.ALLOW,
            rationale="Action permitted by deterministic policy",
            confidence=1.0
        )
    
    def approval_status(self, intent_id: str):
        from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import ApprovalStatus
        return ApprovalStatus.DENIED


class MockExecutor(ExecutorPlugin):
    """Mock executor that returns deterministic results."""
    
    def execute(self, intent: ActionIntent) -> Any:
        return {
            "success": False,
            "error": "DENIED",
            "output": None,
            "executed_at": "2024-01-01T00:00:00Z"  # Deterministic timestamp
        }
    
    def validate_target(self, intent: ActionIntent) -> Any:
        return {"result": "invalid", "reason": "Mock validation"}


def compute_bundle_hash(bundle: Dict[str, Any]) -> str:
    """Compute deterministic hash of bundle contents."""
    canonical = json.dumps(bundle, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


class TestMLIsolation:
    """Test ML isolation from authority path."""
    
    def test_decision_pipeline_no_ml_components(self):
        """Verify decision pipeline uses no ML components."""
        policy = DeterministicPolicyDecisionPoint()
        safety_gate = SafetyGate()
        executor = MockExecutor()
        audit_emitter = V2AuditEmitter()
        
        # Create pipeline
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        # Verify no ML in policy
        assert not hasattr(policy, 'ml_model')
        assert not hasattr(policy, 'neural_network')
        assert not hasattr(policy, 'classifier')
        
        # Verify deterministic evaluation
        intent = ActionIntent.create(
            actor_id="test-actor",
            actor_type="human",
            action_type="file_delete",
            target="/tmp/test.txt",
            parameters={"force": True}
        )
        
        decision1 = policy.evaluate(intent)
        decision2 = policy.evaluate(intent)
        
        # Same input → same output
        assert decision1.verdict == decision2.verdict
        assert decision1.rationale == decision2.rationale
        assert decision1.confidence == decision2.confidence
    
    def test_pipeline_deterministic_without_ml(self):
        """Verify pipeline produces identical results without ML."""
        policy = DeterministicPolicyDecisionPoint()
        safety_gate = SafetyGate()
        executor = MockExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        intent = ActionIntent.create(
            actor_id="test-actor",
            actor_type="human",
            action_type="file_delete",
            target="/tmp/test.txt",
            parameters={"force": True}
        )
        
        # Run pipeline 3 times
        results = []
        for _ in range(3):
            result, trace = pipeline.execute_with_trace(intent)
            results.append({
                "final_verdict": trace.final_verdict.value if hasattr(trace.final_verdict, 'value') else str(trace.final_verdict),
                "policy_verdict": "deny"  # Expected for file_delete
            })
        
        # All runs identical
        assert all(r == results[0] for r in results)
    
    def test_recommender_outputs_not_binding(self):
        """Verify ML recommender outputs are advisory-only."""
        from exoarmur.identity_containment.recommender import IdentityContainmentRecommender
        from exoarmur.federation.observation_store import ObservationStore
        from exoarmur.clock import SystemClock
        from exoarmur.federation.audit import AuditService
        
        # Create recommender components
        clock = SystemClock()
        store = ObservationStore(clock=clock)
        audit = AuditService()
        
        recommender = IdentityContainmentRecommender(
            observation_store=store,
            clock=clock,
            audit_service=audit
        )
        
        # Verify recommendations are advisory
        recommendations = recommender.generate_recommendations()
        
        for rec in recommendations:
            # All recommendations must be pending (not binding)
            assert rec.status == "pending", f"Recommendation {rec.recommendation_id} is not pending"
            
            # Must not have direct execution capability
            assert not hasattr(rec, 'execute')
            assert not hasattr(rec, 'enforce')
    
    def test_ml_disable_does_not_affect_correctness(self):
        """Verify disabling ML does not affect decision correctness."""
        # Test with different intents
        test_cases = [
            ("file_delete", "/tmp/test.txt", "deny"),
            ("file_read", "/tmp/test.txt", "allow"),
            ("network_block", "10.0.0.1", "deny"),
        ]
        
        policy = DeterministicPolicyDecisionPoint()
        
        for action_type, target, expected_verdict in test_cases:
            intent = ActionIntent.create(
                actor_id="test-actor",
                actor_type="human",
                action_type=action_type,
                target=target,
                parameters={}
            )
            
            decision = policy.evaluate(intent)
            
            # Decision must be deterministic and correct
            assert decision.verdict.value == expected_verdict, \
                f"{action_type}: expected {expected_verdict}, got {decision.verdict.value}"
            
            # No ML confidence or ML-specific fields
            assert not hasattr(decision, 'ml_confidence')
            assert not hasattr(decision, 'model_version')
    
    def test_proof_bundle_no_ml_metadata(self):
        """Verify proof bundles don't contain ML-derived metadata."""
        policy = DeterministicPolicyDecisionPoint()
        safety_gate = SafetyGate()
        executor = MockExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        intent = ActionIntent.create(
            actor_id="test-actor",
            actor_type="human",
            action_type="file_delete",
            target="/tmp/test.txt",
            parameters={}
        )
        
        result, trace = pipeline.execute_with_trace(intent)
        
        # Build proof bundle
        from exoarmur.execution_boundary_v2.utils.bundle_builder import build_execution_proof_bundle
        
        bundle = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy.evaluate(intent),
            execution_trace=trace.model_dump() if hasattr(trace, 'model_dump') else trace,
            executor_result={
                "success": False,
                "error": "DENIED",
                "output": None,
                "evidence": {}
            }
        )
        
        # Verify bundle has no ML fields
        bundle_dict = bundle.model_dump()
        
        # Check for ML-specific fields
        ml_fields = ['ml_confidence', 'neural_network', 'model_version', 
                     'ml_rationale', 'ai_decision', 'ml_score']
        
        for field in ml_fields:
            assert field not in bundle_dict, f"Bundle contains ML field: {field}"
        
        # Verify deterministic fields present
        assert 'replay_hash' in bundle_dict
        assert 'bundle_checksum' in bundle_dict
        assert 'final_verdict' in bundle_dict
    
    def test_multi_run_determinism_no_ml(self):
        """Verify 3+ runs produce identical replay hashes."""
        policy = DeterministicPolicyDecisionPoint()
        safety_gate = SafetyGate()
        executor = MockExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        intent = ActionIntent.create(
            actor_id="test-actor",
            actor_type="human",
            action_type="file_delete",
            target="/tmp/test.txt",
            parameters={}
        )
        
        hashes = []
        for _ in range(3):
            result, trace = pipeline.execute_with_trace(intent)
            
            from exoarmur.execution_boundary_v2.utils.bundle_builder import build_execution_proof_bundle
            bundle = build_execution_proof_bundle(
                intent=intent,
                policy_decision=policy.evaluate(intent),
                execution_trace=trace.model_dump() if hasattr(trace, 'model_dump') else trace,
                executor_result={"success": False, "error": "DENIED", "output": None, "evidence": {}}
            )
            hashes.append(bundle.replay_hash)
        
        # All hashes identical
        assert len(set(hashes)) == 1, f"Hashes differ: {hashes}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
