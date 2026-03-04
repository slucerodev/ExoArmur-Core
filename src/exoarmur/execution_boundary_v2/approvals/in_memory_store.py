"""
In-memory approval store implementation for execution governance boundary.

Provides deterministic, testable approval decision storage.
"""

import logging
from typing import Dict, Optional

from .approval_store import ApprovalStore
from .approval_models import ApprovalRecord

logger = logging.getLogger(__name__)


class InMemoryApprovalStore(ApprovalStore):
    """In-memory implementation of ApprovalStore for testing and development."""
    
    def __init__(self):
        """Initialize the in-memory approval store."""
        self._records: Dict[str, ApprovalRecord] = {}
        logger.info("InMemoryApprovalStore initialized")
    
    def record(self, record: ApprovalRecord) -> None:
        """Record an approval decision.
        
        Args:
            record: The approval record to store
            
        Raises:
            ValueError: If a decision already exists for the intent_id
        """
        if record.intent_id in self._records:
            existing = self._records[record.intent_id]
            raise ValueError(
                f"Approval decision already exists for intent {record.intent_id}. "
                f"Existing: {existing.decision.value} by {existing.decided_by} at {existing.decided_at}. "
                f"Attempted: {record.decision.value} by {record.decided_by} at {record.decided_at}."
            )
        
        self._records[record.intent_id] = record
        logger.info(f"Recorded approval decision: {record.decision.value} for intent {record.intent_id} by {record.decided_by}")
    
    def get(self, intent_id: str) -> Optional[ApprovalRecord]:
        """Get the approval record for an intent.
        
        Args:
            intent_id: The intent identifier to look up
            
        Returns:
            The approval record if found, None otherwise
        """
        record = self._records.get(intent_id)
        if record:
            logger.debug(f"Retrieved approval record for intent {intent_id}: {record.decision.value}")
        else:
            logger.debug(f"No approval record found for intent {intent_id}")
        return record
    
    def clear(self) -> None:
        """Clear all approval records (for testing)."""
        self._records.clear()
        logger.info("InMemoryApprovalStore cleared")
    
    def list_all(self) -> Dict[str, ApprovalRecord]:
        """Get all stored approval records (for testing).
        
        Returns:
            Dictionary mapping intent_id to ApprovalRecord
        """
        return self._records.copy()