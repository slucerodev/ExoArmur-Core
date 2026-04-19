"""
Policy Evaluator for Safety Gate
Deterministic policy evaluation with governance rules based on action class.

Governance policy (ExoArmur baseline):
  A0_observe           -> allow         (read-only observation, no risk)
  A1_soft_containment  -> allow         (reversible, low-risk containment)
  A2_hard_containment  -> require_human (irreversible impact, human review required)
  A3_irreversible      -> deny          (permanent action, denied by default)
  unknown / missing    -> require_human (fail-safe: unknown action class requires review)

Kill switches (env vars, checked before action-class rules):
  EXOARMUR_KILL_SWITCH_GLOBAL=true  -> deny all
  EXOARMUR_KILL_SWITCH_<TENANT>=true -> deny for that tenant (uppercased, hyphens→underscores)
"""

import logging
import os
from typing import Optional
from dataclasses import dataclass

from spec.contracts.models_v1 import ExecutionIntentV1

logger = logging.getLogger(__name__)

# Action-class governance table: maps action_class -> required_approval verdict
_ACTION_CLASS_POLICY: dict = {
    "A0_observe":          "none",
    "A1_soft_containment": "none",
    "A2_hard_containment": "human",
    "A3_irreversible":     "deny",   # special: causes policy_verified=False
}

# Trust threshold below which policy escalates to human review regardless of action class
_TRUST_ESCALATION_THRESHOLD = 0.60


@dataclass
class PolicyEvaluationContext:
    """Context for policy evaluation"""
    intent: Optional[ExecutionIntentV1]
    tenant_id: str
    cell_id: str
    action_class: Optional[str]
    correlation_id: str


class PolicyEvaluator:
    """Deterministic policy evaluator — ExoArmur baseline governance rules"""

    def __init__(self):
        logger.info("PolicyEvaluator initialized with baseline governance rules")

    def evaluate_policy(
        self,
        intent: Optional[ExecutionIntentV1],
        tenant_id: str,
        cell_id: str
    ) -> 'PolicyState':
        """
        Evaluate policy state against ExoArmur baseline governance rules.

        Args:
            intent: Execution intent for context (may be None pre-execution)
            tenant_id: Tenant identifier
            cell_id: Cell identifier

        Returns:
            PolicyState reflecting governance decision
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
            return self._evaluate_policy_internal(context)
        except Exception as e:
            logger.warning(f"Policy evaluation error, applying safe fallback: {e}")
            return self._get_safe_fallback_policy_state()

    def _evaluate_policy_internal(self, context: PolicyEvaluationContext) -> 'PolicyState':
        """Apply ExoArmur baseline governance rules deterministically."""
        from exoarmur.safety.safety_gate import PolicyState

        # --- Kill switch checks (highest precedence) ---
        kill_switch_global = os.getenv("EXOARMUR_KILL_SWITCH_GLOBAL", "false").lower() == "true"
        if kill_switch_global:
            logger.warning("Global kill switch engaged — denying all execution")
            return PolicyState(
                policy_verified=False,
                kill_switch_global=True,
                kill_switch_tenant=False,
                required_approval="none"
            )

        tenant_env_key = "EXOARMUR_KILL_SWITCH_" + context.tenant_id.upper().replace("-", "_")
        kill_switch_tenant = os.getenv(tenant_env_key, "false").lower() == "true"
        if kill_switch_tenant:
            logger.warning(f"Tenant kill switch engaged for {context.tenant_id} — denying")
            return PolicyState(
                policy_verified=False,
                kill_switch_global=False,
                kill_switch_tenant=True,
                required_approval="none"
            )

        # --- Action-class governance rules ---
        action_class = context.action_class or "unknown"
        approval = _ACTION_CLASS_POLICY.get(action_class, "human")  # unknown -> human review

        if action_class == "A3_irreversible":
            logger.warning(
                f"A3_irreversible action denied by policy "
                f"[correlation={context.correlation_id}, tenant={context.tenant_id}]"
            )
            return PolicyState(
                policy_verified=False,
                kill_switch_global=False,
                kill_switch_tenant=False,
                required_approval="none"
            )

        logger.info(
            f"Policy decision: action_class={action_class} "
            f"required_approval={approval} "
            f"[correlation={context.correlation_id}, tenant={context.tenant_id}]"
        )
        return PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval=approval
        )

    def _get_safe_fallback_policy_state(self) -> 'PolicyState':
        """Fail-safe fallback: require human review on any evaluator error."""
        from exoarmur.safety.safety_gate import PolicyState

        return PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="human"
        )
