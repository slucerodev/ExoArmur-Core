"""
Identity Containment Execution Integration

Integrates identity containment with the ExecutionKernel for
approved containment operations.
Phase 5: Added execution gate enforcement for all side effects.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from enum import Enum

from spec.contracts.models_v1 import (
    IdentityContainmentIntentV1,
    IdentityContainmentAppliedRecordV1,
    IdentityContainmentRevertedRecordV1
)
from federation.clock import Clock
from federation.audit import AuditService, AuditEventType
from control_plane.approval_service import ApprovalService
from identity_containment.effector import IdentityContainmentEffector
from identity_containment.intent_service import IdentityContainmentIntentService
from safety import enforce_execution_gate, ExecutionActionType, GateDecision

logger = logging.getLogger(__name__)


class ExecutionActionType(str, Enum):
    """Execution action types"""
    IDENTITY_CONTAINMENT_APPLY = "identity_containment_apply"
    IDENTITY_CONTAINMENT_REVERT = "identity_containment_revert"


class IdentityContainmentExecutor:
    """Handles execution of identity containment operations"""
    
    def __init__(
        self,
        clock: Clock,
        audit_service: AuditService,
        approval_service: ApprovalService,
        intent_service: IdentityContainmentIntentService,
        effector: IdentityContainmentEffector
    ):
        """Initialize executor
        
        Args:
            clock: Clock for deterministic time handling
            audit_service: Audit service for event emission
            approval_service: Approval service for verification
            intent_service: Intent service for intent retrieval
            effector: Identity containment effector for operations
        """
        self.clock = clock
        self.audit_service = audit_service
        self.approval_service = approval_service
        self.intent_service = intent_service
        self.effector = effector
    
    async def execute_containment_apply(self, approval_id: str) -> Optional[IdentityContainmentAppliedRecordV1]:
        """Execute containment apply operation
        
        Args:
            approval_id: Approval identifier for the operation
            
        Returns:
            Applied record or None if execution failed
        """
        # Get approval status
        approval = self.approval_service.get_approval_details(approval_id)
        if not approval:
            logger.error(f"Approval {approval_id} not found")
            return None
        
        if approval.status != "APPROVED":
            logger.error(f"Approval {approval_id} not approved: {approval.status}")
            return None
        
        # Get intent by approval
        intent = self.intent_service.get_intent_by_approval(approval_id)
        if not intent:
            logger.error(f"No intent found for approval {approval_id}")
            return None
        
        # PHASE 5: Enforce execution gate BEFORE any side effects
        gate_result = await enforce_execution_gate(
            action_type=ExecutionActionType.IDENTITY_CONTAINMENT_APPLY,
            tenant_id=intent.subject_id,  # Use subject_id as tenant identifier
            correlation_id=intent.metadata.get("correlation_id", ""),
            trace_id=intent.metadata.get("trace_id", ""),
            principal_id=approval.approver_id,
            additional_context={
                "approval_id": approval_id,
                "intent_id": intent.intent_id,
                "subject": intent.subject_id
            }
        )
        
        if gate_result.decision != GateDecision.ALLOW:
            logger.warning(f"Containment apply blocked by execution gate: {gate_result.reason.value}")
            # Audit event already emitted by execution gate
            return None
        
        # Verify approval binding
        intent_hash = intent.metadata.get("intent_hash")
        if not intent_hash:
            logger.error(f"Intent {intent.intent_id} has no intent_hash in metadata")
            return None
            
        if not self.intent_service.verify_approval_binding(approval_id, intent_hash):
            logger.error(f"Approval {approval_id} not bound to intent {intent.intent_id}")
            return None
        
        # Verify intent not expired
        now = self.clock.now()
        if now >= intent.expires_at_utc:
            logger.error(f"Intent {intent.intent_id} expired at {intent.expires_at_utc}")
            return None
        
        try:
            # Execute containment
            applied_record = self.effector.apply(intent, approval_id)
            
            logger.info(f"Successfully executed containment apply for intent {intent.intent_id}")
            
            return applied_record
            
        except Exception as e:
            logger.error(f"Failed to execute containment apply for intent {intent.intent_id}: {e}")
            
            # Emit audit event for execution failure
            self.audit_service.emit_event(
                event_type=AuditEventType.IDENTITY_CONTAINMENT_DENIED,
                correlation_id=intent.correlation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent.intent_id,
                    "approval_id": approval_id,
                    "error": str(e),
                    "stage": "execution_apply"
                }
            )
            
            return None
    
    async def execute_containment_revert(self, intent_hash: str, reason: str) -> Optional[IdentityContainmentRevertedRecordV1]:
        """Execute containment revert operation
        
        Args:
            intent_hash: Hash of the intent to revert
            reason: Reason for reversion
            
        Returns:
            Reverted record or None if execution failed
        """
        # Get intent by hash
        intent = self.intent_service.get_intent(intent_hash)
        if not intent:
            logger.error(f"No intent found for hash {intent_hash}")
            return None
        
        # PHASE 5: Enforce execution gate BEFORE any side effects
        gate_result = await enforce_execution_gate(
            action_type=ExecutionActionType.IDENTITY_CONTAINMENT_REVERT,
            tenant_id=intent.tenant_id,
            correlation_id=intent.correlation_id,
            trace_id=intent.trace_id,
            principal_id="system",  # System-initiated revert
            additional_context={
                "intent_hash": intent_hash,
                "intent_id": intent.intent_id,
                "reason": reason
            }
        )
        
        if gate_result.decision != GateDecision.ALLOW:
            logger.warning(f"Containment revert blocked by execution gate: {gate_result.reason.value}")
            # Audit event already emitted by execution gate
            return None
        
        try:
            # Execute revert
            reverted_record = self.effector.revert(intent, reason)
            
            logger.info(f"Successfully executed containment revert for intent {intent.intent_id}")
            
            return reverted_record
            
        except Exception as e:
            logger.error(f"Failed to execute containment revert for intent {intent.intent_id}: {e}")
            
            # Emit audit event for execution failure
            self.audit_service.emit_event(
                event_type=AuditEventType.IDENTITY_CONTAINMENT_DENIED,
                correlation_id=intent.correlation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent.intent_id,
                    "intent_hash": intent_hash,
                    "error": str(e),
                    "stage": "execution_revert"
                }
            )
            
            return None
    
    async def process_expirations(self) -> int:
        """Process expired containments
        
        Returns:
            Number of containments that expired and were reverted
        """
        try:
            # PHASE 5: Enforce execution gate for batch expiration processing
            gate_result = await enforce_execution_gate(
                action_type=ExecutionActionType.IDENTITY_CONTAINMENT_EXPIRE,
                tenant_id="system",  # System-level operation
                correlation_id=None,
                trace_id=None,
                principal_id="system",
                additional_context={
                    "operation": "batch_expiration_processing",
                    "timestamp": self.clock.now().isoformat()
                }
            )
            
            if gate_result.decision != GateDecision.ALLOW:
                logger.warning(f"Expiration processing blocked by execution gate: {gate_result.reason.value}")
                return 0
            
            reverted_records = self.effector.process_expirations()
            
            logger.info(f"Processed {len(reverted_records)} expired containments")
            
            return len(reverted_records)
            
        except Exception as e:
            logger.error(f"Failed to process expirations: {e}")
            return 0


class IdentityContainmentTickService:
    """Service for periodic processing of containment expirations"""
    
    def __init__(
        self,
        executor: IdentityContainmentExecutor,
        clock: Clock,
        audit_service: AuditService,
        tick_interval_seconds: int = 60
    ):
        """Initialize tick service
        
        Args:
            executor: Identity containment executor
            clock: Clock for deterministic time handling
            audit_service: Audit service for event emission
            tick_interval_seconds: Interval between ticks (default 1 minute)
        """
        self.executor = executor
        self.clock = clock
        self.audit_service = audit_service
        self.tick_interval_seconds = tick_interval_seconds
        self.last_tick_utc: Optional[datetime] = None
    
    def should_tick(self) -> bool:
        """Check if tick should run based on interval"""
        now = self.clock.now()
        
        if self.last_tick_utc is None:
            return True
        
        elapsed = (now - self.last_tick_utc).total_seconds()
        return elapsed >= self.tick_interval_seconds
    
    async def tick(self) -> int:
        """Run expiration processing tick
        
        Returns:
            Number of containments that expired and were reverted
        """
        if not self.should_tick():
            return 0
        
        now = self.clock.now()
        
        try:
            # Process expirations (includes gate enforcement)
            expired_count = await self.executor.process_expirations()
            
            # Update last tick time
            self.last_tick_utc = now
            
            # Emit audit event for tick
            self.audit_service.emit_event(
                event_type=AuditEventType.IDENTITY_CONTAINMENT_EXPIRED,
                correlation_id=None,  # System operation
                source_federate_id=None,  # Local operation
                event_data={
                    "tick_timestamp_utc": now.isoformat().replace('+00:00', 'Z'),
                    "expired_count": expired_count,
                    "tick_interval_seconds": self.tick_interval_seconds
                }
            )
            
            logger.info(f"Tick completed: processed {expired_count} expired containments")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Tick failed: {e}")
            return 0
