"""
Tests for execution trace functionality in V2 execution boundary.

Tests deterministic trace generation and audit emission across all pipeline paths.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.execution_boundary_v2.models.execution_dispatch import ExecutionDispatch, DispatchStatus
from exoarmur.execution_boundary_v2.models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorPlugin, ExecutorResult
from exoarmur.execution_boundary_v2.approvals.approval_models import ApprovalDecision, ApprovalRecord
from exoarmur.execution_boundary_v2.approvals.in_memory_store import InMemoryApprovalStore

# Import V1 primitives for testing
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict


class MockExecutor(ExecutorPlugin):
    """Mock executor for testing."""
    
    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self._name = "mock_executor"
    
    def execute(self, intent: ActionIntent) -> ExecutorResult:
        return ExecutorResult(
            success=self.should_succeed,
            output={"executed": True},
            error=None if self.should_succeed else "Mock execution failed"
        )
    
    def name(self) -> str:
        return self._name


class MockPDP(PolicyDecisionPoint):
    """Mock PDP for testing."""
    
    def __init__(self, verdict: PolicyVerdict, approval_store=None):
        self.verdict = verdict
        self.approval_store = approval_store
        self._policy_version = "1.0.0"
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision(
            verdict=self.verdict,
            rationale=f"Mock rationale for {self.verdict.value}",
            policy_version=self._policy_version,
            approval_required=self.verdict == PolicyVerdict.REQUIRE_APPROVAL
        )
    
    def approval_status(self, intent_id: str) -> str:
        if not self.approval_store:
            return "not_required"
        
        record = self.approval_store.get(intent_id)
        if not record:
            return "pending" if self.verdict == PolicyVerdict.REQUIRE_APPROVAL else "not_required"
        return "approved" if record.decision == ApprovalDecision.APPROVE else "denied"
    
    def evaluate_with_approval_bypass(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale="Approval bypass granted",
            policy_version=self._policy_version,
            approval_required=False
        )


class MockSafetyGate(SafetyGate):
    """Mock safety gate for testing."""
    
    def __init__(self, should_allow=True):
        self.should_allow = should_allow
    
    def evaluate_safety(self, intent, local_decision=None, collective_state=None, policy_state=None, trust_state=None, environment_state=None):
        return SafetyVerdict(
            verdict="allow" if self.should_allow else "block",
            rationale="Mock safety evaluation",
            rule_ids=["rule-1"] if not self.should_allow else []
        )


class TestExecutionTrace:
    """Test execution trace generation and structure."""
    
    def test_trace_models_creation(self):
        """Test that trace models can be created with valid data."""
        # Test TraceEvent creation
        event = TraceEvent(
            stage=TraceStage.INTENT_RECEIVED,
            ok=True,
            code="RECEIVED",
            details={"action_type": "test_action", "target": "test_target"}
        )
        assert event.stage == TraceStage.INTENT_RECEIVED
        assert event.ok is True
        assert event.code == "RECEIVED"
        assert event.details["action_type"] == "test_action"
        
        # Test ExecutionTrace creation
        trace = ExecutionTrace(
            intent_id="test-intent-1",
            events=[event],
            final_status="COMPLETED",
            evidence={"test": "evidence"}
        )
        assert trace.intent_id == "test-intent-1"
        assert trace.trace_version == "v1"
        assert len(trace.events) == 1
        assert trace.final_status == "COMPLETED"
        assert trace.evidence["test"] == "evidence"
    
    def test_deny_trace_deterministic(self):
        """Test that DENY produces deterministic trace events in correct order."""
        # Setup
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.DENY)
        mock_safety = MockSafetyGate()
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-deny-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute
        result, trace = pipeline.execute_with_trace(intent)
        
        # Verify result
        assert isinstance(result, ExecutorResult)
        assert result.success is False
        assert result.error == "DENIED"
        
        # Verify trace structure
        assert isinstance(trace, ExecutionTrace)
        assert trace.intent_id == "test-deny-intent"
        assert len(trace.events) == 2  # INTENT_RECEIVED, POLICY_EVALUATED
        
        # Verify event order and content
        assert trace.events[0].stage == TraceStage.INTENT_RECEIVED
        assert trace.events[0].ok is True
        assert trace.events[0].code == "RECEIVED"
        
        assert trace.events[1].stage == TraceStage.POLICY_EVALUATED
        assert trace.events[1].ok is False  # DENY verdict
        assert trace.events[1].code == PolicyVerdict.DENY.value
        assert "rationale" in trace.events[1].details
        
        # Verify final status
        assert trace.final_status == "DENIED"
        assert trace.trace_version == "v1"
        assert "policy_decision" in trace.evidence
        assert trace.evidence["policy_decision"] == mock_pdp.verdict.value
        
        # Verify audit emission
        assert len(audit_emitter.audit_records) == 1
        assert audit_emitter.audit_records[0].event_kind == "policy_denial"
        assert audit_emitter.audit_records[0].payload_ref["outcome"] == "denied"
    
    def test_approval_pending_trace(self):
        """Test that REQUIRE_APPROVAL produces approval pending trace."""
        # Setup
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.REQUIRE_APPROVAL)
        mock_safety = MockSafetyGate()
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-approval-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute
        result, trace = pipeline.execute_with_trace(intent)
        
        # Verify result
        assert isinstance(result, ExecutionDispatch)
        assert result.status == DispatchStatus.APPROVAL_PENDING
        
        # Verify trace structure
        assert len(trace.events) == 2  # INTENT_RECEIVED, POLICY_EVALUATED
        assert trace.final_status == DispatchStatus.APPROVAL_PENDING.value
        assert trace.trace_version == "v1"
        assert "policy_decision" in trace.evidence
        assert trace.evidence["policy_decision"] == PolicyVerdict.REQUIRE_APPROVAL.value
        
        # Verify audit emission
        assert len(audit_emitter.audit_records) == 1
        assert audit_emitter.audit_records[0].event_kind == "policy_deferral"
    
    def test_approved_path_trace(self):
        """Test that APPROVED path produces executor dispatched trace."""
        # Setup
        mock_executor = MockExecutor(should_succeed=True)
        approval_store = InMemoryApprovalStore()
        
        # Add approval record
        approval_record = ApprovalRecord(
            intent_id="test-approved-intent",
            decision=ApprovalDecision.APPROVE,
            decided_by="test_approver",
            decided_at=datetime.now(timezone.utc),
            reason="Test approval"
        )
        approval_store.record(approval_record)
        
        mock_pdp = MockPDP(PolicyVerdict.REQUIRE_APPROVAL, approval_store)
        mock_safety = MockSafetyGate(should_allow=True)
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-approved-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute approval check
        result, trace = pipeline.check_approval_and_execute(intent)
        
        # Verify result
        assert isinstance(result, ExecutorResult)
        assert result.success is True
        
        # Verify trace structure
        assert len(trace.events) == 4  # INTENT_RECEIVED, APPROVAL_CHECKED, SAFETY_EVALUATED, EXECUTOR_DISPATCHED
        assert trace.final_status == "EXECUTED" if result.success else "FAILED"
        assert trace.trace_version == "v1"
        assert "executor_name" in trace.evidence
        assert trace.evidence["execution_success"] is result.success
        
        # Verify key events
        approval_checked_event = next(e for e in trace.events if e.stage == TraceStage.APPROVAL_CHECKED)
        assert approval_checked_event.ok is True
        assert approval_checked_event.code == "APPROVED"
        
        executor_event = next(e for e in trace.events if e.stage == TraceStage.EXECUTOR_DISPATCHED)
        assert executor_event.ok is True
        assert executor_event.code == "EXECUTED"
        
        # Verify audit emission
        assert len(audit_emitter.audit_records) == 1
        assert audit_emitter.audit_records[0].event_kind == "execution"
        assert audit_emitter.audit_records[0].payload_ref["outcome"] == "success"
    
    def test_safety_blocked_trace(self):
        """Test that SAFETY_BLOCKED path produces correct trace and no executor call."""
        # Setup
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.ALLOW)
        mock_safety = MockSafetyGate(should_allow=False)  # Block at safety gate
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-safety-block-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute
        result, trace = pipeline.execute_with_trace(intent)
        
        # Verify result
        assert isinstance(result, ExecutorResult)
        assert result.success is False
        assert result.error == "SAFETY_GATE_BLOCKED"
        
        # Verify trace structure
        assert len(trace.events) == 3  # INTENT_RECEIVED, POLICY_EVALUATED, SAFETY_EVALUATED
        assert trace.final_status == "SAFETY_BLOCKED"
        assert trace.trace_version == "v1"
        assert "safety_verdict" in trace.evidence
        assert trace.evidence["safety_verdict"] == "block"
        
        # Verify safety evaluation event
        safety_event = next(e for e in trace.events if e.stage == TraceStage.SAFETY_EVALUATED)
        assert safety_event.ok is False
        assert safety_event.code == "block"
        
        # Verify no executor dispatched event
        executor_events = [e for e in trace.events if e.stage == TraceStage.EXECUTOR_DISPATCHED]
        assert len(executor_events) == 0
        
        # Verify audit emission
        assert len(audit_emitter.audit_records) == 1
        assert audit_emitter.audit_records[0].event_kind == "safety_gate_block"
        assert audit_emitter.audit_records[0].payload_ref["outcome"] == "blocked"
    
    def test_trace_no_nondeterministic_fields(self):
        """Test that trace contains no nondeterministic fields."""
        # Setup
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.ALLOW)
        mock_safety = MockSafetyGate()
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-deterministic-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute multiple times
        result1, trace1 = pipeline.execute_with_trace(intent)
        result2, trace2 = pipeline.execute_with_trace(intent)
        
        # Verify traces are identical (deterministic)
        assert trace1.intent_id == trace2.intent_id
        assert len(trace1.events) == len(trace2.events)
        
        # Verify event details don't contain timestamps or random IDs
        for event in trace1.events:
            assert "timestamp" not in event.details
            assert "random_id" not in event.details
            assert "uuid" not in event.details
        
        # Verify evidence doesn't contain timestamps
        assert "timestamp" not in trace1.evidence
        assert "recorded_at" not in trace1.evidence
    
    def test_audit_emitter_called_exactly_once_per_terminal_path(self):
        """Test that AuditEmitter is called exactly once per terminal path."""
        # Test DENY path
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.DENY)
        mock_safety = MockSafetyGate()
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-audit-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute and verify single audit call
        result, trace = pipeline.execute_with_trace(intent)
        assert len(audit_emitter.audit_records) == 1
        
        # Reset and test execution path
        audit_emitter.audit_records.clear()
        mock_pdp = MockPDP(PolicyVerdict.ALLOW)
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        
        result, trace = pipeline.execute_with_trace(intent)
        assert len(audit_emitter.audit_records) == 1
        
        # Reset and test approval denied path
        audit_emitter.audit_records.clear()
        approval_store = InMemoryApprovalStore()
        approval_record = ApprovalRecord(
            intent_id="test-audit-intent",
            decision=ApprovalDecision.DENY,
            decided_by="test_approver",
            decided_at=datetime.now(timezone.utc),
            reason="Test denial"
        )
        approval_store.record(approval_record)
        
        mock_pdp = MockPDP(PolicyVerdict.REQUIRE_APPROVAL, approval_store)
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        
        result, trace = pipeline.check_approval_and_execute(intent)
        assert len(audit_emitter.audit_records) == 1
    
    def test_execute_backward_compatibility(self):
        """Test that execute() method maintains backward compatibility."""
        # Setup
        mock_executor = MockExecutor()
        mock_pdp = MockPDP(PolicyVerdict.DENY)
        mock_safety = MockSafetyGate()
        audit_emitter = AuditEmitter()
        
        pipeline = ProxyPipeline(mock_pdp, mock_safety, mock_executor, audit_emitter)
        intent = ActionIntent(
            intent_id="test-compatibility-intent",
            action_type="test_action",
            target="test_target",
            tenant_id="test-tenant",
            actor_id="test_actor",
            actor_type="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Execute with original method (should return only result, not trace)
        result = pipeline.execute_with_trace(intent)[0]  # Get first element of tuple
        
        # Verify backward compatibility
        assert isinstance(result, ExecutorResult)
        assert result.success is False
        assert result.error == "DENIED"
        # Should not return a tuple when using execute()
