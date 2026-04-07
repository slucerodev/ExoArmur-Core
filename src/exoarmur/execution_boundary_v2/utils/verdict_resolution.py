"""
Verdict resolution utilities for deterministic governance.

Provides deterministic precedence resolution between PolicyDecisionPoint
and SafetyGate verdicts according to strict governance rules.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.safety.safety_gate import SafetyVerdict
from exoarmur.ids import make_id


class FinalVerdict(Enum):
    """Final resolved verdict with precedence ordering.
    
    Precedence (highest to lowest):
    - DENY: Absolute rejection, overrides all other verdicts
    - REQUIRE_APPROVAL: Conditional approval, requires human intervention
    - REQUIRE_QUORUM: Requires consensus among multiple evaluators
    - REQUIRE_HUMAN: Requires human operator intervention
    - ALLOW: Unconditional approval
    """
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_QUORUM = "require_quorum"
    REQUIRE_HUMAN = "require_human"
    ALLOW = "allow"
    
    @classmethod
    def precedence_rank(cls, verdict: "FinalVerdict") -> int:
        """Get precedence rank for verdict resolution (lower = higher precedence)."""
        precedence = {
            cls.DENY: 0,
            cls.REQUIRE_APPROVAL: 1,
            cls.REQUIRE_QUORUM: 2,
            cls.REQUIRE_HUMAN: 3,
            cls.ALLOW: 4
        }
        return precedence.get(verdict, 0)  # Default to highest precedence (DENY)


def resolve_verdicts(
    policy_decision: PolicyDecision,
    safety_verdict: SafetyVerdict,
    intent_id: Optional[str] = None
) -> Tuple[FinalVerdict, Dict[str, Any]]:
    """Resolve PDP and SafetyGate verdicts according to precedence rules.
    
    Precedence Rules:
    1. DENY overrides ALLOW
    2. REQUIRE_APPROVAL overrides ALLOW
    3. If PDP = ALLOW and SafetyGate = ALLOW → final = ALLOW
    4. If either PDP or SafetyGate returns DENY → final = DENY
    5. If PDP returns REQUIRE_APPROVAL and SafetyGate returns ALLOW → final = REQUIRE_APPROVAL
    6. If SafetyGate returns REQUIRE_APPROVAL and PDP returns ALLOW → final = REQUIRE_APPROVAL
    7. If both return REQUIRE_APPROVAL → final = REQUIRE_APPROVAL
    8. If SafetyGate returns a verdict not recognized, treat as DENY
    
    Args:
        policy_decision: Policy decision from PolicyDecisionPoint
        safety_verdict: Safety verdict from SafetyGate
        intent_id: Optional intent ID for evidence tracking
        
    Returns:
        Tuple of (FinalVerdict, resolution_evidence)
    """
    evidence = {
        "policy_verdict": policy_decision.verdict.value,
        "policy_rationale": policy_decision.rationale,
        "safety_verdict": safety_verdict.verdict,
        "safety_rationale": safety_verdict.rationale,
        "safety_rule_ids": safety_verdict.rule_ids,
        "resolution_rules_applied": []
    }
    
    # Rule 8: SafetyGate verdict validation
    valid_safety_verdicts = {"allow", "deny", "block", "warn", "require_quorum", "require_human"}
    if safety_verdict.verdict not in valid_safety_verdicts:
        evidence["resolution_rules_applied"].append("invalid_safety_verdict_treated_as_deny")
        return FinalVerdict.DENY, evidence
    
    # Rule 4: Any DENY verdict results in final DENY
    if policy_decision.verdict == PolicyVerdict.DENY:
        evidence["resolution_rules_applied"].append("policy_deny_overrides_all")
        return FinalVerdict.DENY, evidence
    
    if safety_verdict.verdict in ["deny", "block"]:
        evidence["resolution_rules_applied"].append("safety_deny_overrides_all")
        return FinalVerdict.DENY, evidence
    
    # Rule 3: Both ALLOW results in ALLOW
    if (policy_decision.verdict == PolicyVerdict.ALLOW and 
        safety_verdict.verdict == "allow"):
        evidence["resolution_rules_applied"].append("both_allow")
        return FinalVerdict.ALLOW, evidence
    
    # Rule 5 & 7: PDP REQUIRE_APPROVAL takes precedence
    if policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL:
        if safety_verdict.verdict in ["allow", "require_human", "require_quorum"]:
            evidence["resolution_rules_applied"].append("policy_require_approval_overrides")
            return FinalVerdict.REQUIRE_APPROVAL, evidence
    
    # Rule 6: SafetyGate REQUIRE_APPROVAL equivalents
    if safety_verdict.verdict in ["require_quorum", "require_human"]:
        if policy_decision.verdict == PolicyVerdict.ALLOW:
            evidence["resolution_rules_applied"].append(f"safety_{safety_verdict.verdict}_overrides_allow")
            if safety_verdict.verdict == "require_quorum":
                return FinalVerdict.REQUIRE_QUORUM, evidence
            else:
                return FinalVerdict.REQUIRE_HUMAN, evidence
    
    # Rule 2: PDP REQUIRE_APPROVAL with SafetyGate ALLOW
    if (policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL and 
        safety_verdict.verdict == "allow"):
        evidence["resolution_rules_applied"].append("policy_require_approval_with_safety_allow")
        return FinalVerdict.REQUIRE_APPROVAL, evidence
    
    # Default fallback to most restrictive
    evidence["resolution_rules_applied"].append("default_restrictive_fallback")
    return FinalVerdict.DENY, evidence


def create_verdict_resolution_id(
    policy_decision_id: str,
    safety_verdict: SafetyVerdict,
    intent_id: Optional[str] = None
) -> str:
    """Create deterministic ID for verdict resolution."""
    payload = {
        "policy_decision_id": policy_decision_id,
        "safety_verdict": safety_verdict.verdict,
        "safety_rule_ids": safety_verdict.rule_ids
    }
    if intent_id:
        payload["intent_id"] = intent_id
    
    return make_id("verdict_resolution", payload)
