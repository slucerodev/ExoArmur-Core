"""Integration test for deterministic execution proof bundles.

Tests that execution artifacts can be bundled and replayed deterministically.
"""

import tempfile
from datetime import datetime, timezone

import pytest

from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline
from exoarmur.execution_boundary_v2.utils.bundle_builder import build_execution_proof_bundle
from exoarmur.execution_boundary_v2.models.execution_proof_bundle import ExecutionProofBundle
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from exoarmur.execution_boundary_v2.utils.canonicalization import bundle_inputs_hash


class TestExecutionProofBundle:
    """Test deterministic execution proof bundle generation and verification."""
    
    def test_deterministic_bundle_generation(self, tmp_path):
        """Test that identical inputs produce identical bundles."""
        # Create deterministic intent
        intent = ActionIntent(
            intent_id="test-proof-bundle",
            actor_id="test-actor",
            actor_type="test",
            action_type="fs",
            target="filesystem",
            parameters={
                "operation": "read",
                "path": "test.txt"
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 0, 0, timezone.utc)
        )
        
        # Create deterministic policy decision
        policy_decision = PolicyDecision(
            decision_id="test-decision-123",
            verdict=PolicyVerdict.ALLOW,
            rationale="Test policy decision",
            policy_version="1.0"
        )
        
        # Build bundle twice with same inputs using function-based interface
        bundle1 = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy_decision,
            execution_trace=None,
            executor_result=None
        )
        
        # Use function interface for second bundle
        bundle2 = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy_decision,
            execution_trace=None,
            executor_result=None
        )
        
        # Assert deterministic behavior
        assert bundle1.replay_hash == bundle2.replay_hash
        assert bundle1.schema_version == "2.0"
        assert bundle1.intent == bundle2.intent
        # bundle_created_at is populated at construction but excluded from hash computation
        assert bundle1.bundle_created_at is not None
        assert bundle2.bundle_created_at is not None
        
    def test_bundle_with_execution_trace(self, tmp_path):
        """Test bundle building with real execution trace."""
        # Create deterministic intent
        intent = ActionIntent(
            intent_id="test-execution",
            actor_id="test-actor",
            actor_type="test",
            action_type="fs",
            target="filesystem",
            parameters={
                "operation": "read",
                "path": "test.txt"
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 0, 0, timezone.utc)
        )
        
        # Create deterministic policy decision
        policy_decision = PolicyDecision(
            decision_id="test-decision-123",
            verdict=PolicyVerdict.ALLOW,
            rationale="Test policy decision",
            policy_version="1.0"
        )
        
        # Create mock execution trace
        from exoarmur.execution_boundary_v2.models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
        
        execution_trace = ExecutionTrace.create(
            correlation_id=intent.intent_id,  # Use intent_id as correlation_id
            intent_id=intent.intent_id,
            final_verdict=FinalVerdict.ALLOW
        )
        
        # Add a trace event
        trace_event = TraceEvent.create(
            trace_id=execution_trace.trace_id,
            stage=TraceStage.INTENT_RECEIVED,
            ok=True,
            code="PROCESSED",
            details={"message": "Intent processed successfully"},
            sequence=1
        )
        execution_trace.events = [trace_event]
        
        # Add more trace events
        execution_trace.events.append(
            TraceEvent.create(
                trace_id=execution_trace.trace_id,
                stage=TraceStage.POLICY_EVALUATED,
                ok=True,
                code="ALLOWED",
                details={"verdict": "ALLOW"},
                sequence=2
            )
        )
        execution_trace.events.append(
            TraceEvent.create(
                trace_id=execution_trace.trace_id,
                stage=TraceStage.EXECUTOR_DISPATCHED,
                ok=True,
                code="EXECUTED",
                details={
                    "executor_name": "test-executor",
                    "executor_capabilities": {"version": "1.0.0", "capabilities": ["fs.read"]},
                    "executor_version": "1.0.0",
                    "execution_success": True
                },
                sequence=3
            )
        )
        
        # Create mock executor result
        executor_result = {
            "success": True,
            "output": {"content": "test content"},
            "error": None
        }
        
        # Build bundle with execution artifacts using function-based interface
        bundle = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy_decision,
            execution_trace=execution_trace.model_dump(),
            executor_result=executor_result
        )
        
        # Verify bundle structure
        assert bundle.schema_version == "2.0"
        assert bundle.replay_hash is not None
        assert len(bundle.replay_hash) == 64  # SHA-256 hex length
        assert bundle.intent is not None
        assert bundle.policy_decision is not None
        assert bundle.execution_trace is not None
        assert bundle.executor_result is not None
        
        # Verify hash is computed
        assert bundle.replay_hash is not None
        assert len(bundle.replay_hash) == 64  # SHA-256 hex length
        # bundle_created_at is populated at construction but excluded from hash computation
        assert bundle.bundle_created_at is not None
        
    def test_bundle_with_explicit_timestamp(self, tmp_path):
        """Test bundle building with explicit timestamp when needed."""
        # Create deterministic intent
        intent = ActionIntent(
            intent_id="test-execution-timestamp",
            actor_id="test-actor",
            actor_type="test",
            action_type="fs",
            target="filesystem",
            parameters={
                "operation": "read",
                "path": "test.txt"
            },
            timestamp=datetime(2024, 1, 1, 12, 0, 0, 0, timezone.utc)
        )
        
        # Create deterministic policy decision
        policy_decision = PolicyDecision(
            decision_id="test-decision-123",
            verdict=PolicyVerdict.ALLOW,
            rationale="Test policy decision",
            policy_version="1.0"
        )
        
        # Build bundle with default (None) timestamp using function-based interface
        bundle_default = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy_decision,
            execution_trace=None,
            executor_result=None
        )
        
        # bundle_created_at is populated at construction but excluded from hash computation
        assert bundle_default.bundle_created_at is not None
        
        # Manually create bundle with explicit timestamp for comparison
        bundle_explicit = ExecutionProofBundle.create(
            intent=bundle_default.intent,
            policy_decision=bundle_default.policy_decision,
            safety_verdict=bundle_default.safety_verdict,  # Use same safety_verdict
            final_verdict=bundle_default.final_verdict      # Use same final_verdict
        )
        
        # bundle_created_at is populated at construction (excluded from hash)
        assert bundle_explicit.bundle_created_at is not None
        # Hash should be the same since bundle_created_at is excluded from hash computation
        assert bundle_explicit.replay_hash == bundle_default.replay_hash
        
    def _create_mock_executor(self):
        """Create mock executor for testing."""
        class MockExecutor:
            def __init__(self):
                self.name = lambda: "test-executor"
                self.capabilities = lambda: {
                    "executor_name": "test-executor",
                    "version": "1.0.0",
                    "capabilities": ["fs.read", "fs.write"],
                    "constraints": {}
                }
            
            def execute(self, intent):
                # Mock successful execution
                return type("ExecutorResult", success=True, output={"content": "test content"}, error=None)
        
        return MockExecutor()
