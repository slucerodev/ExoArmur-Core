"""
Tests for execution boundary V2 proxy pipeline.

Comprehensive tests for proxy pipeline using V1 primitives.
Infra-free with test doubles for all external dependencies.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, V2AuditEmitter
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.execution_boundary_v2.models.execution_dispatch import ExecutionDispatch, DispatchStatus
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorPlugin, ExecutorResult, TargetValidationResult, ValidationResult


class FakePDP:
    """Fake PolicyDecisionPoint for testing."""
    
    def __init__(self, verdict: PolicyVerdict, rationale: str = None):
        self.verdict = verdict
        self.rationale = rationale or f"Test {verdict.value}"
        self.evaluate_called = False
        self.evaluate_intent = None
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        self.evaluate_called = True
        self.evaluate_intent = intent
        
        return PolicyDecision(
            verdict=self.verdict,
            rationale=self.rationale,
            confidence=0.95,
            approval_required=(self.verdict == PolicyVerdict.REQUIRE_APPROVAL),
            policy_version="1.0.0"
        )
    
    def approval_status(self, intent_id: str):
        return "not_required"


class FakeExecutor:
    """Fake ExecutorPlugin for testing."""
    
    def __init__(self, success: bool = True, output: dict = None, error: str = None):
        self.success = success
        self.output = output or {"status": "ok"}
        self.error = error
        self.execute_called = False
        self.execute_intent = None
    
    def name(self) -> str:
        return "fake-executor"
    
    def capabilities(self) -> dict:
        return {"actions": ["test_action"]}
    
    def validate_target(self, intent: ActionIntent) -> TargetValidationResult:
        return TargetValidationResult(
            result=ValidationResult.VALID,
            evidence={"validated": True}
        )

    def execute(self, intent: ActionIntent, policy_decision=None, governance_context=None) -> ExecutorResult:
        self.execute_called = True
        self.execute_intent = intent
        
        return ExecutorResult(
            success=self.success,
            output=self.output,
            error=self.error,
            evidence={"execution_time": 0.1}
        )


class FakeSafetyGate:
    """Fake SafetyGate for testing."""
    
    def __init__(self, allow: bool = True, rationale: str = "Safety check passed"):
        self.allow = allow
        self.rationale = rationale
        self.evaluate_called = False
    
    def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
        from exoarmur.safety.safety_gate import SafetyVerdict
        
        self.evaluate_called = True
        
        if self.allow:
            return SafetyVerdict(
                verdict="allow",
                rationale=self.rationale,
                rule_ids=[]
            )
        else:
            return SafetyVerdict(
                verdict="deny",
                rationale="Safety check failed",
                rule_ids=["SAFETY-001"]
            )


@pytest.fixture
def sample_intent():
    """Create a sample ActionIntent for testing."""
    return ActionIntent(
        intent_id="01HV1234567890ABCDEFGHJKMN",
        actor_id="agent-001",
        actor_type="agent",
        action_type="http_request",
        target="https://api.example.com/health",
        parameters={"method": "GET"},
        safety_context={"risk_level": "low"},
        timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def audit_emitter():
    """Create an V2AuditEmitter for testing."""
    return V2AuditEmitter()


def test_proxy_pipeline_policy_deny(sample_intent, audit_emitter):
    """Test DENY policy verdict: no executor call, audit emitted, result indicates denied."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.DENY, "High risk action")
    fake_executor = FakeExecutor()
    fake_safety_gate = FakeSafetyGate()
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify
    assert isinstance(result, ExecutorResult)
    assert result.success is False
    assert result.error == "DENIED"
    assert result.evidence["final_verdict"] == "deny"
    
    # Verify PDP was called, executor was not
    assert fake_pdp.evaluate_called is True
    assert fake_pdp.evaluate_intent == sample_intent
    assert fake_executor.execute_called is False
    
    # Verify audit record emitted
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "policy_denial"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id
    assert audit_record.payload_ref["details"]["policy_verdict"] == "deny"


def test_proxy_pipeline_policy_require_approval(sample_intent, audit_emitter):
    """Test REQUIRE_APPROVAL: no executor call, dispatch indicates approval pending, audit emitted."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.REQUIRE_APPROVAL, "Human approval required")
    fake_executor = FakeExecutor()
    fake_safety_gate = FakeSafetyGate()
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify
    assert isinstance(result, ExecutionDispatch)
    assert result.status == DispatchStatus.APPROVAL_PENDING
    assert result.details["final_verdict"] == "require_approval"
    
    # Verify PDP was called, executor was not
    assert fake_pdp.evaluate_called is True
    assert fake_executor.execute_called is False
    
    # Verify audit record emitted
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "approval_required"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id
    assert audit_record.payload_ref["details"]["final_verdict"] == "require_approval"


def test_proxy_pipeline_policy_defer(sample_intent, audit_emitter):
    """Test DEFER: no executor call, dispatch indicates blocked, audit emitted."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.DEFER, "Deferred for review")
    fake_executor = FakeExecutor()
    fake_safety_gate = FakeSafetyGate()
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify - DEFER maps to DENY via default_restrictive_fallback in resolve_verdicts
    assert isinstance(result, ExecutorResult)
    assert result.success is False
    assert result.error == "DENIED"
    
    # Verify PDP was called, executor was not
    assert fake_pdp.evaluate_called is True
    assert fake_executor.execute_called is False
    
    # Verify audit record emitted
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "policy_denial"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id


def test_proxy_pipeline_allow_safety_gate_blocks(sample_intent, audit_emitter):
    """Test ALLOW + SafetyGate blocks: no executor call, result indicates safety blocked, audit emitted."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.ALLOW, "Low risk action")
    fake_executor = FakeExecutor()
    fake_safety_gate = FakeSafetyGate(allow=False, rationale="Safety policy violation")
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify
    assert isinstance(result, ExecutorResult)
    assert result.success is False
    assert result.error == "SAFETY_GATE_BLOCKED"
    assert result.evidence["final_verdict"] == "deny"
    
    # Verify PDP and safety gate were called, executor was not
    assert fake_pdp.evaluate_called is True
    assert fake_safety_gate.evaluate_called is True
    assert fake_executor.execute_called is False
    
    # Verify audit record emitted
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "safety_gate_block"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id
    assert audit_record.payload_ref["details"]["safety_verdict"] == "deny"


def test_proxy_pipeline_allow_safety_gate_passes_executor_success(sample_intent, audit_emitter):
    """Test ALLOW + SafetyGate passes: executor called once, audit emitted, result success reflects executor output."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.ALLOW, "Low risk action")
    fake_executor = FakeExecutor(
        success=True,
        output={"status_code": 200, "response": "OK"},
        error=None
    )
    fake_safety_gate = FakeSafetyGate(allow=True)
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify
    assert isinstance(result, ExecutorResult)
    assert result.success is True
    assert result.output["status_code"] == 200
    assert result.output["response"] == "OK"
    assert result.error is None
    assert result.evidence["execution_time"] == 0.1
    
    # Verify PDP, safety gate, and executor were all called
    assert fake_pdp.evaluate_called is True
    assert fake_safety_gate.evaluate_called is True
    assert fake_executor.execute_called is True
    assert fake_executor.execute_intent == sample_intent
    
    # Verify audit record emitted
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "execution"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id
    assert audit_record.payload_ref["details"]["success"] is True


def test_proxy_pipeline_allow_safety_gate_passes_executor_failure(sample_intent, audit_emitter):
    """Test ALLOW + SafetyGate passes but executor fails: audit emitted, result reflects executor failure."""
    # Setup
    fake_pdp = FakePDP(PolicyVerdict.ALLOW, "Low risk action")
    fake_executor = FakeExecutor(
        success=False,
        output={},
        error="Connection timeout"
    )
    fake_safety_gate = FakeSafetyGate(allow=True)
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute
    result = pipeline.execute(sample_intent)
    
    # Verify
    assert isinstance(result, ExecutorResult)
    assert result.success is False
    assert result.error == "Connection timeout"
    assert result.evidence["execution_time"] == 0.1
    
    # Verify all components were called
    assert fake_pdp.evaluate_called is True
    assert fake_safety_gate.evaluate_called is True
    assert fake_executor.execute_called is True
    
    # Verify audit record emitted with failure outcome
    assert len(audit_emitter.audit_records) == 1
    audit_record = audit_emitter.audit_records[0]
    assert audit_record.event_kind == "execution"
    assert audit_record.payload_ref["ref"] == sample_intent.intent_id
    assert audit_record.payload_ref["details"]["success"] is False
    assert audit_record.payload_ref["details"]["error"] == "Connection timeout"


def test_audit_emitter_functionality():
    """Test V2AuditEmitter functionality directly."""
    emitter = V2AuditEmitter()
    
    # Emit audit record
    audit_record = emitter.emit_audit_record(
        intent_id="test-123",
        event_type="test_event",
        outcome="success",
        details={"key": "value"}
    )
    
    # Verify record structure
    assert audit_record.payload_ref["ref"] == "test-123"
    assert audit_record.event_kind == "test_event"
    assert audit_record.payload_ref["details"]["key"] == "value"
    assert audit_record.schema_version == "1.0.0"
    
    # Verify stored in emitter
    assert len(emitter.audit_records) == 1
    assert emitter.audit_records[0] == audit_record


def test_proxy_pipeline_multiple_intents(sample_intent, audit_emitter):
    """Test pipeline with multiple intents to ensure state isolation."""
    fake_pdp = FakePDP(PolicyVerdict.ALLOW)
    fake_executor = FakeExecutor(success=True)
    fake_safety_gate = FakeSafetyGate(allow=True)
    
    pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, fake_executor, audit_emitter)
    
    # Execute first intent
    result1 = pipeline.execute(sample_intent)
    assert result1.success is True
    
    # Create second intent
    intent2 = ActionIntent(
        intent_id="01HVABCDEF0123456789MNPQRS",
        actor_id="agent-002",
        actor_type="agent",
        action_type="http_request",
        target="https://api.example.com/status",
        parameters={"method": "GET"},
        safety_context={"risk_level": "medium"},
        timestamp=datetime.now(timezone.utc)
    )
    
    # Execute second intent
    result2 = pipeline.execute(intent2)
    assert result2.success is True
    
    # Verify both audit records were created
    assert len(audit_emitter.audit_records) == 2
    assert audit_emitter.audit_records[0].payload_ref["ref"] == "01HV1234567890ABCDEFGHJKMN"
    assert audit_emitter.audit_records[1].payload_ref["ref"] == "01HVABCDEF0123456789MNPQRS"
