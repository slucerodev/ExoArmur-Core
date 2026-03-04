"""
Tests for Simple Policy Decision Point.

Infra-free tests for policy evaluation logic.
"""

import pytest
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyVerdict


class TestSimplePolicyDecisionPoint:
    """Test Simple Policy Decision Point functionality."""
    
    @pytest.fixture
    def sample_intent(self):
        """Create sample ActionIntent for testing."""
        return ActionIntent(
            intent_id="test-intent-123",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/health",
            parameters={
                "method": "GET",
                "headers": {"Authorization": "Bearer token123"}
            },
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def allow_rule(self):
        """Create an allowing policy rule."""
        return PolicyRule(
            rule_id="allow-api-access",
            description="Allow access to API endpoints",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "POST"],
            require_approval=False
        )
    
    @pytest.fixture
    def approval_rule(self):
        """Create a policy rule that requires approval."""
        return PolicyRule(
            rule_id="require-sensitive-approval",
            description="Require approval for sensitive operations",
            allowed_domains=["sensitive.example.com"],
            allowed_methods=["POST", "PUT", "DELETE"],
            require_approval=True
        )
    
    def test_no_rules_deny(self, sample_intent):
        """Test that intents are denied when no rules are configured."""
        pdp = SimplePolicyDecisionPoint(rules=[])
        
        decision = pdp.evaluate(sample_intent)
        
        assert decision.verdict == PolicyVerdict.DENY
        assert "No policy rule allows" in decision.rationale
        assert decision.confidence == 1.0
        assert decision.approval_required is False
        assert decision.policy_version == "v0"
    
    def test_matching_rule_allow(self, sample_intent, allow_rule):
        """Test that matching rule allows the intent."""
        pdp = SimplePolicyDecisionPoint(rules=[allow_rule])
        
        decision = pdp.evaluate(sample_intent)
        
        assert decision.verdict == PolicyVerdict.ALLOW
        assert "Allowed by policy rule" in decision.rationale
        assert allow_rule.rule_id in decision.rationale
        assert decision.confidence == 1.0
        assert decision.approval_required is False
        assert decision.policy_version == "v0"
    
    def test_matching_rule_require_approval(self):
        """Test that matching rule requiring approval returns REQUIRE_APPROVAL."""
        intent = ActionIntent(
            intent_id="test-intent-456",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://sensitive.example.com/data",
            parameters={"method": "POST"},
            safety_context={"risk_level": "medium"},
            timestamp=datetime.now(timezone.utc)
        )
        
        approval_rule = PolicyRule(
            rule_id="require-sensitive-approval",
            description="Require approval for sensitive operations",
            allowed_domains=["sensitive.example.com"],
            allowed_methods=["POST", "PUT", "DELETE"],
            require_approval=True
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.REQUIRE_APPROVAL
        assert "requires approval" in decision.rationale
        assert approval_rule.rule_id in decision.rationale
        assert decision.confidence == 1.0
        assert decision.approval_required is True
        assert decision.policy_version == "v0"
    
    def test_disallowed_domain_deny(self):
        """Test that disallowed domain is denied."""
        intent = ActionIntent(
            intent_id="test-intent-789",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://malicious.example.com/steal",
            parameters={"method": "GET"},
            safety_context={"risk_level": "high"},
            timestamp=datetime.now(timezone.utc)
        )
        
        restricted_rule = PolicyRule(
            rule_id="restricted-access",
            description="Allow access only to trusted domains",
            allowed_domains=["api.example.com", "safe.example.com"],
            allowed_methods=["GET"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[restricted_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.DENY
        # The domain doesn't match, so rule doesn't match, resulting in "No policy rule allows"
        assert "No policy rule allows" in decision.rationale
        assert decision.confidence == 1.0
        assert decision.approval_required is False
        assert decision.policy_version == "v0"
    
    def test_disallowed_method_deny(self):
        """Test that disallowed method is denied."""
        intent = ActionIntent(
            intent_id="test-intent-999",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "DELETE"},
            safety_context={"risk_level": "medium"},
            timestamp=datetime.now(timezone.utc)
        )
        
        read_only_rule = PolicyRule(
            rule_id="read-only-access",
            description="Allow only read operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "HEAD"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[read_only_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.DENY
        # The method doesn't match, so rule doesn't match, resulting in "No policy rule allows"
        assert "No policy rule allows" in decision.rationale
        assert decision.confidence == 1.0
        assert decision.approval_required is False
        assert decision.policy_version == "v0"
    
    def test_multiple_rules_precedence(self):
        """Test that first matching rule takes precedence."""
        intent = ActionIntent(
            intent_id="test-intent-multi",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "POST"},
            safety_context={"risk_level": "medium"},
            timestamp=datetime.now(timezone.utc)
        )
        
        # First rule: allows but requires approval
        approval_rule = PolicyRule(
            rule_id="approval-rule",
            description="Require approval for POST",
            allowed_domains=["api.example.com"],
            allowed_methods=["POST"],
            require_approval=True
        )
        
        # Second rule: would allow without approval (but should not be checked)
        allow_rule = PolicyRule(
            rule_id="allow-rule",
            description="Allow all operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule, allow_rule])
        
        decision = pdp.evaluate(intent)
        
        # Should use first matching rule (approval)
        assert decision.verdict == PolicyVerdict.REQUIRE_APPROVAL
        assert approval_rule.rule_id in decision.rationale
        assert decision.approval_required is True
    
    def test_tenant_isolation(self):
        """Test tenant isolation in policy rules."""
        intent = ActionIntent(
            intent_id="test-intent-tenant",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "GET"},
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc),
            tenant_id="tenant-a"
        )
        
        tenant_rule = PolicyRule(
            rule_id="tenant-specific",
            description="Tenant-specific rule",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET"],
            require_approval=False,
            tenant_id="tenant-a"
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[tenant_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.ALLOW
        assert tenant_rule.rule_id in decision.rationale
    
    def test_tenant_isolation_mismatch(self):
        """Test tenant isolation when tenant doesn't match."""
        intent = ActionIntent(
            intent_id="test-intent-tenant-mismatch",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "GET"},
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc),
            tenant_id="tenant-b"
        )
        
        tenant_rule = PolicyRule(
            rule_id="tenant-specific",
            description="Tenant-specific rule",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET"],
            require_approval=False,
            tenant_id="tenant-a"
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[tenant_rule])
        
        decision = pdp.evaluate(intent)
        
        # Should be denied because tenant doesn't match
        assert decision.verdict == PolicyVerdict.DENY
        assert "No policy rule allows" in decision.rationale
    
    def test_invalid_intent_format(self):
        """Test handling of invalid intent format."""
        # Create intent with invalid URL
        intent = ActionIntent(
            intent_id="test-intent-invalid",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="not-a-valid-url",
            parameters={"method": "GET"},
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc)
        )
        
        rule = PolicyRule(
            rule_id="test-rule",
            description="Test rule",
            allowed_domains=["example.com"],
            allowed_methods=["GET"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.DENY
        # The invalid URL causes rule matching to fail, resulting in "No policy rule allows"
        assert "No policy rule allows" in decision.rationale
        assert decision.confidence == 1.0
    
    def test_approval_status_method(self):
        """Test approval_status method."""
        pdp = SimplePolicyDecisionPoint(rules=[])
        
        status = pdp.approval_status("test-intent-123")
        
        assert status == "not_required"
    
    def test_no_domain_constraints(self):
        """Test rule with no domain constraints (allows all domains)."""
        intent = ActionIntent(
            intent_id="test-intent-any-domain",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://any-domain.com/api",
            parameters={"method": "GET"},
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc)
        )
        
        unrestricted_rule = PolicyRule(
            rule_id="unrestricted",
            description="Allow GET requests to any domain",
            allowed_domains=None,  # No domain constraints
            allowed_methods=["GET"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[unrestricted_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.ALLOW
        assert unrestricted_rule.rule_id in decision.rationale
    
    def test_no_method_constraints(self):
        """Test rule with no method constraints (allows all methods)."""
        intent = ActionIntent(
            intent_id="test-intent-any-method",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "PATCH"},
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc)
        )
        
        unrestricted_rule = PolicyRule(
            rule_id="unrestricted-methods",
            description="Allow any method to api.example.com",
            allowed_domains=["api.example.com"],
            allowed_methods=None,  # No method constraints
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[unrestricted_rule])
        
        decision = pdp.evaluate(intent)
        
        assert decision.verdict == PolicyVerdict.ALLOW
        assert unrestricted_rule.rule_id in decision.rationale
