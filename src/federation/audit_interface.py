"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Audit Interface
Boundary-safe adapter for V1 audit system integration
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class AuditInterface(ABC):
    """Abstract interface for audit logging to maintain V1/V2 boundary"""
    
    @abstractmethod
    def log_event(self, event_type: str, correlation_id: str, data: Dict[str, Any], recorded_at: datetime) -> bool:
        """
        Log an audit event
        
        Args:
            event_type: Type of audit event
            correlation_id: Correlation ID for event tracking
            data: Event data payload
            recorded_at: When the event was recorded
            
        Returns:
            True if event was logged successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_events(self, event_type_prefix: str, correlation_id: str, limit: int) -> Optional[list]:
        """
        Retrieve audit events
        
        Args:
            event_type_prefix: Prefix for event type filtering
            correlation_id: Correlation ID for filtering
            limit: Maximum number of events to retrieve
            
        Returns:
            List of events or None if not available
        """
        pass


class V1AuditAdapter(AuditInterface):
    """Adapter for V1 audit system that implements the boundary interface"""
    
    def __init__(self, v1_audit_logger):
        """
        Initialize adapter with V1 audit logger
        
        Args:
            v1_audit_logger: V1 audit logger instance
        """
        self.v1_audit_logger = v1_audit_logger
    
    def log_event(self, event_type: str, correlation_id: str, data: Dict[str, Any], recorded_at: datetime) -> bool:
        """Log event using V1 audit logger"""
        try:
            if self.v1_audit_logger and hasattr(self.v1_audit_logger, 'log_event'):
                self.v1_audit_logger.log_event(
                    event_type=event_type,
                    correlation_id=correlation_id,
                    data=data,
                    recorded_at=recorded_at
                )
                return True
            return False
        except Exception:
            return False
    
    def get_events(self, event_type_prefix: str, correlation_id: str, limit: int) -> Optional[list]:
        """Get events using V1 audit logger"""
        try:
            if self.v1_audit_logger and hasattr(self.v1_audit_logger, 'get_events'):
                return self.v1_audit_logger.get_events(
                    event_type_prefix=event_type_prefix,
                    correlation_id=correlation_id,
                    limit=limit
                )
            return None
        except Exception:
            return None


class NoOpAuditInterface(AuditInterface):
    """No-op implementation for testing/disabled scenarios"""
    
    def log_event(self, event_type: str, correlation_id: str, data: Dict[str, Any], recorded_at: datetime) -> bool:
        """No-op logging"""
        return False
    
    def get_events(self, event_type_prefix: str, correlation_id: str, limit: int) -> Optional[list]:
        """No-op event retrieval"""
        return None
