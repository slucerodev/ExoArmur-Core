"""
ExecutorPlugin interface for execution governance boundary.

Interface for executor modules that perform real side effects.
"""

from typing import Any, Dict, List, Optional, Protocol

from ..models.action_intent import ActionIntent


class ExecutorResult:
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


class ExecutorCapabilities:
    """Standardized executor capability declaration."""
    
    def __init__(
        self,
        executor_name: str,
        version: str,
        capabilities: List[str],
        constraints: Dict[str, Any]
    ):
        self.executor_name = executor_name
        self.version = version
        self.capabilities = capabilities
        self.constraints = constraints


class ExecutorPlugin(Protocol):
    """Interface for executor modules.
    
    All ExecutorPlugin implementations MUST expose standardized capabilities() schema:
    - executor_name: str
    - version: str  
    - capabilities: list[str] (canonical capability strings)
    - constraints: dict[str, Any] (security/operational constraints)
    """
    
    def name(self) -> str:
        """Return the executor name."""
        ...
    
    def capabilities(self) -> Dict[str, Any]:
        """Return executor capabilities."""
        ...
    
    def execute(self, intent: ActionIntent) -> ExecutorResult:
        """Execute an action with proper authorization.
        
        Args:
            intent: The action intent to execute
            
        Returns:
            Execution result with output and evidence
        """
        ...
