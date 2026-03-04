"""
ExecutorPlugin interface for execution governance boundary.

Interface for executor modules that perform real side effects.
"""

from typing import Any, Dict, Optional, Protocol

from ..models.action_intent import ActionIntent


class ExecutionResult:
    """Result of an execution action."""
    
    def __init__(
        self,
        success: bool,
        output: Dict[str, Any],
        error: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.output = output
        self.error = error
        self.evidence = evidence or {}


class ExecutorPlugin(Protocol):
    """Interface for executor modules."""
    
    def name(self) -> str:
        """Return the executor name."""
        ...
    
    def capabilities(self) -> Dict[str, Any]:
        """Return executor capabilities."""
        ...
    
    def execute(self, intent: ActionIntent) -> ExecutionResult:
        """Execute an action with proper authorization.
        
        Args:
            intent: The action intent to execute
            
        Returns:
            Execution result with output and evidence
        """
        ...
