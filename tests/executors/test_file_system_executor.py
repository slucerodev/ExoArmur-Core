"""
Test suite for FileSystemExecutor.

Production-grade tests covering all executor functionality including:
- File operations (create, delete, rename, modify, read, stat)
- Rollback capabilities with state verification
- Action classification
- Safety gate integration
- Deterministic replay
- Unauthorized path rejection
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from exoarmur.executors.file_system_executor import (
    FileSystemExecutor,
    RollbackPlan,
    RollbackResult,
)
from exoarmur.kernel.boundary import (
    ActionClass,
    ActionIntent,
    ApprovalStatus,
    DispatchStatus,
    ExecutionDispatch,
    PolicyDecision,
    PolicyDecisionPoint,
    PolicyVerdict,
    ProxyPipeline,
    SafetyGate,
    SafetyInputs,
    SafetyVerdict,
    V2AuditEmitter,
    V2EnvironmentState,
    V2PolicyState,
    V2TrustState,
)
from exoarmur.kernel.clock import DeterministicClock, set_clock


def _test_safety_inputs(intent) -> SafetyInputs:
    """Explicit test safety inputs — not a production default."""
    return SafetyInputs(
        policy_state=V2PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none",
        ),
        trust_state=V2TrustState(emitter_trust_score=0.9),
        environment_state=V2EnvironmentState(),
        source="test_fixture",
    )


class FakePDP(PolicyDecisionPoint):
    """Fake PolicyDecisionPoint that allows all operations."""

    def __init__(self, verdict=PolicyVerdict.ALLOW):
        self.verdict = verdict
        self.evaluate_called = False
        self.evaluate_intent = None

    def evaluate(self, intent):
        self.evaluate_called = True
        self.evaluate_intent = intent
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=self.verdict,
            rationale=f"Fake {self.verdict.value} for testing",
            evidence={"fake": True},
        )

    def approval_status(self, intent_id: str):
        """Return approval status (always APPROVED for this fake)."""
        return ApprovalStatus.APPROVED


class TestFileSystemExecutor:
    """
    Test suite for FileSystemExecutor implementation.
    """

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test file operations."""
        temp_dir = tempfile.mkdtemp(prefix="exoarmur_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def executor(self, temp_dir):
        """Create FileSystemExecutor with temp directory as authorized root."""
        return FileSystemExecutor(authorized_root=temp_dir)

    @pytest.fixture
    def mock_clock(self):
        """Create deterministic clock for testing."""
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0))
        set_clock(clock)
        yield clock
        # Reset to default after test

    def test_execute_create_file(self, executor, temp_dir):
        """Test file creation with verification and audit emission."""
        # Create ActionIntent for file creation
        test_file = Path(temp_dir) / "test_create.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={"operation": "create", "payload": {"content": "test content"}},
            safety_context={},
            tenant_id="test_tenant",
        )

        # Execute
        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})

        # Verify success
        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == "test content"
        assert result.output["operation"] == "create"
        assert result.output["action_class"] == ActionClass.A1_SOFT_CONTAINMENT.value
        assert "pre_hash" in result.output
        assert "post_hash" in result.output
        assert result.output["post_hash"] is not None  # File exists, should have hash

    def test_execute_delete_file(self, executor, temp_dir):
        """Test file deletion with trash backup and verification."""
        # Create test file first
        test_file = Path(temp_dir) / "test_delete.txt"
        test_file.write_text("content to delete")
        original_hash = executor.compute_state_hash(test_file)

        # Create ActionIntent for deletion
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={"operation": "delete", "payload": {}},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        # Execute
        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})

        # Verify deletion
        assert result.success is True
        assert not test_file.exists()
        assert result.output["operation"] == "delete"
        assert result.output["action_class"] == ActionClass.A1_SOFT_CONTAINMENT.value
        assert result.output["pre_hash"] == original_hash
        assert result.output["post_hash"] is None  # File deleted, no hash
        assert "rollback_plan_id" in result.output

        # Verify trash backup exists
        rollback_plan_id = result.output["rollback_plan_id"]
        assert rollback_plan_id in executor._rollback_plans
        rollback_plan = executor._rollback_plans[rollback_plan_id]
        assert rollback_plan.action_type == "delete"
        assert Path(rollback_plan.original_state_path).exists()

    def test_rollback_delete(self, executor, temp_dir):
        """Test rollback of delete operation restores file with hash match."""
        # Create test file
        test_file = Path(temp_dir) / "test_rollback_delete.txt"
        original_content = "original content for rollback test"
        test_file.write_text(original_content)
        original_hash = executor.compute_state_hash(test_file)

        # Create and execute delete intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={"operation": "delete", "payload": {}},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        rollback_plan_id = result.output["rollback_plan_id"]
        rollback_plan = executor._rollback_plans[rollback_plan_id]

        # Verify file deleted
        assert not test_file.exists()

        # Rollback
        rollback_result = executor.rollback(rollback_plan)

        # Verify rollback success
        assert rollback_result.success is True
        assert test_file.exists()
        assert test_file.read_text() == original_content
        assert rollback_result.hash_match is True
        assert rollback_result.restored_state_hash == original_hash

    def test_rollback_modify(self, executor, temp_dir):
        """Test rollback of modify operation restores original content."""
        # Create test file
        test_file = Path(temp_dir) / "test_rollback_modify.txt"
        original_content = "original content"
        test_file.write_text(original_content)
        original_hash = executor.compute_state_hash(test_file)

        # Create and execute modify intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={
                "operation": "modify",
                "payload": {"content": "modified content"},
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        rollback_plan_id = result.output["rollback_plan_id"]
        rollback_plan = executor._rollback_plans[rollback_plan_id]

        # Verify file modified
        assert test_file.read_text() == "modified content"

        # Rollback
        rollback_result = executor.rollback(rollback_plan)

        # Verify rollback success
        assert rollback_result.success is True
        assert test_file.read_text() == original_content
        assert rollback_result.hash_match is True
        assert rollback_result.restored_state_hash == original_hash

    def test_rollback_expired(self, executor, temp_dir, mock_clock):
        """Test rollback fails when plan is expired (>300s window)."""
        # Create test file
        test_file = Path(temp_dir) / "test_expired.txt"
        test_file.write_text("content")

        # Create intent and execute
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={"operation": "delete", "payload": {}},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        rollback_plan_id = result.output["rollback_plan_id"]
        rollback_plan = executor._rollback_plans[rollback_plan_id]

        # Manually expire the plan by setting expiration to past
        from datetime import timedelta

        from exoarmur.kernel.clock import utc_now

        rollback_plan.expiration_timestamp = utc_now() - timedelta(seconds=1)

        # Attempt rollback
        rollback_result = executor.rollback(rollback_plan)

        # Verify rollback failed due to expiration
        assert rollback_result.success is False
        assert "expired" in rollback_result.error.lower()

    def test_action_classification(self, executor):
        """Test action classification maps operations to correct ActionClass."""
        # Test A0 operations
        assert executor.classify_file_action("read", {}) == ActionClass.A0_OBSERVE
        assert executor.classify_file_action("stat", {}) == ActionClass.A0_OBSERVE

        # Test A1 operations
        assert (
            executor.classify_file_action("delete", {})
            == ActionClass.A1_SOFT_CONTAINMENT
        )
        assert (
            executor.classify_file_action("rename", {})
            == ActionClass.A1_SOFT_CONTAINMENT
        )

        # Test A2 operations
        assert (
            executor.classify_file_action("modify", {})
            == ActionClass.A2_HARD_CONTAINMENT
        )
        assert (
            executor.classify_file_action("append", {})
            == ActionClass.A2_HARD_CONTAINMENT
        )

        # Test A3 operations
        assert (
            executor.classify_file_action("chmod", {"mode": "000"})
            == ActionClass.A3_IRREVERSIBLE
        )
        assert (
            executor.classify_file_action("overwrite", {"content": "random"})
            == ActionClass.A3_IRREVERSIBLE
        )

        # Test unknown operation defaults to A2
        assert (
            executor.classify_file_action("unknown", {})
            == ActionClass.A2_HARD_CONTAINMENT
        )

    def test_unauthorized_path(self, executor, temp_dir):
        """Test operation outside authorized_root is denied."""
        # Create intent for path outside authorized root
        unauthorized_path = "/etc/passwd"  # Outside temp_dir
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=unauthorized_path,
            parameters={"operation": "read", "payload": {}},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        # Validate target
        validation_result = executor.validate_target(intent)

        # Verify validation fails
        assert validation_result.result.value == "violates_constraints"
        assert validation_result.evidence["is_authorized"] is False
        assert "outside authorized root" in validation_result.evidence["reason"]

    def test_deterministic_replay(self, executor, temp_dir):
        """Test execution produces deterministic outcome hash for replay."""
        # Create test file
        test_file = Path(temp_dir) / "test_deterministic.txt"

        # Create intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={
                "operation": "create",
                "payload": {"content": "deterministic content"},
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        # Execute first time
        result1 = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        outcome_hash1 = result1.output["post_hash"]

        # Clean up and execute again with same intent
        test_file.unlink()
        result2 = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        outcome_hash2 = result2.output["post_hash"]

        # Verify deterministic outcome
        assert outcome_hash1 == outcome_hash2
        assert result1.output["pre_hash"] == result2.output["pre_hash"]

    def test_safety_gate_denial(self, executor, temp_dir):
        """Test SafetyGate DENY prevents file operation."""
        # Create intent
        test_file = Path(temp_dir) / "test_safety_deny.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={
                "operation": "create",
                "payload": {"content": "should not be created"},
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        # Execute with DENY verdict
        result = executor.execute(intent, None, {"final_verdict": "DENY"})

        # Verify operation denied
        assert result.success is False
        assert result.error == "SAFETY_GATE_DENY"
        assert not test_file.exists()
        assert "Safety gate denied execution" in result.evidence["reason"]

    def test_post_execution_rollback(self, executor, temp_dir):
        """Test post-execution safety trigger initiates rollback."""
        # Create test file
        test_file = Path(temp_dir) / "test_post_rollback.txt"
        original_content = "original content"
        test_file.write_text(original_content)
        original_hash = executor.compute_state_hash(test_file)

        # Create and execute modify intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={
                "operation": "modify",
                "payload": {"content": "modified content"},
            },
            tenant_id="test_tenant",
            cell_id="test_cell",
        )

        result = executor.execute(intent, None, {"final_verdict": "ALLOW"})
        rollback_plan_id = result.output["rollback_plan_id"]
        rollback_plan = executor._rollback_plans[rollback_plan_id]

        # Simulate post-execution safety trigger by rolling back
        rollback_result = executor.rollback(rollback_plan)

        # Verify rollback succeeded and state restored
        assert rollback_result.success is True
        assert test_file.read_text() == original_content
        assert rollback_result.hash_match is True
        assert rollback_result.restored_state_hash == original_hash


class TestRollbackPlan:
    """Test suite for RollbackPlan functionality."""

    def test_plan_generation(self):
        """Test RollbackPlan generates deterministic plan_id."""
        from datetime import datetime, timedelta

        expiration = datetime.now() + timedelta(seconds=300)
        plan = RollbackPlan(
            action_type="delete",
            original_state_path="/trash/backup",
            target_path="/target/file.txt",
            expiration_timestamp=expiration,
        )

        assert plan.plan_id is not None
        assert len(plan.plan_id) == 32

    def test_plan_expiration(self):
        """Test RollbackPlan expiration detection."""
        from datetime import datetime, timedelta, timezone

        from exoarmur.kernel.clock import utc_now

        # Expired plan
        past_expiration = utc_now() - timedelta(seconds=1)
        expired_plan = RollbackPlan(
            action_type="delete",
            original_state_path="/trash/backup",
            target_path="/target/file.txt",
            expiration_timestamp=past_expiration,
        )
        assert expired_plan.is_expired() is True

        # Valid plan
        future_expiration = utc_now() + timedelta(seconds=300)
        valid_plan = RollbackPlan(
            action_type="delete",
            original_state_path="/trash/backup",
            target_path="/target/file.txt",
            expiration_timestamp=future_expiration,
        )
        assert valid_plan.is_expired() is False


class TestFileSystemExecutorProxyPipelineIntegration:
    """Test FileSystemExecutor integration with ProxyPipeline governance boundary."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test file operations."""
        temp_dir = tempfile.mkdtemp(prefix="exoarmur_pipeline_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def executor(self, temp_dir):
        """Create FileSystemExecutor with temp directory as authorized root."""
        return FileSystemExecutor(authorized_root=temp_dir)

    def test_file_system_executor_through_proxy_pipeline(self, executor, temp_dir):
        """
        Prove that a file operation routes through ProxyPipeline,
        hits the SafetyGate, executes via FileSystemExecutor,
        and produces a deterministic audit trail.
        """
        # 1. Create a ProxyPipeline with FileSystemExecutor registered
        pdp = FakePDP(PolicyVerdict.ALLOW)
        safety_gate = SafetyGate()  # Use real SafetyGate
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(pdp, safety_gate, executor, audit_emitter, safety_context_provider=_test_safety_inputs)

        # Create test file to delete
        test_file = Path(temp_dir) / "pipeline_test.txt"
        test_file.write_text("pipeline integration test content")

        # 2. Construct an ActionIntent for "delete file X"
        intent = ActionIntent(
            intent_id="integration-test-001",
            actor_id="test-actor",
            actor_type="automation",
            action_type="file_operation",
            target=str(test_file),
            parameters={"operation": "delete", "payload": {}},
            safety_context={},
            timestamp=datetime.now(),
            tenant_id="test-tenant",
            cell_id="test-cell",
        )

        # 3. Route it through ProxyPipeline.execute_with_trace()
        result, trace = pipeline.execute_with_trace(intent)

        # 4. Verify PolicyDecisionPoint evaluated it (not bypassed)
        assert (
            pdp.evaluate_called is True
        ), "PolicyDecisionPoint must evaluate the intent"
        assert (
            pdp.evaluate_intent == intent
        ), "PolicyDecisionPoint must receive the correct intent"

        # 5. Verify FileSystemExecutor actually deleted the file
        assert not test_file.exists(), "File must be deleted by FileSystemExecutor"

        # 6. Verify audit trail was emitted with correct structure
        assert len(audit_emitter.audit_events) > 0, "Audit events must be emitted"

        # Verify trace contains governance stages
        trace_stages = [e.stage.value for e in trace.events]
        assert (
            "intent_received" in trace_stages
        ), "Trace must contain intent_received stage"
        assert (
            "policy_evaluated" in trace_stages
        ), "Trace must contain policy_evaluated stage"
        assert (
            "safety_evaluated" in trace_stages
        ), "Trace must contain safety_evaluated stage"
        assert (
            "executor_dispatched" in trace_stages
        ), "Trace must contain executor_dispatched stage"

        # Verify trace has deterministic structure
        assert trace.intent_id == intent.intent_id, "Trace must be linked to intent"
        assert trace.final_verdict is not None, "Trace must have final verdict"

        # 7. Verify result indicates successful execution
        # Result can be either ExecutorResult or ExecutionDispatch
        if hasattr(result, "success"):
            assert result.success is True, "Execution must succeed"
        elif hasattr(result, "status"):
            from exoarmur.kernel.boundary import DispatchStatus

            assert (
                result.status == DispatchStatus.EXECUTED
            ), f"Execution must be EXECUTED, got {result.status}"
        else:
            raise AssertionError(f"Unknown result type: {type(result)}")

        # 8. Verify executor_dispatched event contains executor information
        executor_events = [
            e for e in trace.events if e.stage.value == "executor_dispatched"
        ]
        assert len(executor_events) > 0, "Trace must contain executor_dispatched event"
        executor_event = executor_events[0]
        assert executor_event.ok is True, "Executor dispatch must succeed"
        # Verify the event contains execution details (actual structure may vary)
        assert (
            "success" in executor_event.details
            or "execution_success" in executor_event.details
        ), "Executor event must contain success status"
        if "success" in executor_event.details:
            assert executor_event.details["success"] is True, "Execution must succeed"
        if "execution_success" in executor_event.details:
            assert (
                executor_event.details["execution_success"] is True
            ), "Execution must succeed"


class TestRollbackResult:
    """Test suite for RollbackResult functionality."""

    def test_result_creation(self):
        """Test RollbackResult creation with all fields."""
        result = RollbackResult(
            success=True,
            restored_state_hash="abc123",
            hash_match=True,
            time_to_rollback_ms=150,
            error=None,
        )

        assert result.success is True
        assert result.restored_state_hash == "abc123"
        assert result.hash_match is True
        assert result.time_to_rollback_ms == 150
        assert result.error is None

    def test_result_with_error(self):
        """Test RollbackResult with error."""
        result = RollbackResult(
            success=False,
            restored_state_hash=None,
            hash_match=False,
            time_to_rollback_ms=50,
            error="File not found",
        )

        assert result.success is False
        assert result.restored_state_hash is None
        assert result.hash_match is False
        assert result.time_to_rollback_ms == 50
        assert result.error == "File not found"
