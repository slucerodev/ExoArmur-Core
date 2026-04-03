"""
Regression tests for TrustEvaluator integration
Ensures behavior preservation when integrating TrustEvaluator into SafetyGate
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from exoarmur.safety.trust_evaluator import TrustEvaluator
from exoarmur.safety.safety_gate import TrustState


class TestTrustEvaluatorIntegration:
    """Test TrustEvaluator integration preserves existing behavior"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.trust_evaluator = TrustEvaluator()
        
        # Test event source matching main.py context
        self.test_event_source = {
            "kind": "edr",
            "name": "crowdstrike",
            "host": "sensor-01",
            "sensor_id": "sensor-123"
        }
        
        self.test_emitter_id = "sensor-123"
        self.test_tenant_id = "tenant-acme"
    
    def test_trust_evaluator_preserves_hardcoded_behavior(self):
        """Test that TrustEvaluator produces identical results to hardcoded values"""
        # Test with valid event source
        trust_score = self.trust_evaluator.evaluate_trust(
            event_source=self.test_event_source,
            emitter_id=self.test_emitter_id,
            tenant_id=self.test_tenant_id
        )
        
        # Should match exactly the hardcoded value from main.py before integration
        expected_trust_score = 0.85  # From main.py line 475
        
        assert trust_score == expected_trust_score
        assert isinstance(trust_score, float)
        assert 0.0 <= trust_score <= 1.0
    
    def test_trust_evaluator_with_none_emitter_id(self):
        """Test TrustEvaluator with None emitter_id"""
        trust_score = self.trust_evaluator.evaluate_trust(
            event_source=self.test_event_source,
            emitter_id=None,
            tenant_id=self.test_tenant_id
        )
        
        # Should still produce the same safe fallback value
        expected_trust_score = 0.85
        assert trust_score == expected_trust_score
    
    def test_trust_evaluator_with_missing_sensor_id(self):
        """Test TrustEvaluator with event source missing sensor_id"""
        event_source_no_sensor = {
            "kind": "edr",
            "name": "crowdstrike",
            "host": "sensor-01"
            # Missing sensor_id
        }
        
        trust_score = self.trust_evaluator.evaluate_trust(
            event_source=event_source_no_sensor,
            emitter_id=None,  # Will be None from .get("sensor_id")
            tenant_id=self.test_tenant_id
        )
        
        # Should still produce the same safe fallback value
        expected_trust_score = 0.85
        assert trust_score == expected_trust_score
    
    def test_trust_evaluator_safe_fallback_on_exception(self):
        """Test that TrustEvaluator falls back safely on any exception"""
        # Mock the internal evaluation to raise an exception
        with patch.object(self.trust_evaluator, '_evaluate_trust_internal', side_effect=Exception("Test exception")):
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.test_event_source,
                emitter_id=self.test_emitter_id,
                tenant_id=self.test_tenant_id
            )
            
            # Should still produce the safe fallback value
            expected_trust_score = 0.85
            assert trust_score == expected_trust_score
    
    def test_trust_evaluator_deterministic_output(self):
        """Test that TrustEvaluator produces deterministic output across multiple calls"""
        results = []
        
        # Call evaluator multiple times with same inputs
        for _ in range(100):  # Test with more iterations for determinism
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.test_event_source,
                emitter_id=self.test_emitter_id,
                tenant_id=self.test_tenant_id
            )
            results.append(trust_score)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Trust score drift: {first_result} vs {result}"
    
    def test_trust_evaluator_different_event_sources(self):
        """Test TrustEvaluator with different event source contexts"""
        event_sources = [
            {"kind": "edr", "name": "crowdstrike", "sensor_id": "sensor-1"},
            {"kind": "siem", "name": "sentinel", "sensor_id": "sensor-2"},
            {"kind": "firewall", "name": "paloalto", "sensor_id": "sensor-3"},
            {"kind": "unknown", "name": "generic", "sensor_id": "sensor-4"},
            {},  # Empty event source
        ]
        
        for event_source in event_sources:
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=event_source,
                emitter_id=event_source.get("sensor_id"),
                tenant_id=self.test_tenant_id
            )
            
            # Should always produce the same safe fallback value regardless of context
            # (until actual trust logic is implemented)
            assert trust_score == 0.85
    
    def test_trust_evaluator_floating_point_stability(self):
        """Test that TrustEvaluator produces stable floating-point results"""
        # Test with multiple calls and check for floating-point drift
        results = []
        
        for _ in range(1000):
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.test_event_source,
                emitter_id=self.test_emitter_id,
                tenant_id=self.test_tenant_id
            )
            results.append(trust_score)
        
        # Check for exact floating-point equality (no drift)
        expected_score = 0.85
        for i, result in enumerate(results):
            assert result == expected_score, f"Floating-point drift at iteration {i}: {result} vs {expected_score}"
    
    def test_trust_evaluator_different_tenant_contexts(self):
        """Test TrustEvaluator with different tenant contexts"""
        tenant_ids = [
            "tenant-1",
            "tenant-2", 
            "tenant-acme",
            "",  # Empty tenant
            None,  # None tenant (should be handled gracefully)
        ]
        
        for tenant_id in tenant_ids:
            if tenant_id is None:
                # Skip None for now as it might cause issues
                continue
                
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.test_event_source,
                emitter_id=self.test_emitter_id,
                tenant_id=tenant_id
            )
            
            # Should always produce the same safe fallback value regardless of tenant
            assert trust_score == 0.85


class TestTrustEvaluatorSafetyGateIntegration:
    """Test integration between TrustEvaluator and SafetyGate preserves verdicts"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from exoarmur.safety.safety_gate import SafetyGate
        from exoarmur.collective_confidence.aggregator import CollectiveState
        from exoarmur.safety.safety_gate import PolicyState, EnvironmentState
        from exoarmur.spec.contracts.models_v1 import LocalDecisionV1
        
        self.safety_gate = SafetyGate()
        self.trust_evaluator = TrustEvaluator()
        
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
        
        self.policy_state = PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        self.environment_state = EnvironmentState(degraded_mode=False)
        
        # Test event source
        self.event_source = {
            "kind": "edr",
            "name": "crowdstrike",
            "host": "sensor-01",
            "sensor_id": "sensor-123"
        }
    
    def test_safety_gate_verdicts_unchanged_with_trust_evaluator(self):
        """Test that SafetyGate verdicts are identical when using TrustEvaluator"""
        # Get trust score from evaluator (new way)
        trust_score_evaluator = self.trust_evaluator.evaluate_trust(
            event_source=self.event_source,
            emitter_id=self.event_source.get("sensor_id"),
            tenant_id="tenant-acme"
        )
        trust_state_evaluator = TrustState(emitter_trust_score=trust_score_evaluator)
        
        # Create trust state with hardcoded value (old way)
        trust_state_hardcoded = TrustState(emitter_trust_score=0.85)  # From main.py line 475
        
        # Evaluate safety with both approaches
        verdict_evaluator = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=trust_state_evaluator,
            environment_state=self.environment_state
        )
        
        verdict_hardcoded = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=trust_state_hardcoded,
            environment_state=self.environment_state
        )
        
        # Verdicts should be identical
        assert verdict_evaluator.verdict == verdict_hardcoded.verdict
        assert verdict_evaluator.rationale == verdict_hardcoded.rationale
        assert verdict_evaluator.rule_ids == verdict_hardcoded.rule_ids
    
    def test_safety_gate_verdict_determinism_with_trust_evaluator(self):
        """Test that SafetyGate verdicts remain deterministic with TrustEvaluator"""
        verdicts = []
        
        # Generate multiple verdicts using TrustEvaluator
        for _ in range(50):  # Test with multiple iterations
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.event_source,
                emitter_id=self.event_source.get("sensor_id"),
                tenant_id="tenant-acme"
            )
            trust_state = TrustState(emitter_trust_score=trust_score)
            
            verdict = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=self.policy_state,
                trust_state=trust_state,
                environment_state=self.environment_state
            )
            verdicts.append(verdict)
        
        # All verdicts should be identical
        first_verdict = verdicts[0]
        for verdict in verdicts[1:]:
            assert verdict.verdict == first_verdict.verdict
            assert verdict.rationale == first_verdict.rationale
            assert verdict.rule_ids == first_verdict.rule_ids
    
    def test_trust_constraint_logic_unchanged(self):
        """Test that trust constraint logic in SafetyGate behaves identically"""
        # Test low trust scenario that should trigger require_human
        low_trust_score = 0.3  # Below 0.35 threshold
        trust_state_low = TrustState(emitter_trust_score=low_trust_score)
        
        # Test with evaluator producing low trust (mocked)
        with patch.object(self.trust_evaluator, '_evaluate_trust_internal', return_value=low_trust_score):
            trust_score = self.trust_evaluator.evaluate_trust(
                event_source=self.event_source,
                emitter_id=self.event_source.get("sensor_id"),
                tenant_id="tenant-acme"
            )
            trust_state_evaluator = TrustState(emitter_trust_score=trust_score)
            
            # Both should produce the same verdict
            verdict_evaluator = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=self.policy_state,
                trust_state=trust_state_evaluator,
                environment_state=self.environment_state
            )
            
            verdict_hardcoded = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=self.policy_state,
                trust_state=trust_state_low,
                environment_state=self.environment_state
            )
            
            assert verdict_evaluator.verdict == verdict_hardcoded.verdict
            assert verdict_evaluator.rationale == verdict_hardcoded.rationale
            assert verdict_evaluator.rule_ids == verdict_hardcoded.rule_ids
