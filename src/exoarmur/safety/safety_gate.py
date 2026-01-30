"""
Safety gate with arbitration precedence enforcement
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Literal, Optional
from dataclasses import dataclass

import sys
import os
from spec.contracts.models_v1 import LocalDecisionV1, ExecutionIntentV1

logger = logging.getLogger(__name__)


@dataclass
class SafetyVerdict:
    """Safety gate verdict"""
    verdict: Literal["allow", "deny", "require_quorum", "require_human"]
    rationale: str
    rule_ids: List[str]


@dataclass
class PolicyState:
    """Policy verification state"""
    policy_verified: bool
    kill_switch_global: bool
    kill_switch_tenant: bool
    required_approval: Literal["none", "quorum", "human"]


@dataclass
class TrustState:
    """Trust constraint state"""
    emitter_trust_score: float


@dataclass
class EnvironmentState:
    """Environment state"""
    degraded_mode: bool


class SafetyGate:
    """Evaluates safety gate verdict with arbitration precedence"""
    
    def __init__(self):
        logger.info("SafetyGate initialized")
    
    def evaluate_safety(
        self,
        intent: Optional[ExecutionIntentV1],
        local_decision: LocalDecisionV1,
        collective_state,
        policy_state: PolicyState,
        trust_state: TrustState,
        environment_state: EnvironmentState
    ) -> SafetyVerdict:
        """Evaluate safety gate with arbitration precedence"""
        
        intent_id = intent.intent_id if intent else "pre-execution"
        logger.info(f"Evaluating safety gate for intent {intent_id}")
        
        # Arbitration precedence: KillSwitch > PolicyVerification > SafetyGate > PolicyAuthorization > TrustConstraints > CollectiveConfidence > LocalDecision
        
        # 1. Kill switches (highest precedence)
        if policy_state.kill_switch_global:
            return SafetyVerdict(
                verdict="deny",
                rationale="Global kill switch engaged; only A0 observe permitted.",
                rule_ids=["SG-101"]
            )
        
        if policy_state.kill_switch_tenant:
            return SafetyVerdict(
                verdict="deny",
                rationale="Tenant kill switch engaged; only A0 observe permitted.",
                rule_ids=["SG-102"]
            )
        
        # 2. Policy verification
        if not policy_state.policy_verified:
            return SafetyVerdict(
                verdict="require_quorum",
                rationale="Policy not verified; degrade and require escalation for non-A0.",
                rule_ids=["SG-201"]
            )
        
        # 3. Determine action class for remaining checks
        # Determine action class from local decision if intent not available
        action_class = "A0_observe"  # Default
        if intent:
            action_class = intent.action_class
        else:
            # Derive from local decision classification
            if local_decision.classification == "malicious":
                action_class = "A2_hard_containment"
            elif local_decision.classification == "suspicious":
                action_class = "A1_soft_containment"
        
        # 4. Trust constraints
        if trust_state.emitter_trust_score < 0.35 and action_class in ["A2_hard_containment", "A3_irreversible"]:
            return SafetyVerdict(
                verdict="require_human",
                rationale="Trust too low for A2/A3 execution.",
                rule_ids=["SG-301"]
            )
        
        if trust_state.emitter_trust_score < 0.50 and action_class == "A2_hard_containment":
            return SafetyVerdict(
                verdict="require_quorum",
                rationale="Trust below floor for local A2; require quorum.",
                rule_ids=["SG-302"]
            )
        
        if trust_state.emitter_trust_score < 0.80 and action_class == "A3_irreversible":
            return SafetyVerdict(
                verdict="require_human",
                rationale="Trust below floor for local A3; require human approval.",
                rule_ids=["SG-303"]
            )
        
        # 5. Threshold checks based on action class
        
        if action_class == "A1_soft_containment":
            if local_decision.confidence >= 0.80:
                return SafetyVerdict(
                    verdict="allow",
                    rationale="A1 soft containment: confidence threshold met.",
                    rule_ids=["SG-401"]
                )
            else:
                return SafetyVerdict(
                    verdict="deny",
                    rationale="A1 soft containment: confidence threshold not met.",
                    rule_ids=["SG-402"]
                )
        
        elif action_class == "A2_hard_containment":
            if (local_decision.confidence >= 0.90 or 
                (collective_state.quorum_count >= 2 and collective_state.aggregate_score >= 0.85)):
                return SafetyVerdict(
                    verdict="allow",
                    rationale="A2 hard containment: local or collective thresholds met.",
                    rule_ids=["SG-403"]
                )
            else:
                return SafetyVerdict(
                    verdict="require_quorum",
                    rationale="A2 hard containment: thresholds not met, require quorum.",
                    rule_ids=["SG-404"]
                )
        
        elif action_class == "A3_irreversible":
            if (local_decision.confidence >= 0.97 and 
                ((collective_state.quorum_count >= 3 and collective_state.aggregate_score >= 0.92) or
                 policy_state.required_approval == 'human')):
                return SafetyVerdict(
                    verdict="allow",
                    rationale="A3 irreversible: all thresholds and approvals met.",
                    rule_ids=["SG-405"]
                )
            else:
                return SafetyVerdict(
                    verdict="require_human",
                    rationale="A3 irreversible: requires human approval or higher thresholds.",
                    rule_ids=["SG-406"]
                )
        
        # 6. Default allow for A0_observe
        if action_class == "A0_observe":
            return SafetyVerdict(
                verdict="allow",
                rationale="A0 observe: always allowed.",
                rule_ids=["SG-501"]
            )
        
        # 6. Default deny for anything else
        return SafetyVerdict(
            verdict="deny",
            rationale="No safety rule matched; default deny.",
            rule_ids=["SG-999"]
        )
