"""
Determinism Engine implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, FrozenSet, Any
from enum import Enum
import hashlib
import json
import threading
import time

from ..core.core_types import *

# === CONCURRENCY MODEL ===

class ConcurrencyModel(Enum):
    SINGLE_THREADED = "single_threaded"
    DETERMINISTIC_SCHEDULER = "deterministic_scheduler"

# === RANDOMNESS PROTOCOL ===

class SeedSource(Enum):
    INPUT_SEED = "input_seed"
    CONTEXT_SEED = "context_seed"
    HASH_DERIVED = "hash_derived"
    DETERMINISTIC_TIME = "deterministic_time"

class SeedDerivationMethod(Enum):
    DIRECT = "direct"
    HASH_CHAIN = "hash_chain"
    KEY_DERIVATION = "key_derivation"
    COUNTER_MODE = "counter_mode"
    HASH_DERIVED = "hash_derived"

class RandomnessFunction(Enum):
    DETERMINISTIC_PRNG = "deterministic_prng"
    HASH_BASED = "hash_based"
    LINEAR_CONGRUENTIAL = "linear_congruential"

@dataclass(frozen=True)
class RandomnessProtocol:
    seed_source: SeedSource
    seed_derivation: SeedDerivationMethod
    randomness_function: RandomnessFunction
    replay_capture: str

# === LOGICAL TIME ===

@dataclass(frozen=True)
class LogicalTime:
    tick_count: int
    execution_id: str
    module_id: str
    timestamp_ms: int
    
    def advance(self, ticks: int = 1) -> 'LogicalTime':
        return LogicalTime(
            tick_count=self.tick_count + ticks,
            execution_id=self.execution_id,
            module_id=self.module_id,
            timestamp_ms=self.timestamp_ms + (ticks * 1000)
        )
    
    def to_audit_timestamp(self) -> str:
        from datetime import datetime, timezone, timedelta
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        audit_time = base_time + timedelta(milliseconds=self.timestamp_ms)
        return audit_time.isoformat()

class LogicalClock:
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.current_tick = 0
        self.module_times = {}
        self.global_timestamp_ms = 0
    
    def create_module_time(self, module_id: str) -> LogicalTime:
        module_time = LogicalTime(
            tick_count=self.current_tick,
            execution_id=self.execution_id,
            module_id=module_id,
            timestamp_ms=self.global_timestamp_ms
        )
        self.module_times[module_id] = module_time
        return module_time
    
    def advance_global_time(self, ticks: int = 1):
        self.current_tick += ticks
        self.global_timestamp_ms += ticks * 1000
        
        for module_id in self.module_times:
            self.module_times[module_id] = self.module_times[module_id].advance(ticks)
    
    def get_module_time(self, module_id: str) -> LogicalTime:
        if module_id not in self.module_times:
            return self.create_module_time(module_id)
        return self.module_times[module_id]

# === DETERMINISTIC RNG ===

@dataclass(frozen=True)
class DeterministicRNG:
    protocol: RandomnessProtocol
    base_seed: int
    step_counter: int = 0
    captured_sequence: List[Dict[str, Any]] = field(default_factory=list)
    
    def random(self) -> float:
        self.step_counter += 1
        step_seed = self._derive_step_seed(self.step_counter)
        
        if self.protocol.randomness_function == RandomnessFunction.DETERMINISTIC_PRNG:
            value = self._prng_random(step_seed)
        elif self.protocol.randomness_function == RandomnessFunction.HASH_BASED:
            value = self._hash_random(step_seed)
        elif self.protocol.randomness_function == RandomnessFunction.LINEAR_CONGRUENTIAL:
            value = self._lcg_random(step_seed)
        
        self._capture_random_value(value, self.step_counter)
        return value
    
    def randint(self, min_val: int, max_val: int) -> int:
        random_float = self.random()
        return min_val + int(random_float * (max_val - min_val + 1))
    
    def choice(self, sequence: List[Any]) -> Any:
        if not sequence:
            raise ValueError("Cannot choose from empty sequence")
        
        index = self.randint(0, len(sequence) - 1)
        return sequence[index]
    
    def _derive_step_seed(self, step_index: int) -> int:
        if self.protocol.seed_derivation == SeedDerivationMethod.DIRECT:
            return self.base_seed
        elif self.protocol.seed_derivation == SeedDerivationMethod.HASH_CHAIN:
            return self._hash_chain_seed(self.base_seed, step_index)
        elif self.protocol.seed_derivation == SeedDerivationMethod.KEY_DERIVATION:
            return self._key_derivation_seed(self.base_seed, step_index)
        elif self.protocol.seed_derivation == SeedDerivationMethod.COUNTER_MODE:
            return self._counter_mode_seed(self.base_seed, step_index)
        elif self.protocol.seed_derivation == SeedDerivationMethod.HASH_DERIVED:
            return self._hash_derived_seed(self.base_seed, step_index)
        else:
            raise ValueError(f"Unsupported seed derivation method: {self.protocol.seed_derivation}")
    
    def _hash_derived_seed(self, base_seed: int, step_index: int) -> int:
        """Hash-derived seed method for deterministic seed derivation"""
        combined = f"derived:{base_seed}:{step_index}".encode()
        hash_digest = hashlib.sha256(combined).hexdigest()
        return int(hash_digest[:16], 16)
    
    def _hash_chain_seed(self, base_seed: int, step_index: int) -> int:
        combined = f"{base_seed}:{step_index}".encode()
        hash_digest = hashlib.sha256(combined).hexdigest()
        return int(hash_digest[:16], 16)
    
    def _key_derivation_seed(self, base_seed: int, step_index: int) -> int:
        info = step_index.to_bytes(8, 'big')
        salt = base_seed.to_bytes(32, 'big')
        prk = hashlib.hmac('sha256', salt, b'ExoArmur-RNG').digest()
        seed = int.from_bytes(hashlib.hmac('sha256', prk, info).digest()[:8], 'big')
        return seed
    
    def _counter_mode_seed(self, base_seed: int, step_index: int) -> int:
        return base_seed ^ step_index
    
    def _prng_random(self, seed: int) -> float:
        # Simplified ChaCha20-like PRNG
        state = [
            seed & 0xffffffff, (seed >> 32) & 0xffffffff,
            (seed >> 64) & 0xffffffff, (seed >> 96) & 0xffffffff
        ]
        
        for _ in range(20):
            state[0] = (state[0] + state[1]) & 0xffffffff
            state[1] = (state[1] ^ ((state[0] << 16) | (state[0] >> 16))) & 0xffffffff
            state[2] = (state[2] + state[3]) & 0xffffffff
            state[3] = (state[3] ^ ((state[2] << 12) | (state[2] >> 20))) & 0xffffffff
        
        random_int = (state[0] << 32) | state[1]
        return random_int / (2**64 - 1)
    
    def _hash_random(self, seed: int) -> float:
        hash_digest = hashlib.sha256(seed.to_bytes(32, 'big')).hexdigest()
        random_int = int(hash_digest[:16], 16)
        return random_int / (2**64 - 1)
    
    def _lcg_random(self, seed: int) -> float:
        a = 1664525
        c = 1013904223
        m = 2**32
        
        next_val = (a * seed + c) % m
        return next_val / m
    
    def _capture_random_value(self, value: float, step: int):
        capture_entry = {
            'step': step,
            'value': value,
            'seed_used': self._derive_step_seed(step)
        }
        self.captured_sequence.append(capture_entry)

# === IO HANDLING ===

@dataclass(frozen=True)
class IOEvent:
    event_id: str
    operation_type: str
    resource_path: str
    input_data: Optional[bytes]
    output_data: Optional[bytes]
    timestamp: LogicalTime
    deterministic_hash: str
    
    def is_deterministic(self) -> bool:
        return self.deterministic_hash == self._compute_hash()
    
    def _compute_hash(self) -> str:
        event_data = {
            'operation_type': self.operation_type,
            'resource_path': self.resource_path,
            'input_data': self.input_data.hex() if self.input_data else None,
            'timestamp': self.timestamp.tick_count
        }
        return hashlib.sha256(json.dumps(event_data, sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class PreCapturedIOContext:
    file_system: Dict[str, bytes]
    network_responses: Dict[str, bytes]
    io_sequence: List[IOEvent]
    
    def get_io_event(self, event_id: str) -> Optional[IOEvent]:
        for event in self.io_sequence:
            if event.event_id == event_id:
                return event
        return None
    
    def validate_determinism(self) -> bool:
        return all(event.is_deterministic() for event in self.io_sequence)

class DeterministicIOHandler:
    def __init__(self, io_context: PreCapturedIOContext):
        self.io_context = io_context
        self.executed_events = []
        self.current_event_index = 0
    
    def handle_file_read(self, path: str, timestamp: LogicalTime) -> bytes:
        event_id = f"file_read_{path}_{timestamp.tick_count}"
        
        event = self.io_context.get_io_event(event_id)
        if event and event.operation_type == "file_read":
            self.executed_events.append(event)
            return event.output_data or b""
        
        if path in self.io_context.file_system:
            content = self.io_context.file_system[path]
            synthetic_event = IOEvent(
                event_id=event_id,
                operation_type="file_read",
                resource_path=path,
                input_data=None,
                output_data=content,
                timestamp=timestamp,
                deterministic_hash=""
            )
            self.executed_events.append(synthetic_event)
            return content
        
        raise IOError(f"File not found in deterministic context: {path}")
    
    def handle_file_write(self, path: str, data: bytes, timestamp: LogicalTime) -> bool:
        event_id = f"file_write_{path}_{timestamp.tick_count}"
        
        synthetic_event = IOEvent(
            event_id=event_id,
            operation_type="file_write",
            resource_path=path,
            input_data=data,
            output_data=None,
            timestamp=timestamp,
            deterministic_hash=""
        )
        
        self.executed_events.append(synthetic_event)
        self.io_context.file_system[path] = data
        
        return True
    
    def validate_io_determinism(self) -> bool:
        if len(self.executed_events) != len(self.io_context.io_sequence):
            return False
        
        for i, (executed, expected) in enumerate(zip(self.executed_events, self.io_context.io_sequence)):
            if executed.operation_type != expected.operation_type:
                return False
            if executed.resource_path != expected.resource_path:
                return False
        
        return True

# === STATE TRANSITION MODEL ===

@dataclass(frozen=True)
class StateTransition:
    transition_id: str
    input_state_hash: str
    output_state_hash: str
    input_data_hash: str
    context_hash: str
    timestamp: LogicalTime
    
    def is_pure(self) -> bool:
        return True

class PureStateMachine:
    def __init__(self, initial_state: Dict[str, Any]):
        self.current_state = initial_state
        self.state_history = [initial_state]
        self.transition_history = []
    
    def transition(self, input_data: Any, context: ModuleExecutionContext) -> StateTransition:
        input_state_hash = self._compute_state_hash(self.current_state)
        input_data_hash = self._compute_data_hash(input_data)
        context_hash = context.compute_context_hash()
        
        output_state = self._execute_pure_transition(self.current_state, input_data, context)
        output_state_hash = self._compute_state_hash(output_state)
        
        from ..lifecycle.lifecycle_state_machine import LogicalClock
        logical_clock = getattr(context, 'logical_clock', LogicalClock(context.execution_id.value))
        timestamp = logical_clock.get_module_time(context.module_id.value)
        
        transition = StateTransition(
            transition_id=f"transition_{len(self.transition_history)}",
            input_state_hash=input_state_hash,
            output_state_hash=output_state_hash,
            input_data_hash=input_data_hash,
            context_hash=context_hash,
            timestamp=timestamp
        )
        
        self.current_state = output_state
        self.state_history.append(output_state)
        self.transition_history.append(transition)
        
        return transition
    
    def _execute_pure_transition(self, current_state: Dict[str, Any], 
                                input_data: Any, 
                                context: ModuleExecutionContext) -> Dict[str, Any]:
        new_state = current_state.copy()
        
        if isinstance(input_data, dict) and 'operation' in input_data:
            if input_data['operation'] == 'increment':
                new_state['counter'] = new_state.get('counter', 0) + 1
            elif input_data['operation'] == 'reset':
                new_state['counter'] = 0
        
        return new_state
    
    def _compute_state_hash(self, state: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    
    def _compute_data_hash(self, data: Any) -> str:
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        else:
            return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

# === RANDOMNESS CONTROLLER ===

class RandomnessController:
    def __init__(self, protocol: RandomnessProtocol):
        self.protocol = protocol
        self.rng_instances = {}
    
    def get_rng(self, module_id: str, context: ModuleExecutionContext) -> DeterministicRNG:
        if module_id not in self.rng_instances:
            seed = self._extract_seed(context, module_id)
            self.rng_instances[module_id] = DeterministicRNG(self.protocol, seed)
        
        return self.rng_instances[module_id]
    
    def _extract_seed(self, context: ModuleExecutionContext, module_id: str) -> int:
        if self.protocol.seed_source == SeedSource.INPUT_SEED:
            return context.deterministic_seed.value
        
        elif self.protocol.seed_source == SeedSource.CONTEXT_SEED:
            context_hash = self._hash_context(context, module_id)
            return int(context_hash[:16], 16)
        
        elif self.protocol.seed_source == SeedSource.HASH_DERIVED:
            combined = f"{module_id}:{context.execution_id.value}".encode()
            hash_digest = hashlib.sha256(combined).hexdigest()
            return int(hash_digest[:16], 16)
        
        elif self.protocol.seed_source == SeedSource.DETERMINISTIC_TIME:
            return getattr(context, 'logical_timestamp', 0)
        
        return 0
    
    def _hash_context(self, context: ModuleExecutionContext, module_id: str) -> str:
        context_data = {
            'execution_id': context.execution_id.value,
            'module_id': module_id,
            'dependency_hash': context.dependency_hash
        }
        return hashlib.sha256(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
    
    def get_replay_data(self) -> Dict[str, List[Dict]]:
        return {
            module_id: rng.captured_sequence 
            for module_id, rng in self.rng_instances.items()
        }

# === TIME DETERMINISM ENFORCER ===

class TimeDeterminismEnforcer:
    def __init__(self):
        self.forbidden_time_functions = {
            'time.time': 'Use logical clock instead',
            'datetime.now': 'Use logical timestamp instead',
            'datetime.utcnow': 'Use logical timestamp instead',
            'time.perf_counter': 'Use logical clock instead',
            'time.monotonic': 'Use logical clock instead'
        }
    
    def validate_time_usage(self, module_code: str) -> 'TimeValidationResult':
        violations = []
        lines = module_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for forbidden_func, reason in self.forbidden_time_functions.items():
                if forbidden_func in line:
                    violations.append({
                        'line': line_num,
                        'function': forbidden_func,
                        'reason': reason,
                        'code': line.strip()
                    })
        
        return TimeValidationResult(
            is_valid=len(violations) == 0,
            violations=violations
        )
    
    def get_logical_time_provider(self, logical_clock: LogicalClock, module_id: str) -> 'LogicalTimeProvider':
        return LogicalTimeProvider(logical_clock, module_id)

class LogicalTimeProvider:
    def __init__(self, logical_clock: LogicalClock, module_id: str):
        self.logical_clock = logical_clock
        self.module_id = module_id
    
    def time(self) -> float:
        current_time = self.logical_clock.get_module_time(self.module_id)
        return current_time.tick_count
    
    def now(self) -> LogicalTime:
        return self.logical_clock.get_module_time(self.module_id)
    
    def sleep(self, ticks: int):
        self.logical_clock.advance_global_time(ticks)
    
    def timestamp(self) -> str:
        current_time = self.logical_clock.get_module_time(self.module_id)
        return current_time.to_audit_timestamp()

@dataclass(frozen=True)
class TimeValidationResult:
    is_valid: bool
    violations: List[Dict[str, Any]]