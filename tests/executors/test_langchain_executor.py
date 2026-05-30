"""
Tests for LangChain Executor

These tests verify that the LangChain executor follows ExoArmur architecture principles
and maintains determinism guarantees.
"""

import pytest
from datetime import datetime, timezone
from exoarmur.executors.langchain_executor import (
    LangChainExecutor,
    LangChainActionType,
    create_langchain_intent,
    LangChainActionIntent,
    LangChainExecutionResult
)
from exoarmur.kernel.boundary import ActionIntent, ActionClass
from exoarmur.kernel.clock import DeterministicClock, set_clock


class TestLangChainExecutorBasics:
    """Test basic LangChain executor functionality."""
    
    def test_executor_initialization(self):
        """Test that executor initializes correctly."""
        executor = LangChainExecutor()
        assert executor is not None
        assert len(executor.get_execution_history()) == 0
    
    def test_create_langchain_intent(self):
        """Test intent creation with deterministic ID generation."""
        # Use deterministic clock for reproducible IDs
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        set_clock(clock)
        
        intent1 = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        intent2 = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        # Same inputs should produce same intent_id (deterministic)
        assert intent1.intent_id == intent2.intent_id
        assert intent1.actor_id == "test_actor"
        assert intent1.action_type == LangChainActionType.AGENT_RUN
        assert intent1.target == "test_target"
        assert intent1.payload == {"test": "data"}


class TestLangChainExecution:
    """Test LangChain operation execution."""
    
    def test_execute_agent_run(self):
        """Test execution of agent run operation."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_agent",
            payload={"input": "test input"}
        )
        
        # Convert to ActionIntent for governance boundary
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
        assert result.error is None
        assert result.execution_id is not None
        assert result.evidence["intent_id"] == intent.intent_id
        assert result.evidence["state_hash"] is not None
    
    def test_execute_tool_call(self):
        """Test execution of tool call operation."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.TOOL_CALL,
            target="test_tool",
            payload={"tool_input": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
        assert result.evidence["rollback_available"] is True  # Tool calls are reversible
    
    def test_execute_chain_execution(self):
        """Test execution of chain operation."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.CHAIN_EXECUTION,
            target="test_chain",
            payload={"chain_input": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
    
    def test_execute_memory_operation(self):
        """Test execution of memory operation."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.MEMORY_OPERATION,
            target="test_memory",
            payload={"memory_key": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
        assert result.evidence["rollback_available"] is True  # Memory operations are reversible
    
    def test_execution_history_tracking(self):
        """Test that execution history is tracked correctly."""
        executor = LangChainExecutor()
        
        langchain_intent1 = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_agent",
            payload={"input": "test1"}
        )
        
        langchain_intent2 = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.TOOL_CALL,
            target="test_tool",
            payload={"tool_input": "test2"}
        )
        
        intent1 = ActionIntent(
            intent_id=langchain_intent1.intent_id,
            actor_id=langchain_intent1.actor_id,
            actor_type=langchain_intent1.actor_type,
            action_type=langchain_intent1.action_type,
            target=langchain_intent1.target,
            parameters=langchain_intent1.payload,
            safety_context={},
            timestamp=langchain_intent1.timestamp
        )
        
        intent2 = ActionIntent(
            intent_id=langchain_intent2.intent_id,
            actor_id=langchain_intent2.actor_id,
            actor_type=langchain_intent2.actor_type,
            action_type=langchain_intent2.action_type,
            target=langchain_intent2.target,
            parameters=langchain_intent2.payload,
            safety_context={},
            timestamp=langchain_intent2.timestamp
        )
        
        executor.execute(intent1, None, {"final_verdict": "allow"})
        executor.execute(intent2, None, {"final_verdict": "allow"})
        
        history = executor.get_execution_history()
        assert len(history) == 2
        assert history[0].intent_id == intent1.intent_id
        assert history[1].intent_id == intent2.intent_id


class TestLangChainDeterminism:
    """Test determinism guarantees of LangChain executor."""
    
    def test_deterministic_intent_hash(self):
        """Test that intent hashing is deterministic."""
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        hash1 = langchain_intent.compute_hash()
        hash2 = langchain_intent.compute_hash()
        
        assert hash1 == hash2
    
    def test_deterministic_state_hash(self):
        """Test that state hashing is deterministic."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = result.evidence["state_hash"]
        hash2 = result.evidence["state_hash"]
        
        assert hash1 == hash2
    
    def test_deterministic_executor_state_hash(self):
        """Test that executor state hash is deterministic."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = executor.get_state_hash()
        hash2 = executor.get_state_hash()
        
        assert hash1 == hash2


class TestLangChainRollback:
    """Test rollback functionality."""
    
    def test_rollback_reversible_operation(self):
        """Test rollback of reversible operation (tool call)."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.TOOL_CALL,
            target="test_tool",
            payload={"tool_input": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.evidence["rollback_available"] is True
        
        # Attempt rollback
        rollback_result = executor.rollback(result.execution_id)
        assert rollback_result.success is True
    
    def test_rollback_memory_operation(self):
        """Test rollback of memory operation."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.MEMORY_OPERATION,
            target="test_memory",
            payload={"memory_key": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.evidence["rollback_available"] is True
        
        # Attempt rollback
        rollback_result = executor.rollback(result.execution_id)
        assert rollback_result.success is True
    
    def test_rollback_non_reversible_operation(self):
        """Test that non-reversible operations don't have rollback info."""
        executor = LangChainExecutor()
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_agent",
            payload={"input": "test"}
        )
        
        intent = ActionIntent(
            intent_id=langchain_intent.intent_id,
            actor_id=langchain_intent.actor_id,
            actor_type=langchain_intent.actor_type,
            action_type=langchain_intent.action_type,
            target=langchain_intent.target,
            parameters=langchain_intent.payload,
            safety_context={},
            timestamp=langchain_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        # Agent runs are not reversible
        assert result.evidence["rollback_available"] is False
    
    def test_rollback_nonexistent_decision(self):
        """Test rollback of non-existent decision ID."""
        executor = LangChainExecutor()
        
        rollback_result = executor.rollback("nonexistent_id")
        assert rollback_result.success is False


class TestLangChainCanonicalJSON:
    """Test canonical JSON encoding for determinism."""
    
    def test_canonical_json_determinism(self):
        """Test that canonical JSON is deterministic."""
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"test": "data"}
        )
        
        canonical1 = langchain_intent.to_canonical()
        canonical2 = langchain_intent.to_canonical()
        
        assert canonical1 == canonical2
    
    def test_canonical_json_sorted_keys(self):
        """Test that canonical JSON has sorted keys."""
        langchain_intent = create_langchain_intent(
            actor_id="test_actor",
            action_type=LangChainActionType.AGENT_RUN,
            target="test_target",
            payload={"z": 1, "a": 2, "m": 3}
        )
        
        canonical = langchain_intent.to_canonical()
        # Keys should appear in sorted order
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')


class TestLangChainIsolation:
    """Test that executor maintains isolation from governance internals."""
    
    def test_executor_no_governance_access(self):
        """Test that executor doesn't directly access governance internals."""
        executor = LangChainExecutor()
        
        # Executor should only have its own methods and state
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'rollback')
        assert hasattr(executor, 'get_execution_history')
        assert hasattr(executor, 'get_state_hash')
        
        # Should not have direct access to policy, safety, or audit internals
        assert not hasattr(executor, 'policy_engine')
        assert not hasattr(executor, 'safety_evaluator')
        assert not hasattr(executor, 'audit_store')
    
    def test_executor_state_encapsulation(self):
        """Test that executor state is properly encapsulated."""
        executor = LangChainExecutor()
        
        # Execution history should be encapsulated
        history = executor.get_execution_history()
        assert history is not executor._execution_history  # Should return a copy
