"""
Audit logging with JetStream publishing
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
from models_v1 import AuditRecordV1
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from clock import utc_now

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger with JetStream publishing"""
    
    def __init__(self, nats_client=None):
        self.nats_client = nats_client
        self.audit_records: Dict[str, List[AuditRecordV1]] = {}  # In-memory storage for testing
        logger.info("AuditLogger initialized")
    
    def emit_audit_record(
        self,
        event_kind: str,
        payload_ref: Dict[str, Any],
        correlation_id: str,
        trace_id: str,
        tenant_id: str,
        cell_id: str,
        idempotency_key: str
    ) -> AuditRecordV1:
        """Emit audit record for an event"""
        logger.info(f"Emitting audit record for {event_kind}")
        
        # Create audit record
        audit_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",  # TODO: generate ULID
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=idempotency_key,
            recorded_at=utc_now(),
            event_kind=event_kind,
            payload_ref=payload_ref,
            hashes={
                "sha256": self._compute_hash(payload_ref),
                "upstream_hashes": []
            },
            correlation_id=correlation_id,
            trace_id=trace_id
        )
        
        # Store in memory for retrieval
        if correlation_id not in self.audit_records:
            self.audit_records[correlation_id] = []
        self.audit_records[correlation_id].append(audit_record)
        
        # Publish to JetStream if available
        if self.nats_client:
            # TODO: implement actual JetStream publishing
            pass
        
        return audit_record
    
    def get_audit_records(self, correlation_id: str) -> List[AuditRecordV1]:
        """Get audit records for a correlation ID"""
        return self.audit_records.get(correlation_id, [])
    
    def get_records_by_correlation(self, correlation_id: str) -> List[AuditRecordV1]:
        """Get audit records for a correlation ID (alias for get_audit_records)"""
        return self.get_audit_records(correlation_id)
    
    def record_audit(self, event_kind: str, payload_ref: Dict[str, Any], correlation_id: str, trace_id: str, tenant_id: str, cell_id: str, idempotency_key: str) -> AuditRecordV1:
        """Record audit event (alias for emit_audit_record)"""
        return self.emit_audit_record(
            event_kind=event_kind,
            payload_ref=payload_ref,
            correlation_id=correlation_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=idempotency_key
        )
    
    def _compute_hash(self, payload_ref: Dict[str, Any]) -> str:
        """Compute SHA256 hash of payload"""
        payload_str = json.dumps(payload_ref, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    async def start_consumer(self) -> None:
        """Start consuming audit records from JetStream"""
        logger.info("Starting audit record consumer")
        # TODO: implement actual JetStream consumer
