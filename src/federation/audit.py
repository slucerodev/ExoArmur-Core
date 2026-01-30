"""
Audit Service

Provides audit event emission for federation operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.federation.audit_interface import AuditInterface, NoOpAuditInterface

logger = logging.getLogger(__name__)


class AuditEventType:
    """Audit event types for federation operations"""
    # Handshake events
    HANDSHAKE_INITIATED = "handshake_initiated"
    HANDSHAKE_COMPLETED = "handshake_completed"
    HANDSHAKE_FAILED = "handshake_failed"
    HANDSHAKE_TIMEOUT = "handshake_timeout"
    
    # Observation events
    OBSERVATION_INGESTED = "observation_ingested"
    OBSERVATION_REJECTED = "observation_rejected"
    
    # Belief events
    BELIEF_CREATED = "belief_created"
    BELIEF_CONFLICT_DETECTED = "belief_conflict_detected"
    
    # Arbitration events
    ARBITRATION_CREATED = "arbitration_created"
    ARBITRATION_RESOLUTION_PROPOSED = "arbitration_resolution_proposed"
    ARBITRATION_RESOLVED = "arbitration_resolved"
    ARBITRATION_REJECTED = "arbitration_rejected"
    
    # Conflict events
    CONFLICT_DETECTED = "conflict_detected"


class AuditEventEnvelope:
    """Envelope for audit events"""
    
    def __init__(
        self,
        event_type: str,
        timestamp_utc: datetime,
        correlation_id: Optional[str] = None,
        source_federate_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ):
        self.event_type = event_type
        self.timestamp_utc = timestamp_utc
        self.correlation_id = correlation_id
        self.source_federate_id = source_federate_id
        self.event_data = event_data or {}


class AuditService:
    """Service for emitting audit events"""
    
    def __init__(self, audit_interface: Optional[AuditInterface] = None):
        self.audit_interface = audit_interface or NoOpAuditInterface()
    
    def emit_audit_event(self, event: AuditEventEnvelope) -> bool:
        """
        Emit an audit event
        
        Args:
            event: Audit event envelope
            
        Returns:
            True if emitted successfully, False otherwise
        """
        try:
            return self.audit_interface.log_event(
                event_type=event.event_type,
                correlation_id=event.correlation_id or "no_correlation",
                data=event.event_data,
                recorded_at=event.timestamp_utc
            )
        except Exception as e:
            logger.error(f"Failed to emit audit event {event.event_type}: {e}")
            return False
