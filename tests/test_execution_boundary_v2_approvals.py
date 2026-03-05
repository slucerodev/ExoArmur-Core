"""
Tests for approval workflow scaffolding.

Infra-free tests for approval models, store, and integration.
"""

import pytest
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.approvals.approval_models import ApprovalDecision, ApprovalRecord
from exoarmur.execution_boundary_v2.approvals.approval_store import ApprovalStore
from exoarmur.execution_boundary_v2.approvals.in_memory_store import InMemoryApprovalStore


class TestApprovalModels:
    """Test approval model definitions."""
    
    def test_approval_decision_enum(self):
        """Test ApprovalDecision enum values."""
        assert ApprovalDecision.APPROVE == "APPROVE"
        assert ApprovalDecision.DENY == "DENY"
        assert len(ApprovalDecision) == 2
    
    def test_approval_record_creation(self):
        """Test ApprovalRecord creation and validation."""
        record = ApprovalRecord(
            intent_id="test-intent-123",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-001",
            decided_at=datetime.now(timezone.utc),
            reason="Safe to execute"
        )
        
        assert record.intent_id == "test-intent-123"
        assert record.decision == ApprovalDecision.APPROVE
        assert record.decided_by == "approver-001"
        assert record.reason == "Safe to execute"
        assert record.decided_at.tzinfo is not None  # Should be timezone-aware
    
    def test_approval_record_optional_reason(self):
        """Test ApprovalRecord with optional reason."""
        record = ApprovalRecord(
            intent_id="test-intent-456",
            decision=ApprovalDecision.DENY,
            decided_by="approver-002",
            decided_at=datetime.now(timezone.utc)
        )
        
        assert record.intent_id == "test-intent-456"
        assert record.decision == ApprovalDecision.DENY
        assert record.decided_by == "approver-002"
        assert record.reason is None


class TestInMemoryApprovalStore:
    """Test InMemoryApprovalStore implementation."""
    
    @pytest.fixture
    def store(self):
        """Create a fresh InMemoryApprovalStore for each test."""
        return InMemoryApprovalStore()
    
    @pytest.fixture
    def sample_record(self):
        """Create a sample approval record."""
        return ApprovalRecord(
            intent_id="test-intent-123",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-001",
            decided_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            reason="Approved for testing"
        )
    
    def test_record_and_get_success(self, store, sample_record):
        """Test successful record and retrieve operation."""
        # Record the approval
        store.record(sample_record)
        
        # Retrieve the approval
        retrieved = store.get(sample_record.intent_id)
        
        assert retrieved is not None
        assert retrieved.intent_id == sample_record.intent_id
        assert retrieved.decision == sample_record.decision
        assert retrieved.decided_by == sample_record.decided_by
        assert retrieved.decided_at == sample_record.decided_at
        assert retrieved.reason == sample_record.reason
    
    def test_get_nonexistent_record(self, store):
        """Test getting a record that doesn't exist."""
        result = store.get("nonexistent-intent")
        assert result is None
    
    def test_double_decision_rejection(self, store, sample_record):
        """Test that recording a second decision for the same intent raises an error."""
        # Record first decision
        store.record(sample_record)
        
        # Attempt to record second decision
        second_record = ApprovalRecord(
            intent_id=sample_record.intent_id,  # Same intent_id
            decision=ApprovalDecision.DENY,
            decided_by="approver-002",
            decided_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            reason="Changed mind"
        )
        
        with pytest.raises(ValueError, match="Approval decision already exists"):
            store.record(second_record)
    
    def test_clear_all_records(self, store, sample_record):
        """Test clearing all records."""
        # Record multiple approvals
        store.record(sample_record)
        
        second_record = ApprovalRecord(
            intent_id="test-intent-456",
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-002",
            decided_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        )
        store.record(second_record)
        
        # Verify records exist
        assert store.get("test-intent-123") is not None
        assert store.get("test-intent-456") is not None
        
        # Clear all records
        store.clear()
        
        # Verify records are gone
        assert store.get("test-intent-123") is None
        assert store.get("test-intent-456") is None
    
    def test_list_all_records(self, store, sample_record):
        """Test listing all stored records."""
        # Record multiple approvals
        store.record(sample_record)
        
        second_record = ApprovalRecord(
            intent_id="test-intent-456",
            decision=ApprovalDecision.DENY,
            decided_by="approver-002",
            decided_at=datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        )
        store.record(second_record)
        
        # List all records
        all_records = store.list_all()
        
        assert len(all_records) == 2
        assert "test-intent-123" in all_records
        assert "test-intent-456" in all_records
        assert all_records["test-intent-123"].decision == ApprovalDecision.APPROVE
        assert all_records["test-intent-456"].decision == ApprovalDecision.DENY
        
        # Verify it's a copy (modifying shouldn't affect store)
        all_records.clear()
        assert len(store.list_all()) == 2


class TestApprovalIntegration:
    """Test approval workflow integration with policy and pipeline."""
    
    @pytest.fixture
    def sample_intent(self):
        """Create sample ActionIntent for testing."""
        from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
        return ActionIntent(
            intent_id="test-intent-approval",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/sensitive",
            parameters={"method": "POST"},
            safety_context={"risk_level": "medium"},
            timestamp=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def approval_store(self):
        """Create approval store for testing."""
        return InMemoryApprovalStore()
    
    @pytest.fixture
    def approval_rule(self):
        """Create a policy rule that requires approval."""
        from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule
        return PolicyRule(
            rule_id="require-approval-rule",
            description="Require approval for sensitive operations",
            allowed_domains=["api.example.com"],
            allowed_methods=["POST", "PUT", "DELETE"],
            require_approval=True
        )
    
    def test_pending_when_no_record(self, sample_intent, approval_rule, approval_store):
        """Test pending status when no approval record exists."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        status = pdp.approval_status(sample_intent.intent_id)
        
        assert status == "pending"
    
    def test_approved_status_mapping(self, sample_intent, approval_rule, approval_store):
        """Test approved status when APPROVE record exists."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        # Record approval
        approval_record = ApprovalRecord(
            intent_id=sample_intent.intent_id,
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-001",
            decided_at=datetime.now(timezone.utc),
            reason="Approved for testing"
        )
        approval_store.record(approval_record)
        
        status = pdp.approval_status(sample_intent.intent_id)
        
        assert status == "approved"
    
    def test_denied_status_mapping(self, sample_intent, approval_rule, approval_store):
        """Test denied status when DENY record exists."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        # Record denial
        denial_record = ApprovalRecord(
            intent_id=sample_intent.intent_id,
            decision=ApprovalDecision.DENY,
            decided_by="approver-001",
            decided_at=datetime.now(timezone.utc),
            reason="Too risky"
        )
        approval_store.record(denial_record)
        
        status = pdp.approval_status(sample_intent.intent_id)
        
        assert status == "denied"
    
    def test_not_required_when_no_approval_rules(self, sample_intent, approval_store):
        """Test not_required status when no rules require approval."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        from exoarmur.execution_boundary_v2.policy.policy_models import PolicyRule
        
        # Rule that doesn't require approval
        allow_rule = PolicyRule(
            rule_id="allow-rule",
            description="Allow without approval",
            allowed_domains=["api.example.com"],
            allowed_methods=["GET", "POST"],
            require_approval=False
        )
        
        pdp = SimplePolicyDecisionPoint(rules=[allow_rule], approval_store=approval_store)
        
        status = pdp.approval_status(sample_intent.intent_id)
        
        assert status == "not_required"
    
    def test_not_required_when_no_approval_store(self, sample_intent, approval_rule):
        """Test not_required status when no approval store is provided."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=None)
        
        status = pdp.approval_status(sample_intent.intent_id)
        
        assert status == "not_required"
    
    def test_pipeline_approval_pending_flow(self, sample_intent, approval_rule, approval_store):
        """Test pipeline returns approval pending when no record exists."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
        from exoarmur.execution_boundary_v2.models.execution_dispatch import DispatchStatus
        
        # Setup pipeline with approval requirement
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        class FakeSafetyGate:
            def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
                from exoarmur.safety.safety_gate import SafetyVerdict
                return SafetyVerdict(verdict="allow", rationale="Safe", rule_ids=[])
        
        class FakeExecutor:
            def name(self):
                return "fake-executor"
            def capabilities(self):
                return {"actions": ["test"]}
            def execute(self, intent):
                raise Exception("Should not be called")
        
        pipeline = ProxyPipeline(pdp, FakeSafetyGate(), FakeExecutor(), AuditEmitter())
        
        # Execute intent - should return approval pending
        result = pipeline.execute(sample_intent)
        
        assert hasattr(result, 'status')
        assert result.status == DispatchStatus.APPROVAL_PENDING
        assert result.intent_id == sample_intent.intent_id
    
    def test_pipeline_approval_denied_flow(self, sample_intent, approval_rule, approval_store):
        """Test pipeline returns denied when approval record is DENY."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
        
        # Setup pipeline with approval requirement
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        class FakeSafetyGate:
            def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
                from exoarmur.safety.safety_gate import SafetyVerdict
                return SafetyVerdict(verdict="allow", rationale="Safe", rule_ids=[])
        
        class FakeExecutor:
            def name(self):
                return "fake-executor"
            def capabilities(self):
                return {"actions": ["test"]}
            def execute(self, intent):
                raise Exception("Should not be called")
        
        pipeline = ProxyPipeline(pdp, FakeSafetyGate(), FakeExecutor(), AuditEmitter())
        
        # Record denial
        denial_record = ApprovalRecord(
            intent_id=sample_intent.intent_id,
            decision=ApprovalDecision.DENY,
            decided_by="approver-001",
            decided_at=datetime.now(timezone.utc),
            reason="Too risky"
        )
        approval_store.record(denial_record)
        
        # Check approval and execute - should return denied
        result, trace = pipeline.check_approval_and_execute(sample_intent)
        
        assert result.success is False
        assert result.error == "APPROVAL_DENIED"
        assert result.evidence["approval_status"] == "denied"
    
    def test_pipeline_approval_approved_flow(self, sample_intent, approval_rule, approval_store):
        """Test pipeline proceeds when approval record is APPROVE."""
        from exoarmur.execution_boundary_v2.policy.simple_pdp import SimplePolicyDecisionPoint
        from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
        
        # Setup pipeline with approval requirement
        pdp = SimplePolicyDecisionPoint(rules=[approval_rule], approval_store=approval_store)
        
        class FakeSafetyGate:
            def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
                from exoarmur.safety.safety_gate import SafetyVerdict
                return SafetyVerdict(verdict="allow", rationale="Safe", rule_ids=[])
        
        class FakeExecutor:
            def __init__(self):
                self.execute_called = False
            def name(self):
                return "fake-executor"
            def capabilities(self):
                return {"actions": ["test"]}
            def execute(self, intent):
                self.execute_called = True
                from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
                return ExecutorResult(success=True, output={"status": "success"}, error=None, evidence={})
        
        fake_executor = FakeExecutor()
        pipeline = ProxyPipeline(pdp, FakeSafetyGate(), fake_executor, AuditEmitter())
        
        # Record approval
        approval_record = ApprovalRecord(
            intent_id=sample_intent.intent_id,
            decision=ApprovalDecision.APPROVE,
            decided_by="approver-001",
            decided_at=datetime.now(timezone.utc),
            reason="Approved for testing"
        )
        approval_store.record(approval_record)
        
        # Check approval and execute - should proceed to execution
        result, trace = pipeline.check_approval_and_execute(sample_intent)
        
        # Should now succeed with approval bypass
        assert hasattr(result, 'success')
        assert result.success is True
        assert fake_executor.execute_called is True
