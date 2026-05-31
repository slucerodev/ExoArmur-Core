"""
LangChain Executor Scaffold for ExoArmur Governance

This is a SCAFFOLD/REFERENCE IMPLEMENTATION for LangChain agent governance.

This file demonstrates the structure for a LangChain executor but does NOT include
real LangChain integration. The _execute_langchain_operation() method returns mock data.

For a real LangChain executor with actual integration, see the optional addon package:
exoarmur-langchain-executor

This scaffold implements:
- ExecutorPlugin protocol compliance
- Governance boundary integration
- Evidence capture structure
- Rollback semantics for agent operations

Real platform integrations belong in optional addon packages that:
- Implement actual LangChain agent operations
- Use Core's ExternalEffectEvidence schema
- Support LIVE/REPLAY modes
- Require vendor SDK dependencies (langchain package)
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from exoarmur.kernel.boundary import (
    ActionClass,
    ActionIntent,
    ExecutorCapabilities,
    ExecutorPlugin,
    ExecutorResult,
    TargetValidationResult,
    ValidationResult,
)
from exoarmur.kernel.clock import utc_now
from exoarmur.kernel.ids import make_decision_id, make_intent_id

# ============================================================================
# LANGCHAIN ACTION TYPES
# ============================================================================


class LangChainActionType:
    """Classification of LangChain operations for governance."""

    AGENT_RUN = "agent_run"
    TOOL_CALL = "tool_call"
    CHAIN_EXECUTION = "chain_execution"
    PROMPT_EXECUTION = "prompt_execution"
    LLM_INVOKE = "llm_invoke"
    MEMORY_OPERATION = "memory_operation"


# ============================================================================
# LANGCHAIN ACTION INTENT
# ============================================================================


@dataclass
class LangChainActionIntent:
    """Canonical action intent for LangChain operations."""

    intent_id: str
    actor_id: str
    actor_type: str
    action_type: str
    target: str
    payload: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_canonical(self) -> str:
        """Convert to canonical JSON for deterministic hashing."""
        canonical = json.dumps(
            {
                "intent_id": self.intent_id,
                "actor_id": self.actor_id,
                "actor_type": self.actor_type,
                "action_type": self.action_type,
                "target": self.target,
                "payload": self.payload,
                "timestamp": self.timestamp.isoformat(),
                "metadata": self.metadata,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return canonical

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical intent."""
        canonical = self.to_canonical()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ============================================================================
# LANGCHAIN EXECUTION RESULT
# ============================================================================


@dataclass
class LangChainExecutionResult:
    """Result of LangChain operation execution."""

    decision_id: str
    intent_id: str
    status: str
    output: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    rollback_info: Optional[Dict[str, Any]] = None
    state_hash: Optional[str] = None

    def compute_state_hash(self) -> str:
        """Compute hash of execution state for verification."""
        state = {
            "decision_id": self.decision_id,
            "intent_id": self.intent_id,
            "status": self.status,
            "output": str(self.output),
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }
        canonical = json.dumps(
            state, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ============================================================================
# LANGCHAIN EXECUTOR
# ============================================================================


class LangChainExecutor(ExecutorPlugin):
    """
    Executor for LangChain operations with governance boundary enforcement.

    This executor provides:
    - Deterministic audit trails for LangChain operations
    - Rollback capabilities for reversible operations
    - State hash verification for integrity
    - Integration with ExoArmur governance boundary
    """

    def __init__(self):
        """Initialize LangChain executor."""
        self._execution_history: List[LangChainExecutionResult] = []
        self._rollback_stack: List[Dict[str, Any]] = []

    def get_capabilities(self) -> ExecutorCapabilities:
        """Return executor capabilities."""
        return ExecutorCapabilities(
            executor_name="LangChainExecutor",
            version="1.0.0",
            capabilities=[
                "agent_run",
                "tool_call",
                "chain_execution",
                "prompt_execution",
                "llm_invoke",
                "memory_operation",
            ],
            constraints={"max_execution_time_ms": 30000, "max_payload_size_mb": 10},
            supported_targets=[
                "langchain_agent",
                "langchain_tool",
                "langchain_chain",
                "langchain_memory",
            ],
        )

    def validate_target(self, target: str, action_type: str) -> TargetValidationResult:  # type: ignore[override]
        """Validate target for LangChain operation."""
        # Basic validation - in real implementation, this would check
        # if the target is a valid LangChain component
        # Note: This scaffold has incorrect signature - real implementation should use intent: ActionIntent
        return TargetValidationResult(
            result=ValidationResult.VALID,
            evidence={"target": target, "action_type": action_type},
            validation_id="scaffold_validation",
        )

    def execute(
        self,
        intent: ActionIntent,
        policy_decision: Any,
        governance_context: Dict[str, Any],
    ) -> ExecutorResult:
        """
        Execute a LangChain action with governance boundary enforcement.

        Args:
            intent: The action intent to execute
            policy_decision: Policy decision authorizing execution
            governance_context: Additional governance context (e.g., final_verdict)

        Returns:
            Execution result with audit information
        """
        # Check governance context for final verdict
        final_verdict = governance_context.get("final_verdict")
        if final_verdict and str(final_verdict).upper() == "DENY":
            return ExecutorResult(
                success=False,
                output={},
                error="Execution denied by governance boundary",
                evidence={"intent_id": intent.intent_id, "governance_verdict": "DENY"},
                execution_id=make_decision_id(intent.intent_id, intent.action_type),
            )

        execution_id = make_decision_id(intent.intent_id, intent.action_type)
        start_time = utc_now()

        try:
            # Execute the LangChain operation
            output = self._execute_langchain_operation(intent)
            success = True
            error = None

            # Capture rollback information if operation is reversible
            rollback_info = (
                self._capture_rollback_info(intent, output)
                if self._is_reversible(intent)
                else None
            )

        except Exception as e:
            output = {}
            success = False
            error = str(e)
            rollback_info = None

        # Calculate execution time
        end_time = utc_now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Create execution result
        langchain_result = LangChainExecutionResult(
            decision_id=execution_id,
            intent_id=intent.intent_id,
            status="success" if success else "error",
            output=output,
            error=error,
            execution_time_ms=execution_time_ms,
            rollback_info=rollback_info,
        )

        # Compute state hash
        langchain_result.state_hash = langchain_result.compute_state_hash()

        # Add to execution history
        self._execution_history.append(langchain_result)

        # Add to rollback stack if reversible
        if rollback_info:
            self._rollback_stack.append(rollback_info)

        # Return ExecutorResult for governance boundary compatibility
        return ExecutorResult(
            success=success,
            output=output,
            error=error,
            evidence={
                "execution_id": execution_id,
                "intent_id": intent.intent_id,
                "execution_time_ms": execution_time_ms,
                "state_hash": langchain_result.state_hash,
                "rollback_available": rollback_info is not None,
            },
            execution_id=execution_id,
        )

    def _execute_langchain_operation(self, intent: ActionIntent) -> Any:
        """
        Execute the actual LangChain operation.

        This is a placeholder for the actual LangChain integration.
        In a real implementation, this would:
        - Initialize LangChain components based on intent
        - Execute the operation (agent run, tool call, chain execution, etc.)
        - Return the output

        For now, this returns a mock output for testing purposes.
        """
        # Mock implementation for testing
        if intent.action_type == LangChainActionType.AGENT_RUN:
            return {"agent_output": "Mock agent execution result", "steps": []}
        elif intent.action_type == LangChainActionType.TOOL_CALL:
            return {"tool_output": "Mock tool call result"}
        elif intent.action_type == LangChainActionType.CHAIN_EXECUTION:
            return {"chain_output": "Mock chain execution result"}
        elif intent.action_type == LangChainActionType.PROMPT_EXECUTION:
            return {"prompt_output": "Mock prompt execution result"}
        elif intent.action_type == LangChainActionType.LLM_INVOKE:
            return {"llm_output": "Mock LLM invocation result"}
        elif intent.action_type == LangChainActionType.MEMORY_OPERATION:
            return {"memory_output": "Mock memory operation result"}
        else:
            raise ValueError(f"Unknown action type: {intent.action_type}")

    def _is_reversible(self, intent: ActionIntent) -> bool:
        """
        Determine if an operation is reversible.

        Memory operations and some tool calls are reversible.
        Agent runs and LLM invocations are generally not reversible.
        """
        reversible_types = [
            LangChainActionType.MEMORY_OPERATION,
            LangChainActionType.TOOL_CALL,
        ]
        return intent.action_type in reversible_types

    def _capture_rollback_info(
        self, intent: ActionIntent, output: Any
    ) -> Dict[str, Any]:
        """
        Capture information needed for rollback.

        For memory operations, this captures the previous state.
        For tool calls, this captures the pre-operation state.
        """
        rollback_info = {
            "intent_id": intent.intent_id,
            "action_type": intent.action_type,
            "timestamp": utc_now().isoformat(),
            "previous_state": self._get_previous_state(intent),
        }
        return rollback_info

    def _get_previous_state(self, intent: ActionIntent) -> Dict[str, Any]:
        """
        Get the previous state for rollback purposes.

        This is a placeholder for actual state capture.
        In a real implementation, this would:
        - Query the current state of the affected resource
        - Capture it for rollback
        """
        # Mock implementation
        return {"state": "previous_state_placeholder"}

    def rollback(self, execution_id: str) -> ExecutorResult:
        """
        Rollback a specific execution.

        Args:
            execution_id: The execution ID to rollback

        Returns:
            ExecutorResult with rollback status
        """
        # Find the execution in rollback stack by execution_id (decision_id)
        rollback_info = None
        for info in reversed(self._rollback_stack):
            # Check if this rollback info matches the execution_id
            # The rollback_info contains intent_id, but we need to match against execution_id
            # For now, we'll just take the most recent rollback info
            rollback_info = info
            break

        if not rollback_info:
            return ExecutorResult(
                success=False,
                output={},
                error="Rollback info not found",
                evidence={"execution_id": execution_id},
                execution_id=execution_id,
            )

        # Perform the rollback
        try:
            self._perform_rollback(rollback_info)
            return ExecutorResult(
                success=True,
                output={"rollback_status": "completed"},
                error=None,
                evidence={
                    "execution_id": execution_id,
                    "intent_id": rollback_info.get("intent_id", ""),
                    "state_hash": self.get_state_hash(),
                },
                execution_id=execution_id,
            )
        except Exception as e:
            return ExecutorResult(
                success=False,
                output={},
                error=str(e),
                evidence={
                    "execution_id": execution_id,
                    "intent_id": rollback_info.get("intent_id", ""),
                },
                execution_id=execution_id,
            )

    def _perform_rollback(self, rollback_info: Dict[str, Any]) -> None:
        """
        Perform the actual rollback operation.

        This is a placeholder for actual rollback implementation.
        In a real implementation, this would:
        - Restore the previous state
        - Verify the rollback was successful
        - Update audit trail
        """
        # Mock implementation
        pass

    def get_execution_history(self) -> List[LangChainExecutionResult]:
        """Get the execution history."""
        return self._execution_history.copy()

    def get_state_hash(self) -> str:
        """
        Compute the current state hash of the executor.

        Returns:
            SHA-256 hash of current executor state
        """
        state = {
            "execution_count": len(self._execution_history),
            "rollback_stack_size": len(self._rollback_stack),
            "last_execution": (
                self._execution_history[-1].state_hash
                if self._execution_history
                else None
            ),
        }
        canonical = json.dumps(
            state, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_langchain_intent(
    actor_id: str,
    action_type: str,
    target: str,
    payload: Dict[str, Any],
    actor_type: str = "langchain_agent",
) -> LangChainActionIntent:
    """
    Create a LangChain action intent.

    Args:
        actor_id: ID of the actor initiating the action
        action_type: Type of LangChain operation
        target: Target of the operation
        payload: Operation payload
        actor_type: Type of actor (default: langchain_agent)

    Returns:
        LangChainActionIntent instance
    """
    intent_id = make_intent_id(actor_id, action_type, target)
    timestamp = utc_now()

    return LangChainActionIntent(
        intent_id=intent_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action_type=action_type,
        target=target,
        payload=payload,
        timestamp=timestamp,
    )
