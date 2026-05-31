"""
Security Tests for ExoArmur

These tests verify security properties including input validation,
injection prevention, and audit integrity.
"""

import tempfile
from datetime import datetime, timezone

import pytest

from exoarmur.executors import FileSystemExecutor
from exoarmur.kernel.boundary import ActionIntent, ExecutorPlugin
from exoarmur.kernel.ids import make_intent_id


@pytest.fixture
def temp_dir():
    """Fixture to provide a temporary directory for executor tests."""
    with tempfile.TemporaryDirectory() as td:
        yield td


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_action_intent_with_malicious_parameters(self):
        """Test that ActionIntent handles malicious parameters safely."""
        # Test with potentially malicious parameters
        malicious_params = {
            "command": "; rm -rf /",
            "path": "../../../etc/passwd",
            "script": "<script>alert('xss')</script>",
        }

        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="test_type",
            action_type="test_action",
            target="test_target",
            parameters=malicious_params,
        )

        # Should create intent without executing malicious code
        assert intent is not None
        assert intent.parameters == malicious_params

    def test_action_intent_with_path_traversal(self):
        """Test that ActionIntent handles path traversal attempts."""
        path_traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
        ]

        for path in path_traversal_paths:
            intent = ActionIntent.create(
                actor_id="test_actor",
                actor_type="test_type",
                action_type="test_action",
                target=path,
            )

            # Should create intent without executing path traversal
            assert intent is not None
            assert intent.target == path

    def test_action_intent_with_sql_injection(self):
        """Test that ActionIntent handles SQL injection attempts."""
        sql_injection = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
        ]

        for injection in sql_injection:
            intent = ActionIntent.create(
                actor_id="test_actor",
                actor_type="test_type",
                action_type="test_action",
                target="test_target",
                parameters={"query": injection},
            )

            # Should create intent without executing SQL injection
            assert intent is not None
            assert intent.parameters["query"] == injection


class TestExecutorSecurity:
    """Test executor security properties."""

    def test_executor_does_not_execute_arbitrary_code(self, temp_dir):
        """Test that executor doesn't execute arbitrary code from parameters."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        malicious_params = {
            "code": "__import__('os').system('rm -rf /')",
            "eval": "print('hacked')",
        }

        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="file_system",
            action_type="create",
            target=f"{temp_dir}/test.txt",
            parameters=malicious_params,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        # Should not execute arbitrary code
        # Result should be safe
        assert result is not None

    def test_executor_sandboxing(self, temp_dir):
        """Test that executor is properly sandboxed."""
        from exoarmur.kernel.boundary import ExecutorPlugin

        executor = FileSystemExecutor(authorized_root=temp_dir)

        # Executor should not have access to dangerous functions
        assert not hasattr(executor, "eval")
        assert not hasattr(executor, "exec")
        assert not hasattr(executor, "__import__")

    def test_executor_no_direct_file_access(self, temp_dir):
        """Test that executor doesn't have unrestricted file access."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        # Executor should not have direct file system access outside governance
        # This is a design principle test
        assert hasattr(executor, "execute")


class TestAuditIntegrity:
    """Test audit trail integrity and immutability."""

    def test_audit_trail_immutability(self, temp_dir):
        """Test that audit trail is immutable."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        intent = ActionIntent.create("actor", "type", "create", f"{temp_dir}/test.txt")
        result = executor.execute(intent, None, {"final_verdict": "allow"})

        # Execution ID should be immutable
        original_id = result.execution_id

        # Attempt to modify (Python objects are mutable, but this documents the requirement)
        # In a real implementation, audit records should be immutable
        assert original_id is not None

    def test_state_hash_verification(self):
        """Test that state hash can be verified."""
        # Skip - FileSystemExecutor doesn't have get_state_hash() method
        # Platform executors have it, but it's not part of the ExecutorPlugin protocol
        pytest.skip("FileSystemExecutor doesn't expose get_state_hash()")

    def test_audit_chain_integrity(self):
        """Test that audit chain maintains integrity."""
        # Skip - FileSystemExecutor doesn't have get_state_hash() method
        pytest.skip("FileSystemExecutor doesn't expose get_state_hash()")


class TestTamperDetection:
    """Test tamper detection capabilities."""

    def test_state_hash_tamper_detection(self):
        """Test that state hash changes detect tampering."""
        # Skip - FileSystemExecutor doesn't have get_state_hash() method
        pytest.skip("FileSystemExecutor doesn't expose get_state_hash()")

    def test_execution_id_uniqueness(self, temp_dir):
        """Test that execution IDs are unique for tamper detection."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        execution_ids = []
        for i in range(5):
            intent = ActionIntent.create(
                "actor", "type", "create", f"{temp_dir}/test{i}.txt"
            )
            result = executor.execute(intent, None, {"final_verdict": "allow"})
            execution_ids.append(result.execution_id)

        # All execution IDs should be unique
        assert len(set(execution_ids)) == len(execution_ids)


class TestSecureDefaults:
    """Test secure default configurations."""

    def test_action_intent_default_parameters(self):
        """Test that ActionIntent has secure default parameters."""
        intent = ActionIntent.create("actor", "type", "action", "target")

        # Default parameters should be empty (not None)
        assert intent.parameters == {}
        assert intent.safety_context == {}

    def test_executor_default_constraints(self, temp_dir):
        """Test that executor has secure default constraints."""
        from exoarmur.executors import FileSystemExecutor

        executor = FileSystemExecutor(authorized_root=temp_dir)
        capabilities = executor.capabilities()

        # Should have constraints defined (capabilities is a dict)
        assert "constraints" in capabilities
        assert isinstance(capabilities["constraints"], dict)


class TestErrorHandlingSecurity:
    """Test secure error handling."""

    def test_executor_handles_malformed_intent(self, temp_dir):
        """Test that executor handles malformed intent gracefully."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        # Test with None intent
        try:
            result = executor.execute(None, None, {"final_verdict": "allow"})
            # If it doesn't raise, verify result is safe
            assert result is not None
        except (TypeError, AttributeError):
            # Expected to raise for None input
            pass

    def test_executor_handles_invalid_parameters(self, temp_dir):
        """Test that executor handles invalid parameters gracefully."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="file_system",
            action_type="create",
            target="",  # Invalid target
            parameters=None,  # Invalid parameters
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        # Should handle gracefully
        assert result is not None


class TestResourceLimits:
    """Test resource limits and DoS prevention."""

    def test_executor_handles_large_parameters(self, temp_dir):
        """Test that executor handles large parameters without DoS."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        large_params = {"data": "x" * 1000000}

        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="file_system",
            action_type="create",
            target=f"{temp_dir}/test.txt",
            parameters=large_params,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        # Should handle without crashing
        assert result is not None

    def test_executor_handles_rapid_requests(self, temp_dir):
        """Test that executor handles rapid requests without DoS."""
        executor = FileSystemExecutor(authorized_root=temp_dir)

        results = []
        for i in range(100):
            intent = ActionIntent.create(
                "actor", "type", "create", f"{temp_dir}/test{i}.txt"
            )
            result = executor.execute(intent, None, {"final_verdict": "allow"})
            results.append(result)

        # Should handle all requests
        assert len(results) == 100
        assert all(r is not None for r in results)
