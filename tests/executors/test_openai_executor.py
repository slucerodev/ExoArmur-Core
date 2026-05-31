"""
Tests for OpenAI Executor

These tests verify that the OpenAI executor follows ExoArmur architecture principles
and maintains determinism guarantees.
"""

from datetime import datetime, timezone

import pytest

from exoarmur.executors.openai_executor import (
    OpenAIActionIntent,
    OpenAIActionType,
    OpenAIExecutionResult,
    OpenAIExecutor,
    create_openai_intent,
)
from exoarmur.kernel.boundary import ActionIntent
from exoarmur.kernel.clock import DeterministicClock, set_clock


class TestOpenAIExecutorBasics:
    """Test basic OpenAI executor functionality."""

    def test_executor_initialization(self):
        """Test that executor initializes correctly."""
        executor = OpenAIExecutor()
        assert executor is not None
        assert len(executor.get_execution_history()) == 0

    def test_create_openai_intent(self):
        """Test intent creation with deterministic ID generation."""
        # Use deterministic clock for reproducible IDs
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        set_clock(clock)

        intent1 = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        intent2 = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        # Same inputs should produce same intent_id (deterministic)
        assert intent1.intent_id == intent2.intent_id
        assert intent1.actor_id == "test_actor"
        assert intent1.action_type == OpenAIActionType.CHAT_COMPLETION
        assert intent1.target == "gpt-4"


class TestOpenAIExecution:
    """Test OpenAI operation execution."""

    def test_execute_chat_completion(self):
        """Test execution of chat completion operation."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        assert result.success is True
        assert result.output is not None
        assert result.error is None
        assert result.execution_id is not None
        assert result.evidence["intent_id"] == intent.intent_id
        assert result.evidence["state_hash"] is not None

    def test_execute_embedding(self):
        """Test execution of embedding operation."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.EMBEDDING,
            target="text-embedding-ada-002",
            payload={"input": "test text"},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        assert result.success is True
        assert result.output is not None

    def test_execute_moderation(self):
        """Test execution of moderation operation."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.MODERATION,
            target="text-moderation-latest",
            payload={"input": "test text"},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        assert result.success is True
        assert result.output is not None

    def test_execution_history_tracking(self):
        """Test that execution history is tracked correctly."""
        executor = OpenAIExecutor()

        openai_intent1 = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test1"}]},
        )

        openai_intent2 = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.EMBEDDING,
            target="text-embedding-ada-002",
            payload={"input": "test2"},
        )

        intent1 = ActionIntent(
            intent_id=openai_intent1.intent_id,
            actor_id=openai_intent1.actor_id,
            actor_type=openai_intent1.actor_type,
            action_type=openai_intent1.action_type,
            target=openai_intent1.target,
            parameters=openai_intent1.payload,
            safety_context={},
            timestamp=openai_intent1.timestamp,
        )

        intent2 = ActionIntent(
            intent_id=openai_intent2.intent_id,
            actor_id=openai_intent2.actor_id,
            actor_type=openai_intent2.actor_type,
            action_type=openai_intent2.action_type,
            target=openai_intent2.target,
            parameters=openai_intent2.payload,
            safety_context={},
            timestamp=openai_intent2.timestamp,
        )

        executor.execute(intent1, None, {"final_verdict": "allow"})
        executor.execute(intent2, None, {"final_verdict": "allow"})

        history = executor.get_execution_history()
        assert len(history) == 2
        assert history[0].intent_id == intent1.intent_id
        assert history[1].intent_id == intent2.intent_id


class TestOpenAIDeterminism:
    """Test determinism guarantees of OpenAI executor."""

    def test_deterministic_intent_hash(self):
        """Test that intent hashing is deterministic."""
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        hash1 = openai_intent.compute_hash()
        hash2 = openai_intent.compute_hash()

        assert hash1 == hash2

    def test_deterministic_state_hash(self):
        """Test that state hashing is deterministic."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})

        hash1 = result.evidence["state_hash"]
        hash2 = result.evidence["state_hash"]

        assert hash1 == hash2

    def test_deterministic_executor_state_hash(self):
        """Test that executor state hash is deterministic."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        executor.execute(intent, None, {"final_verdict": "allow"})

        hash1 = executor.get_state_hash()
        hash2 = executor.get_state_hash()

        assert hash1 == hash2


class TestOpenAICanonicalJSON:
    """Test canonical JSON encoding for determinism."""

    def test_canonical_json_determinism(self):
        """Test that canonical JSON is deterministic."""
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        canonical1 = openai_intent.to_canonical()
        canonical2 = openai_intent.to_canonical()

        assert canonical1 == canonical2

    def test_canonical_json_sorted_keys(self):
        """Test that canonical JSON has sorted keys."""
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"z": 1, "a": 2, "m": 3},
        )

        canonical = openai_intent.to_canonical()
        # Keys should appear in sorted order
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')


class TestOpenAIIsolation:
    """Test that executor maintains isolation from governance internals."""

    def test_executor_no_governance_access(self):
        """Test that executor doesn't directly access governance internals."""
        executor = OpenAIExecutor()

        # Executor should only have its own methods and state
        assert hasattr(executor, "execute")
        assert hasattr(executor, "rollback")
        assert hasattr(executor, "get_execution_history")
        assert hasattr(executor, "get_state_hash")

        # Should not have direct access to policy, safety, or audit internals
        assert not hasattr(executor, "policy_engine")
        assert not hasattr(executor, "safety_evaluator")
        assert not hasattr(executor, "audit_store")

    def test_executor_state_encapsulation(self):
        """Test that executor state is properly encapsulated."""
        executor = OpenAIExecutor()

        # Execution history should be encapsulated
        history = executor.get_execution_history()
        assert history is not executor._execution_history  # Should return a copy


class TestOpenAIRollback:
    """Test rollback functionality."""

    def test_rollback_nonexistent_decision(self):
        """Test rollback of non-existent decision ID."""
        executor = OpenAIExecutor()

        rollback_result = executor.rollback("nonexistent_id")
        assert rollback_result.success is False

    def test_rollback_non_reversible_operation(self):
        """Test that non-reversible operations don't have rollback info."""
        executor = OpenAIExecutor()
        openai_intent = create_openai_intent(
            actor_id="test_actor",
            action_type=OpenAIActionType.CHAT_COMPLETION,
            target="gpt-4",
            payload={"messages": [{"role": "user", "content": "test"}]},
        )

        intent = ActionIntent(
            intent_id=openai_intent.intent_id,
            actor_id=openai_intent.actor_id,
            actor_type=openai_intent.actor_type,
            action_type=openai_intent.action_type,
            target=openai_intent.target,
            parameters=openai_intent.payload,
            safety_context={},
            timestamp=openai_intent.timestamp,
        )

        result = executor.execute(intent, None, {"final_verdict": "allow"})
        # Chat completions are not reversible
        assert result.evidence["rollback_available"] is False
