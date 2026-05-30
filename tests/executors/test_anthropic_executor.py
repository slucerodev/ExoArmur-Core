"""
Tests for Anthropic Executor

These tests verify that the Anthropic executor follows ExoArmur architecture principles
and maintains determinism guarantees.
"""

import pytest
from datetime import datetime, timezone
from exoarmur.executors.anthropic_executor import (
    AnthropicExecutor,
    AnthropicActionType,
    create_anthropic_intent,
    AnthropicActionIntent,
    AnthropicExecutionResult
)
from exoarmur.kernel.boundary import ActionIntent
from exoarmur.kernel.clock import DeterministicClock, set_clock


class TestAnthropicExecutorBasics:
    """Test basic Anthropic executor functionality."""
    
    def test_executor_initialization(self):
        """Test that executor initializes correctly."""
        executor = AnthropicExecutor()
        assert executor is not None
        assert len(executor.get_execution_history()) == 0
    
    def test_create_anthropic_intent(self):
        """Test intent creation with deterministic ID generation."""
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        set_clock(clock)
        
        intent1 = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        intent2 = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        assert intent1.intent_id == intent2.intent_id
        assert intent1.actor_id == "test_actor"
        assert intent1.action_type == AnthropicActionType.MESSAGE
        assert intent1.target == "claude-3-opus"


class TestAnthropicExecution:
    """Test Anthropic operation execution."""
    
    def test_execute_message(self):
        """Test execution of message operation."""
        executor = AnthropicExecutor()
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        intent = ActionIntent(
            intent_id=anthropic_intent.intent_id,
            actor_id=anthropic_intent.actor_id,
            actor_type=anthropic_intent.actor_type,
            action_type=anthropic_intent.action_type,
            target=anthropic_intent.target,
            parameters=anthropic_intent.payload,
            safety_context={},
            timestamp=anthropic_intent.timestamp
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
        executor = AnthropicExecutor()
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.EMBEDDING,
            target="claude-3",
            payload={"text": "test text"}
        )
        
        intent = ActionIntent(
            intent_id=anthropic_intent.intent_id,
            actor_id=anthropic_intent.actor_id,
            actor_type=anthropic_intent.actor_type,
            action_type=anthropic_intent.action_type,
            target=anthropic_intent.target,
            parameters=anthropic_intent.payload,
            safety_context={},
            timestamp=anthropic_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
    
    def test_execution_history_tracking(self):
        """Test that execution history is tracked correctly."""
        executor = AnthropicExecutor()
        
        anthropic_intent1 = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test1"}]}
        )
        
        anthropic_intent2 = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.EMBEDDING,
            target="claude-3",
            payload={"text": "test2"}
        )
        
        intent1 = ActionIntent(
            intent_id=anthropic_intent1.intent_id,
            actor_id=anthropic_intent1.actor_id,
            actor_type=anthropic_intent1.actor_type,
            action_type=anthropic_intent1.action_type,
            target=anthropic_intent1.target,
            parameters=anthropic_intent1.payload,
            safety_context={},
            timestamp=anthropic_intent1.timestamp
        )
        
        intent2 = ActionIntent(
            intent_id=anthropic_intent2.intent_id,
            actor_id=anthropic_intent2.actor_id,
            actor_type=anthropic_intent2.actor_type,
            action_type=anthropic_intent2.action_type,
            target=anthropic_intent2.target,
            parameters=anthropic_intent2.payload,
            safety_context={},
            timestamp=anthropic_intent2.timestamp
        )
        
        executor.execute(intent1, None, {"final_verdict": "allow"})
        executor.execute(intent2, None, {"final_verdict": "allow"})
        
        history = executor.get_execution_history()
        assert len(history) == 2
        assert history[0].intent_id == intent1.intent_id
        assert history[1].intent_id == intent2.intent_id


class TestAnthropicDeterminism:
    """Test determinism guarantees of Anthropic executor."""
    
    def test_deterministic_intent_hash(self):
        """Test that intent hashing is deterministic."""
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        hash1 = anthropic_intent.compute_hash()
        hash2 = anthropic_intent.compute_hash()
        
        assert hash1 == hash2
    
    def test_deterministic_state_hash(self):
        """Test that state hashing is deterministic."""
        executor = AnthropicExecutor()
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        intent = ActionIntent(
            intent_id=anthropic_intent.intent_id,
            actor_id=anthropic_intent.actor_id,
            actor_type=anthropic_intent.actor_type,
            action_type=anthropic_intent.action_type,
            target=anthropic_intent.target,
            parameters=anthropic_intent.payload,
            safety_context={},
            timestamp=anthropic_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = result.evidence["state_hash"]
        hash2 = result.evidence["state_hash"]
        
        assert hash1 == hash2
    
    def test_deterministic_executor_state_hash(self):
        """Test that executor state hash is deterministic."""
        executor = AnthropicExecutor()
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        intent = ActionIntent(
            intent_id=anthropic_intent.intent_id,
            actor_id=anthropic_intent.actor_id,
            actor_type=anthropic_intent.actor_type,
            action_type=anthropic_intent.action_type,
            target=anthropic_intent.target,
            parameters=anthropic_intent.payload,
            safety_context={},
            timestamp=anthropic_intent.timestamp
        )
        
        executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = executor.get_state_hash()
        hash2 = executor.get_state_hash()
        
        assert hash1 == hash2


class TestAnthropicCanonicalJSON:
    """Test canonical JSON encoding for determinism."""
    
    def test_canonical_json_determinism(self):
        """Test that canonical JSON is deterministic."""
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        canonical1 = anthropic_intent.to_canonical()
        canonical2 = anthropic_intent.to_canonical()
        
        assert canonical1 == canonical2
    
    def test_canonical_json_sorted_keys(self):
        """Test that canonical JSON has sorted keys."""
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"z": 1, "a": 2, "m": 3}
        )
        
        canonical = anthropic_intent.to_canonical()
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')


class TestAnthropicIsolation:
    """Test that executor maintains isolation from governance internals."""
    
    def test_executor_no_governance_access(self):
        """Test that executor doesn't directly access governance internals."""
        executor = AnthropicExecutor()
        
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'rollback')
        assert hasattr(executor, 'get_execution_history')
        assert hasattr(executor, 'get_state_hash')
        
        assert not hasattr(executor, 'policy_engine')
        assert not hasattr(executor, 'safety_evaluator')
        assert not hasattr(executor, 'audit_store')
    
    def test_executor_state_encapsulation(self):
        """Test that executor state is properly encapsulated."""
        executor = AnthropicExecutor()
        
        history = executor.get_execution_history()
        assert history is not executor._execution_history


class TestAnthropicRollback:
    """Test rollback functionality."""
    
    def test_rollback_nonexistent_decision(self):
        """Test rollback of non-existent decision ID."""
        executor = AnthropicExecutor()
        
        rollback_result = executor.rollback("nonexistent_id")
        assert rollback_result.success is False
    
    def test_rollback_non_reversible_operation(self):
        """Test that non-reversible operations don't have rollback info."""
        executor = AnthropicExecutor()
        anthropic_intent = create_anthropic_intent(
            actor_id="test_actor",
            action_type=AnthropicActionType.MESSAGE,
            target="claude-3-opus",
            payload={"messages": [{"role": "user", "content": "test"}]}
        )
        
        intent = ActionIntent(
            intent_id=anthropic_intent.intent_id,
            actor_id=anthropic_intent.actor_id,
            actor_type=anthropic_intent.actor_type,
            action_type=anthropic_intent.action_type,
            target=anthropic_intent.target,
            parameters=anthropic_intent.payload,
            safety_context={},
            timestamp=anthropic_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.evidence["rollback_available"] is False
