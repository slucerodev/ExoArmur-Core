"""
Phase 2A Threat Classification Decision Engine
Constitutionally compliant autonomous decision-making under governance

This module implements the ONLY autonomous decision type permitted in Phase 2A:
- Threat classification (IGNORE/SIMULATE/ESCALATE)
- Decision-only (no execution)
- Machine-speed governance
- Deterministic transcripts
"""

import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..feature_flags.feature_flags import get_feature_flags, FeatureFlagContext
from ..clock import Clock, SystemClock
from .threat_classification_v2 import (
    ThreatEventV2, ThreatFactsV2, ThreatDecisionV2, 
    DecisionTranscriptV2, GovernanceRuleV2
)

logger = logging.getLogger(__name__)


class ThreatClassificationEngineV2:
    """
    Phase 2A autonomous threat classification decision engine.
    
    Constitutional compliance:
    - Decision-only (no execution capabilities)
    - Authority envelope limited to T0/T1
    - Deterministic replay capability
    - Complete audit transcripts
    - Feature flag isolation
    """
    
    def __init__(self, clock: Optional[Clock] = None):
        self.clock = clock or SystemClock()
        self.feature_flags = get_feature_flags()
        
        # Phase 2A governance rules (constitutionally limited)
        self._governance_rules = self._load_phase2a_rules()
        
        # Verify Phase 2A constraints
        self._verify_phase2a_compliance()
    
    def _load_phase2a_rules(self) -> List[GovernanceRuleV2]:
        """Load Phase 2A governance rules (threat classification only)"""
        return [
            GovernanceRuleV2(
                rule_id="tc_ignore_low_confidence",
                rule_name="Ignore Low Confidence Threats",
                rule_version="2.0.0",
                description="Ignore threats with low confidence and low risk scores",
                conditions={
                    "max_confidence": 0.3,
                    "max_risk_score": 0.4,
                    "min_threat_score": 3.0
                },
                action="ALLOW",
                max_authority_tier="T0_OBSERVE",
                priority=1,
                enabled=True
            ),
            GovernanceRuleV2(
                rule_id="tc_simulate_medium_threat",
                rule_name="Simulate Medium Threat Response",
                rule_version="2.0.0", 
                description="Simulate response for medium-level threats without execution",
                conditions={
                    "min_confidence": 0.3,
                    "max_confidence": 0.7,
                    "min_risk_score": 0.4,
                    "max_risk_score": 0.8,
                    "min_threat_score": 3.0
                },
                action="ALLOW",
                max_authority_tier="T1_SOFT_CONTAINMENT",
                priority=2,
                enabled=True
            ),
            GovernanceRuleV2(
                rule_id="tc_escalate_high_threat",
                rule_name="Escalate High Threat Events",
                rule_version="2.0.0",
                description="Escalate high-confidence, high-risk threats for human review",
                conditions={
                    "min_confidence": 0.7,
                    "min_risk_score": 0.8,
                    "min_threat_score": 7.0
                },
                action="ESCALATE",
                max_authority_tier="T1_SOFT_CONTAINMENT",
                priority=3,
                enabled=True
            ),
            GovernanceRuleV2(
                rule_id="tc_deny_unknown_patterns",
                rule_name="Deny Unknown Threat Patterns",
                rule_version="2.0.0",
                description="Deny autonomous decisions for unknown threat patterns",
                conditions={
                    "unknown_threat_type": True
                },
                action="DENY",
                max_authority_tier="T0_OBSERVE",
                priority=10,
                enabled=True
            )
        ]
    
    def _verify_phase2a_compliance(self):
        """Verify Phase 2A constitutional compliance"""
        # Check feature flag
        context = FeatureFlagContext(
            cell_id="system",
            tenant_id="system", 
            environment="verification",
            timestamp=self.clock.now()
        )
        
        # Phase 2A should be disabled by default (constitutional requirement)
        if self.feature_flags.is_enabled('v2_threat_classification_enabled', context):
            logger.warning("Phase 2A threat classification flag is enabled - ensure explicit opt-in")
        
        # Verify no execution capabilities
        for rule in self._governance_rules:
            if rule.max_authority_tier not in ["T0_OBSERVE", "T1_SOFT_CONTAINMENT"]:
                raise ValueError(f"Phase 2A violation: Rule {rule.rule_id} exceeds authority tier T1")
        
        logger.info("Phase 2A threat classification engine verified constitutionally compliant")
    
    def classify_threat(self, threat_event: ThreatEventV2) -> Tuple[ThreatDecisionV2, DecisionTranscriptV2]:
        """
        Classify threat with autonomous decision under governance.
        
        This is the ONLY autonomous decision permitted in Phase 2A.
        
        Args:
            threat_event: Synthetic threat event for classification
            
        Returns:
            Tuple of (decision, transcript) for complete audit trail
        """
        # Phase 2A feature flag check
        if not self._is_phase2a_enabled():
            raise NotImplementedError("Phase 2A threat classification is not enabled")
        
        # Step 1: Derive observable facts
        facts = self._derive_facts(threat_event)
        
        # Step 2: Evaluate governance rules
        governance_result = self._evaluate_governance(facts)
        
        # Step 3: Make autonomous decision
        decision = self._make_decision(facts, governance_result)
        
        # Step 4: Generate complete transcript
        transcript = self._generate_transcript(threat_event, facts, decision, governance_result)
        
        logger.info(f"Threat classification decision: {decision.classification} for {threat_event.event_id}")
        
        return decision, transcript
    
    def _is_phase2a_enabled(self) -> bool:
        """Check if Phase 2A is explicitly enabled (constitutional requirement)"""
        context = FeatureFlagContext(
            cell_id="system",
            tenant_id="system",
            environment="production", 
            timestamp=self.clock.now()
        )
        return self.feature_flags.is_enabled('v2_threat_classification_enabled', context)
    
    def _derive_facts(self, event: ThreatEventV2) -> ThreatFactsV2:
        """Derive observable facts from threat event (deterministic)"""
        import ulid
        
        # Observable facts (verifiable, not heuristic)
        is_internal_ip = self._is_internal_ip(event.source_ip) if event.source_ip else False
        is_known_bad_ip = self._is_known_bad_ip(event.source_ip) if event.source_ip else False
        is_unusual_time = self._is_unusual_time(event.observed_at)
        is_high_risk_asset = self._is_high_risk_asset(event.target_asset)
        is_repeated_pattern = len(event.indicators) > 1
        
        # Quantitative scoring (deterministic algorithms)
        threat_score = self._calculate_threat_score(event)
        risk_score = self._calculate_risk_score(event, threat_score)
        
        facts = ThreatFactsV2(
            facts_id=str(ulid.ULID()),
            derived_from_event_id=event.event_id,
            tenant_id=event.tenant_id,
            cell_id=event.cell_id,
            is_internal_ip=is_internal_ip,
            is_known_bad_ip=is_known_bad_ip,
            is_unusual_time=is_unusual_time,
            is_high_risk_asset=is_high_risk_asset,
            is_repeated_pattern=is_repeated_pattern,
            threat_score=threat_score,
            risk_score=risk_score,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id
        )
        
        logger.debug(f"Derived facts for {event.event_id}: risk={risk_score:.2f}, threat={threat_score:.2f}")
        return facts
    
    def _evaluate_governance(self, facts: ThreatFactsV2) -> Dict[str, Any]:
        """Evaluate governance rules (deterministic)"""
        applicable_rules = []
        authorization = "DENY"
        authority_tier = "T0_OBSERVE"
        
        # Sort rules by priority (1 = highest)
        sorted_rules = sorted(self._governance_rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
                
            if self._rule_conditions_match(rule, facts):
                applicable_rules.append(rule.rule_id)
                
                if rule.action == "ALLOW":
                    authorization = "ALLOW_AUTO"
                    authority_tier = rule.max_authority_tier
                elif rule.action == "ESCALATE":
                    authorization = "REQUIRE_APPROVAL"
                    authority_tier = rule.max_authority_tier
                elif rule.action == "DENY":
                    authorization = "DENY"
                    authority_tier = "T0_OBSERVE"
                    break  # DENY rules are final
        
        return {
            "applicable_rules": applicable_rules,
            "authorization": authorization,
            "authority_tier": authority_tier,
            "evidence_score": facts.risk_score,
            "risk_score": facts.risk_score
        }
    
    def _make_decision(self, facts: ThreatFactsV2, governance_result: Dict[str, Any]) -> ThreatDecisionV2:
        """Make autonomous decision based on governance evaluation"""
        import ulid
        
        # Map authorization to decision outcome
        if governance_result["authorization"] == "DENY":
            classification = "IGNORE"
            reasoning = "Governance rules deny autonomous action"
        elif governance_result["authorization"] == "REQUIRE_APPROVAL":
            classification = "ESCALATE"
            reasoning = "Threat requires human approval per governance rules"
        elif governance_result["authorization"] == "ALLOW_AUTO":
            # Determine SIMULATE vs IGNORE based on authority tier from governance
            if governance_result["authority_tier"] == "T1_SOFT_CONTAINMENT":
                classification = "SIMULATE"
                reasoning = "Medium risk threat qualifies for simulation"
            else:
                classification = "IGNORE"
                reasoning = "Low risk threat qualifies for observation only"
        else:
            # Default to safe option
            classification = "IGNORE"
            reasoning = "Default safe classification"
        
        decision_id = str(ulid.ULID())
        
        # Create decision without hash first
        decision_data = {
            "decision_id": decision_id,
            "facts_id": facts.facts_id,
            "tenant_id": facts.tenant_id,
            "cell_id": facts.cell_id,
            "classification": classification,
            "confidence": facts.risk_score,
            "reasoning": reasoning,
            "governance_rules_fired": governance_result["applicable_rules"],
            "authority_tier": governance_result["authority_tier"],
            "inputs_hash": None,  # Will be computed below
            "decided_at": self.clock.now(),
            "correlation_id": facts.correlation_id,
            "trace_id": facts.trace_id
        }
        
        decision = ThreatDecisionV2(**decision_data)
        
        # Compute deterministic inputs hash
        decision.inputs_hash = decision.compute_inputs_hash()
        
        return decision
    
    def _generate_transcript(self, event: ThreatEventV2, facts: ThreatFactsV2, 
                           decision: ThreatDecisionV2, governance_result: Dict[str, Any]) -> DecisionTranscriptV2:
        """Generate complete deterministic decision transcript"""
        import ulid
        
        transcript_id = str(ulid.ULID())
        
        # Compute normalized inputs hash (same as decision hash)
        inputs_hash = decision.compute_inputs_hash()
        
        transcript = DecisionTranscriptV2(
            transcript_id=transcript_id,
            decision_id=decision.decision_id,
            correlation_id=event.correlation_id,
            normalized_inputs_hash=inputs_hash,
            policy_version="2.0.0",
            feature_flags_snapshot=self._get_feature_flags_snapshot(),
            belief_summary=f"Threat score: {facts.threat_score:.2f}, Risk score: {facts.risk_score:.2f}",
            proposed_action=f"Threat classification: {decision.classification}",
            authority_tier=decision.authority_tier,
            governance_rules_fired=governance_result["applicable_rules"],
            evidence_score=governance_result["evidence_score"],
            risk_score=governance_result["risk_score"],
            authorization_result=governance_result["authorization"],
            constraints={"max_authority_tier": decision.authority_tier},
            explanation=decision.reasoning,
            rollback_plan="Decision-only, no execution to rollback",
            decision_timestamp=decision.decided_at,
            operator_approval_reference=None,  # No approval needed for decision-only
            audit_chain_link=f"transcript_{transcript_id}"
        )
        
        return transcript
    
    def _rule_conditions_match(self, rule: GovernanceRuleV2, facts: ThreatFactsV2) -> bool:
        """Check if rule conditions match facts (deterministic)"""
        conditions = rule.conditions
        
        # Simple condition matching (deterministic logic)
        if "max_confidence" in conditions and facts.risk_score > conditions["max_confidence"]:
            return False
        if "min_confidence" in conditions and facts.risk_score < conditions["min_confidence"]:
            return False
        if "max_risk_score" in conditions and facts.risk_score > conditions["max_risk_score"]:
            return False
        if "min_risk_score" in conditions and facts.risk_score < conditions["min_risk_score"]:
            return False
        if "min_threat_score" in conditions and facts.threat_score < conditions["min_threat_score"]:
            return False
        if "max_threat_score" in conditions and facts.threat_score > conditions["max_threat_score"]:
            return False
        if "unknown_threat_type" in conditions and conditions["unknown_threat_type"]:
            # This would need threat type context, simplified for Phase 2A
            return False
        
        return True
    
    def _get_feature_flags_snapshot(self) -> Dict[str, bool]:
        """Get current feature flags state for transcript"""
        return {
            "v2_threat_classification_enabled": self._is_phase2a_enabled(),
            "v2_federation_enabled": self.feature_flags.is_v2_federation_enabled(),
            "v2_control_plane_enabled": self.feature_flags.is_v2_control_plane_enabled()
        }
    
    # Helper methods for fact derivation (deterministic)
    
    def _is_internal_ip(self, ip: Optional[str]) -> bool:
        """Check if IP is internal network range"""
        if not ip:
            return False
        # Simple internal IP ranges (deterministic)
        internal_ranges = [
            "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
            "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
            "127.", "169.254."
        ]
        return any(ip.startswith(prefix) for prefix in internal_ranges)
    
    def _is_known_bad_ip(self, ip: Optional[str]) -> bool:
        """Check if IP is in threat intelligence (simplified for Phase 2A)"""
        # Phase 2A: simplified deterministic check
        # In production, this would query threat intelligence feeds
        known_bad_patterns = ["192.0.2.", "203.0.113.", "198.51.100."]
        if not ip:
            return False
        return any(ip.startswith(pattern) for pattern in known_bad_patterns)
    
    def _is_unusual_time(self, timestamp: datetime) -> bool:
        """Check if event occurred outside business hours (simplified)"""
        # Phase 2A: simplified deterministic check
        hour = timestamp.hour
        return hour < 6 or hour > 18  # 6 AM - 6 PM business hours
    
    def _is_high_risk_asset(self, asset: str) -> bool:
        """Check if asset is high value (simplified for Phase 2A)"""
        # Phase 2A: simplified deterministic check
        high_risk_patterns = ["dc", "database", "auth", "admin", "controller"]
        return any(pattern in asset.lower() for pattern in high_risk_patterns)
    
    def _calculate_threat_score(self, event: ThreatEventV2) -> float:
        """Calculate threat score (deterministic algorithm)"""
        # Base score by threat type
        type_scores = {
            "malware": 8.0,
            "phishing": 6.0,
            "command_control": 9.0,
            "data_exfiltration": 10.0,
            "anomaly": 4.0
        }
        
        base_score = type_scores.get(event.threat_type, 5.0)
        severity_multiplier = {"low": 0.5, "medium": 1.0, "high": 1.5, "critical": 2.0}
        
        threat_score = base_score * severity_multiplier.get(event.severity, 1.0)
        threat_score *= event.confidence_score  # Apply confidence weighting
        
        return min(10.0, max(0.0, threat_score))
    
    def _calculate_risk_score(self, event: ThreatEventV2, threat_score: float) -> float:
        """Calculate risk score (deterministic algorithm)"""
        # Normalize threat score to 0-1 range
        normalized_threat = threat_score / 10.0
        
        # Apply event confidence
        risk_score = normalized_threat * event.confidence_score
        
        return min(1.0, max(0.0, risk_score))
    
    def replay_decision(self, transcript: DecisionTranscriptV2, threat_event: ThreatEventV2) -> ThreatDecisionV2:
        """
        Replay a decision from transcript for verification.
        
        Args:
            transcript: Original decision transcript
            threat_event: Original threat event
            
        Returns:
            Replay decision that should match original exactly
        """
        # Verify inputs match
        facts = self._derive_facts(threat_event)
        governance_result = self._evaluate_governance(facts)
        replay_decision = self._make_decision(facts, governance_result)
        
        # Verify deterministic replay
        if replay_decision.inputs_hash != transcript.normalized_inputs_hash:
            raise ValueError("Replay failed: Input hash mismatch")
        
        if replay_decision.classification != self._extract_classification_from_transcript(transcript):
            raise ValueError("Replay failed: Decision mismatch")
        
        logger.info(f"Decision replay verified for {transcript.decision_id}")
        return replay_decision
    
    def _extract_classification_from_transcript(self, transcript: DecisionTranscriptV2) -> str:
        """Extract classification decision from transcript"""
        # Parse the proposed action to extract classification
        if "IGNORE" in transcript.proposed_action:
            return "IGNORE"
        elif "SIMULATE" in transcript.proposed_action:
            return "SIMULATE"
        elif "ESCALATE" in transcript.proposed_action:
            return "ESCALATE"
        else:
            return "IGNORE"  # Safe default