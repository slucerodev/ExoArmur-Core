"""
Operator-approved policy source for governed execution (2.2.0 pilot).

A versioned JSON policy file is loaded from an operator-controlled path and
verified against an independently configured, pinned SHA-256 digest. The
digest proves content consistency with what the operator approved — it does
NOT establish signer identity.

Rules bind tenant, principal, operation, action class, and approval
requirement. Missing, invalid, altered, or unmatched policy denies by
default. Request data can never supply or override policy, action class, or
trust values.
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from exoarmur.kernel.boundary import (
    ActionClass,
    ActionIntent,
    ApprovalStatus,
    PolicyDecision,
    PolicyDecisionPoint,
    PolicyVerdict,
)
from exoarmur.kernel.ids import make_decision_id

VALID_APPROVAL_REQUIREMENTS = {"none", "quorum", "human"}
VALID_ACTION_CLASSES = {c.value for c in ActionClass}


class PolicyUnavailableError(Exception):
    """Policy file missing, unreadable, or failed digest verification."""


class PolicyVerificationError(Exception):
    """Policy content failed schema validation."""


@dataclass(frozen=True)
class PolicyRule:
    """One operator-approved rule binding principal+tenant+operation."""

    tenant_id: str
    principal_id: str
    operations: List[str]  # operation names, or ["*"]
    action_classes: Dict[str, str]  # operation -> ActionClass value
    default_action_class: Optional[str]
    required_approval: str  # "none" | "quorum" | "human"
    trust_score: Optional[float] = None  # operator-configured, not measured

    def matches(self, intent: ActionIntent) -> bool:
        if intent.tenant_id != self.tenant_id:
            return False
        if intent.actor_id != self.principal_id:
            return False
        return "*" in self.operations or intent.action_type in self.operations

    def action_class_for(self, operation: str) -> Optional[str]:
        if operation in self.action_classes:
            return self.action_classes[operation]
        return self.default_action_class


@dataclass(frozen=True)
class OperatorPolicy:
    """Verified operator policy document."""

    version: int
    rules: List[PolicyRule]
    sha256: str

    def matching_rule(self, intent: ActionIntent) -> Optional[PolicyRule]:
        for rule in self.rules:
            if rule.matches(intent):
                return rule
        return None


def load_operator_policy(
    path: str, expected_sha256: str
) -> OperatorPolicy:
    """Load and verify an operator policy file.

    Args:
        path: Operator-controlled policy file location.
        expected_sha256: Independently configured pinned digest. Must be
            supplied by the operator — never auto-generated or auto-trusted.

    Raises:
        PolicyUnavailableError: file missing/unreadable or digest mismatch.
        PolicyVerificationError: content fails schema validation.
    """
    if not expected_sha256:
        raise PolicyUnavailableError("No pinned policy digest configured")

    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as e:
        raise PolicyUnavailableError(f"Cannot read policy file: {e}") from e

    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != expected_sha256.strip().lower():
        raise PolicyUnavailableError(
            "Policy digest mismatch — file altered or wrong digest pinned"
        )

    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise PolicyVerificationError(f"Policy is not valid JSON: {e}") from e

    return _parse_policy(doc, actual)


def _parse_policy(doc: Any, sha256: str) -> OperatorPolicy:
    if not isinstance(doc, dict):
        raise PolicyVerificationError("Policy root must be an object")
    version = doc.get("version")
    if version != 1:
        raise PolicyVerificationError(f"Unsupported policy version: {version!r}")
    rules_raw = doc.get("rules")
    if not isinstance(rules_raw, list):
        raise PolicyVerificationError("Policy 'rules' must be a list")

    rules: List[PolicyRule] = []
    for i, r in enumerate(rules_raw):
        rules.append(_parse_rule(r, i))
    return OperatorPolicy(version=version, rules=rules, sha256=sha256)


def _parse_rule(r: Any, index: int) -> PolicyRule:
    ctx = f"rules[{index}]"
    if not isinstance(r, dict):
        raise PolicyVerificationError(f"{ctx} must be an object")

    tenant_id = r.get("tenant_id")
    principal_id = r.get("principal_id")
    if not tenant_id or not isinstance(tenant_id, str):
        raise PolicyVerificationError(f"{ctx}.tenant_id required")
    if not principal_id or not isinstance(principal_id, str):
        raise PolicyVerificationError(f"{ctx}.principal_id required")

    operations = r.get("operations")
    if not isinstance(operations, list) or not operations or not all(
        isinstance(o, str) for o in operations
    ):
        raise PolicyVerificationError(f"{ctx}.operations must be a non-empty list")

    approval = r.get("required_approval")
    if approval not in VALID_APPROVAL_REQUIREMENTS:
        raise PolicyVerificationError(
            f"{ctx}.required_approval must be one of {sorted(VALID_APPROVAL_REQUIREMENTS)}"
        )

    action_classes = r.get("action_classes", {})
    if not isinstance(action_classes, dict):
        raise PolicyVerificationError(f"{ctx}.action_classes must be an object")
    for op, cls in action_classes.items():
        if cls not in VALID_ACTION_CLASSES:
            raise PolicyVerificationError(
                f"{ctx}.action_classes[{op!r}] invalid class {cls!r}"
            )

    default_class = r.get("default_action_class")
    if default_class is not None and default_class not in VALID_ACTION_CLASSES:
        raise PolicyVerificationError(
            f"{ctx}.default_action_class invalid: {default_class!r}"
        )

    trust = r.get("trust_score")
    if trust is not None and not (isinstance(trust, (int, float)) and 0.0 <= trust <= 1.0):
        raise PolicyVerificationError(f"{ctx}.trust_score must be in [0.0, 1.0]")

    return PolicyRule(
        tenant_id=tenant_id,
        principal_id=principal_id,
        operations=list(operations),
        action_classes=dict(action_classes),
        default_action_class=default_class,
        required_approval=approval,
        trust_score=float(trust) if trust is not None else None,
    )


class OperatorPolicyDecisionPoint:
    """PolicyDecisionPoint backed by a verified OperatorPolicy.

    Denies by default: no policy loaded, unmatched tenant/principal/
    operation, or unmapped action class all produce DENY.
    """

    def __init__(self, policy: Optional[OperatorPolicy]):
        self.policy = policy

    @property
    def policy_version(self) -> Optional[str]:
        return self.policy.sha256[:16] if self.policy else None

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """Evaluate intent; REQUIRE_APPROVAL when the matched rule demands it."""
        if self.policy is None:
            return self._decision(
                intent,
                PolicyVerdict.DENY,
                "No verified operator policy loaded",
                {"reason": "policy_unavailable"},
            )

        rule = self.policy.matching_rule(intent)
        if rule is None:
            return self._decision(
                intent,
                PolicyVerdict.DENY,
                "No policy rule matches tenant/principal/operation",
                {"reason": "no_matching_rule"},
            )

        action_class = rule.action_class_for(intent.action_type)
        if action_class is None or action_class not in VALID_ACTION_CLASSES:
            return self._decision(
                intent,
                PolicyVerdict.DENY,
                f"No action class mapped for operation {intent.action_type!r}",
                {"reason": "unmapped_action_class", "rule": rule.__dict__},
            )

        if rule.required_approval != "none":
            return self._decision(
                intent,
                PolicyVerdict.REQUIRE_APPROVAL,
                f"Policy requires {rule.required_approval} approval",
                {
                    "reason": "approval_required",
                    "required_approval": rule.required_approval,
                    "action_class": action_class,
                },
                approval_required=True,
            )

        return self._decision(
            intent,
            PolicyVerdict.ALLOW,
            "Operator policy allows",
            {
                "reason": "policy_allow",
                "action_class": action_class,
                "required_approval": rule.required_approval,
            },
        )

    def evaluate_approved(
        self, intent: ActionIntent, approval_valid: bool
    ) -> PolicyDecision:
        """Re-evaluate for an approved resume.

        REQUIRE_APPROVAL converts to ALLOW only when the caller supplies a
        validated approval record; matching rules are still enforced.
        """
        decision = self.evaluate(intent)
        if (
            decision.verdict == PolicyVerdict.REQUIRE_APPROVAL
            and approval_valid
        ):
            return self._decision(
                intent,
                PolicyVerdict.ALLOW,
                "Operator policy allows (approved)",
                {**decision.evidence, "approval_bypass": True},
            )
        return decision

    def approval_status(self, intent_id: str) -> ApprovalStatus:
        return ApprovalStatus.NOT_REQUIRED

    def _decision(
        self,
        intent: ActionIntent,
        verdict: PolicyVerdict,
        rationale: str,
        evidence: Dict[str, Any],
        approval_required: bool = False,
    ) -> PolicyDecision:
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=verdict,
            rationale=rationale,
            evidence=evidence,
            approval_required=approval_required,
            policy_version=self.policy_version,
        )
