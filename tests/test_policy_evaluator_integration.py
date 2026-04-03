"""
Regression tests for PolicyEvaluator integration
Ensures behavior preservation when integrating PolicyEvaluator into SafetyGate
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from exoarmur.safety.policy_evaluator import PolicyEvaluator
from exoarmur.safety.safety_gate import PolicyState
from spec.contracts.models_v1 import ExecutionIntentV1


class TestPolicyEvaluatorIntegration:
    """Test PolicyEvaluator integration preserves existing behavior"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.policy_evaluator = PolicyEvaluator()
        
        # Test execution intent
        self.test_intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="idemp-123",
            subject={"subject_type": "host", "subject_id": "host-123"},
            intent_type="isolate_host",
            action_class="A1_soft_containment",
            requested_at=datetime.now(),
            parameters={"duration": 3600},
            policy_context={"bundle_hash_sha256": "abc123"},
            safety_context={"safety_verdict": "allow"},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
    
    def test_policy_evaluator_preserves_hardcoded_behavior(self):
        """Test that PolicyEvaluator produces identical results to hardcoded values"""
        # Test with valid intent
        policy_state = self.policy_evaluator.evaluate_policy(
            intent=self.test_intent,
            tenant_id="tenant-acme",
            cell_id="cell-okc-01"
        )
        
        # Should match exactly the hardcoded values from main.py before integration
        expected_policy_state = PolicyState(
            policy_verified=True,  # From main.py line 465
            kill_switch_global=False,  # From main.py line 466
            kill_switch_tenant=False,  # From main.py line 467
            required_approval="none"  # From main.py line 468
        )
        
        assert policy_state.policy_verified == expected_policy_state.policy_verified
        assert policy_state.kill_switch_global == expected_policy_state.kill_switch_global
        assert policy_state.kill_switch_tenant == expected_policy_state.kill_switch_tenant
        assert policy_state.required_approval == expected_policy_state.required_approval
    
    def test_policy_evaluator_with_none_intent(self):
        """Test PolicyEvaluator with None intent (pre-execution case)"""
        policy_state = self.policy_evaluator.evaluate_policy(
            intent=None,
            tenant_id="tenant-acme",
            cell_id="cell-okc-01"
        )
        
        # Should still produce the same safe fallback values
        expected_policy_state = PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        assert policy_state.policy_verified == expected_policy_state.policy_verified
        assert policy_state.kill_switch_global == expected_policy_state.kill_switch_global
        assert policy_state.kill_switch_tenant == expected_policy_state.kill_switch_tenant
        assert policy_state.required_approval == expected_policy_state.required_approval
    
    def test_policy_evaluator_safe_fallback_on_exception(self):
        """Test that PolicyEvaluator falls back safely on any exception"""
        # Mock the internal evaluation to raise an exception
        with patch.object(self.policy_evaluator, '_evaluate_policy_internal', side_effect=Exception("Test exception")):
            policy_state = self.policy_evaluator.evaluate_policy(
                intent=self.test_intent,
                tenant_id="tenant-acme",
                cell_id="cell-okc-01"
            )
            
            # Should still produce the safe fallback values
            expected_policy_state = PolicyState(
                policy_verified=True,
                kill_switch_global=False,
                kill_switch_tenant=False,
                required_approval="none"
            )
            
            assert policy_state.policy_verified == expected_policy_state.policy_verified
            assert policy_state.kill_switch_global == expected_policy_state.kill_switch_global
            assert policy_state.kill_switch_tenant == expected_policy_state.kill_switch_tenant
            assert policy_state.required_approval == expected_policy_state.required_approval
    
    def test_policy_evaluator_deterministic_output(self):
        """Test that PolicyEvaluator produces deterministic output across multiple calls"""
        results = []
        
        # Call evaluator multiple times with same inputs
        for _ in range(10):
            policy_state = self.policy_evaluator.evaluate_policy(
                intent=self.test_intent,
                tenant_id="tenant-acme",
                cell_id="cell-okc-01"
            )
            results.append(policy_state)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.policy_verified == first_result.policy_verified
            assert result.kill_switch_global == first_result.kill_switch_global
            assert result.kill_switch_tenant == first_result.kill_switch_tenant
            assert result.required_approval == first_result.required_approval
    
    def test_policy_evaluator_different_tenant_cell_contexts(self):
        """Test PolicyEvaluator with different tenant/cell contexts"""
        contexts = [
            ("tenant-1", "cell-1"),
            ("tenant-2", "cell-2"),
            ("tenant-acme", "cell-okc-01"),
            ("", ""),  # Empty context
        ]
        
        for tenant_id, cell_id in contexts:
            policy_state = self.policy_evaluator.evaluate_policy(
                intent=self.test_intent,
                tenant_id=tenant_id,
                cell_id=cell_id
            )
            
            # Should always produce the same safe fallback values regardless of context
            # (until actual policy logic is implemented)
            assert policy_state.policy_verified == True
            assert policy_state.kill_switch_global == False
            assert policy_state.kill_switch_tenant == False
            assert policy_state.required_approval == "none"


class TestPolicyEvaluatorSafetyGateIntegration:
    """Test integration between PolicyEvaluator and SafetyGate preserves verdicts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from exoarmur.safety.safety_gate import SafetyGate
        from exoarmur.collective_confidence.aggregator import CollectiveState
        from exoarmur.safety.safety_gate import TrustState, EnvironmentState
        from exoarmur.spec.contracts.models_v1 import LocalDecisionV1
        
        self.safety_gate = SafetyGate()
        self.policy_evaluator = PolicyEvaluator()
        
        # Test local decision
        self.local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="suspicious",
            severity="medium",
            confidence=0.85,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        self.collective_state = CollectiveState(
            aggregate_score=0.85,
            quorum_count=2,
            conflict_detected=False
        )
        
        self.trust_state = TrustState(emitter_trust_score=0.85)
        self.environment_state = EnvironmentState(degraded_mode=False)
    
    def test_safety_gate_verdicts_unchanged_with_policy_evaluator(self):
        """Test that SafetyGate verdicts are identical when using PolicyEvaluator"""
        # Get policy state from evaluator (new way)
        policy_state_evaluator = self.policy_evaluator.evaluate_policy(
            intent=None,
            tenant_id="tenant-acme",
            cell_id="cell-okc-01"
        )
        
        # Create policy state with hardcoded values (old way)
        from exoarmur.safety.safety_gate import PolicyState
        policy_state_hardcoded = PolicyState(
            policy_verified=True,  # TODO: implement actual policy verification
            kill_switch_global=False,  # TODO: implement actual kill switch checks
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        # Evaluate safety with both approaches
        verdict_evaluator = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=policy_state_evaluator,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        verdict_hardcoded = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=policy_state_hardcoded,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        # Verdicts should be identical
        assert verdict_evaluator.verdict == verdict_hardcoded.verdict
        assert verdict_evaluator.rationale == verdict_hardcoded.rationale
        assert verdict_evaluator.rule_ids == verdict_hardcoded.rule_ids
    
    def test_safety_gate_verdict_determinism_with_evaluator(self):
        """Test that SafetyGate verdicts remain deterministic with PolicyEvaluator"""
        verdicts = []
        
        # Generate multiple verdicts using PolicyEvaluator
        for _ in range(10):
            policy_state = self.policy_evaluator.evaluate_policy(
                intent=None,
                tenant_id="tenant-acme",
                cell_id="cell-okc-01"
            )
            
            verdict = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=policy_state,
                trust_state=self.trust_state,
                environment_state=self.environment_state
            )
            verdicts.append(verdict)
        
        # All verdicts should be identical
        first_verdict = verdicts[0]
        for verdict in verdicts[1:]:
            assert verdict.verdict == first_verdict.verdict
            assert verdict.rationale == first_verdict.rationale
            assert verdict.rule_ids == first_verdict.rule_ids
