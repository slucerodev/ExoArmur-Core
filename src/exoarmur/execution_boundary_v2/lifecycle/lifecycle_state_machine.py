"""
Lifecycle State Machine implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, FrozenSet, Any
from enum import Enum
import hashlib
import json

from ..core.core_types import *

# === LIFECYCLE EVENTS ===

class LifecycleEvent(Enum):
    """Lifecycle events for state transitions"""
    REGISTER_MODULE = "register_module"
    START_VALIDATION = "start_validation"
    VALIDATION_COMPLETE = "validation_complete"
    VALIDATION_FAILED = "validation_failed"
    START_INITIALIZATION = "start_initialization"
    INITIALIZATION_COMPLETE = "initialization_complete"
    INITIALIZATION_FAILED = "initialization_failed"
    START_EXECUTION = "start_execution"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    START_COMMIT = "start_commit"
    COMMIT_COMPLETE = "commit_complete"
    COMMIT_FAILED = "commit_failed"
    START_ROLLBACK = "start_rollback"
    ROLLBACK_COMPLETE = "rollback_complete"
    START_FINALIZATION = "start_finalization"
    FINALIZATION_COMPLETE = "finalization_complete"

# === TRANSITION FUNCTION ===

@dataclass(frozen=True)
class TransitionContext:
    """Context for state transitions"""
    execution_context: ModuleExecutionContext
    logical_timestamp: int
    event_data: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class TransitionResult:
    """Result of state transition"""
    success: bool
    next_state: StateEnum
    transition: DeterministicTransition
    error: Optional[str] = None

class DeterministicTransitionFunction:
    """Deterministic state transition function: STATE_NEXT = f(STATE_CURRENT, EVENT, CONTEXT)"""
    
    def __init__(self):
        self.transition_matrix = self._build_transition_matrix()
    
    def next_state(self, current_state: StateEnum, event: LifecycleEvent, context: TransitionContext) -> TransitionResult:
        """Compute next state deterministically"""
        
        if not self._is_transition_allowed(current_state, event):
            return TransitionResult(
                success=False,
                next_state=StateEnum.EXECUTION_FAILED,
                transition=DeterministicTransition(
                    from_state=current_state,
                    to_state=StateEnum.EXECUTION_FAILED,
                    event=event.value,
                    context_hash=context.execution_context.compute_context_hash(),
                    transition_hash="",
                    timestamp=context.logical_timestamp
                ),
                error=f"Invalid transition: {current_state.value} + {event.value}"
            )
        
        next_state = self.transition_matrix[(current_state, event)]
        
        transition = DeterministicTransition(
            from_state=current_state,
            to_state=next_state,
            event=event.value,
            context_hash=context.execution_context.compute_context_hash(),
            transition_hash="",
            timestamp=context.logical_timestamp
        )
        
        return TransitionResult(
            success=True,
            next_state=next_state,
            transition=transition
        )
    
    def _build_transition_matrix(self) -> Dict[Tuple[StateEnum, LifecycleEvent], StateEnum]:
        """Build explicit transition table"""
        return {
            # Registration phase
            (StateEnum.REGISTERED, LifecycleEvent.START_VALIDATION): StateEnum.VALIDATING,
            (StateEnum.REGISTERED, LifecycleEvent.START_FINALIZATION): StateEnum.FINALIZING,
            
            # Validation phase
            (StateEnum.VALIDATING, LifecycleEvent.VALIDATION_COMPLETE): StateEnum.INITIALIZING,
            (StateEnum.VALIDATING, LifecycleEvent.VALIDATION_FAILED): StateEnum.REJECTED,
            
            # Initialization phase
            (StateEnum.INITIALIZING, LifecycleEvent.INITIALIZATION_COMPLETE): StateEnum.INITIALIZED,
            (StateEnum.INITIALIZING, LifecycleEvent.INITIALIZATION_FAILED): StateEnum.INIT_FAILED,
            
            # Ready phase
            (StateEnum.INITIALIZED, LifecycleEvent.START_EXECUTION): StateEnum.READY,
            (StateEnum.READY, LifecycleEvent.START_EXECUTION): StateEnum.EXECUTING,
            
            # Execution phase
            (StateEnum.EXECUTING, LifecycleEvent.EXECUTION_COMPLETE): StateEnum.COMMITTING,
            (StateEnum.EXECUTING, LifecycleEvent.EXECUTION_FAILED): StateEnum.EXECUTION_FAILED,
            
            # Commit phase
            (StateEnum.COMMITTING, LifecycleEvent.COMMIT_COMPLETE): StateEnum.COMMITTED,
            (StateEnum.COMMITTING, LifecycleEvent.COMMIT_FAILED): StateEnum.ROLLING_BACK,
            
            # Failure handling
            (StateEnum.EXECUTION_FAILED, LifecycleEvent.START_ROLLBACK): StateEnum.ROLLING_BACK,
            (StateEnum.INIT_FAILED, LifecycleEvent.START_FINALIZATION): StateEnum.FINALIZING,
            
            # Rollback phase
            (StateEnum.ROLLING_BACK, LifecycleEvent.ROLLBACK_COMPLETE): StateEnum.ROLLED_BACK,
            (StateEnum.ROLLED_BACK, LifecycleEvent.START_FINALIZATION): StateEnum.FINALIZING,
            
            # Rejection phase
            (StateEnum.REJECTED, LifecycleEvent.START_FINALIZATION): StateEnum.FINALIZING,
            
            # Success finalization
            (StateEnum.COMMITTED, LifecycleEvent.START_FINALIZATION): StateEnum.FINALIZING,
            
            # Final phase
            (StateEnum.FINALIZING, LifecycleEvent.FINALIZATION_COMPLETE): StateEnum.FINALIZED,
        }
    
    def _is_transition_allowed(self, current_state: StateEnum, event: LifecycleEvent) -> bool:
        """Check if transition is allowed in transition matrix"""
        return (current_state, event) in self.transition_matrix

# === STATE VALIDATION ===

@dataclass(frozen=True)
class StateInvariant:
    """State invariant definition"""
    invariant_id: str
    description: str

class StateValidator:
    """State invariant validator"""
    
    def __init__(self):
        self.state_invariants = self._build_state_invariants()
    
    def validate_state(self, state: StateEnum, context: TransitionContext) -> bool:
        """Validate state invariants"""
        if state not in self.state_invariants:
            return False
        
        invariants = self.state_invariants[state]
        
        for invariant in invariants:
            if not self._check_invariant(invariant, context):
                return False
        
        return True
    
    def _build_state_invariants(self) -> Dict[StateEnum, List[StateInvariant]]:
        """Build state invariants"""
        return {
            StateEnum.REGISTERED: [
                StateInvariant("module_id_defined", "Module ID must be defined"),
                StateInvariant("execution_context_valid", "Execution context must be valid")
            ],
            StateEnum.VALIDATING: [
                StateInvariant("validation_rules_present", "Validation rules must be present"),
                StateInvariant("resource_limits_enforced", "Resource limits must be enforced")
            ],
            StateEnum.EXECUTING: [
                StateInvariant("determinism_guaranteed", "Determinism must be guaranteed"),
                StateInvariant("audit_trail_consistent", "Audit trail must be consistent")
            ],
            StateEnum.COMMITTED: [
                StateInvariant("commit_successful", "Commit must be successful")
            ],
            StateEnum.FINALIZED: [
                StateInvariant("lifecycle_complete", "Lifecycle must be complete")
            ]
        }
    
    def _check_invariant(self, invariant: StateInvariant, context: TransitionContext) -> bool:
        """Check individual invariant"""
        if invariant.invariant_id == "module_id_defined":
            return bool(context.execution_context.module_id.value)
        elif invariant.invariant_id == "execution_context_valid":
            return context.execution_context is not None
        elif invariant.invariant_id == "determinism_guaranteed":
            return context.execution_context.deterministic_seed.value >= 0
        
        return True