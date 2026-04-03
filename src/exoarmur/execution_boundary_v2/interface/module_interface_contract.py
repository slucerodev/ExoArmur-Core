"""
Module Interface Contract implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, FrozenSet, Any
from enum import Enum
import hashlib
import json

from ..core.core_types import *

# === INTERFACE ENUMS ===

class CertificationTier(Enum):
    TIER_0_SANDBOX = "tier_0_sandbox"
    TIER_1_COMMUNITY = "tier_1_community"
    TIER_2_ENTERPRISE = "tier_2_enterprise"
    TIER_3_OFFICIAL = "tier_3_official"

class SerializationFormat(Enum):
    CANONICAL_JSON = "canonical_json"
    MESSAGEPACK = "messagepack"
    PROTOBUF_V3 = "protobuf_v3"
    CBOR_CANONICAL = "cbor_canonical"

class DeterminismLevel(Enum):
    PURE_DETERMINISTIC = "pure_deterministic"
    INPUT_DETERMINISTIC = "input_deterministic"
    PROBABILISTIC = "probabilistic"
    NON_DETERMINISTIC = "non_deterministic"

class ReplayCapability(Enum):
    FULL_REPLAY = "full_replay"
    LOGICAL_REPLAY = "logical_replay"
    STATE_REPLAY = "state_replay"
    NO_REPLAY = "no_replay"

class SideEffectProfile(Enum):
    PURE_FUNCTION = "pure_function"
    LOCAL_STATE = "local_state"
    SANDBOXED_IO = "sandboxed_io"
    EXTERNAL_IO = "external_io"

class StateAccessPattern(Enum):
    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ISOLATED = "isolated"

class IsolationLevel(Enum):
    MODULE_LEVEL = "module_level"
    EXECUTION_LEVEL = "execution_level"
    SESSION_LEVEL = "session_level"
    GLOBAL_LEVEL = "global_level"

# === SCHEMA TYPES ===

@dataclass(frozen=True)
class SchemaType:
    type_name: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    nullable: bool = False
    default_value: Optional[Any] = None
    custom_validator: Optional[str] = None

@dataclass(frozen=True)
class ValidationRule:
    rule_type: str
    parameters: Dict[str, Any]
    error_message: str

# === MODULE INPUT ===

@dataclass(frozen=True)
class ModuleInputSchema:
    schema_version: str = "1.0"
    input_types: Dict[str, SchemaType] = field(default_factory=dict)
    required_fields: FrozenSet[str] = field(default_factory=frozenset)
    optional_fields: FrozenSet[str] = field(default_factory=frozenset)
    serialization_format: SerializationFormat = SerializationFormat.CANONICAL_JSON
    validation_rules: Tuple[ValidationRule, ...] = field(default_factory=tuple)
    max_input_size: int = 1024 * 1024
    strict_mode: bool = True
    
    def validate_input(self, input_data: bytes) -> 'ValidatedInput':
        if len(input_data) > self.max_input_size:
            raise ValueError(f"Input size {len(input_data)} exceeds limit {self.max_input_size}")
        
        parsed = self._deserialize_input(input_data)
        self._validate_schema(parsed)
        
        for rule in self.validation_rules:
            self._apply_validation_rule(rule, parsed)
        
        return ValidatedInput(
            data=parsed,
            hash=self._compute_input_hash(input_data),
            serialization_format=self.serialization_format
        )
    
    def _deserialize_input(self, input_data: bytes) -> Dict[str, Any]:
        if self.serialization_format == SerializationFormat.CANONICAL_JSON:
            try:
                return json.loads(input_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON input: {e}")
        else:
            raise ValueError(f"Unsupported serialization format: {self.serialization_format}")
    
    def _validate_schema(self, parsed: Dict[str, Any]):
        for field_name in self.required_fields:
            if field_name not in parsed:
                raise ValueError(f"Required field {field_name} missing")
        
        for field_name, field_value in parsed.items():
            if field_name in self.input_types:
                schema_type = self.input_types[field_name]
                self._validate_field_type(field_value, schema_type)
    
    def _validate_field_type(self, value: Any, schema_type: SchemaType):
        if schema_type.type_name == "string" and not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")
        elif schema_type.type_name == "integer" and not isinstance(value, int):
            raise ValueError(f"Expected integer, got {type(value)}")
        elif schema_type.type_name == "float" and not isinstance(value, (float, int)):
            raise ValueError(f"Expected number, got {type(value)}")
        elif schema_type.type_name == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Expected boolean, got {type(value)}")
        
        # Apply constraints
        if 'min_value' in schema_type.constraints and isinstance(value, (int, float)):
            if value < schema_type.constraints['min_value']:
                raise ValueError(f"Value {value} below minimum {schema_type.constraints['min_value']}")
        
        if 'max_value' in schema_type.constraints and isinstance(value, (int, float)):
            if value > schema_type.constraints['max_value']:
                raise ValueError(f"Value {value} above maximum {schema_type.constraints['max_value']}")
    
    def _apply_validation_rule(self, rule: ValidationRule, data: Dict[str, Any]):
        if rule.rule_type == "range_check":
            field = rule.parameters.get("field")
            min_val = rule.parameters.get("min")
            max_val = rule.parameters.get("max")
            
            if field in data:
                value = data[field]
                if not (min_val <= value <= max_val):
                    raise ValueError(f"{rule.error_message}: {value} not in range [{min_val}, {max_val}]")
        
        elif rule.rule_type == "required_fields":
            required = rule.parameters.get("fields", [])
            for field in required:
                if field not in data:
                    raise ValueError(f"{rule.error_message}: {field} is required")
    
    def _compute_input_hash(self, input_data: bytes) -> str:
        return hashlib.sha256(input_data).hexdigest()

@dataclass(frozen=True)
class ValidatedInput:
    data: Dict[str, Any]
    hash: str
    serialization_format: SerializationFormat

# === MODULE OUTPUT ===

@dataclass(frozen=True)
class ModuleOutputSchema:
    schema_version: str = "1.0"
    output_types: Dict[str, SchemaType] = field(default_factory=dict)
    metadata_fields: FrozenSet[str] = field(default_factory=frozenset)
    serialization_format: SerializationFormat = SerializationFormat.CANONICAL_JSON
    hash_inclusion_fields: FrozenSet[str] = field(default_factory=frozenset(['result', 'metadata']))
    max_output_size: int = 1024 * 1024
    
    def serialize_output(self, result: Any, metadata: Dict[str, Any]) -> 'SerializedOutput':
        output_data = {
            'result': result,
            'metadata': self._build_metadata(metadata)
        }
        
        serialized = self._serialize_output_data(output_data)
        
        if len(serialized) > self.max_output_size:
            raise ValueError(f"Output size {len(serialized)} exceeds limit {self.max_output_size}")
        
        output_hash = self._compute_output_hash(serialized)
        
        return SerializedOutput(
            data=serialized,
            hash=output_hash,
            serialization_format=self.serialization_format
        )
    
    def _build_metadata(self, custom_metadata: Dict[str, Any]) -> Dict[str, Any]:
        base_metadata = {
            'timestamp': time.time(),
            'schema_version': self.schema_version,
            'serialization_format': self.serialization_format.value
        }
        
        filtered_metadata = {k: v for k, v in custom_metadata.items() if k in self.metadata_fields}
        
        return {**base_metadata, **filtered_metadata}
    
    def _serialize_output_data(self, output_data: Dict[str, Any]) -> bytes:
        if self.serialization_format == SerializationFormat.CANONICAL_JSON:
            return json.dumps(output_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        else:
            raise ValueError(f"Unsupported serialization format: {self.serialization_format}")
    
    def _compute_output_hash(self, serialized: bytes) -> str:
        return hashlib.sha256(serialized).hexdigest()

@dataclass(frozen=True)
class SerializedOutput:
    data: bytes
    hash: str
    serialization_format: SerializationFormat

# === MODULE STATE BOUNDARY ===

@dataclass(frozen=True)
class ModuleStateBoundary:
    schema_version: str = "1.0"
    local_state_schema: Dict[str, SchemaType] = field(default_factory=dict)
    max_local_state_size: int = 10 * 1024 * 1024
    global_state_access: StateAccessPattern = StateAccessPattern.READ_ONLY
    allowed_mutations: FrozenSet[str] = field(default_factory=frozenset)
    forbidden_mutations: FrozenSet[str] = field(default_factory=frozenset(['system', 'core', 'v2']))
    state_isolation_level: IsolationLevel = IsolationLevel.MODULE_LEVEL
    
    def validate_state_mutation(self, mutation: 'StateMutation') -> bool:
        if mutation.field_path in self.forbidden_mutations:
            return False
        
        if self.allowed_mutations and mutation.field_path not in self.allowed_mutations:
            return False
        
        if mutation.estimated_size > self.max_local_state_size:
            return False
        
        return True

@dataclass(frozen=True)
class StateMutation:
    field_path: str
    operation: str
    value: Any
    estimated_size: int

# === MODULE INTERFACE ===

@dataclass(frozen=True)
class ModuleInterface:
    """Complete module interface contract"""
    module_id: ModuleID
    module_version: ModuleVersion
    input_schema: ModuleInputSchema
    output_schema: ModuleOutputSchema
    state_model: ModuleStateBoundary
    determinism_level: DeterminismLevel
    replay_capability: ReplayCapability
    side_effect_profile: SideEffectProfile
    certification_tier: CertificationTier = CertificationTier.TIER_0_SANDBOX
    interface_version: str = "1.0"
    
    def compute_interface_hash(self) -> str:
        """Compute deterministic hash of interface definition"""
        interface_data = {
            'module_id': self.module_id.value,
            'module_version': str(self.module_version),
            'input_schema': {
                'schema_version': self.input_schema.schema_version,
                'input_types': {k: v.type_name for k, v in self.input_schema.input_types.items()},
                'required_fields': list(self.input_schema.required_fields),
                'serialization_format': self.input_schema.serialization_format.value
            },
            'output_schema': {
                'schema_version': self.output_schema.schema_version,
                'output_types': {k: v.type_name for k, v in self.output_schema.output_types.items()},
                'serialization_format': self.output_schema.serialization_format.value
            },
            'state_model': {
                'schema_version': self.state_model.schema_version,
                'global_state_access': self.state_model.global_state_access.value,
                'state_isolation_level': self.state_model.state_isolation_level.value
            },
            'determinism_level': self.determinism_level.value,
            'replay_capability': self.replay_capability.value,
            'side_effect_profile': self.side_effect_profile.value,
            'certification_tier': self.certification_tier.value
        }
        
        return hashlib.sha256(json.dumps(interface_data, sort_keys=True).encode()).hexdigest()
    
    def validate_interface_completeness(self) -> 'InterfaceValidationResult':
        """Validate interface completeness"""
        violations = []
        
        # Check required components
        if not self.input_schema.required_fields:
            violations.append("input_schema.required_fields is required")
        
        if not self.output_schema.output_types:
            violations.append("output_schema.output_types is required")
        
        if not self.state_model.local_state_schema:
            violations.append("state_model.local_state_schema is required")
        
        # Check determinism requirements
        if self.determinism_level == DeterminismLevel.NON_DETERMINISTIC:
            violations.append("NON_DETERMINISTIC not allowed in V2")
        
        if self.replay_capability == ReplayCapability.NO_REPLAY:
            violations.append("NO_REPLAY not allowed in V2")
        
        # Check side effect constraints
        if self.side_effect_profile == SideEffectProfile.EXTERNAL_IO:
            if self.certification_tier != CertificationTier.TIER_3_OFFICIAL:
                violations.append("EXTERNAL_IO only allowed for TIER_3_OFFICIAL")
        
        return InterfaceValidationResult(
            is_valid=len(violations) == 0,
            violations=tuple(violations)
        )

@dataclass(frozen=True)
class InterfaceValidationResult:
    """Result of interface validation"""
    is_valid: bool
    violations: Tuple[str, ...]

# === DEPENDENCY SPECIFICATION ===

@dataclass(frozen=True)
class DependencySpecification:
    """Dependency specification for modules"""
    module_id: str
    version_requirement: str
    hash_requirement: str
    load_order: int
    optional: bool = False
    
    def satisfies_requirement(self, available_version: str, available_hash: str) -> bool:
        """Check if available version satisfies requirement"""
        if not self._check_version_constraint(available_version):
            return False
        
        if available_hash != self.hash_requirement:
            return False
        
        return True
    
    def _check_version_constraint(self, version: str) -> bool:
        """Check semantic version constraint"""
        if self.version_requirement.startswith("^"):
            return self._is_caret_compatible(version, self.version_requirement[1:])
        elif self.version_requirement.startswith("~"):
            return self._is_tilde_compatible(version, self.version_requirement[1:])
        else:
            return version == self.version_requirement
    
    def _is_caret_compatible(self, version: str, base: str) -> bool:
        """Check caret compatibility (^)"""
        base_parts = list(map(int, base.split('.')))
        version_parts = list(map(int, version.split('.')))
        
        if version_parts[0] != base_parts[0]:
            return False
        if version_parts[0] == 0:
            return version_parts[1] == base_parts[1]
        
        return True
    
    def _is_tilde_compatible(self, version: str, base: str) -> bool:
        """Check tilde compatibility (~)"""
        base_parts = list(map(int, base.split('.')))
        version_parts = list(map(int, version.split('.')))
        
        if version_parts[0] != base_parts[0] or version_parts[1] != base_parts[1]:
            return False
        
        return True

# === MODULE DEFINITION ===

@dataclass(frozen=True)
class ModuleDefinition:
    """Complete module definition with interface and implementation"""
    interface: ModuleInterface
    module_bytecode: bytes
    dependency_specifications: List[DependencySpecification]
    module_metadata: Dict[str, Any]
    
    def validate_definition(self) -> 'ModuleValidationResult':
        """Validate complete module definition"""
        violations = []
        
        # Validate interface
        interface_result = self.interface.validate_interface_completeness()
        if not interface_result.is_valid:
            violations.extend(interface_result.violations)
        
        # Validate bytecode hash
        computed_hash = hashlib.sha256(self.module_bytecode).hexdigest()
        # Note: Would need to add module_hash to ModuleInterface for full validation
        
        # Validate dependencies
        for dep in self.dependency_specifications:
            if not self._validate_dependency_specification(dep):
                violations.append(f"Invalid dependency specification: {dep.module_id}")
        
        return ModuleValidationResult(
            is_valid=len(violations) == 0,
            violations=tuple(violations)
        )
    
    def _validate_dependency_specification(self, dep: DependencySpecification) -> bool:
        """Validate individual dependency specification"""
        return bool(dep.module_id and dep.version_requirement and dep.hash_requirement)

@dataclass(frozen=True)
class ModuleValidationResult:
    """Result of module validation"""
    is_valid: bool
    violations: Tuple[str, ...]