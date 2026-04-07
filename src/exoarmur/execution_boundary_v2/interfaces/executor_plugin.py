"""
ExecutorPlugin interface for execution governance boundary.

Interface for executor modules that perform real side effects.
Enhanced with capability enforcement and sandboxing requirements.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple
from enum import Enum

from ..models.action_intent import ActionIntent


class ValidationResult(Enum):
    """Target validation result enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"
    VIOLATES_CONSTRAINTS = "violates_constraints"


class ExecutorResult:
    """Result of an execution action with deterministic behavior."""
    
    def __init__(
        self,
        success: bool,
        output: Dict[str, Any],
        error: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ):
        self.success = success
        self.output = output
        self.error = error
        self.evidence = evidence or {}
        self.execution_id = execution_id


class ExecutorCapabilities:
    """Standardized executor capability declaration with enforcement."""
    
    def __init__(
        self,
        executor_name: str,
        version: str,
        capabilities: List[str],
        constraints: Dict[str, Any],
        supported_targets: Optional[List[str]] = None,
        required_parameters: Optional[List[str]] = None
    ):
        self.executor_name = executor_name
        self.version = version
        self.capabilities = capabilities
        self.constraints = constraints
        self.supported_targets = supported_targets or []
        self.required_parameters = required_parameters or []


class TargetValidationResult:
    """Result of target validation with evidence."""
    
    def __init__(
        self,
        result: ValidationResult,
        evidence: Dict[str, Any],
        validation_id: Optional[str] = None
    ):
        self.result = result
        self.evidence = evidence
        self.validation_id = validation_id


class ExecutorPlugin(Protocol):
    """Interface for executor modules with sandboxing and capability enforcement.
    
    All ExecutorPlugin implementations MUST:
    - Expose standardized capabilities() schema
    - Implement validate_target() for pre-execution validation
    - Implement deterministic execute() behavior
    - Cannot bypass governance or access internal pipeline state
    """
    
    def name(self) -> str:
        """Return the executor name."""
        ...
    
    def capabilities(self) -> Dict[str, Any]:
        """Return executor capabilities with enforcement metadata."""
        ...
    
    def validate_target(self, intent: ActionIntent) -> TargetValidationResult:
        """Validate target against executor capabilities and constraints.
        
        Args:
            intent: The action intent to validate
            
        Returns:
            TargetValidationResult with validation evidence
        """
        ...
    
    def execute(self, intent: ActionIntent, policy_decision: Any, governance_context: Dict[str, Any]) -> ExecutorResult:
        """Execute an action with proper authorization and deterministic behavior.
        
        Args:
            intent: The action intent to execute
            policy_decision: The policy decision authorizing execution
            governance_context: Additional governance context for execution
            
        Returns:
            Execution result with output and evidence
        """
        ...
    
    def supports_capability(self, capability: str) -> bool:
        """Check if executor supports a specific capability."""
        ...
