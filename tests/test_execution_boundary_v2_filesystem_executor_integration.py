"""
Integration test for Filesystem Executor with ExoArmur Core

Tests the integration between ProxyPipeline and FilesystemExecutorPlugin.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
# Note: Filesystem executor integration test requires exoarmur-executors-fs package
# This test will be skipped if the package is not available
try:
    import sys
    from exoarmur_executors_fs.executor import FilesystemExecutorPlugin
    FILESYSTEM_EXECUTOR_AVAILABLE = True
except ImportError as e:
    FILESYSTEM_EXECUTOR_AVAILABLE = False
    FilesystemExecutorPlugin = None
    # If the error is about missing exoarmur package, it's likely a CI environment issue
    # This is expected and should be handled gracefully
    if "exoarmur" in str(e):
        print(f" Filesystem executor not available in CI environment: {e}")
        print(" This is expected - filesystem executor is an optional capability")
        print(f"ℹ️  Filesystem executor not available in CI environment: {e}")
        print("ℹ️  This is expected - filesystem executor is an optional capability")


class FakePDP:
    """Fake PolicyDecisionPoint that allows all operations."""
    
    def __init__(self, verdict=PolicyVerdict.ALLOW):
        self.verdict = verdict
        self.evaluate_called = False
        self.evaluate_intent = None
    
    def evaluate(self, intent):
        self.evaluate_called = True
        self.evaluate_intent = intent
        return PolicyDecision(
            verdict=self.verdict,
            rationale=f"Fake {self.verdict.value} for testing",
            evidence={"fake": True}
        )


class FakeSafetyGate:
    """Fake SafetyGate that allows all operations."""
    
    def __init__(self, allow=True):
        self.allow = allow
        self.evaluate_called = False
        self.evaluate_intent = None
    
    def evaluate(self, intent, policy_decision):
        self.evaluate_called = True
        self.evaluate_intent = intent
        return "allow" if self.allow else "deny"
    
    def evaluate_safety(self, intent, policy_decision=None, **kwargs):
        """Alias for evaluate method to match expected interface."""
        # Return an object with verdict attribute to match expected interface
        verdict = self.evaluate(intent, policy_decision)
        
        class SafetyVerdict:
            def __init__(self, verdict):
                self.verdict = verdict
                self.rationale = f"Fake {verdict} for testing"
                self.rule_ids = []
        
        return SafetyVerdict(verdict)


class TestFilesystemExecutorIntegration:
    """Test filesystem executor integration with ProxyPipeline."""
    
    @pytest.mark.skipif(not FILESYSTEM_EXECUTOR_AVAILABLE, reason="Filesystem executor package not available")
    def test_filesystem_executor_integration(self):
        """Test filesystem executor working with ProxyPipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create filesystem executor
            fs_executor = FilesystemExecutorPlugin(
                allowed_roots=[temp_dir],
                allow_write=True,
                allow_delete=True,
                max_bytes=10_000
            )
            
            # Create pipeline components
            pdp = FakePDP(PolicyVerdict.ALLOW)
            safety_gate = FakeSafetyGate(allow=True)
            audit_emitter = AuditEmitter()
            
            # Create pipeline
            pipeline = ProxyPipeline(pdp, safety_gate, fs_executor, audit_emitter)
            
            # Create test file first
            test_file = os.path.join(temp_dir, "test.txt")
            test_content = "Hello, filesystem executor!"
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            # Create intent for filesystem read
            intent = ActionIntent(
                intent_id="integration-read-test",
                actor_id="test-actor",
                actor_type="test",
                action_type="fs",
                target="filesystem",
                parameters={
                    "operation": "read",
                    "path": "test.txt"
                },
                timestamp=datetime.now(timezone.utc)
            )
            
            result, trace = pipeline.execute_with_trace(intent)
            
            # Verify result
            assert result.success is True
            assert result.output["operation"] == "read"
            assert result.output["content"] == test_content
            
            # Verify trace structure
            assert trace.intent_id == "integration-read-test"
            assert len(trace.events) >= 2  # INTENT_RECEIVED, EXECUTOR_DISPATCHED
            assert trace.final_status == "EXECUTED"
            assert trace.trace_version == "v1"
            
            # Verify executor capabilities in trace
            executor_events = [e for e in trace.events if e.stage.value == "executor_dispatched"]
            assert len(executor_events) == 1
            executor_event = executor_events[0]
            assert executor_event.details["executor_name"] == "fs"
            assert "executor_capabilities" in executor_event.details
            assert executor_event.details["execution_success"] is True
    
    @pytest.mark.skipif(not FILESYSTEM_EXECUTOR_AVAILABLE, reason="Filesystem executor package not available")
    def test_filesystem_executor_write_through_pipeline(self):
        """Test write operation through ProxyPipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create filesystem executor
            fs_executor = FilesystemExecutorPlugin(
                allowed_roots=[temp_dir],
                allow_write=True,
                allow_delete=False,
                max_bytes=10_000
            )
            
            # Create pipeline components
            pdp = FakePDP(PolicyVerdict.ALLOW)
            safety_gate = FakeSafetyGate(allow=True)
            audit_emitter = AuditEmitter()
            
            # Create pipeline
            pipeline = ProxyPipeline(pdp, safety_gate, fs_executor, audit_emitter)
            
            # Execute write intent through pipeline
            intent = ActionIntent(
                intent_id="integration-write-test",
                action_type="fs",
                target="filesystem",
                parameters={
                    "operation": "write",
                    "path": "pipeline_write_test.txt",
                    "content": "Written through pipeline",
                    "mode": "overwrite"
                },
                tenant_id="test-tenant",
                actor_id="test-actor",
                actor_type="test",
                timestamp=datetime.now(timezone.utc)
            )
            
            result, trace = pipeline.execute_with_trace(intent)
            
            # Verify result
            assert result.success is True
            assert result.output["operation"] == "write"
            assert result.output["bytes_written"] == len("Written through pipeline")
            
            # Verify file was created
            created_file = os.path.join(temp_dir, "pipeline_write_test.txt")
            assert os.path.exists(created_file)
            with open(created_file, 'r') as f:
                assert f.read() == "Written through pipeline"
            
            # Verify trace includes executor capabilities
            executor_events = [e for e in trace.events if e.stage.value == "executor_dispatched"]
            assert len(executor_events) == 1
            executor_event = executor_events[0]
            assert executor_event.details["executor_name"] == "fs"
            capabilities = executor_event.details["executor_capabilities"]
            assert "fs.read" in capabilities["capabilities"]
            assert "fs.write" in capabilities["capabilities"]
            assert "fs.delete" in capabilities["capabilities"]
    
    @pytest.mark.skipif(not FILESYSTEM_EXECUTOR_AVAILABLE, reason="Filesystem executor package not available")
    def test_filesystem_executor_blocked_operation(self):
        """Test blocked operation through pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create filesystem executor with write disabled
            fs_executor = FilesystemExecutorPlugin(
                allowed_roots=[temp_dir],
                allow_write=False,  # Write operations blocked
                allow_delete=False,
                max_bytes=10_000
            )
            
            # Create pipeline components
            pdp = FakePDP(PolicyVerdict.ALLOW)
            safety_gate = FakeSafetyGate(allow=True)
            audit_emitter = AuditEmitter()
            
            # Create pipeline
            pipeline = ProxyPipeline(pdp, safety_gate, fs_executor, audit_emitter)
            
            # Execute write intent (should be blocked by executor)
            intent = ActionIntent(
                intent_id="integration-blocked-test",
                action_type="fs",
                target="filesystem",
                parameters={
                    "operation": "write",
                    "path": "blocked_write.txt",
                    "content": "This should be blocked"
                },
                tenant_id="test-tenant",
                actor_id="test-actor",
                actor_type="test",
                timestamp=datetime.now(timezone.utc)
            )
            
            result, trace = pipeline.execute_with_trace(intent)
            
            # Verify result is failure
            assert result.success is False
            assert "Write operations not allowed" in result.error
            
            # Verify trace shows execution failure
            assert trace.final_status == "FAILED"
            executor_events = [e for e in trace.events if e.stage.value == "executor_dispatched"]
            assert len(executor_events) == 1
            executor_event = executor_events[0]
            assert executor_event.details["execution_success"] is False
            assert executor_event.details["execution_error"] == "Write operations not allowed"
