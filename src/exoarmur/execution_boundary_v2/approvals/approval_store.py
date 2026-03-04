"""
Approval store interface for execution governance boundary.

Defines the contract for approval decision storage and retrieval.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .approval_models import ApprovalRecord


class ApprovalStore(ABC):
    """Abstract interface for approval decision storage."""
    
    @abstractmethod
    def record(self, record: ApprovalRecord) -> None:
        """Record an approval decision.
        
        Args:
            record: The approval record to store
            
        Raises:
            ValueError: If a decision already exists for the intent_id
        """
        pass
    
    @abstractmethod
    def get(self, intent_id: str) -> Optional[ApprovalRecord]:
        """Get the approval record for an intent.
        
        Args:
            intent_id: The intent identifier to look up
            
        Returns:
            The approval record if found, None otherwise
        """
        pass