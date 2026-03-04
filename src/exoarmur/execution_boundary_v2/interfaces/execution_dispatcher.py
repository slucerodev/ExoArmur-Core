"""
ExecutionDispatcher interface for execution governance boundary.

Interface for execution dispatch coordination and tracking.
"""

from typing import Protocol

from ..models.action_intent import ActionIntent
from ..models.execution_dispatch import ExecutionDispatch


class ExecutionDispatcher(Protocol):
    """Interface for execution dispatch coordination."""
    
    def submit_intent(self, intent: ActionIntent) -> ExecutionDispatch:
        """Submit an intent for execution.
        
        Args:
            intent: The action intent to submit
            
        Returns:
            Execution dispatch tracking record
        """
        ...
    
    def get_status(self, intent_id: str) -> ExecutionDispatch:
        """Get execution status for an intent.
        
        Args:
            intent_id: Intent identifier
            
        Returns:
            Current execution dispatch status
        """
        ...
