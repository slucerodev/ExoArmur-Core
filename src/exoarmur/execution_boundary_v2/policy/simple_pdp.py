"""
Simple Policy Decision Point implementation.

Provides deterministic policy evaluation for ActionIntent objects.
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

from ..interfaces.policy_decision_point import PolicyDecisionPoint
from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision, PolicyVerdict
from .policy_models import PolicyRule

logger = logging.getLogger(__name__)


class SimplePolicyDecisionPoint(PolicyDecisionPoint):
    """Simple deterministic Policy Decision Point for execution governance."""
    
    def __init__(self, rules: List[PolicyRule]):
        """Initialize PDP with a list of policy rules."""
        self.rules = rules
        logger.info(f"SimplePolicyDecisionPoint initialized with {len(rules)} rules")
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """Evaluate ActionIntent against policy rules."""
        logger.info(f"Evaluating intent {intent.intent_id} against policy rules")
        
        # Extract URL and method from intent
        try:
            parsed_url = urlparse(intent.target)
            domain = parsed_url.netloc.lower()
            method = intent.parameters.get("method", "").upper()
        except Exception as e:
            logger.error(f"Failed to parse intent {intent.intent_id}: {e}")
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=f"Invalid intent format: {e}",
                confidence=1.0,
                approval_required=False,
                policy_version="v0"
            )
        
        # Find matching rule
        matching_rule = self._find_matching_rule(intent, domain, method)
        
        if not matching_rule:
            logger.warning(f"No matching rule found for intent {intent.intent_id}")
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=f"No policy rule allows {method} requests to {domain}",
                confidence=1.0,
                approval_required=False,
                policy_version="v0"
            )
        
        # Apply rule logic
        if matching_rule.require_approval:
            logger.info(f"Intent {intent.intent_id} requires approval per rule {matching_rule.rule_id}")
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                rationale=f"Rule {matching_rule.rule_id} requires approval for {method} requests to {domain}",
                confidence=1.0,
                approval_required=True,
                policy_version="v0"
            )
        
        # Check domain and method constraints
        if matching_rule.allowed_domains and domain not in matching_rule.allowed_domains:
            logger.warning(f"Domain {domain} not allowed by rule {matching_rule.rule_id}")
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=f"Domain {domain} not allowed by policy rule {matching_rule.rule_id}",
                confidence=1.0,
                approval_required=False,
                policy_version="v0"
            )
        
        if matching_rule.allowed_methods and method not in matching_rule.allowed_methods:
            logger.warning(f"Method {method} not allowed by rule {matching_rule.rule_id}")
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=f"Method {method} not allowed by policy rule {matching_rule.rule_id}",
                confidence=1.0,
                approval_required=False,
                policy_version="v0"
            )
        
        # Allow the request
        logger.info(f"Intent {intent.intent_id} allowed by rule {matching_rule.rule_id}")
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale=f"Allowed by policy rule {matching_rule.rule_id}: {matching_rule.description}",
            confidence=1.0,
            approval_required=False,
            policy_version="v0"
        )
    
    def approval_status(self, intent_id: str) -> str:
        """Get approval status for an intent (simplified implementation)."""
        return "not_required"
    
    def _find_matching_rule(self, intent: ActionIntent, domain: str, method: str) -> Optional[PolicyRule]:
        """Find the first rule that matches the intent."""
        for rule in self.rules:
            # Check tenant isolation
            if rule.tenant_id and hasattr(intent, 'tenant_id'):
                if rule.tenant_id != intent.tenant_id:
                    continue
            
            # Check domain constraints
            if rule.allowed_domains:
                if domain not in rule.allowed_domains:
                    continue
            
            # Check method constraints
            if rule.allowed_methods:
                if method not in rule.allowed_methods:
                    continue
            
            # Rule matches
            return rule
        
        return None