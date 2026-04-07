"""
Integration test for Simple Policy Decision Point with ProxyPipeline.

Tests that the PDP influences pipeline behavior correctly.
"""

import pytest
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, V2AuditEmitter
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyVerdict
from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule


class FakeSafetyGate:
    """Fake SafetyGate that always allows."""
    
    def __init__(self):
        self.evaluate_called = False
    
    def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
        self.evaluate_called = True
        from exoarmur.safety.safety_gate import SafetyVerdict
        return SafetyVerdict(
            verdict="allow",
            rationale="Safety check passed",
            rule_ids=[]
        )


class FakeExecutor:
    """Fake Executor that always succeeds."""
    
    def __init__(self):
        self.execute_called = False
        self.execute_intent = None
    
    def name(self) -> str:
        return "fake-executor"
    
    def capabilities(self) -> dict:
        return {"actions": ["test_action"]}
    
    def execute(self, intent):
        self.execute_called = True
        self.execute_intent = intent
        from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
        return ExecutorResult(
            success=True,
            output={"status": "success"},
            error=None,
            evidence={"execution_time": 0.1}
        )


class TestPolicyPipelineIntegration:
    """Test PDP integration with ProxyPipeline."""
    
    @pytest.fixture
    def sample_intent(self):
        """Create sample ActionIntent for testing."""
        return ActionIntent(
            intent_id="test-intent-123",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/health",
            parameters={"method": "GET"},
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
    def deny_rule(self):
        """Create a policy rule that denies by domain."""
        return PolicyRule(
            rule_id="deny-malicious",
            description="Deny access to malicious domains",
            allowed_domains=["safe.example.com"],  # Doesn't match our intent
            allowed_methods=["GET"],
            require_approval=False
        )
    
    @pytest.fixture
    def approval_rule(self):
        """Create a policy rule that requires approval."""
        return PolicyRule(
            rule_id="require-sensitive-approval",
            description="Require approval for sensitive operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["POST", "PUT", "DELETE"],
            require_approval=True
        )
    
    def test_policy_allow_pipeline_flow(self, sample_intent, allow_rule):
        """Test that ALLOW policy permits full pipeline execution."""
        # Setup
        pdp = SimplePolicyDecisionPoint(rules=[allow_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(sample_intent)
        
        # Verify
        assert result.success is True
        assert result.output["status"] == "success"
        assert result.error is None
        
        # Verify all components were called
        assert safety_gate.evaluate_called is True
        assert executor.execute_called is True
        assert executor.execute_intent == sample_intent
        
        # Verify audit record
        assert len(audit_emitter.audit_records) == 1
        audit_record = audit_emitter.audit_records[0]
        assert audit_record.event_kind == "execution"
        assert audit_record.payload_ref["ref"] == sample_intent.intent_id
        assert audit_record.payload_ref["details"]["execution_success"] is True
    
    def test_policy_deny_pipeline_flow(self, sample_intent, deny_rule):
        """Test that DENY policy stops pipeline execution."""
        # Setup
        pdp = SimplePolicyDecisionPoint(rules=[deny_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(sample_intent)
        
        # Verify
        assert result.success is False
        assert result.error == "DENIED"
        assert result.evidence["policy_decision"] == "deny"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
        assert safety_gate.evaluate_called is False
        
        # Verify audit record for policy denial
        assert len(audit_emitter.audit_records) == 1
        audit_record = audit_emitter.audit_records[0]
        assert audit_record.event_kind == "policy_denial"
        assert audit_record.payload_ref["ref"] == sample_intent.intent_id
        assert audit_record.payload_ref["details"]["rationale"] is not None
    
    def test_policy_require_approval_pipeline_flow(self, sample_intent):
        """Test that REQUIRE_APPROVAL policy creates dispatch."""
        # Setup
        approval_rule = PolicyRule(
            rule_id="require-approval",
            description="Require approval for GET requests",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET"],
            require_approval=True
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(sample_intent)
        
        # Verify
        assert hasattr(result, 'status')  # Should be ExecutionDispatch
        assert result.status.value == "approval_pending"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
        assert safety_gate.evaluate_called is False
        
        # Verify audit record for policy deferral
        assert len(audit_emitter.audit_records) == 1
        audit_record = audit_emitter.audit_records[0]
        assert audit_record.event_kind == "policy_deferral"
        assert audit_record.payload_ref["ref"] == sample_intent.intent_id
        assert audit_record.payload_ref["details"]["approval_required"] is True
    
    def test_policy_method_rejection(self, sample_intent):
        """Test policy rejection based on HTTP method."""
        # Create intent with disallowed method
        delete_intent = ActionIntent(
            intent_id="test-intent-delete",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/data",
            parameters={"method": "DELETE"},
            safety_context={"risk_level": "medium"},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Rule that only allows GET/POST
        read_only_rule = PolicyRule(
            rule_id="read-only",
            description="Allow only read operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "POST"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[read_only_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(delete_intent)
        
        # Verify
        assert result.success is False
        assert result.error == "DENIED"
        # The method doesn't match, so rule doesn't match, resulting in deny
        assert result.evidence.get("policy_decision") == "deny"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
    
    def test_policy_domain_rejection(self):
        """Test policy rejection based on domain."""
        # Create intent to disallowed domain
        malicious_intent = ActionIntent(
            intent_id="test-intent-malicious",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://malicious.example.com/steal",
            parameters={"method": "GET"},
            safety_context={"risk_level": "high"},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Rule that only allows safe domains
        safe_rule = PolicyRule(
            rule_id="safe-domains",
            description="Allow only safe domains",
            allowed_domains=["api.example.com", "safe.example.com"],
            allowed_methods=["GET"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[safe_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(malicious_intent)
        
        # Verify
        assert result.success is False
        assert result.error == "DENIED"
        # The domain doesn't match, so rule doesn't match, resulting in deny
        assert result.evidence.get("policy_decision") == "deny"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
    
    def test_multiple_rules_precedence_in_pipeline(self, sample_intent):
        """Test that first matching rule takes precedence in pipeline context."""
        # First rule: requires approval
        approval_rule = PolicyRule(
            rule_id="approval-first",
            description="Require approval for api.example.com",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET"],
            require_approval=True
        )
        
        # Second rule: would allow (but shouldn't be checked)
        allow_rule = PolicyRule(
            rule_id="allow-second",
            description="Allow all operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule, allow_rule])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(sample_intent)
        
        # Verify first rule was used (approval required)
        assert hasattr(result, 'status')  # Should be ExecutionDispatch
        assert result.status.value == "approval_pending"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
        
        # Verify audit record mentions approval rule
        audit_record = audit_emitter.audit_records[0]
        assert "approval-first" in audit_record.payload_ref["details"]["rationale"]
    
    def test_no_rules_deny_in_pipeline(self, sample_intent):
        """Test that no rules results in denial in pipeline context."""
        pdp = SimplePolicyDecisionPoint(rules=[])
        safety_gate = FakeSafetyGate()
        executor = FakeExecutor()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter)
        
        # Execute
        result = pipeline.execute(sample_intent)
        
        # Verify
        assert result.success is False
        assert result.error == "DENIED"
        # No rules match, resulting in deny
        assert result.evidence.get("policy_decision") == "deny"
        
        # Verify executor was NOT called
        assert executor.execute_called is False
