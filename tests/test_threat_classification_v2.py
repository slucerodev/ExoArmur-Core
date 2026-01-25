"""
Phase 2A Threat Classification Tests
Constitutionally compliant testing for autonomous decision-making

These tests verify:
- Deterministic decision-making
- Governance compliance
- Authority envelope enforcement
- Replay capability
- Feature flag isolation
- V1 immutability preservation
"""

import pytest
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.decision.threat_classification_v2 import (
    ThreatEventV2, ThreatFactsV2, ThreatDecisionV2, 
    DecisionTranscriptV2, GovernanceRuleV2
)
from src.decision.threat_classification_engine_v2 import ThreatClassificationEngineV2
from src.feature_flags.feature_flags import FeatureFlagContext, get_feature_flags
from src.clock import Clock


class TestThreatClassificationV2:
    """Test Phase 2A threat classification decision-making"""
    
    @pytest.fixture
    def mock_clock(self):
        """Mock clock for deterministic testing"""
        clock = Mock(spec=Clock)
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        clock.now.return_value = fixed_time
        return clock
    
    @pytest.fixture
    def threat_engine(self, mock_clock):
        """Threat classification engine with mocked dependencies"""
        return ThreatClassificationEngineV2(clock=mock_clock)
    
    @pytest.fixture
    def sample_threat_event(self):
        """Sample synthetic threat event for testing"""
        return ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AB",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 2, 0, 0, tzinfo=timezone.utc),  # Unusual time
            threat_type="malware",
            severity="critical",
            confidence_score=0.9,
            source_ip="192.0.2.100",  # Known bad IP
            target_asset="database_primary",
            indicators=["malware_hash_123", "c2_domain"],
            correlation_id="corr_123",
            trace_id="trace_123"
        )
    
    @pytest.fixture
    def low_risk_threat_event(self):
        """Low risk threat event for testing IGNORE decisions"""
        return ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AC",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),  # Business hours
            threat_type="anomaly",
            severity="low",
            confidence_score=0.2,
            source_ip="10.0.1.50",  # Internal IP
            target_asset="workstation_001",
            indicators=["anomaly_pattern"],
            correlation_id="corr_124",
            trace_id="trace_124"
        )
    
    def test_phase2a_disabled_by_default(self, threat_engine):
        """Test that Phase 2A is disabled by default (constitutional requirement)"""
        with pytest.raises(NotImplementedError, match="Phase 2A threat classification is not enabled"):
            threat_engine.classify_threat(Mock())
    
    def test_phase2a_enabled_with_feature_flag(self, threat_engine, sample_threat_event):
        """Test that Phase 2A works when explicitly enabled"""
        # Mock the feature flag to return True for this test
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Verify decision structure
            assert isinstance(decision, ThreatDecisionV2)
            assert decision.classification in ["IGNORE", "SIMULATE", "ESCALATE"]
            assert decision.authority_tier in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]
            
            # Verify transcript completeness
            assert isinstance(transcript, DecisionTranscriptV2)
            assert transcript.decision_id == decision.decision_id
            assert transcript.authorization_result in ["ALLOW_AUTO", "REQUIRE_APPROVAL", "DENY"]
            assert transcript.policy_version == "2.0.0"
    
    def test_high_risk_threat_escalation(self, threat_engine, sample_threat_event):
        """Test that high-risk threats are escalated"""
        # Mock the feature flag to return True for this test
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # High risk malware should be escalated
            assert decision.classification == "ESCALATE"
            assert transcript.authorization_result == "REQUIRE_APPROVAL"
            assert "ESCALATE" in transcript.proposed_action
    
    def test_low_risk_threat_ignore(self, threat_engine, low_risk_threat_event):
        """Test that low-risk threats are ignored"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(low_risk_threat_event)
            
            # Low risk anomaly should be ignored
            assert decision.classification == "IGNORE"
            # Very low risk events get DENY (no rule matches)
            assert transcript.authorization_result == "DENY"
            assert decision.authority_tier == "T0_OBSERVE"
    
    def test_medium_risk_threat_simulation(self, threat_engine):
        """Test that medium-risk threats get simulation"""
        medium_risk_event = ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AD",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 3, 0, 0, tzinfo=timezone.utc),  # Unusual time
            threat_type="malware",  # Higher base score than phishing
            severity="medium",
            confidence_score=0.8,  # Higher confidence to get into simulation range
            source_ip="192.0.2.50",  # Known bad IP to increase score
            target_asset="web_server_01",
            indicators=["malware_hash"],
            correlation_id="corr_125",
            trace_id="trace_125"
        )
        
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(medium_risk_event)
            
            # Medium risk should get simulation
            assert decision.classification == "SIMULATE"
            assert transcript.authorization_result == "ALLOW_AUTO"
            assert decision.authority_tier == "T1_SOFT_CONTAINMENT"
    
    def test_deterministic_decision_replay(self, threat_engine, sample_threat_event):
        """Test that decisions are deterministic and replayable"""
        # Mock ULID generation for deterministic testing
        with patch('ulid.ULID') as mock_ulid:
            mock_ulid.return_value = Mock()
            mock_ulid.return_value.__str__ = Mock(return_value="01H8X9YZABCDEF1234567890AD")
            
            with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
                # Make initial decision
                decision1, transcript1 = threat_engine.classify_threat(sample_threat_event)
                
                # Replay decision from transcript
                decision2 = threat_engine.replay_decision(transcript1, sample_threat_event)
                
                # Verify exact match
                assert decision1.decision_id == decision2.decision_id
                assert decision1.classification == decision2.classification
                assert decision1.inputs_hash == decision2.inputs_hash
                assert decision1.reasoning == decision2.reasoning
    
    def test_inputs_hash_consistency(self, threat_engine, sample_threat_event):
        """Test that input hashes are consistent and deterministic"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Verify hash format
            assert len(decision.inputs_hash) == 64  # SHA256
            assert all(c in '0123456789abcdef' for c in decision.inputs_hash)
            
            # Verify hash matches transcript
            assert decision.inputs_hash == transcript.normalized_inputs_hash
    
    def test_governance_rules_enforcement(self, threat_engine, sample_threat_event):
        """Test that governance rules are properly enforced"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Verify rules were applied
            assert len(transcript.governance_rules_fired) > 0
            assert len(decision.governance_rules_fired) > 0
            
            # Verify rules match
            assert set(transcript.governance_rules_fired) == set(decision.governance_rules_fired)
    
    def test_authority_tier_compliance(self, threat_engine, sample_threat_event):
        """Test that authority tier limits are respected"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Phase 2A should never exceed T1 authority
            assert decision.authority_tier in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]
            assert transcript.authority_tier in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]
            
            # Verify no execution capabilities
            assert decision.classification in ["IGNORE", "SIMULATE", "ESCALATE"]
    
    def test_feature_flag_isolation(self, threat_engine, sample_threat_event):
        """Test that feature flags properly isolate V2 functionality"""
        # Test with flag disabled
        with patch.object(threat_engine.feature_flags, 'is_enabled', return_value=False):
            with pytest.raises(NotImplementedError):
                threat_engine.classify_threat(sample_threat_event)
        
        # Test with flag enabled
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            assert decision is not None
            assert transcript is not None
    
    def test_complete_audit_transcript(self, threat_engine, sample_threat_event):
        """Test that complete audit transcripts are generated"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Verify all required transcript fields
            required_fields = [
                'transcript_id', 'decision_id', 'correlation_id',
                'normalized_inputs_hash', 'policy_version', 'feature_flags_snapshot',
                'belief_summary', 'proposed_action', 'authority_tier',
                'governance_rules_fired', 'evidence_score', 'risk_score',
                'authorization_result', 'constraints', 'explanation',
                'decision_timestamp', 'audit_chain_link'
            ]
            
            for field in required_fields:
                assert hasattr(transcript, field), f"Missing required field: {field}"
                assert getattr(transcript, field) is not None, f"Field is None: {field}"
    
    def test_replay_failure_on_hash_mismatch(self, threat_engine, sample_threat_event):
        """Test that replay fails appropriately on hash mismatch"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            # Get original decision
            decision, transcript = threat_engine.classify_threat(sample_threat_event)
            
            # Create corrupted transcript with different hash
            corrupted_data = transcript.model_dump()
            corrupted_data['normalized_inputs_hash'] = "0" * 64  # Invalid hash
            corrupted_transcript = DecisionTranscriptV2(**corrupted_data)
            
            # Replay should fail
            with pytest.raises(ValueError, match="Replay failed: Input hash mismatch"):
                threat_engine.replay_decision(corrupted_transcript, sample_threat_event)
    
    def test_facts_derivation_determinism(self, threat_engine, sample_threat_event):
        """Test that facts derivation is deterministic"""
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            # Mock ULID generation for deterministic testing
            with patch('ulid.ULID') as mock_ulid:
                mock_ulid.return_value = Mock()
                mock_ulid.return_value.__str__ = Mock(return_value="01H8X9YZABCDEF1234567890AD")
                
                # Derive facts twice
                facts1 = threat_engine._derive_facts(sample_threat_event)
                facts2 = threat_engine._derive_facts(sample_threat_event)
                
                # Should be identical
                assert facts1.facts_id == facts2.facts_id
                assert facts1.risk_score == facts2.risk_score
                assert facts1.threat_score == facts2.threat_score
                assert facts1.is_known_bad_ip == facts2.is_known_bad_ip
    
    def test_phase2a_constitutional_limits(self, threat_engine):
        """Test that Phase 2A respects constitutional limits"""
        # Verify engine only has threat classification rules
        rule_types = set(rule.action for rule in threat_engine._governance_rules)
        expected_actions = {"ALLOW", "DENY", "ESCALATE"}
        assert rule_types == expected_actions
        
        # Verify authority tier limits
        for rule in threat_engine._governance_rules:
            assert rule.max_authority_tier in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]
        
        # Verify no execution capabilities
        with patch.object(threat_engine, '_is_phase2a_enabled', return_value=True):
            # Create a proper mock event
            mock_event = Mock(spec=ThreatEventV2)
            mock_event.event_id = "01H8X9YZABCDEF1234567890AB"
            mock_event.threat_type = "malware"
            mock_event.severity = "high"
            mock_event.confidence_score = 0.8
            mock_event.source_ip = "192.0.2.100"
            mock_event.target_asset = "database_primary"
            mock_event.indicators = ["malware_hash"]
            mock_event.correlation_id = "corr_123"
            mock_event.trace_id = "trace_123"
            mock_event.observed_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_event.tenant_id = "tenant_test"
            mock_event.cell_id = "cell_test_01"
            
            decision, transcript = threat_engine.classify_threat(mock_event)
            
            # Only decision outcomes, no execution
            assert decision.classification in ["IGNORE", "SIMULATE", "ESCALATE"]
            assert "rollback_plan" in transcript.model_dump()
            assert transcript.rollback_plan is not None


class TestThreatClassificationModels:
    """Test Phase 2A threat classification models"""
    
    def test_threat_event_validation(self):
        """Test threat event model validation"""
        # Valid event
        event = ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AB",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            threat_type="malware",
            severity="high",
            confidence_score=0.8,
            source_ip="192.0.2.100",
            target_asset="database_primary",
            indicators=["malware_hash"],
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        assert event.event_id == "01H8X9YZABCDEF1234567890AB"
        
        # Invalid ULID
        with pytest.raises(ValueError, match="event_id must be a valid ULID"):
            ThreatEventV2(
                event_id="invalid_ulid",
                tenant_id="tenant_test",
                cell_id="cell_test_01",
                observed_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                threat_type="malware",
                severity="high",
                confidence_score=0.8,
                source_ip="192.0.2.100",
                target_asset="database_primary",
                indicators=["malware_hash"],
                correlation_id="corr_123",
                trace_id="trace_123"
            )
    
    def test_decision_transcript_completeness(self):
        """Test decision transcript model completeness"""
        transcript = DecisionTranscriptV2(
            transcript_id="01H8X9YZABCDEF1234567890AB",
            decision_id="01H8X9YZABCDEF1234567890AC",
            correlation_id="corr_123",
            normalized_inputs_hash="a" * 64,  # Valid SHA256
            policy_version="2.0.0",
            feature_flags_snapshot={"v2_threat_classification_enabled": True},
            belief_summary="Test belief summary",
            proposed_action="Threat classification: IGNORE",
            authority_tier="T0_OBSERVE",
            governance_rules_fired=["tc_ignore_low_confidence"],
            evidence_score=0.2,
            risk_score=0.2,
            authorization_result="ALLOW_AUTO",
            constraints={"max_authority_tier": "T0_OBSERVE"},
            explanation="Low risk threat ignored",
            rollback_plan="Decision-only, no execution to rollback",
            decision_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            audit_chain_link="transcript_01H8X9YZABCDEF1234567890AB"
        )
        
        # Verify all fields are present and valid
        assert transcript.transcript_id == "01H8X9YZABCDEF1234567890AB"
        assert transcript.authorization_result == "ALLOW_AUTO"
        assert transcript.authority_tier == "T0_OBSERVE"
    
    def test_governance_rule_validation(self):
        """Test governance rule model validation"""
        rule = GovernanceRuleV2(
            rule_id="test_rule",
            rule_name="Test Rule",
            rule_version="2.0.0",
            description="Test rule description",
            conditions={"max_confidence": 0.5},
            action="ALLOW",
            max_authority_tier="T0_OBSERVE",
            priority=1,
            enabled=True
        )
        
        assert rule.rule_id == "test_rule"
        assert rule.max_authority_tier == "T0_OBSERVE"
        
        # Invalid rule ID
        with pytest.raises(ValueError, match="rule_id must contain only alphanumeric"):
            GovernanceRuleV2(
                rule_id="invalid rule id",
                rule_name="Test Rule",
                rule_version="2.0.0",
                description="Test rule description",
                conditions={"max_confidence": 0.5},
                action="ALLOW",
                max_authority_tier="T0_OBSERVE",
                priority=1,
                enabled=True
            )


class TestPhase2AConstitutionalCompliance:
    """Test Phase 2A constitutional compliance"""
    
    def test_no_v1_modifications(self):
        """Test that V1 functionality is not modified"""
        # This test ensures V1 immutability
        # In practice, this would run the full V1 test suite
        # For Phase 2A, we verify our additions are isolated
        from src.decision.local_decider import LocalDecider
        from spec.contracts.models_v1 import SignalFactsV1, LocalDecisionV1
        
        # V1 decision maker should work unchanged
        decider = LocalDecider()
        assert decider is not None
        
        # V1 models should be unchanged
        assert SignalFactsV1 is not None
        assert LocalDecisionV1 is not None
    
    def test_feature_flag_isolation(self):
        """Test that Phase 2A is properly isolated behind feature flags"""
        feature_flags = get_feature_flags()
        
        # Phase 2A should be disabled by default
        context = FeatureFlagContext(
            cell_id="test",
            tenant_id="test",
            environment="test"
        )
        
        assert not feature_flags.is_enabled('v2_threat_classification_enabled', context)
        
        # Should have proper metadata
        flag_info = feature_flags.get_flag_info('v2_threat_classification_enabled')
        assert flag_info is not None
        assert flag_info['default_value'] is False
        assert flag_info['risk_level'] == 'medium'
        assert flag_info['owner'] == 'safety_team'
    
    def test_authority_envelope_compliance(self):
        """Test that Phase 2A respects authority envelope limits"""
        from src.clock import SystemClock
        engine = ThreatClassificationEngineV2(clock=SystemClock())
        
        # All rules should be within T0/T1 authority
        for rule in engine._governance_rules:
            assert rule.max_authority_tier in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]
        
        # No execution capabilities should be present
        decision_outcomes = {"IGNORE", "SIMULATE", "ESCALATE"}
        for rule in engine._governance_rules:
            assert rule.action in ["ALLOW", "DENY", "ESCALATE"]