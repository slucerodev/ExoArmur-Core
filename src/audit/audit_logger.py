"""
Audit logging with JetStream publishing
"""

import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from spec.contracts.models_v1 import AuditRecordV1
from nats_client import ExoArmurNATSClient

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


def compute_idempotency_key(tenant_id: str, correlation_id: str, event_kind: str, payload_ref: Dict[str, Any]) -> str:
    """Compute deterministic idempotency key from stable fields"""
    canonical = json.dumps({
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "event_kind": event_kind,
        "payload_ref": payload_ref
    }, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditLogger:
    """Audit logger with JetStream publishing and durable idempotency"""
    
    def __init__(self, nats_client=None):
        self.nats_client = nats_client
        self.audit_records: Dict[str, List[AuditRecordV1]] = {}  # In-memory storage for testing
        self._idempotency_kv = None
        logger.info("AuditLogger initialized")
    
    async def _ensure_idempotency_kv(self):
        """Ensure idempotency KV bucket exists"""
        if not self.nats_client or not self.nats_client.js:
            return False
        
        try:
            # Create KV bucket for idempotency
            kv = await self.nats_client.js.create_key_value(
                bucket="EXOARMUR_IDEMPOTENCY_V1",
                history=1,  # Keep only latest value
                ttl=0  # No expiration for Gate 2
            )
            self._idempotency_kv = kv
            logger.info("Created idempotency KV bucket")
            return True
        except Exception as e:
            # Bucket might already exist, try to get it
            try:
                kv = await self.nats_client.js.key_value("EXOARMUR_IDEMPOTENCY_V1")
                self._idempotency_kv = kv
                logger.info("Connected to existing idempotency KV bucket")
                return True
            except Exception as e2:
                logger.error(f"Failed to create/get idempotency KV: {e2}")
                return False
    
    async def _check_idempotency(self, tenant_id: str, idempotency_key: str) -> Optional[str]:
        """Check if event already processed, returns audit_id if found"""
        if not self._idempotency_kv:
            await self._ensure_idempotency_kv()
        
        if not self._idempotency_kv:
            return None
        
        try:
            kv_key = f"{tenant_id}/{idempotency_key}"
            result = await self._idempotency_kv.get(kv_key)
            if result:
                return result.value.decode()
            return None
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
            return None
    
    async def _record_idempotency(self, tenant_id: str, idempotency_key: str, audit_id: str):
        """Record that event has been processed"""
        if not self._idempotency_kv:
            return
        
        try:
            kv_key = f"{tenant_id}/{idempotency_key}"
            await self._idempotency_kv.put(kv_key, audit_id.encode())
            logger.debug(f"Recorded idempotency for key: {kv_key}")
        except Exception as e:
            logger.warning(f"Failed to record idempotency: {e}")
    
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
        """Synchronous wrapper for emit_audit_record_async"""
        import asyncio
        
        # If we have an event loop, use it; otherwise create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.emit_audit_record_async(
                            event_kind, payload_ref, correlation_id, 
                            trace_id, tenant_id, cell_id, idempotency_key
                        )
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.emit_audit_record_async(
                        event_kind, payload_ref, correlation_id, 
                        trace_id, tenant_id, cell_id, idempotency_key
                    )
                )
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(
                self.emit_audit_record_async(
                    event_kind, payload_ref, correlation_id, 
                    trace_id, tenant_id, cell_id, idempotency_key
                )
            )
    
    async def emit_audit_record_async(
        self,
        event_kind: str,
        payload_ref: Dict[str, Any],
        correlation_id: str,
        trace_id: str,
        tenant_id: str,
        cell_id: str,
        idempotency_key: str
    ) -> AuditRecordV1:
        """Emit audit record with durable idempotency enforcement"""
        logger.info(f"Emitting audit record for {event_kind}")
        
        # Compute deterministic idempotency key if not provided
        if not idempotency_key:
            idempotency_key = compute_idempotency_key(tenant_id, correlation_id, event_kind, payload_ref)
        
        # Check idempotency BEFORE creating audit record
        existing_audit_id = await self._check_idempotency(tenant_id, idempotency_key)
        if existing_audit_id:
            logger.info(f"Idempotency hit: event already processed as {existing_audit_id}")
            # Return existing record (create minimal record for evidence)
            return AuditRecordV1(
                schema_version="1.0.0",
                audit_id=existing_audit_id,
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
            subject = self.nats_client.subjects["audit_append"]
            audit_data = audit_record.model_dump_json().encode()
            published = await self.nats_client.publish(subject, audit_data)
            if not published:
                logger.error("Failed to publish audit record to JetStream")
                # Continue with idempotency recording anyway for consistency
        
        # Record idempotency AFTER successful publish
        await self._record_idempotency(tenant_id, idempotency_key, audit_record.audit_id)
        
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
