"""
Core type definitions for ExoArmur V2 Module System
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, FrozenSet, Set, Any, Union, Callable
from enum import Enum
from datetime import datetime, timezone
import hashlib
import json

# === CORE IDENTIFIERS ===

@dataclass(frozen=True)
class ModuleID:
    """Module identifier with strict typing"""
    value: str
    
    def __post_init__(self):
        if len(self.value) != 26:
            raise ValueError("ModuleID must be 26-character ULID")
        if not self.value.isalnum():
            raise ValueError("ModuleID must be alphanumeric")

@dataclass(frozen=True)
class ModuleVersion:
    """Module version with semantic versioning"""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    
    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        return base
    
    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version numbers must be non-negative")

@dataclass(frozen=True)
class ExecutionID:
    """Execution identifier with strict typing"""
    value: str
    
    def __post_init__(self):
        if len(self.value) != 26:
            raise ValueError("ExecutionID must be 26-character ULID")
        if not self.value.isalnum():
            raise ValueError("ExecutionID must be alphanumeric")

@dataclass(frozen=True)
class DeterministicSeed:
    """Deterministic seed for reproducible execution"""
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("DeterministicSeed must be non-negative")
        if self.value > 2**63 - 1:
            raise ValueError("DeterministicSeed exceeds maximum value")

# === STATE ENUMS ===

class StateEnum(Enum):
    """Lifecycle states matching V2 specification"""
    REGISTERED = "registered"
    VALIDATING = "validating"
    REJECTED = "rejected"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    INIT_FAILED = "init_failed"
    READY = "ready"
    EXECUTING = "executing"
    EXECUTION_FAILED = "execution_failed"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FINALIZING = "finalizing"
    FINALIZED = "finalized"

# === FAILURE CODES ===

class FailureCode(Enum):
    """Standardized failure codes"""
    SCHEMA_INVALID = "schema_invalid"
    INTERFACE_MISMATCH = "interface_mismatch"
    FORBIDDEN_PATTERN_DETECTED = "forbidden_pattern_detected"
    DEPENDENCY_CYCLE = "dependency_cycle"
    REPLAY_DIVERGENCE = "replay_divergence"
    LIFECYCLE_NONCOMPLIANCE = "lifecycle_noncompliance"
    INPUT_OUTPUT_INCONSISTENCY = "input_output_inconsistency"
    CONCURRENCY_VIOLATION = "concurrency_violation"
    RANDOMNESS_VIOLATION = "randomness_violation"
    TIME_MODEL_VIOLATION = "time_model_violation"
    IO_VIOLATION = "io_violation"
    MODULE_INVARIANT_FAILURE = "module_invariant_failure"
    SYSTEM_INVARIANT_FAILURE = "system_invariant_failure"
    FAILURE_NONDETERMINISM = "failure_nondeterminism"
    MALFORMED_INPUT_FAILURE = "malformed_input_failure"
    CORRUPTED_CONTEXT_FAILURE = "corrupted_context_failure"
    ADVERSARIAL_BREAKDOWN = "adversarial_breakdown"
    DEPENDENCY_MANIPULATION_FAILURE = "dependency_manipulation_failure"
    CERTIFICATION_EXCEPTION = "certification_exception"

# === CORE DATA STRUCTURES ===

@dataclass(frozen=True)
class ModuleExecutionContext:
    """Complete execution context for deterministic execution"""
    execution_id: ExecutionID
    module_id: ModuleID
    module_version: ModuleVersion
    deterministic_seed: DeterministicSeed
    logical_timestamp: int
    dependency_hash: str
    
    def compute_context_hash(self) -> str:
        """Compute deterministic context hash"""
        context_data = {
            'execution_id': self.execution_id.value,
            'module_id': self.module_id.value,
            'module_version': str(self.module_version),
            'deterministic_seed': self.deterministic_seed.value,
            'logical_timestamp': self.logical_timestamp,
            'dependency_hash': self.dependency_hash
        }
        return hashlib.sha256(json.dumps(context_data, sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class DeterministicTransition:
    """Deterministic state transition record"""
    from_state: StateEnum
    to_state: StateEnum
    event: str
    context_hash: str
    transition_hash: str
    timestamp: int
    
    def __post_init__(self):
        if not self.transition_hash:
            # Compute transition hash if not provided
            transition_data = {
                'from_state': self.from_state.value,
                'to_state': self.to_state.value,
                'event': self.event,
                'context_hash': self.context_hash,
                'timestamp': self.timestamp
            }
            object.__setattr__(self, 'transition_hash', 
                            hashlib.sha256(json.dumps(transition_data, sort_keys=True).encode()).hexdigest())

@dataclass(frozen=True)
class ModuleInput:
    """Deterministic module input"""
    data: Dict[str, Any]
    input_hash: str
    timestamp: int
    
    def __post_init__(self):
        if not self.input_hash:
            # Compute input hash if not provided
            input_data = {
                'data': self.data,
                'timestamp': self.timestamp
            }
            object.__setattr__(self, 'input_hash',
                            hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest())

@dataclass(frozen=True)
class ModuleOutput:
    """Deterministic module output"""
    data: Dict[str, Any]
    output_hash: str
    timestamp: int
    success: bool
    
    def __post_init__(self):
        if not self.output_hash:
            # Compute output hash if not provided
            output_data = {
                'data': self.data,
                'timestamp': self.timestamp,
                'success': self.success
            }
            object.__setattr__(self, 'output_hash',
                            hashlib.sha256(json.dumps(output_data, sort_keys=True).encode()).hexdigest())

@dataclass(frozen=True)
class AuditEvent:
    """Deterministic audit event"""
    event_id: str
    execution_id: ExecutionID
    module_id: ModuleID
    event_type: str
    event_data: Dict[str, Any]
    timestamp: int
    previous_event_hash: str
    current_event_hash: str
    
    def __post_init__(self):
        if not self.current_event_hash:
            # Compute event hash if not provided
            event_data = {
                'event_id': self.event_id,
                'execution_id': self.execution_id.value,
                'module_id': self.module_id.value,
                'event_type': self.event_type,
                'event_data': self.event_data,
                'timestamp': self.timestamp,
                'previous_event_hash': self.previous_event_hash
            }
            object.__setattr__(self, 'current_event_hash',
                            hashlib.sha256(json.dumps(event_data, sort_keys=True).encode()).hexdigest())

# === TYPE ALIASES ===

ModuleHash = str
ContextHash = str
EventHash = str
TransitionHash = str
LogicalTimestamp = int