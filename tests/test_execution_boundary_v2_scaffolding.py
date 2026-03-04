"""
Tests for execution boundary V2 scaffolding.

Minimal smoke tests to ensure V2 components import and instantiate correctly.
No network/NATS dependencies - pure unit tests only.
"""

import pytest
from datetime import datetime

# Test imports succeed
def test_v2_imports():
    """Test that all V2 components can be imported."""
    from exoarmur.execution_boundary_v2 import EXECUTION_BOUNDARY_V2_ENABLED
    from exoarmur.execution_boundary_v2.models import (
        ActionIntent, 
        PolicyDecision, 
        PolicyVerdict,
        ExecutionDispatch,
        DispatchStatus
    )
    from exoarmur.execution_boundary_v2.interfaces import (
        PolicyDecisionPoint,
        ApprovalStatus,
        ExecutorPlugin,
        ExecutionResult,
        ExecutionDispatcher
    )
    
    # Verify imports worked
    assert EXECUTION_BOUNDARY_V2_ENABLED is not None
    assert ActionIntent is not None
    assert PolicyDecision is not None
    assert PolicyVerdict is not None
    assert ExecutionDispatch is not None
    assert DispatchStatus is not None
    assert PolicyDecisionPoint is not None
    assert ApprovalStatus is not None
    assert ExecutorPlugin is not None
    assert ExecutionResult is not None
    assert ExecutionDispatcher is not None


def test_feature_flag_default():
    """Test that feature flag defaults to False."""
    from exoarmur.execution_boundary_v2.flags.feature_flags import EXECUTION_BOUNDARY_V2_ENABLED
    
    assert EXECUTION_BOUNDARY_V2_ENABLED is False


def test_action_intent_model():
    """Test ActionIntent model instantiation."""
    from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
    
    intent = ActionIntent(
        intent_id="test-intent-123",
        actor_id="agent-001",
        actor_type="agent",
        action_type="http_request",
        target="https://api.example.com",
        parameters={"method": "GET", "path": "/health"},
        safety_context={"risk_level": "low"},
        timestamp=datetime.now()
    )
    
    assert intent.intent_id == "test-intent-123"
    assert intent.actor_id == "agent-001"
    assert intent.actor_type == "agent"
    assert intent.action_type == "http_request"
    assert intent.target == "https://api.example.com"
    assert intent.parameters["method"] == "GET"
    assert intent.safety_context["risk_level"] == "low"


def test_policy_decision_model():
    """Test PolicyDecision model instantiation."""
    from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
    
    decision = PolicyDecision(
        verdict=PolicyVerdict.ALLOW,
        rationale="Low risk action",
        confidence=0.95,
        approval_required=False,
        policy_version="1.0.0"
    )
    
    assert decision.verdict == PolicyVerdict.ALLOW
    assert decision.rationale == "Low risk action"
    assert decision.confidence == 0.95
    assert decision.approval_required is False
    assert decision.policy_version == "1.0.0"


def test_execution_dispatch_model():
    """Test ExecutionDispatch model instantiation."""
    from exoarmur.execution_boundary_v2.models.execution_dispatch import ExecutionDispatch, DispatchStatus
    
    dispatch = ExecutionDispatch(
        intent_id="test-intent-123",
        status=DispatchStatus.SUBMITTED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        details={"queue": "high-priority"}
    )
    
    assert dispatch.intent_id == "test-intent-123"
    assert dispatch.status == DispatchStatus.SUBMITTED
    assert dispatch.details["queue"] == "high-priority"


def test_policy_verdict_enum():
    """Test PolicyVerdict enum values."""
    from exoarmur.execution_boundary_v2.models.policy_decision import PolicyVerdict
    
    assert PolicyVerdict.ALLOW.value == "allow"
    assert PolicyVerdict.DENY.value == "deny"
    assert PolicyVerdict.REQUIRE_APPROVAL.value == "require_approval"
    assert PolicyVerdict.DEFER.value == "defer"


def test_dispatch_status_enum():
    """Test DispatchStatus enum values."""
    from exoarmur.execution_boundary_v2.models.execution_dispatch import DispatchStatus
    
    assert DispatchStatus.SUBMITTED.value == "submitted"
    assert DispatchStatus.EVALUATING.value == "evaluating"
    assert DispatchStatus.BLOCKED.value == "blocked"
    assert DispatchStatus.APPROVAL_PENDING.value == "approval_pending"
    assert DispatchStatus.APPROVED.value == "approved"
    assert DispatchStatus.DISPATCHED.value == "dispatched"
    assert DispatchStatus.EXECUTED.value == "executed"
    assert DispatchStatus.FAILED.value == "failed"


def test_approval_status_enum():
    """Test ApprovalStatus enum values."""
    from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import ApprovalStatus
    
    assert ApprovalStatus.NOT_REQUIRED.value == "not_required"
    assert ApprovalStatus.PENDING.value == "pending"
    assert ApprovalStatus.APPROVED.value == "approved"
    assert ApprovalStatus.DENIED.value == "denied"
    assert ApprovalStatus.EXPIRED.value == "expired"


def test_execution_result_model():
    """Test ExecutionResult model instantiation."""
    from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutionResult
    
    result = ExecutionResult(
        success=True,
        output={"status_code": 200, "response": "OK"},
        evidence={"execution_time": 0.123}
    )
    
    assert result.success is True
    assert result.output["status_code"] == 200
    assert result.evidence["execution_time"] == 0.123
    
    # Test with error
    error_result = ExecutionResult(
        success=False,
        output={},
        error="Connection timeout"
    )
    
    assert error_result.success is False
    assert error_result.error == "Connection timeout"


def test_interface_smoke_checks():
    """Test that interfaces define required callables."""
    from exoarmur.execution_boundary_v2.interfaces import (
        PolicyDecisionPoint,
        ExecutorPlugin,
        ExecutionDispatcher
    )
    
    # Check that interfaces have required methods (Protocol smoke check)
    assert hasattr(PolicyDecisionPoint, 'evaluate')
    assert hasattr(PolicyDecisionPoint, 'approval_status')
    assert hasattr(ExecutorPlugin, 'name')
    assert hasattr(ExecutorPlugin, 'capabilities')
    assert hasattr(ExecutorPlugin, 'execute')
    assert hasattr(ExecutionDispatcher, 'submit_intent')
    assert hasattr(ExecutionDispatcher, 'get_status')
