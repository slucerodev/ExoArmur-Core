"""
Audit Record Normalization Layer
Purely derivative transformation for unified audit representation
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from spec.contracts.models_v1 import AuditRecordV1

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


@dataclass
class CanonicalAuditEnvelope:
    """Canonical audit envelope for unified representation (DERIVATIVE ONLY)"""
    
    # Core identity fields (preserved from source) - no defaults
    audit_id: str
    tenant_id: str
    cell_id: str
    correlation_id: str
    trace_id: str
    
    # Temporal fields (normalized)
    recorded_at: datetime
    event_timestamp: Optional[datetime]
    
    # Event classification (normalized)
    event_kind: str
    event_category: str
    event_severity: str
    
    # Content (preserved)
    payload_ref: Dict[str, Any]
    
    # Metadata (enhanced) - all fields with defaults at the end
    source_format: str = "unknown"  # "v1", "canonical", etc.
    source_hashes: Optional[Dict[str, Any]] = None  # Original hashes preserved
    canonical_hashes: Optional[Dict[str, Any]] = None  # Normalized hashes
    normalized_at: Optional[datetime] = None
    normalizer_version: str = "1.0.0"
    ordering_key: str = ""
    
    def __post_init__(self):
        """Initialize default values for optional fields"""
        if self.source_hashes is None:
            self.source_hashes = {}
        if self.canonical_hashes is None:
            self.canonical_hashes = {}
        if self.normalized_at is None:
            self.normalized_at = utc_now()


class AuditNormalizer:
    """Purely derivative audit normalization layer - stateless and deterministic"""
    
    def __init__(self):
        logger.info("AuditNormalizer initialized")
        self.normalizer_version = "1.0.0"
    
    def normalize_audit_record(
        self,
        audit_record: Union[AuditRecordV1, CanonicalAuditEnvelope],
        preserve_ordering: bool = True
    ) -> CanonicalAuditEnvelope:
        """
        Normalize audit record to canonical format (DERIVATIVE ONLY)
        
        This is a pure transformation function that:
        - Never modifies stored data
        - Is stateless and deterministic
        - Preserves exact ordering semantics
        - Has no side effects
        
        Args:
            audit_record: Source audit record (V1 or canonical)
            preserve_ordering: Ensure ordering preservation
            
        Returns:
            CanonicalAuditEnvelope with normalized representation
        """
        try:
            if isinstance(audit_record, AuditRecordV1):
                return self._normalize_from_v1(audit_record, preserve_ordering)
            elif isinstance(audit_record, CanonicalAuditEnvelope):
                return self._normalize_from_canonical(audit_record, preserve_ordering)
            else:
                raise ValueError(f"Unsupported audit record type: {type(audit_record)}")
                
        except Exception as e:
            logger.error(f"Audit normalization failed: {e}")
            # CRITICAL: Never fail normalization - return safe fallback
            return self._create_safe_fallback_envelope(audit_record, preserve_ordering)
    
    def _normalize_from_v1(
        self, 
        audit_record: AuditRecordV1, 
        preserve_ordering: bool
    ) -> CanonicalAuditEnvelope:
        """Normalize V1 audit record to canonical envelope"""
        
        # Extract event timestamp from payload if available
        event_timestamp = self._extract_event_timestamp(audit_record.payload_ref)
        
        # Normalize event category and severity
        event_category = self._normalize_event_category(audit_record.event_kind)
        event_severity = self._normalize_event_severity(audit_record.event_kind, audit_record.payload_ref)
        
        # Create canonical hashes
        canonical_hashes = self._compute_canonical_hashes(audit_record)
        
        # Generate ordering key (preserves original ordering)
        ordering_key = self._generate_ordering_key(audit_record) if preserve_ordering else ""
        
        return CanonicalAuditEnvelope(
            # Core identity (preserved)
            audit_id=audit_record.audit_id,
            tenant_id=audit_record.tenant_id,
            cell_id=audit_record.cell_id,
            correlation_id=audit_record.correlation_id,
            trace_id=audit_record.trace_id,
            
            # Temporal fields
            recorded_at=audit_record.recorded_at,
            event_timestamp=event_timestamp,
            
            # Event classification
            event_kind=audit_record.event_kind,
            event_category=event_category,
            event_severity=event_severity,
            
            # Content (preserved)
            payload_ref=audit_record.payload_ref,
            
            # Metadata (defaults will be applied)
            source_format="v1",
            source_hashes=audit_record.hashes,
            canonical_hashes=canonical_hashes,
            
            # Normalization metadata (defaults will be applied)
            normalized_at=utc_now(),
            normalizer_version=self.normalizer_version,
            
            # Ordering
            ordering_key=ordering_key
        )
    
    def _normalize_from_canonical(
        self, 
        audit_record: CanonicalAuditEnvelope, 
        preserve_ordering: bool
    ) -> CanonicalAuditEnvelope:
        """Normalize canonical envelope (passthrough with updated metadata)"""
        
        # For canonical input, this is essentially a passthrough
        # but we update normalization metadata to track the transformation
        
        return CanonicalAuditEnvelope(
            # Core identity (preserved)
            audit_id=audit_record.audit_id,
            tenant_id=audit_record.tenant_id,
            cell_id=audit_record.cell_id,
            correlation_id=audit_record.correlation_id,
            trace_id=audit_record.trace_id,
            
            # Temporal fields (preserved)
            recorded_at=audit_record.recorded_at,
            event_timestamp=audit_record.event_timestamp,
            
            # Event classification (preserved)
            event_kind=audit_record.event_kind,
            event_category=audit_record.event_category,
            event_severity=audit_record.event_severity,
            
            # Content (preserved)
            payload_ref=audit_record.payload_ref,
            
            # Metadata (updated)
            source_format="canonical",
            source_hashes=audit_record.source_hashes,
            canonical_hashes=audit_record.canonical_hashes,
            
            # Normalization metadata (updated)
            normalized_at=utc_now(),
            normalizer_version=self.normalizer_version,
            
            # Ordering (preserved)
            ordering_key=audit_record.ordering_key if preserve_ordering else ""
        )
    
    def _extract_event_timestamp(self, payload_ref: Dict[str, Any]) -> Optional[datetime]:
        """Extract event timestamp from payload if available"""
        # Look for common timestamp fields in payload
        timestamp_fields = ['observed_at', 'timestamp', 'event_time', 'created_at']
        
        for field in timestamp_fields:
            if field in payload_ref:
                try:
                    if isinstance(payload_ref[field], str):
                        return datetime.fromisoformat(payload_ref[field].replace('Z', '+00:00'))
                    elif isinstance(payload_ref[field], datetime):
                        return payload_ref[field]
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _normalize_event_category(self, event_kind: str) -> str:
        """Normalize event category from event kind"""
        # Deterministic category mapping
        category_mapping = {
            'telemetry_ingested': 'ingestion',
            'local_decision_generated': 'decision',
            'belief_generated': 'reasoning',
            'collective_state_computed': 'aggregation',
            'safety_gate_evaluated': 'safety',
            'execution_intent_created': 'execution',
            'action_executed': 'execution',
            'approval_requested': 'approval',
            'approval_granted': 'approval',
            'approval_denied': 'approval',
        }
        
        return category_mapping.get(event_kind, 'other')
    
    def _normalize_event_severity(self, event_kind: str, payload_ref: Dict[str, Any]) -> str:
        """Normalize event severity"""
        # Extract severity from payload if available
        if 'severity' in payload_ref:
            severity = str(payload_ref['severity']).lower()
            if severity in ['low', 'medium', 'high', 'critical']:
                return severity
        
        # Default severity based on event kind
        high_severity_events = {
            'safety_gate_denied',
            'action_executed',
            'approval_denied'
        }
        
        medium_severity_events = {
            'safety_gate_evaluated',
            'execution_intent_created',
            'approval_requested'
        }
        
        if event_kind in high_severity_events:
            return 'high'
        elif event_kind in medium_severity_events:
            return 'medium'
        else:
            return 'low'
    
    def _compute_canonical_hashes(self, audit_record: AuditRecordV1) -> Dict[str, Any]:
        """Compute canonical hashes for the normalized record"""
        import hashlib
        import json
        
        # Create canonical representation for hashing
        canonical_data = {
            'audit_id': audit_record.audit_id,
            'tenant_id': audit_record.tenant_id,
            'cell_id': audit_record.cell_id,
            'correlation_id': audit_record.correlation_id,
            'trace_id': audit_record.trace_id,
            'recorded_at': audit_record.recorded_at.isoformat(),
            'event_kind': audit_record.event_kind,
            'payload_ref': audit_record.payload_ref,
            'idempotency_key': audit_record.idempotency_key
        }
        
        canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))
        
        return {
            'canonical_sha256': hashlib.sha256(canonical_json.encode()).hexdigest(),
            'canonical_length': len(canonical_json)
        }
    
    def _generate_ordering_key(self, audit_record: AuditRecordV1) -> str:
        """Generate deterministic ordering key that preserves original sequence"""
        # Use recorded_at + audit_id for deterministic ordering
        # This preserves the original temporal ordering while being deterministic
        timestamp_str = audit_record.recorded_at.isoformat()
        return f"{timestamp_str}_{audit_record.audit_id}"
    
    def _create_safe_fallback_envelope(
        self, 
        audit_record: Union[AuditRecordV1, CanonicalAuditEnvelope], 
        preserve_ordering: bool
    ) -> CanonicalAuditEnvelope:
        """Create safe fallback envelope when normalization fails"""
        
        # Extract basic fields safely
        if isinstance(audit_record, AuditRecordV1):
            return CanonicalAuditEnvelope(
                audit_id=audit_record.audit_id,
                tenant_id=audit_record.tenant_id,
                cell_id=audit_record.cell_id,
                correlation_id=audit_record.correlation_id,
                trace_id=audit_record.trace_id,
                recorded_at=audit_record.recorded_at,
                event_timestamp=None,
                event_kind=audit_record.event_kind,
                event_category='unknown',
                event_severity='low',
                payload_ref=audit_record.payload_ref,
                source_format='v1',
                source_hashes=audit_record.hashes,
                canonical_hashes={'fallback': True},
                normalized_at=utc_now(),
                normalizer_version=self.normalizer_version,
                ordering_key=self._generate_ordering_key(audit_record) if preserve_ordering else ""
            )
        else:
            # For canonical input, return as-is with fallback flag
            return CanonicalAuditEnvelope(
                audit_id=audit_record.audit_id,
                tenant_id=audit_record.tenant_id,
                cell_id=audit_record.cell_id,
                correlation_id=audit_record.correlation_id,
                trace_id=audit_record.trace_id,
                recorded_at=audit_record.recorded_at,
                event_timestamp=audit_record.event_timestamp,
                event_kind=audit_record.event_kind,
                event_category=audit_record.event_category,
                event_severity=audit_record.event_severity,
                payload_ref=audit_record.payload_ref,
                source_format='canonical',
                source_hashes=audit_record.source_hashes,
                canonical_hashes={'fallback': True},
                normalized_at=utc_now(),
                normalizer_version=self.normalizer_version,
                ordering_key=audit_record.ordering_key if preserve_ordering else ""
            )
    
    def batch_normalize(
        self,
        audit_records: list[Union[AuditRecordV1, CanonicalAuditEnvelope]],
        preserve_ordering: bool = True
    ) -> list[CanonicalAuditEnvelope]:
        """
        Batch normalize audit records (preserves ordering)
        
        Args:
            audit_records: List of audit records to normalize
            preserve_ordering: Ensure ordering preservation
            
        Returns:
            List of normalized canonical envelopes in same order
        """
        normalized_records = []
        
        for record in audit_records:
            normalized = self.normalize_audit_record(record, preserve_ordering)
            normalized_records.append(normalized)
        
        return normalized_records
    
    def is_canonical_format(self, audit_record: Union[AuditRecordV1, CanonicalAuditEnvelope]) -> bool:
        """Check if audit record is already in canonical format"""
        return isinstance(audit_record, CanonicalAuditEnvelope)
