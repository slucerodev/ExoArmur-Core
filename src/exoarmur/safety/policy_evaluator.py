"""
Policy Evaluator for Safety Gate
Deterministic policy evaluation with safe fallback to preserve current behavior
"""

import logging
from typing import Optional
from dataclasses import dataclass

from spec.contracts.models_v1 import ExecutionIntentV1

logger = logging.getLogger(__name__)


@dataclass
class PolicyEvaluationContext:
    """Context for policy evaluation"""
    intent: Optional[ExecutionIntentV1]
    tenant_id: str
    cell_id: str
    action_class: Optional[str]
    correlation_id: str


class PolicyEvaluator:
    """Deterministic policy evaluator with safe fallback"""
    
    def __init__(self):
        logger.info("PolicyEvaluator initialized")
    
    def evaluate_policy(
        self,
        intent: Optional[ExecutionIntentV1],
        tenant_id: str,
        cell_id: str
    ) -> 'PolicyState':
        """
        Evaluate policy state with deterministic fallback
        
        Args:
            intent: Execution intent for context
            tenant_id: Tenant identifier
            cell_id: Cell identifier
            
        Returns:
            PolicyState with deterministic evaluation
        """
        from exoarmur.safety.safety_gate import PolicyState
        
        context = PolicyEvaluationContext(
            intent=intent,
            tenant_id=tenant_id,
            cell_id=cell_id,
            action_class=intent.action_class if intent else None,
            correlation_id=intent.correlation_id if intent else "unknown"
        )
        
        try:
            # Attempt real policy evaluation
            policy_state = self._evaluate_policy_internal(context)
            logger.debug(f"Policy evaluation successful: {policy_state}")
            return policy_state
            
        except Exception as e:
            # SAFE FALLBACK: Preserve current hardcoded behavior
            logger.warning(f"Policy evaluation failed, using safe fallback: {e}")
            return self._get_safe_fallback_policy_state()
    
    def _evaluate_policy_internal(self, context: PolicyEvaluationContext) -> 'PolicyState':
        """
        Internal policy evaluation logic
        
        This method implements the actual policy evaluation.
        If it fails for any reason, the fallback ensures behavior preservation.
        """
        from exoarmur.safety.safety_gate import PolicyState
        
        # TODO: Implement actual policy verification logic here
        # For now, maintain current behavior but with extensible structure
        policy_verified = True  # Default to current behavior
        
        # TODO: Implement actual kill switch checks here
        # For now, maintain current behavior but with extensible structure
        kill_switch_global = False  # Default to current behavior
        kill_switch_tenant = False  # Default to current behavior
        
        # TODO: Implement actual required approval logic here
        # For now, maintain current behavior but with extensible structure
        required_approval = "none"  # Default to current behavior
        
        return PolicyState(
            policy_verified=policy_verified,
            kill_switch_global=kill_switch_global,
            kill_switch_tenant=kill_switch_tenant,
            required_approval=required_approval
        )
    
    def _get_safe_fallback_policy_state(self) -> 'PolicyState':
        """
        Safe fallback that preserves current hardcoded behavior
        
        This ensures that even if the evaluator fails completely,
        the system behaves exactly as it did before integration.
        """
        from exoarmur.safety.safety_gate import PolicyState
        
        # Return the exact same values that were hardcoded in main.py
        return PolicyState(
            policy_verified=True,  # From main.py line 465
            kill_switch_global=False,  # From main.py line 466
            kill_switch_tenant=False,  # From main.py line 467
            required_approval="none"  # From main.py line 468
        )
