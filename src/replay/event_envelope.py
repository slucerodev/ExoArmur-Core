"""
Audit Event Envelope for deterministic replay
Provides stable ordering and comprehensive event metadata
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .canonical_utils import canonical_json, stable_hash

logger = logging.getLogger(__name__)


class EventTypePriority(Enum):
    """Event type priority for deterministic ordering"""
    TELEMETRY_INGESTED = 1
    SAFETY_GATE_EVALUATED = 2
    APPROVAL_REQUESTED = 3
    APPROVAL_BOUND_TO_INTENT = 4
    INTENT_DENIED = 5
    INTENT_EXECUTED = 6
    APPROVAL_APPROVED = 7
    APPROVAL_DENIED = 8
    
    @classmethod
    def get_priority(cls, event_type: str) -> int:
        """Get priority for event type, default to 999 for unknown"""
        try:
            return cls[event_type.upper()].value
        except KeyError:
            logger.warning(f"Unknown event type: {event_type}, using default priority")
            return 999


@dataclass(frozen=True)
class AuditEventEnvelope:
    """Canonical audit event envelope for deterministic replay"""
    
    # Core event metadata
    event_id: str
    timestamp: datetime
    event_type: str
    actor: str
    correlation_id: str
    
    # Event payload and integrity
    payload: Dict[str, Any]
    payload_hash: str
    
    # Ordering tiebreakers
    sequence_number: Optional[int] = None
    parent_event_id: Optional[str] = None
    
    # System metadata
    cell_id: str = ""
    tenant_id: str = ""
    trace_id: str = ""
    
    def __post_init__(self):
        """Validate and compute payload hash if not provided"""
        if not self.payload_hash:
            # Compute hash of canonical payload
            canonical_payload = canonical_json(self.payload)
            computed_hash = stable_hash(canonical_payload)
            # Use object.__setattr__ since dataclass is frozen
            object.__setattr__(self, 'payload_hash', computed_hash)
        
        # Validate timestamp is in UTC
        if self.timestamp.tzinfo is None:
            utc_timestamp = self.timestamp.replace(tzinfo=timezone.utc)
            object.__setattr__(self, 'timestamp', utc_timestamp)
    
    @property
    def priority(self) -> int:
        """Get event type priority for ordering"""
        return EventTypePriority.get_priority(self.event_type)
    
    @property
    def ordering_key(self) -> tuple:
        """
        Deterministic ordering key for events
        
        Ordering: (timestamp, priority, event_id, sequence_number)
        Ensures stable ordering across replays
        """
        return (
            self.timestamp,
            self.priority,
            self.event_id,
            self.sequence_number or 0
        )
    
    def verify_payload_integrity(self) -> bool:
        """Verify that payload matches stored hash"""
        try:
            canonical_payload = canonical_json(self.payload)
            computed_hash = stable_hash(canonical_payload)
            return computed_hash == self.payload_hash
        except Exception as e:
            logger.error(f"Payload integrity verification failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat().replace('+00:00', 'Z'),
            'event_type': self.event_type,
            'actor': self.actor,
            'correlation_id': self.correlation_id,
            'payload': self.payload,
            'payload_hash': self.payload_hash,
            'sequence_number': self.sequence_number,
            'parent_event_id': self.parent_event_id,
            'cell_id': self.cell_id,
            'tenant_id': self.tenant_id,
            'trace_id': self.trace_id
        }
    
    @classmethod
    def from_audit_record(cls, audit_record: 'AuditRecordV1', sequence_number: Optional[int] = None) -> 'AuditEventEnvelope':
        """Create envelope from existing audit record"""
        return cls(
            event_id=audit_record.audit_id,
            timestamp=audit_record.recorded_at,
            event_type=audit_record.event_kind,
            actor="system",  # Default actor since AuditRecordV1 doesn't have actor field
            correlation_id=audit_record.correlation_id,
            payload=audit_record.payload_ref,
            payload_hash="",  # Will be computed in __post_init__
            sequence_number=sequence_number,
            cell_id=audit_record.cell_id,
            tenant_id=audit_record.tenant_id,
            trace_id=audit_record.trace_id
        )


class EnvelopeValidationError(Exception):
    """Raised when envelope validation fails"""
    pass
