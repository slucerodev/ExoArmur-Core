"""
Operator-approved execution policy.

Loads a versioned policy file from an operator-controlled location and
verifies its content against an independently configured, operator-pinned
SHA-256 digest. The digest is never generated or trusted automatically:
operators compute it out-of-band and pin it via configuration.

A successfully loaded policy yields:
  - policy_verified=True (content consistency with the pinned digest;
    this is NOT cryptographic signer identity)
  - per-rule action-class mappings and approval requirements

Rules bind (tenant_id, principal_id, operation). Matching is exact;
absent or unmatched rules deny by default. The principal_id in a rule
must be an authenticated principal supplied by the hosting application —
matching a telemetry subject_id to a rule is not authentication.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

POLICY_SCHEMA_VERSION = 1

_VALID_APPROVAL_REQUIREMENTS = ("none", "quorum", "human")
_V1_ACTION_CLASSES = frozenset({
    "A0_observe",
    "A1_soft_containment",
    "A2_hard_containment",
    "A3_irreversible",
})


class PolicyUnavailableError(Exception):
    """Policy file is missing, unreadable, unparseable, or misconfigured."""


class PolicyVerificationError(Exception):
    """Policy content does not match the operator-pinned digest."""


@dataclass(frozen=True)
class PolicyRule:
    """A single operator-approved authorization rule."""

    tenant_id: str
    principal_id: str
    operations: Tuple[str, ...]
    action_classes: Mapping[str, str]
    default_action_class: Optional[str]
    required_approval: str

    def resolve_action_class(self, operation: str) -> Optional[str]:
        """Resolve the V1 action class for an operation; None if unmapped."""
        return (
            self.action_classes.get(operation)
            or self.action_classes.get("*")
            or self.default_action_class
        )


@dataclass(frozen=True)
class OperatorPolicy:
    """A verified, versioned operator policy document."""

    version: int
    rules: Tuple[PolicyRule, ...]
    source_path: str
    sha256: str

    def matching_rule(
        self,
        tenant_id: Optional[str],
        principal_id: Optional[str],
        operation: Optional[str],
    ) -> Optional[PolicyRule]:
        """Return the first rule matching tenant+principal+operation.

        Exact match on tenant_id and principal_id; operation may match a
        listed operation or the "*" wildcard. Returns None (deny) when
        nothing matches — including when any binding value is absent.
        """
        if not tenant_id or not principal_id or not operation:
            return None
        for rule in self.rules:
            if rule.tenant_id != tenant_id or rule.principal_id != principal_id:
                continue
            if operation in rule.operations or "*" in rule.operations:
                return rule
        return None


def _validate_rule(raw: object, index: int) -> PolicyRule:
    if not isinstance(raw, dict):
        raise PolicyUnavailableError(f"policy rule {index} is not an object")

    tenant_id = raw.get("tenant_id")
    principal_id = raw.get("principal_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise PolicyUnavailableError(f"policy rule {index} has missing tenant_id")
    if not isinstance(principal_id, str) or not principal_id.strip():
        raise PolicyUnavailableError(f"policy rule {index} has missing principal_id")

    operations = raw.get("operations")
    if (
        not isinstance(operations, list)
        or not operations
        or not all(isinstance(op, str) and op for op in operations)
    ):
        raise PolicyUnavailableError(
            f"policy rule {index} has missing or invalid operations"
        )

    action_classes = raw.get("action_classes", {})
    if not isinstance(action_classes, dict):
        raise PolicyUnavailableError(
            f"policy rule {index} action_classes must be an object"
        )
    for op, cls in action_classes.items():
        if not isinstance(op, str) or not isinstance(cls, str):
            raise PolicyUnavailableError(
                f"policy rule {index} action_classes must map strings to strings"
            )
        if cls not in _V1_ACTION_CLASSES:
            raise PolicyUnavailableError(
                f"policy rule {index} maps {op!r} to unsupported action_class {cls!r}"
            )

    default_action_class = raw.get("default_action_class")
    if default_action_class is not None and default_action_class not in _V1_ACTION_CLASSES:
        raise PolicyUnavailableError(
            f"policy rule {index} has unsupported default_action_class {default_action_class!r}"
        )

    required_approval = raw.get("required_approval")
    if required_approval not in _VALID_APPROVAL_REQUIREMENTS:
        raise PolicyUnavailableError(
            f"policy rule {index} has missing or invalid required_approval "
            f"{required_approval!r}; expected one of {_VALID_APPROVAL_REQUIREMENTS}"
        )

    return PolicyRule(
        tenant_id=tenant_id,
        principal_id=principal_id,
        operations=tuple(operations),
        action_classes=dict(action_classes),
        default_action_class=default_action_class,
        required_approval=required_approval,
    )


def load_operator_policy(
    path: Optional[str],
    expected_sha256: Optional[str],
) -> OperatorPolicy:
    """Load and verify an operator policy file.

    Fails closed: any missing input, read error, digest mismatch, or
    schema violation raises PolicyUnavailableError/PolicyVerificationError.
    The expected digest must be supplied independently by the operator;
    this function never computes-and-trusts it.
    """
    if not path or not str(path).strip():
        raise PolicyUnavailableError("operator policy file path is not configured")
    if not expected_sha256 or not str(expected_sha256).strip():
        raise PolicyUnavailableError(
            "operator policy pinned SHA-256 digest is not configured; "
            "refusing to trust unverified policy content"
        )

    policy_path = Path(path)
    try:
        content = policy_path.read_bytes()
    except OSError as exc:
        raise PolicyUnavailableError(
            f"cannot read operator policy file {policy_path}: {exc}"
        ) from exc

    actual = hashlib.sha256(content).hexdigest()
    expected = str(expected_sha256).strip().lower()
    if actual != expected:
        raise PolicyVerificationError(
            f"operator policy digest mismatch for {policy_path}: "
            f"expected {expected}, got {actual}"
        )

    try:
        document = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyUnavailableError(
            f"operator policy file {policy_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise PolicyUnavailableError("operator policy document must be a JSON object")

    version = document.get("version")
    if version != POLICY_SCHEMA_VERSION:
        raise PolicyUnavailableError(
            f"unsupported operator policy version {version!r}; "
            f"expected {POLICY_SCHEMA_VERSION}"
        )

    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list):
        raise PolicyUnavailableError("operator policy 'rules' must be a list")

    rules = tuple(_validate_rule(raw, i) for i, raw in enumerate(raw_rules))

    logger.info(
        "Loaded verified operator policy %s (version=%s, rules=%d, sha256=%s)",
        policy_path, version, len(rules), actual,
    )
    return OperatorPolicy(
        version=version,
        rules=rules,
        source_path=str(policy_path),
        sha256=actual,
    )


class OperatorPolicyDecisionPoint:
    """PolicyDecisionPoint backed by a verified OperatorPolicy.

    Default deny: an unavailable policy, an unmatched
    (tenant, principal, operation), or a missing approval store entry
    never produces ALLOW. The intent's actor_id is treated as the
    principal only when the hosting application populated it from
    authenticated context — this class cannot verify authentication
    itself.
    """

    def __init__(self, policy: Optional[OperatorPolicy], approval_store=None):
        self.policy = policy
        self.approval_store = approval_store

    def evaluate(self, intent) -> "PolicyDecision":
        from exoarmur.execution_boundary_v2.models.policy_decision import (
            PolicyDecision,
            PolicyVerdict,
        )

        if self.policy is None:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale="Operator policy is unavailable or unverified; denying",
                confidence=1.0,
                approval_required=False,
                policy_version="operator-policy-unavailable",
            )

        rule = self.policy.matching_rule(
            getattr(intent, "tenant_id", None),
            getattr(intent, "actor_id", None),
            getattr(intent, "action_type", None),
        )
        if rule is None:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=(
                    "No operator policy rule matches "
                    f"tenant={getattr(intent, 'tenant_id', None)!r} "
                    f"principal={getattr(intent, 'actor_id', None)!r} "
                    f"operation={getattr(intent, 'action_type', None)!r}"
                ),
                confidence=1.0,
                approval_required=False,
                policy_version=f"operator-policy-v{self.policy.version}",
            )

        if rule.required_approval != "none":
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                rationale=(
                    f"Operator policy rule requires {rule.required_approval} "
                    f"approval for {intent.action_type!r}"
                ),
                confidence=1.0,
                approval_required=True,
                policy_version=f"operator-policy-v{self.policy.version}",
            )

        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale=(
                f"Allowed by verified operator policy rule "
                f"(tenant={rule.tenant_id}, principal={rule.principal_id})"
            ),
            confidence=1.0,
            approval_required=False,
            policy_version=f"operator-policy-v{self.policy.version}",
        )

    def approval_status(self, intent_id: str) -> str:
        if self.policy is None or not self.approval_store:
            return "not_required"
        if not any(rule.required_approval != "none" for rule in self.policy.rules):
            return "not_required"
        record = self.approval_store.get(intent_id)
        if not record:
            return "pending"
        decision = getattr(record, "decision", None)
        value = getattr(decision, "value", decision)
        if value == "APPROVE":
            return "approved"
        if value == "DENY":
            return "denied"
        return "pending"

    def evaluate_with_approval_bypass(self, intent) -> "PolicyDecision":
        """Re-evaluate after approval; an approved intent bypasses only the
        approval requirement — tenant/principal/operation matching and
        policy availability are still enforced."""
        from exoarmur.execution_boundary_v2.models.policy_decision import (
            PolicyDecision,
            PolicyVerdict,
        )

        decision = self.evaluate(intent)
        if (
            decision.verdict == PolicyVerdict.REQUIRE_APPROVAL
            and self.approval_status(getattr(intent, "intent_id", "")) == "approved"
        ):
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                rationale=(
                    f"Approval bypassed for intent {intent.intent_id} "
                    "(previously approved)"
                ),
                confidence=1.0,
                approval_required=False,
                policy_version=decision.policy_version,
            )
        return decision
