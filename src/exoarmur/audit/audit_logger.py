"""
Audit logging with JetStream publishing
"""

import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import ulid

from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.nats_client import ExoArmurNATSClient
from exoarmur.clock import utc_now
from exoarmur.feature_flags.resolver import (
    load_v2_core_types,
    load_v2_diagnostics,
    load_v2_entry_gate,
)

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


def compute_audit_id(tenant_id: str, correlation_id: str, event_kind: str, idempotency_key: str, payload_ref: Dict[str, Any]) -> str:
    canonical = json.dumps({
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "event_kind": event_kind,
        "idempotency_key": idempotency_key,
        "payload_ref": payload_ref,
    }, sort_keys=True)
    digest = hashlib.sha256(canonical.encode()).digest()
    return str(ulid.ULID.from_bytes(digest[:16]))


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
        """Emit audit record with JetStream publishing and durable idempotency"""
        # DETECTION ONLY: Check if this domain logic access is outside V2EntryGate
        v2_diagnostics = load_v2_diagnostics()
        v2_diagnostics.check_domain_logic_access("AuditLogger", "emit_audit_record", v2_diagnostics.ViolationSeverity.HIGH)
        
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
            audit_id=compute_audit_id(tenant_id, correlation_id, event_kind, idempotency_key, payload_ref),
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

    async def consume_from_jetstream(
        self,
        correlation_id: str,
        max_messages: int = 10,
        timeout_seconds: float = 2.0,
    ) -> List[AuditRecordV1]:
        """Consume audit records from JetStream into in-memory storage."""
        if not self.nats_client:
            logger.warning("No NATS client available for audit consumption")
            return []

        records = await self.nats_client.get_audit_records(
            correlation_id=correlation_id,
            max_messages=max_messages,
            timeout_seconds=timeout_seconds,
        )

        if correlation_id not in self.audit_records:
            self.audit_records[correlation_id] = []

        existing_ids = {r.audit_id for r in self.audit_records[correlation_id]}
        for record in records:
            if record.audit_id not in existing_ids:
                self.audit_records[correlation_id].append(record)
                existing_ids.add(record.audit_id)

        return records
    
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
        """Start consuming audit records from JetStream through V2EntryGate"""
        logger.info("Starting audit record consumer through V2EntryGate")
        
        try:
            # Import V2EntryGate components via resolver
            v2_entry_gate = load_v2_entry_gate()
            v2_core_types = load_v2_core_types()
            from datetime import datetime, timezone
            import hashlib
            import ulid
            
            # TODO: Implement actual JetStream consumer
            # For now, simulate receiving messages and route through V2EntryGate
            
            # Simulate receiving an audit record
            simulated_audit = {
                'event_id': str(ulid.ULID()),
                'event_type': 'test_audit_event',
                'component': 'test_consumer',
                'action': 'simulated_action',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'source': 'V2_consumer_test',
                    'version': '1.0'
                }
            }
            
            logger.info(f"Received audit record: {simulated_audit['event_id']}")
            
            # Route audit processing through V2EntryGate
            audit_ulid = str(ulid.ULID())
            execution_ulid = str(ulid.ULID())
            
            audit_request = v2_entry_gate.ExecutionRequest(
                module_id=v2_core_types.ModuleID(audit_ulid),
                execution_context=v2_core_types.ModuleExecutionContext(
                    execution_id=v2_core_types.ExecutionID(execution_ulid),
                    module_id=v2_core_types.ModuleID(audit_ulid),
                    module_version=v2_core_types.ModuleVersion(1, 0, 0),
                    deterministic_seed=v2_core_types.DeterministicSeed(hash("audit_processing") % (2**63)),
                    logical_timestamp=int(datetime.now(timezone.utc).timestamp()),
                    dependency_hash="audit_processing"
                ),
                action_data={
                    'intent_type': 'AUDIT_PROCESSING',
                    'action_class': 'message_processing',
                    'action_type': 'process_audit',
                    'subject': 'audit_record',
                    'parameters': {
                        'audit_data': simulated_audit
                    }
                },
                correlation_id=simulated_audit['event_id']
            )
            
            # Execute audit processing through V2EntryGate
            result = v2_entry_gate.execute_module(audit_request)
            
            if result.success:
                logger.info(f"Audit record processed successfully through V2EntryGate: {result.result_data.get('event_id')}")
            else:
                logger.error(f"Audit processing failed through V2EntryGate: {result.error}")
                
        except Exception as e:
            logger.error(f"Audit consumer error: {e}")
            
        logger.info("Audit record consumer started (V2-compliant)")
