"""
ExoArmur V2 Execution Boundary
Deterministic module governance and lifecycle management
"""

from .core import *
from .lifecycle import *
from .determinism import *
from .interface import *
from .certification import *
from .trust import *
from .entry import *

# V2 Execution Boundary is always enabled when this module can be imported
EXECUTION_BOUNDARY_V2_ENABLED = True

__version__ = "2.0.0"
__all__ = [
    # Core types
    "ModuleID",
    "ModuleVersion", 
    "ExecutionID",
    "DeterministicSeed",
    "StateEnum",
    "FailureCode",
    "ModuleExecutionContext",
    "DeterministicTransition",
    "ModuleInput",
    "ModuleOutput",
    "AuditEvent",
    
    # Audit logging
    "AuditLogEntry",
    "AuditLog",
    "DeterministicAuditLogger",
    
    # Lifecycle
    "LifecycleEvent",
    "TransitionContext", 
    "TransitionResult",
    "DeterministicTransitionFunction",
    "StateInvariant",
    "StateValidator",
    
    # Determinism
    "ConcurrencyModel",
    "SeedSource",
    "SeedDerivationMethod", 
    "RandomnessFunction",
    "RandomnessProtocol",
    "LogicalTime",
    "LogicalClock",
    "DeterministicRNG",
    "IOEvent",
    "PreCapturedIOContext",
    "DeterministicIOHandler",
    "StateTransition",
    "PureStateMachine",
    "RandomnessController",
    "TimeDeterminismEnforcer",
    "LogicalTimeProvider",
    "TimeValidationResult",
    
    # Interface
    "CertificationTier",
    "SerializationFormat",
    "DeterminismLevel",
    "ReplayCapability",
    "SideEffectProfile",
    "StateAccessPattern",
    "IsolationLevel",
    "SchemaType",
    "ValidationRule",
    "ModuleInputSchema",
    "ValidatedInput",
    "ModuleOutputSchema",
    "SerializedOutput",
    "ModuleStateBoundary",
    "StateMutation",
    "ModuleInterface",
    "InterfaceValidationResult",
    "DependencySpecification",
    "ModuleDefinition",
    "ModuleValidationResult",
    
    # Certification
    "CertificationContext",
    "CertificationResult",
    "CertificationFunction",
    "StaticValidationResult",
    "ExecutionTestingResult",
    "DeterminismComplianceResult",
    "InvariantVerificationResult",
    "AdversarialTestingResult",
    "SchemaConformanceResult",
    "InterfaceCompletenessResult",
    "ForbiddenPatternsResult",
    "DependencyValidationResult",
    "ReplayTestResult",
    "LifecycleComplianceResult",
    "InputOutputConsistencyResult",
    "ConcurrencyComplianceResult",
    "RandomnessComplianceResult",
    "TimeModelComplianceResult",
    "IOComplianceResult",
    "ModuleInvariantsResult",
    "SystemInvariantsResult",
    "FailureDeterminismResult",
    "MalformedInputTestResult",
    "CorruptedContextTestResult",
    "ReplayDivergenceTestResult",
    "DependencyManipulationTestResult",
    
    # Trust enforcement
    "TrustTierDefinition",
    "RuntimeEnforcementProfile",
    "ResourceConstraints",
    "IOConstraints",
    "ValidationProfile",
    "AuditRequirements",
    "FailureHandlingProfile",
    "TIER_0_DEFINITION",
    "TIER_1_DEFINITION", 
    "TIER_2_DEFINITION",
    "TIER_3_DEFINITION",
    "TRUST_TIER_REGISTRY",
    "EnforcementContext",
    "EnforcementResult",
    "ExecutionResult",
    "ValidationResult",
    "RuntimeEnforcer",
    "ValidationEngine",
    "IOController",
    "ResourceMonitor",
    "FailureHandler",
    "FailureHandlingResult",
    "NoFileSystemIO",
    "ReadOnlyFileSystemIO",
    "SandboxedFileSystemIO",
    "IORequest",
    "IOResult",
    "CertificationTrustMapper",
    
    # Entry Gate - SINGLE MANDATORY ENTRY POINT
    "ExecutionRequest",
    "V2EntryGate",
    "get_v2_entry_gate",
    "execute_module",
    
    # Status constants
    "EXECUTION_BOUNDARY_V2_ENABLED"
]