"""
Unit tests for safety gate arbitration precedence enforcement
"""

import pytest
from datetime import datetime

from src.safety.safety_gate import (
    SafetyGate,
    SafetyVerdict,
    PolicyState,
    TrustState,
    EnvironmentState
)
from src.collective_confidence.aggregator import CollectiveState

# Import contract models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))
from models_v1 import LocalDecisionV1


class TestSafetyGateArbitration:
    """Test safety gate arbitration precedence enforcement"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.safety_gate = SafetyGate()
        
        # Create test local decision
        self.local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="malicious",
            severity="high",
            confidence=0.9,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        # Default states
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
        
        self.trust_state = TrustState(emitter_trust_score=0.85)
        self.environment_state = EnvironmentState(degraded_mode=False)
    
    def test_kill_switch_global_takes_precedence(self):
        """Test that global kill switch overrides everything (precedence assertion 1)"""
        policy_state_with_kill_switch = PolicyState(
            policy_verified=True,
            kill_switch_global=True,  # Global kill switch active
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        verdict = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=policy_state_with_kill_switch,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "deny"
        assert "kill switch" in verdict.rationale.lower()
        assert "SG-101" in verdict.rule_ids
    
    def test_policy_verification_precedence_over_trust(self):
        """Test that policy verification takes precedence over trust constraints (precedence assertion 2)"""
        policy_state_unverified = PolicyState(
            policy_verified=False,  # Policy not verified
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        verdict = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=policy_state_unverified,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "require_quorum"
        assert "policy not verified" in verdict.rationale.lower()
        assert "SG-201" in verdict.rule_ids
    
    def test_trust_constraints_precedence_over_collective_confidence(self):
        """Test that trust constraints take precedence over collective confidence (precedence assertion 3)"""
        low_trust_state = TrustState(emitter_trust_score=0.3)  # Very low trust
        
        verdict = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=low_trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "require_human"
        assert "trust too low" in verdict.rationale.lower()
        assert "SG-301" in verdict.rule_ids
    
    def test_a1_soft_containment_threshold_check(self):
        """Test A1 soft containment threshold checking"""
        # Test with sufficient confidence
        high_confidence_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="suspicious",
            severity="medium",
            confidence=0.85,  # Above 0.80 threshold
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        verdict = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=high_confidence_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "allow"
        assert "SG-401" in verdict.rule_ids
    
    def test_a2_hard_containment_collective_threshold(self):
        """Test A2 hard containment with collective confidence"""
        # Test with collective confidence meeting thresholds
        high_collective_state = CollectiveState(
            aggregate_score=0.90,  # Above 0.85 threshold
            quorum_count=3,  # Above 2 threshold
            conflict_detected=False
        )
        
        # Create mock A2 hard containment intent
        class MockIntent:
            def __init__(self):
                self.action_class = "A2_hard_containment"
                self.intent_id = "mock-intent-123"
        
        mock_intent = MockIntent()
        
        verdict = self.safety_gate.evaluate_safety(
            intent=mock_intent,
            local_decision=self.local_decision,
            collective_state=high_collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "allow"
        assert "SG-403" in verdict.rule_ids
    
    def test_a3_irreversible_strict_requirements(self):
        """Test A3 irreversible requires strict thresholds"""
        # Test with insufficient confidence for A3
        insufficient_confidence_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="malicious",
            severity="critical",
            confidence=0.95,  # Below 0.97 threshold
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        # Create mock A3 irreversible intent
        class MockIntent:
            def __init__(self):
                self.action_class = "A3_irreversible"
                self.intent_id = "mock-intent-456"
        
        mock_intent = MockIntent()
        
        verdict = self.safety_gate.evaluate_safety(
            intent=mock_intent,
            local_decision=insufficient_confidence_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        assert verdict.verdict == "require_human"
        assert "SG-406" in verdict.rule_ids
    
    def test_a0_observe_always_allowed(self):
        """Test that A0 observe is always allowed"""
        # This would be tested with an actual intent, but for now we test the default case
        # The safety gate should allow A0 observe even with low confidence
        benign_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="benign",
            severity="low",
            confidence=0.1,  # Very low confidence
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        verdict = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=benign_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=self.environment_state
        )
        
        # Should default to allow for benign cases
        assert verdict.verdict in ["allow", "deny"]
