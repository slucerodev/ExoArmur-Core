"""
Arbitration Store

Stores and retrieves arbitration objects with deterministic ordering.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from spec.contracts.models_v1 import ArbitrationV1, ArbitrationStatus
from src.federation.clock import Clock

logger = logging.getLogger(__name__)


class ArbitrationStore:
    """Store for arbitration objects with deterministic ordering"""
    
    def __init__(self, clock: Clock):
        self.clock = clock
        self._arbitrations: Dict[str, ArbitrationV1] = {}
        self._conflict_key_index: Dict[str, List[str]] = {}
        self._status_index: Dict[ArbitrationStatus, List[str]] = {}
        self._correlation_index: Dict[str, List[str]] = {}
    
    def store_arbitration(self, arbitration: ArbitrationV1) -> bool:
        """
        Store an arbitration object
        
        Args:
            arbitration: Arbitration object to store
            
        Returns:
            True if stored successfully, False if duplicate
        """
        if arbitration.arbitration_id in self._arbitrations:
            logger.warning(f"Arbitration {arbitration.arbitration_id} already exists")
            return False
        
        # Store arbitration
        self._arbitrations[arbitration.arbitration_id] = arbitration
        
        # Update indexes
        self._update_indexes(arbitration)
        
        logger.info(f"Stored arbitration {arbitration.arbitration_id}")
        return True
    
    def get_arbitration(self, arbitration_id: str) -> Optional[ArbitrationV1]:
        """
        Get arbitration by ID
        
        Args:
            arbitration_id: Arbitration identifier
            
        Returns:
            Arbitration object or None if not found
        """
        return self._arbitrations.get(arbitration_id)
    
    def list_arbitrations(
        self,
        conflict_key: Optional[str] = None,
        status: Optional[ArbitrationStatus] = None,
        correlation_id: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[ArbitrationV1]:
        """
        List arbitrations with optional filters
        
        Args:
            conflict_key: Filter by conflict key
            status: Filter by status
            correlation_id: Filter by correlation ID
            limit: Maximum number to return
            since: Filter by creation timestamp (inclusive)
            
        Returns:
            List of arbitrations in creation order
        """
        candidates = list(self._arbitrations.values())
        
        # Apply filters
        if conflict_key:
            candidates = [a for a in candidates if a.conflict_key == conflict_key]
        
        if status:
            candidates = [a for a in candidates if a.status == status]
        
        if correlation_id:
            candidates = [a for a in candidates if a.correlation_id == correlation_id]
        
        if since:
            candidates = [a for a in candidates if a.created_at_utc >= since]
        
        # Sort by creation time (deterministic)
        candidates.sort(key=lambda x: x.created_at_utc)
        
        # Apply limit
        if limit:
            candidates = candidates[:limit]
        
        return candidates
    
    def get_arbitrations_by_conflict_key(self, conflict_key: str) -> List[ArbitrationV1]:
        """
        Get all arbitrations for a conflict key
        
        Args:
            conflict_key: Conflict key
            
        Returns:
            List of arbitrations for the conflict key
        """
        arbitration_ids = self._conflict_key_index.get(conflict_key, [])
        return [self._arbitrations[arb_id] for arb_id in arbitration_ids]
    
    def get_open_arbitrations(self) -> List[ArbitrationV1]:
        """Get all open arbitrations"""
        return self.list_arbitrations(status=ArbitrationStatus.OPEN)
    
    def update_arbitration(self, arbitration: ArbitrationV1) -> bool:
        """
        Update an existing arbitration
        
        Args:
            arbitration: Updated arbitration object
            
        Returns:
            True if updated successfully, False if not found
        """
        if arbitration.arbitration_id not in self._arbitrations:
            logger.warning(f"Arbitration {arbitration.arbitration_id} not found for update")
            return False
        
        # Get old arbitration for index cleanup
        old_arbitration = self._arbitrations[arbitration.arbitration_id]
        
        # Update arbitration
        self._arbitrations[arbitration.arbitration_id] = arbitration
        
        # Update indexes (remove old, add new)
        self._remove_from_indexes(old_arbitration)
        self._update_indexes(arbitration)
        
        logger.info(f"Updated arbitration {arbitration.arbitration_id}")
        return True
    
    def get_statistics(self) -> Dict[str, any]:
        """Get arbitration store statistics"""
        total_arbitrations = len(self._arbitrations)
        
        status_counts = {}
        for status in ArbitrationStatus:
            status_counts[status.value] = len(self._status_index.get(status, []))
        
        # Get oldest and newest arbitration
        arbitrations = list(self._arbitrations.values())
        if arbitrations:
            arbitrations.sort(key=lambda x: x.created_at_utc)
            oldest = arbitrations[0].created_at_utc
            newest = arbitrations[-1].created_at_utc
        else:
            oldest = None
            newest = None
        
        return {
            "total_arbitrations": total_arbitrations,
            "status_counts": status_counts,
            "oldest_arbitration": oldest.isoformat().replace('+00:00', 'Z') if oldest else None,
            "newest_arbitration": newest.isoformat().replace('+00:00', 'Z') if newest else None
        }
    
    def cleanup_expired_arbitrations(self, max_age_days: int = 30) -> int:
        """
        Clean up expired arbitrations
        
        Args:
            max_age_days: Maximum age in days before cleanup
            
        Returns:
            Number of arbitrations cleaned up
        """
        cutoff_time = self.clock.now() - timedelta(days=max_age_days)
        
        expired_ids = []
        for arb_id, arbitration in self._arbitrations.items():
            if arbitration.created_at_utc < cutoff_time:
                expired_ids.append(arb_id)
        
        # Remove expired arbitrations
        for arb_id in expired_ids:
            arbitration = self._arbitrations[arb_id]
            self._remove_from_indexes(arbitration)
            del self._arbitrations[arb_id]
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired arbitrations")
        
        return len(expired_ids)
    
    def _update_indexes(self, arbitration: ArbitrationV1):
        """Update search indexes for an arbitration"""
        # Conflict key index
        if arbitration.conflict_key not in self._conflict_key_index:
            self._conflict_key_index[arbitration.conflict_key] = []
        if arbitration.arbitration_id not in self._conflict_key_index[arbitration.conflict_key]:
            self._conflict_key_index[arbitration.conflict_key].append(arbitration.arbitration_id)
        
        # Status index
        if arbitration.status not in self._status_index:
            self._status_index[arbitration.status] = []
        if arbitration.arbitration_id not in self._status_index[arbitration.status]:
            self._status_index[arbitration.status].append(arbitration.arbitration_id)
        
        # Correlation ID index
        if arbitration.correlation_id:
            if arbitration.correlation_id not in self._correlation_index:
                self._correlation_index[arbitration.correlation_id] = []
            if arbitration.arbitration_id not in self._correlation_index[arbitration.correlation_id]:
                self._correlation_index[arbitration.correlation_id].append(arbitration.arbitration_id)
    
    def _remove_from_indexes(self, arbitration: ArbitrationV1):
        """Remove arbitration from search indexes"""
        # Remove from conflict key index
        if arbitration.conflict_key in self._conflict_key_index:
            if arbitration.arbitration_id in self._conflict_key_index[arbitration.conflict_key]:
                self._conflict_key_index[arbitration.conflict_key].remove(arbitration.arbitration_id)
            
            # Clean up empty entries
            if not self._conflict_key_index[arbitration.conflict_key]:
                del self._conflict_key_index[arbitration.conflict_key]
        
        # Remove from status index
        if arbitration.status in self._status_index:
            if arbitration.arbitration_id in self._status_index[arbitration.status]:
                self._status_index[arbitration.status].remove(arbitration.arbitration_id)
            
            # Clean up empty entries
            if not self._status_index[arbitration.status]:
                del self._status_index[arbitration.status]
        
        # Remove from correlation index
        if arbitration.correlation_id and arbitration.correlation_id in self._correlation_index:
            if arbitration.arbitration_id in self._correlation_index[arbitration.correlation_id]:
                self._correlation_index[arbitration.correlation_id].remove(arbitration.arbitration_id)
            
            # Clean up empty entries
            if not self._correlation_index[arbitration.correlation_id]:
                del self._correlation_index[arbitration.correlation_id]
