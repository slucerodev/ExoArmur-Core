"""
Tests for Hugging Face Executor

These tests verify that the Hugging Face executor follows ExoArmur architecture principles
and maintains determinism guarantees.
"""

import pytest
from datetime import datetime, timezone
from exoarmur.executors.huggingface_executor import (
    HuggingFaceExecutor,
    HuggingFaceActionType,
    create_huggingface_intent,
    HuggingFaceActionIntent,
    HuggingFaceExecutionResult
)
from exoarmur.kernel.boundary import ActionIntent
from exoarmur.kernel.clock import DeterministicClock, set_clock


class TestHuggingFaceExecutorBasics:
    """Test basic Hugging Face executor functionality."""
    
    def test_executor_initialization(self):
        """Test that executor initializes correctly."""
        executor = HuggingFaceExecutor()
        assert executor is not None
        assert len(executor.get_execution_history()) == 0
    
    def test_create_huggingface_intent(self):
        """Test intent creation with deterministic ID generation."""
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        set_clock(clock)
        
        intent1 = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        intent2 = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        assert intent1.intent_id == intent2.intent_id
        assert intent1.actor_id == "test_actor"
        assert intent1.action_type == HuggingFaceActionType.TEXT_GENERATION
        assert intent1.target == "gpt2"


class TestHuggingFaceExecution:
    """Test Hugging Face operation execution."""
    
    def test_execute_text_generation(self):
        """Test execution of text generation operation."""
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
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
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.EMBEDDING,
            target="bert-base-uncased",
            payload={"inputs": "test text"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
    
    def test_execute_question_answering(self):
        """Test execution of question answering operation."""
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.QUESTION_ANSWERING,
            target="deepset/roberta-base-squad2",
            payload={"question": "test", "context": "test context"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        assert result.success is True
        assert result.output is not None
    
    def test_execution_history_tracking(self):
        """Test that execution history is tracked correctly."""
        executor = HuggingFaceExecutor()
        
        hf_intent1 = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test1"}
        )
        
        hf_intent2 = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.EMBEDDING,
            target="bert-base-uncased",
            payload={"inputs": "test2"}
        )
        
        intent1 = ActionIntent(
            intent_id=hf_intent1.intent_id,
            actor_id=hf_intent1.actor_id,
            actor_type=hf_intent1.actor_type,
            action_type=hf_intent1.action_type,
            target=hf_intent1.target,
            parameters=hf_intent1.payload,
            safety_context={},
            timestamp=hf_intent1.timestamp
        )
        
        intent2 = ActionIntent(
            intent_id=hf_intent2.intent_id,
            actor_id=hf_intent2.actor_id,
            actor_type=hf_intent2.actor_type,
            action_type=hf_intent2.action_type,
            target=hf_intent2.target,
            parameters=hf_intent2.payload,
            safety_context={},
            timestamp=hf_intent2.timestamp
        )
        
        executor.execute(intent1, None, {"final_verdict": "allow"})
        executor.execute(intent2, None, {"final_verdict": "allow"})
        
        history = executor.get_execution_history()
        assert len(history) == 2
        assert history[0].intent_id == intent1.intent_id
        assert history[1].intent_id == intent2.intent_id


class TestHuggingFaceDeterminism:
    """Test determinism guarantees of Hugging Face executor."""
    
    def test_deterministic_intent_hash(self):
        """Test that intent hashing is deterministic."""
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        hash1 = hf_intent.compute_hash()
        hash2 = hf_intent.compute_hash()
        
        assert hash1 == hash2
    
    def test_deterministic_state_hash(self):
        """Test that state hashing is deterministic."""
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = result.evidence["state_hash"]
        hash2 = result.evidence["state_hash"]
        
        assert hash1 == hash2
    
    def test_deterministic_executor_state_hash(self):
        """Test that executor state hash is deterministic."""
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
        )
        
        executor.execute(intent, None, {"final_verdict": "allow"})
        
        hash1 = executor.get_state_hash()
        hash2 = executor.get_state_hash()
        
        assert hash1 == hash2


class TestHuggingFaceCanonicalJSON:
    """Test canonical JSON encoding for determinism."""
    
    def test_canonical_json_determinism(self):
        """Test that canonical JSON is deterministic."""
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        canonical1 = hf_intent.to_canonical()
        canonical2 = hf_intent.to_canonical()
        
        assert canonical1 == canonical2
    
    def test_canonical_json_sorted_keys(self):
        """Test that canonical JSON has sorted keys."""
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"z": 1, "a": 2, "m": 3}
        )
        
        canonical = hf_intent.to_canonical()
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')


class TestHuggingFaceIsolation:
    """Test that executor maintains isolation from governance internals."""
    
    def test_executor_no_governance_access(self):
        """Test that executor doesn't directly access governance internals."""
        executor = HuggingFaceExecutor()
        
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'rollback')
        assert hasattr(executor, 'get_execution_history')
        assert hasattr(executor, 'get_state_hash')
        
        assert not hasattr(executor, 'policy_engine')
        assert not hasattr(executor, 'safety_evaluator')
        assert not hasattr(executor, 'audit_store')
    
    def test_executor_state_encapsulation(self):
        """Test that executor state is properly encapsulated."""
        executor = HuggingFaceExecutor()
        
        history = executor.get_execution_history()
        assert history is not executor._execution_history


class TestHuggingFaceRollback:
    """Test rollback functionality."""
    
    def test_rollback_nonexistent_decision(self):
        """Test rollback of non-existent decision ID."""
        executor = HuggingFaceExecutor()
        
        rollback_result = executor.rollback("nonexistent_id")
        assert rollback_result.success is False
    
    def test_rollback_non_reversible_operation(self):
        """Test that non-reversible operations don't have rollback info."""
        executor = HuggingFaceExecutor()
        hf_intent = create_huggingface_intent(
            actor_id="test_actor",
            action_type=HuggingFaceActionType.TEXT_GENERATION,
            target="gpt2",
            payload={"inputs": "test input"}
        )
        
        intent = ActionIntent(
            intent_id=hf_intent.intent_id,
            actor_id=hf_intent.actor_id,
            actor_type=hf_intent.actor_type,
            action_type=hf_intent.action_type,
            target=hf_intent.target,
            parameters=hf_intent.payload,
            safety_context={},
            timestamp=hf_intent.timestamp
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.evidence["rollback_available"] is False
