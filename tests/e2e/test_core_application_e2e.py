"""
End-to-end application validation for ExoArmur-Core.

Tests actual Core behavior through real executors without mocks.
Validates installable, runnable application from clean install through
governed execution paths.
"""

import hashlib
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exoarmur.executors.database_executor import DatabaseExecutor
from exoarmur.executors.file_system_executor import FileSystemExecutor
from exoarmur.kernel.boundary import (
    ActionIntent,
    DispatchStatus,
    ExecutionDispatch,
    ExecutorResult,
    PolicyDecision,
    PolicyDecisionPoint,
    PolicyVerdict,
    ProxyPipeline,
    SafetyGate,
    V2AuditEmitter,
    V2EnvironmentState,
    V2PolicyState,
    V2TrustState,
    ValidationResult,
)
from exoarmur.kernel.canonicalization import canonical_hash
from exoarmur.kernel.external_effect import (
    ExternalEffectEvidence,
    ReplayVerificationStatus,
    RollbackStrategy,
)
from exoarmur.kernel.plugin_registry import PluginRegistry, get_plugin_registry
from exoarmur.kernel.replay_verification import verify_evidence_integrity


class MockPolicyDecisionPoint(PolicyDecisionPoint):
    """Mock policy decision point for testing."""

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=PolicyVerdict.ALLOW,
            rationale="Test policy allows all",
        )

    def approval_status(self, intent_id: str):
        from exoarmur.kernel.boundary import ApprovalStatus

        return ApprovalStatus.NOT_REQUIRED


class TestFileSystemExecutorE2E:
    """End-to-end tests for FileSystemExecutor through ProxyPipeline."""

    def test_filesystem_allow_path(self, tmp_path):
        """Test FileSystemExecutor allows operations within authorized root."""
        # Setup
        authorized_root = tmp_path / "authorized"
        authorized_root.mkdir()

        executor = FileSystemExecutor(authorized_root=str(authorized_root))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create intent for file creation
        target_file = authorized_root / "test.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="file_create",
            target=str(target_file),
            parameters={"operation": "create", "payload": {"content": "test content"}},
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions
        assert isinstance(
            result, ExecutorResult
        ), f"Expected ExecutorResult, got {type(result)}"
        assert result.success, f"Execution failed: {result.error}"
        assert target_file.exists(), "File was not created"
        assert target_file.read_text() == "test content", "File content mismatch"
        assert "evidence" in result.__dict__, "No evidence in result"
        assert (
            result.evidence.get("action_class") is not None
        ), "No action class in evidence"
        assert len(trace.events) > 0, "No trace events recorded"

        # Verify operation didn't escape authorized root
        assert (
            target_file.resolve().parent == authorized_root.resolve()
        ), "File created outside authorized root"

    def test_filesystem_deny_path(self, tmp_path):
        """Test FileSystemExecutor denies operations outside authorized root."""
        # Setup
        authorized_root = tmp_path / "authorized"
        authorized_root.mkdir()
        unauthorized_root = tmp_path / "unauthorized"
        unauthorized_root.mkdir()

        executor = FileSystemExecutor(authorized_root=str(authorized_root))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create intent for file creation outside authorized root
        target_file = unauthorized_root / "test.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="file_create",
            target=str(target_file),
            parameters={"operation": "create", "payload": {"content": "test content"}},
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions - should be blocked by target validation
        # Result is ExecutionDispatch when blocked
        assert isinstance(
            result, ExecutionDispatch
        ), f"Expected ExecutionDispatch, got {type(result)}"
        assert (
            result.status == DispatchStatus.BLOCKED
        ), f"Expected BLOCKED, got {result.status}"
        assert not target_file.exists(), "File should not have been created"

    def test_filesystem_deny_by_safety_gate(self, tmp_path):
        """Test FileSystemExecutor denies operations via safety gate."""
        # Setup
        authorized_root = tmp_path / "authorized"
        authorized_root.mkdir()

        executor = FileSystemExecutor(authorized_root=str(authorized_root))

        # Policy that denies
        class DenyingPolicy(PolicyDecisionPoint):
            def evaluate(self, intent: ActionIntent) -> PolicyDecision:
                return PolicyDecision.create(
                    intent_id=intent.intent_id,
                    verdict=PolicyVerdict.DENY,
                    rationale="Test policy denies",
                )

            def approval_status(self, intent_id: str):
                from exoarmur.kernel.boundary import ApprovalStatus

                return ApprovalStatus.DENIED

        policy = DenyingPolicy()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create intent
        target_file = authorized_root / "test.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="file_create",
            target=str(target_file),
            parameters={"operation": "create", "payload": {"content": "test content"}},
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions
        assert isinstance(
            result, ExecutionDispatch
        ), f"Expected ExecutionDispatch, got {type(result)}"
        assert (
            result.status == DispatchStatus.BLOCKED
        ), f"Expected BLOCKED, got {result.status}"
        assert not target_file.exists(), "File should not have been created"


class TestDatabaseExecutorE2E:
    """End-to-end tests for DatabaseExecutor through ProxyPipeline."""

    def test_database_allow_path(self, tmp_path):
        """Test DatabaseExecutor allows operations within authorized directory."""
        # Setup
        authorized_db_dir = tmp_path / "databases"
        authorized_db_dir.mkdir()

        executor = DatabaseExecutor(authorized_db_dir=str(authorized_db_dir))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create table intent
        db_path = authorized_db_dir / "test.db"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="db_create_table",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "table": "users",
                "payload": {"schema": {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}},
            },
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions
        assert isinstance(
            result, ExecutorResult
        ), f"Expected ExecutorResult, got {type(result)}"
        assert result.success, f"Execution failed: {result.error}"
        assert db_path.exists(), "Database was not created"

        # Verify table was created
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) == 1, "Table was not created"
        assert "evidence" in result.__dict__, "No evidence in result"

        # Insert intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="db_insert",
            target=str(db_path),
            parameters={
                "operation": "insert",
                "table": "users",
                "payload": {"data": {"id": 1, "name": "test"}},
            },
        )

        result, trace = pipeline.execute_with_trace(intent)
        assert isinstance(
            result, ExecutorResult
        ), f"Expected ExecutorResult, got {type(result)}"
        assert result.success, f"Insert failed: {result.error}"

        # Select intent
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="db_select",
            target=str(db_path),
            parameters={
                "operation": "select",
                "table": "users",
                "payload": {"where": {"id": 1}},
            },
        )

        result, trace = pipeline.execute_with_trace(intent)
        assert isinstance(
            result, ExecutorResult
        ), f"Expected ExecutorResult, got {type(result)}"
        assert result.success, f"Select failed: {result.error}"
        assert (
            len(result.output.get("result", {}).get("rows", [])) == 1
        ), "Row not found"

    def test_database_deny_path(self, tmp_path):
        """Test DatabaseExecutor denies operations outside authorized directory."""
        # Setup
        authorized_db_dir = tmp_path / "databases"
        authorized_db_dir.mkdir()
        unauthorized_db_dir = tmp_path / "unauthorized"
        unauthorized_db_dir.mkdir()

        executor = DatabaseExecutor(authorized_db_dir=str(authorized_db_dir))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create intent for database outside authorized directory
        db_path = unauthorized_db_dir / "test.db"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="db_create_table",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "table": "users",
                "payload": {"schema": {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}},
            },
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions
        assert isinstance(
            result, ExecutionDispatch
        ), f"Expected ExecutionDispatch, got {type(result)}"
        assert (
            result.status == DispatchStatus.BLOCKED
        ), f"Expected BLOCKED, got {result.status}"
        assert not db_path.exists(), "Database should not have been created"

    def test_database_deny_by_safety_gate(self, tmp_path):
        """Test DatabaseExecutor denies operations via safety gate."""
        # Setup
        authorized_db_dir = tmp_path / "databases"
        authorized_db_dir.mkdir()

        executor = DatabaseExecutor(authorized_db_dir=str(authorized_db_dir))

        # Policy that denies
        class DenyingPolicy(PolicyDecisionPoint):
            def evaluate(self, intent: ActionIntent) -> PolicyDecision:
                return PolicyDecision.create(
                    intent_id=intent.intent_id,
                    verdict=PolicyVerdict.DENY,
                    rationale="Test policy denies",
                )

            def approval_status(self, intent_id: str):
                from exoarmur.kernel.boundary import ApprovalStatus

                return ApprovalStatus.DENIED

        policy = DenyingPolicy()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()

        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

        # Create intent
        db_path = authorized_db_dir / "test.db"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="human",
            action_type="db_create_table",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "table": "users",
                "payload": {"schema": {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}},
            },
        )

        # Execute through pipeline
        result, trace = pipeline.execute_with_trace(intent)

        # Assertions
        assert isinstance(
            result, ExecutionDispatch
        ), f"Expected ExecutionDispatch, got {type(result)}"
        assert (
            result.status == DispatchStatus.BLOCKED
        ), f"Expected BLOCKED, got {result.status}"
        assert not db_path.exists(), "Database should not have been created"


class TestExternalEffectEvidenceE2E:
    """End-to-end tests for external effect evidence and replay verification."""

    def test_evidence_integrity_verification(self):
        """Test evidence integrity verification passes for untampered evidence."""
        # Create evidence
        request = {"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        response = {"choices": [{"message": {"content": "response"}}]}

        request_hash = canonical_hash(request)
        response_hash = canonical_hash(response)

        evidence = ExternalEffectEvidence(
            execution_id="exec_123",
            intent_id="intent_123",
            trace_id="trace_123",
            provider="openai",
            operation_type="chat_completion",
            request_canonical_hash=request_hash,
            response_canonical_hash=response_hash,
            normalized_request=request,
            normalized_response=response,
            evidence_timestamp=datetime.now(timezone.utc),
            irreversible_effect=False,
            rollback_strategy=RollbackStrategy.RECORD_ONLY,
        )

        # Verify integrity
        result = verify_evidence_integrity(evidence)

        # Assertions
        assert (
            result.status == ReplayVerificationStatus.VERIFIED
        ), f"Expected VERIFIED, got {result.status}"
        assert len(result.details) == 0, f"Expected no details, got {result.details}"

    def test_evidence_tamper_detection(self):
        """Test evidence tamper detection fails closed."""
        # Create evidence
        request = {"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        response = {"choices": [{"message": {"content": "response"}}]}

        request_hash = canonical_hash(request)
        response_hash = canonical_hash(response)

        evidence = ExternalEffectEvidence(
            execution_id="exec_123",
            intent_id="intent_123",
            trace_id="trace_123",
            provider="openai",
            operation_type="chat_completion",
            request_canonical_hash=request_hash,
            response_canonical_hash=response_hash,
            normalized_request=request,
            normalized_response=response,
            evidence_timestamp=datetime.now(timezone.utc),
            irreversible_effect=False,
            rollback_strategy=RollbackStrategy.RECORD_ONLY,
        )

        # Tamper with request
        evidence.normalized_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "tampered"}],
        }

        # Verify integrity
        result = verify_evidence_integrity(evidence)

        # Assertions
        assert (
            result.status == ReplayVerificationStatus.MISMATCH
        ), f"Expected MISMATCH, got {result.status}"
        assert "field" in result.details, "Expected field in details"
        assert (
            result.details["field"] == "request"
        ), f"Expected 'request', got {result.details['field']}"

    def test_response_tamper_detection(self):
        """Test response tamper detection fails closed."""
        # Create evidence
        request = {"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        response = {"choices": [{"message": {"content": "response"}}]}

        request_hash = canonical_hash(request)
        response_hash = canonical_hash(response)

        evidence = ExternalEffectEvidence(
            execution_id="exec_123",
            intent_id="intent_123",
            trace_id="trace_123",
            provider="openai",
            operation_type="chat_completion",
            request_canonical_hash=request_hash,
            response_canonical_hash=response_hash,
            normalized_request=request,
            normalized_response=response,
            evidence_timestamp=datetime.now(timezone.utc),
            irreversible_effect=False,
            rollback_strategy=RollbackStrategy.RECORD_ONLY,
        )

        # Tamper with response
        evidence.normalized_response = {
            "choices": [{"message": {"content": "tampered"}}]
        }

        # Verify integrity
        result = verify_evidence_integrity(evidence)

        # Assertions
        assert (
            result.status == ReplayVerificationStatus.MISMATCH
        ), f"Expected MISMATCH, got {result.status}"
        assert "field" in result.details, "Expected field in details"
        assert (
            result.details["field"] == "response"
        ), f"Expected 'response', got {result.details['field']}"


class TestPluginRegistryE2E:
    """End-to-end tests for plugin registry."""

    def test_manual_plugin_registration(self):
        """Test manual plugin registration and loading."""

        # Create a fake executor plugin
        class FakeExecutor:
            def name(self) -> str:
                return "FakeExecutor"

            def capabilities(self) -> dict:
                return {"executor_name": "FakeExecutor", "version": "1.0.0"}

            def validate_target(self, intent):
                from exoarmur.kernel.boundary import (
                    TargetValidationResult,
                    ValidationResult,
                )

                return TargetValidationResult(
                    result=ValidationResult.VALID,
                    evidence={"test": True},
                    validation_id="test_validation",
                )

            def execute(self, intent, policy_decision, governance_context):
                from exoarmur.kernel.boundary import ExecutorResult

                return ExecutorResult(
                    success=True,
                    output={"test": True},
                    evidence={"test": True},
                    execution_id="test_exec",
                )

            def supports_capability(self, capability: str) -> bool:
                return capability in ["test"]

        # Register plugin
        registry = PluginRegistry()
        registry.register_plugin("fake", FakeExecutor)

        # Load plugin
        plugin = registry.load_plugin("fake")

        # Assertions
        assert plugin is not None, "Plugin should have been loaded"
        assert plugin.name() == "FakeExecutor", f"Wrong name: {plugin.name()}"
        assert plugin.supports_capability("test"), "Should support test capability"

        # Verify it implements ExecutorPlugin contract
        assert hasattr(plugin, "name"), "Missing name method"
        assert hasattr(plugin, "capabilities"), "Missing capabilities method"
        assert hasattr(plugin, "validate_target"), "Missing validate_target method"
        assert hasattr(plugin, "execute"), "Missing execute method"
        assert hasattr(
            plugin, "supports_capability"
        ), "Missing supports_capability method"


class TestKernelIsolationE2E:
    """End-to-end tests for kernel isolation (no vendor SDK imports)."""

    def test_kernel_no_vendor_sdk_imports(self):
        """Confirm kernel imports do not include vendor/network SDKs."""
        import sys

        import exoarmur.kernel as kernel_module

        # Get all modules imported by kernel
        kernel_modules = set()
        for name, module in sys.modules.items():
            if name.startswith("exoarmur.kernel"):
                kernel_modules.add(name)

        # Check for forbidden imports
        forbidden_patterns = [
            "openai",
            "anthropic",
            "langchain",
            "transformers",
            "torch",
            "sklearn",
            "tensorflow",
            "requests",
            "httpx",
            "socket",
            "urllib",
            "nats",  # NATS is in dependencies but not in kernel
        ]

        # Check each kernel module's imports
        for module_name in kernel_modules:
            module = sys.modules.get(module_name)
            if module is None:
                continue

            # Get module file
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue

            # Read source and check for forbidden imports
            try:
                with open(module_file, "r") as f:
                    source = f.read()

                for pattern in forbidden_patterns:
                    # Check for import statements
                    if f"import {pattern}" in source or f"from {pattern}" in source:
                        # Check if it's in a comment or string (basic check)
                        lines = source.split("\n")
                        for line in lines:
                            if (
                                f"import {pattern}" in line or f"from {pattern}" in line
                            ) and not line.strip().startswith("#"):
                                pytest.fail(
                                    f"Found forbidden import '{pattern}' in {module_file}: {line.strip()}"
                                )
            except Exception:
                # Skip files that can't be read
                pass

        # Also check that kernel modules don't import from executors that have vendor SDKs
        vendor_executor_modules = [
            "exoarmur.executors.openai_executor",
            "exoarmur.executors.anthropic_executor",
            "exoarmur.executors.langchain_executor",
            "exoarmur.executors.huggingface_executor",
        ]

        for module_name in kernel_modules:
            module = sys.modules.get(module_name)
            if module is None:
                continue

            # Check module's __dict__ for references to vendor executors
            for attr_name, attr_value in module.__dict__.items():
                if hasattr(attr_value, "__module__"):
                    if attr_value.__module__ in vendor_executor_modules:
                        pytest.fail(
                            f"Kernel module {module_name} imports from vendor executor {attr_value.__module__}"
                        )
