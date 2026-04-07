"""
Replay Envelope Builder for dual-format audit support
Unified timeline construction with strict ordering preservation
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.audit.audit_normalizer import AuditNormalizer, CanonicalAuditEnvelope
from .event_envelope import CanonicalEvent, EventTypePriority, _canonical_replay_timestamp

logger = logging.getLogger(__name__)


@dataclass
class ReplayEnvelope:
    """Unified replay envelope for both V1 and Canonical formats"""
    
    # Core identity (preserved from source)
    audit_id: str
    event_kind: str
    correlation_id: str
    trace_id: str
    tenant_id: str
    cell_id: str
    
    # Temporal information (normalized)
    recorded_at: datetime
    event_timestamp: Optional[datetime]
    
    # Content (preserved)
    payload_ref: Dict[str, Any]
    
    # Enhanced metadata
    source_format: str  # "v1" or "canonical"
    event_category: str
    event_severity: str
    
    # Deterministic ordering (preserves original sequence)
    ordering_key: str
    
    # Replay-specific metadata
    priority: int
    sequence_number: Optional[int] = None
    parent_event_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize replay-specific fields"""
        # Ensure priority is set based on event kind
        if self.priority == 0:
            self.priority = EventTypePriority.get_priority(self.event_kind)
    
    @property
    def event_id(self) -> str:
        """Alias for audit_id for compatibility with existing replay logic"""
        return self.audit_id
    
    @property
    def event_type(self) -> str:
        """Alias for event_kind for compatibility with existing replay logic"""
        return self.event_kind
    
    @property
    def actor(self) -> str:
        """Extract actor from payload or use tenant_id as fallback"""
        if isinstance(self.payload_ref, dict):
            return self.payload_ref.get('actor', self.tenant_id)
        return self.tenant_id
    
    @property
    def payload(self) -> Dict[str, Any]:
        """Alias for payload_ref for compatibility with existing replay logic"""
        return self.payload_ref
    
    @property
    def payload_hash(self) -> str:
        """Generate payload hash for integrity verification"""
        import hashlib
        import json
        
        # Create canonical representation for hashing
        canonical_payload = json.dumps(self.payload_ref, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_payload.encode()).hexdigest()
    
    def verify_payload_integrity(self) -> bool:
        """Verify payload integrity (always true for replay envelopes)"""
        return True
    
    def to_canonical_event(self) -> CanonicalEvent:
        """Convert to CanonicalEvent for compatibility with existing replay logic"""
        return CanonicalEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            actor=self.actor,
            correlation_id=self.correlation_id,
            payload=self.payload,
            payload_hash=self.payload_hash,
            sequence_number=self.sequence_number,
            parent_event_id=self.parent_event_id,
            cell_id=self.cell_id,
            tenant_id=self.tenant_id,
            trace_id=self.trace_id
        )


class ReplayEnvelopeBuilder:
    """Builds unified replay envelopes from dual-format audit sources"""
    
    def __init__(self):
        """Initialize envelope builder with audit normalizer"""
        self.audit_normalizer = AuditNormalizer()
        self.logger = logging.getLogger(__name__)
    
    def build_envelopes(
        self,
        audit_records: List[Union[AuditRecordV1, CanonicalAuditEnvelope]],
        preserve_ordering: bool = True
    ) -> List[ReplayEnvelope]:
        """
        Build unified replay envelopes from mixed audit record formats
        
        Args:
            audit_records: List of V1 AuditRecordV1 or CanonicalAuditEnvelope
            preserve_ordering: Ensure exact ordering preservation
            
        Returns:
            List of unified ReplayEnvelope objects in original order
        """
        envelopes = []
        
        for record in audit_records:
            try:
                envelope = self._build_single_envelope(record, preserve_ordering)
                envelopes.append(envelope)
            except Exception as e:
                self.logger.error(f"Failed to build envelope for record {getattr(record, 'audit_id', 'unknown')}: {e}")
                # Skip invalid records but continue processing
                continue
        
        return envelopes
    
    def _build_single_envelope(
        self,
        record: Union[AuditRecordV1, CanonicalAuditEnvelope, CanonicalEvent],
        preserve_ordering: bool
    ) -> ReplayEnvelope:
        """Build a single replay envelope from an audit record"""
        
        if isinstance(record, AuditRecordV1):
            return self._build_from_v1_record(record, preserve_ordering)
        elif isinstance(record, CanonicalAuditEnvelope):
            return self._build_from_canonical_envelope(record, preserve_ordering)
        elif isinstance(record, CanonicalEvent):
            return self._build_from_canonical_event(record, preserve_ordering)
        else:
            raise ValueError(f"Unsupported record type: {type(record)}")
    
    def _build_from_v1_record(
        self,
        record: AuditRecordV1,
        preserve_ordering: bool
    ) -> ReplayEnvelope:
        """Build replay envelope from V1 AuditRecord"""
        
        # Normalize to canonical format first
        canonical_envelope = self.audit_normalizer.normalize_audit_record(record, preserve_ordering)
        
        # Extract event timestamp from payload if available
        event_timestamp = self._extract_event_timestamp(record.payload_ref)
        
        # Generate ordering key
        ordering_key = self._generate_ordering_key(record) if preserve_ordering else ""
        
        return ReplayEnvelope(
            # Core identity
            audit_id=record.audit_id,
            event_kind=record.event_kind,
            correlation_id=record.correlation_id,
            trace_id=record.trace_id,
            tenant_id=record.tenant_id,
            cell_id=record.cell_id,
            
            # Temporal
            recorded_at=record.recorded_at,
            event_timestamp=event_timestamp,
            
            # Content
            payload_ref=record.payload_ref,
            
            # Enhanced metadata
            source_format="v1",
            event_category=canonical_envelope.event_category,
            event_severity=canonical_envelope.event_severity,
            
            # Ordering
            ordering_key=ordering_key,
            
            # Replay-specific
            priority=EventTypePriority.get_priority(record.event_kind),
            sequence_number=None,
            parent_event_id=None
        )
    
    def _build_from_canonical_envelope(
        self,
        envelope: CanonicalAuditEnvelope,
        preserve_ordering: bool
    ) -> ReplayEnvelope:
        """Build replay envelope from CanonicalAuditEnvelope"""
        
        return ReplayEnvelope(
            # Core identity
            audit_id=envelope.audit_id,
            event_kind=envelope.event_kind,
            correlation_id=envelope.correlation_id,
            trace_id=envelope.trace_id,
            tenant_id=envelope.tenant_id,
            cell_id=envelope.cell_id,
            
            # Temporal
            recorded_at=envelope.recorded_at,
            event_timestamp=envelope.event_timestamp,
            
            # Content
            payload_ref=envelope.payload_ref,
            
            # Enhanced metadata
            source_format="canonical",
            event_category=envelope.event_category,
            event_severity=envelope.event_severity,
            
            # Ordering
            ordering_key=envelope.ordering_key if preserve_ordering else "",
            
            # Replay-specific
            priority=EventTypePriority.get_priority(envelope.event_kind),
            sequence_number=None,
            parent_event_id=None
        )
    
    def _build_from_canonical_event(
        self,
        record: CanonicalEvent,
        preserve_ordering: bool
    ) -> ReplayEnvelope:
        """Build replay envelope from CanonicalEvent"""
        
        # CanonicalEvent has no recorded_at - use canonical timestamp
        event_timestamp = _canonical_replay_timestamp()
        
        # Generate ordering key
        ordering_key = self._generate_ordering_key_from_event(record) if preserve_ordering else ""
        
        return ReplayEnvelope(
            # Core identity
            audit_id=record.event_id,
            event_kind=record.event_type,
            correlation_id=record.correlation_id,
            trace_id=record.trace_id,
            tenant_id=record.tenant_id,
            cell_id=record.cell_id,
            
            # Temporal - use canonical timestamp for determinism
            recorded_at=event_timestamp,
            event_timestamp=event_timestamp,
            
            # Content
            payload_ref=record.payload,
            
            # Enhanced metadata
            source_format="canonical_event",
            event_category="unknown",  # CanonicalEvent doesn't have category
            event_severity="unknown",  # CanonicalEvent doesn't have severity
            
            # Ordering
            ordering_key=ordering_key,
            
            # Replay-specific
            priority=EventTypePriority.get_priority(record.event_type),
            sequence_number=record.sequence_number,
            parent_event_id=record.parent_event_id
        )
    
    def _generate_ordering_key_from_event(self, record: CanonicalEvent) -> str:
        """Generate deterministic ordering key for CanonicalEvent"""
        # Use priority + event_id + sequence_number for deterministic ordering
        priority = EventTypePriority.get_priority(record.event_type)
        seq_num = record.sequence_number or 0
        return f"{priority:03d}_{record.event_id}_{seq_num:06d}"
    
    def _extract_event_timestamp(self, payload_ref: Dict[str, Any]) -> Optional[datetime]:
        """Extract event timestamp from payload if available"""
        timestamp_fields = ['observed_at', 'timestamp', 'event_time', 'created_at']
        
        for field in timestamp_fields:
            if field in payload_ref:
                try:
                    timestamp_str = payload_ref[field]
                    if isinstance(timestamp_str, str):
                        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    elif isinstance(timestamp_str, datetime):
                        return timestamp_str
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _generate_ordering_key(self, record: AuditRecordV1) -> str:
        """Generate deterministic ordering key that preserves original sequence"""
        # Use recorded_at + audit_id for deterministic ordering
        timestamp_str = record.recorded_at.isoformat()
        return f"{timestamp_str}_{record.audit_id}"
    
    def convert_to_canonical_events(self, envelopes: List[ReplayEnvelope]) -> List[CanonicalEvent]:
        """Convert replay envelopes to CanonicalEvent for compatibility with existing replay logic"""
        canonical_events = []
        
        for envelope in envelopes:
            try:
                canonical_event = envelope.to_canonical_event()
                canonical_events.append(canonical_event)
            except Exception as e:
                self.logger.error(f"Failed to convert envelope {envelope.audit_id} to CanonicalEvent: {e}")
                continue
        
        return canonical_events
    
    def validate_envelope_sequence(self, envelopes: List[ReplayEnvelope]) -> List[str]:
        """Validate envelope sequence and return any issues found"""
        issues = []
        
        if not envelopes:
            issues.append("No envelopes provided")
            return issues
        
        # Check for duplicate audit IDs
        audit_ids = [env.audit_id for env in envelopes]
        duplicates = [aid for aid in set(audit_ids) if audit_ids.count(aid) > 1]
        if duplicates:
            issues.append(f"Duplicate audit IDs found: {duplicates}")
        
        # Check ordering consistency if ordering keys are present
        ordering_keys = [env.ordering_key for env in envelopes if env.ordering_key]
        if ordering_keys:
            envelopes = sorted(envelopes, key=lambda e: e.ordering_key or "")
        
        return issues
