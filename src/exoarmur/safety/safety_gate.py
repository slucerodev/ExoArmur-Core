"""
Safety gate with V2-native structures and clean V1/V2 separation.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

The SafetyGate provides the final safety assessment for execution intents.
It operates with deterministic verdict resolution and maintains strict precedence
rules to ensure consistent governance behavior across all executions.
V1 compatibility is handled through the v1_adapter layer.
"""

import logging
from typing import Dict, Any, List, Literal, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SafetyVerdict:
    """V2-native safety gate verdict with precedence ordering.
    
    Precedence (highest to lowest):
    - deny: Absolute rejection, overrides all other verdicts
    - require_quorum: Requires consensus among multiple evaluators
    - require_human: Requires human operator intervention
    - allow: Unconditional approval
    """
    verdict: Literal["allow", "deny", "require_quorum", "require_human"]
    rationale: str
    rule_ids: List[str]
    
    @classmethod
    def precedence_rank(cls, verdict: str) -> int:
        """Get precedence rank for verdict resolution (lower = higher precedence)."""
        precedence = {
            "deny": 0,
            "require_quorum": 1,
            "require_human": 2,
            "allow": 3
        }
        return precedence.get(verdict, 0)  # Default to highest precedence (deny)


@dataclass
class V2PolicyState:
    """V2-native policy verification state for safety evaluation."""
    policy_verified: bool
    kill_switch_global: bool
    kill_switch_tenant: bool
    required_approval: Literal["none", "quorum", "human"]


@dataclass
class V2TrustState:
    """V2-native trust constraint state for safety evaluation."""
    emitter_trust_score: float


@dataclass
class V2EnvironmentState:
    """V2-native environment state for safety evaluation."""
    degraded_mode: bool
    cell_load: float
    network_health: float
    resource_availability: float

    def __init__(
        self,
        degraded_mode: bool = False,
        cell_load: float = 0.5,
        network_health: float = 0.9,
        resource_availability: float = 0.8,
    ):
        self.degraded_mode = degraded_mode
        self.cell_load = cell_load
        self.network_health = network_health
        self.resource_availability = resource_availability


class SafetyGate:
    """V2-native safety gate with clean V1/V2 separation.
    
    The SafetyGate enforces governance boundaries by evaluating execution
    intents against safety constraints and producing deterministic verdicts.
    All verdicts follow strict precedence rules to ensure consistent behavior.
    V1 compatibility is handled through the v1_adapter layer.
    """
    
    def __init__(self):
        logger.info("V2-native SafetyGate initialized with clean V1/V2 separation")
    
    def evaluate_safety_v2(
        self,
        intent: Dict[str, Any],  # V2-native ActionIntent dict
        policy_decision: Dict[str, Any],  # V2-native PolicyDecision dict
        policy_state: V2PolicyState,
        trust_state: V2TrustState,
        environment_state: V2EnvironmentState
    ) -> SafetyVerdict:
        """Evaluate safety using V2-native structures.
        
        Args:
            intent: V2-native execution intent dict
            policy_decision: V2-native policy decision dict
            policy_state: V2-native policy verification state
            trust_state: V2-native trust constraint state
            environment_state: V2-native environment degradation state
            
        Returns:
            SafetyVerdict with deterministic precedence ranking
        """
        # Extract key information from V2 structures
        action_type = intent.get("action_type", "unknown")
        actor_id = intent.get("actor_id", "unknown")
        confidence = policy_decision.get("confidence", 0.0)
        
        # Apply safety rules with deterministic logic
        if not policy_state.policy_verified:
            return SafetyVerdict(
                verdict="deny",
                rationale="Policy verification failed - safety gate denies execution",
                rule_ids=["policy_verification_required"]
            )
        
        if policy_state.kill_switch_global or policy_state.kill_switch_tenant:
            return SafetyVerdict(
                verdict="deny",
                rationale="Kill switch engaged - safety gate denies execution",
                rule_ids=["kill_switch_engaged"]
            )
        
        if trust_state.emitter_trust_score < 0.5:
            return SafetyVerdict(
                verdict="require_human",
                rationale=f"Low trust score ({trust_state.emitter_trust_score:.2f}) requires human review",
                rule_ids=["trust_score_threshold"]
            )
        
        if environment_state.cell_load > 0.9 or environment_state.network_health < 0.7:
            return SafetyVerdict(
                verdict="require_quorum",
                rationale="High system load requires consensus decision",
                rule_ids=["system_load_threshold"]
            )
        
        # Default allow for safe conditions
        return SafetyVerdict(
            verdict="allow",
            rationale=f"Safe execution conditions verified for {action_type} by {actor_id}",
            rule_ids=["safe_execution_verified"]
        )
    
    def evaluate_safety(
        self,
        intent,  # V1 ExecutionIntentV1 (for backward compatibility)
        local_decision,  # V1 LocalDecisionV1 (for backward compatibility)
        *,
        collective_state=None,  # Legacy compatibility; intentionally unused by V2 safety logic
        policy_state,  # V1 PolicyState (for backward compatibility)
        trust_state,  # V1 TrustState (for backward compatibility)
        environment_state  # V1 EnvironmentState (for backward compatibility)
    ) -> SafetyVerdict:
        """Legacy method for V1 compatibility (delegates to V2 implementation)."""
        # Convert V1 structures to V2-native format
        if intent is None:
            subject = getattr(local_decision, "subject", {}) or {}
            v2_intent = {
                "action_type": getattr(local_decision, "classification", "unknown"),
                "actor_id": subject.get("subject_id", "unknown"),
                "target": subject.get("subject_id", "unknown"),
                "parameters": {}
            }
        else:
            v2_intent = {
                "action_type": intent.intent_type,
                "actor_id": intent.subject.get("subject_id", "unknown"),
                "target": intent.parameters.get("target", "unknown"),
                "parameters": intent.parameters
            }
        
        v2_policy_decision = {
            "confidence": local_decision.confidence,
            "verdict": "allow"  # Default for safety evaluation
        }
        
        v2_policy_state = V2PolicyState(
            policy_verified=policy_state.policy_verified,
            kill_switch_global=policy_state.kill_switch_global,
            kill_switch_tenant=policy_state.kill_switch_tenant,
            required_approval=policy_state.required_approval
        )
        
        v2_trust_state = V2TrustState(
            emitter_trust_score=trust_state.emitter_trust_score
        )
        
        v2_environment_state = V2EnvironmentState(
            cell_load=0.5,  # Default values for V1 compatibility
            network_health=0.9,
            resource_availability=0.8
        )
        
        return self.evaluate_safety_v2(
            intent=v2_intent,
            policy_decision=v2_policy_decision,
            policy_state=v2_policy_state,
            trust_state=v2_trust_state,
            environment_state=v2_environment_state
        )


# Backward compatibility aliases
PolicyState = V2PolicyState
TrustState = V2TrustState
EnvironmentState = V2EnvironmentState
