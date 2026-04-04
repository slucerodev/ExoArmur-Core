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
from exoarmur.federation.clock import Clock
from exoarmur.federation.audit import AuditService, AuditEventType
from exoarmur.feature_flags.resolver import load_v2_core_types, load_v2_diagnostics, load_v2_entry_gate
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.identity_containment.effector import IdentityContainmentEffector
from exoarmur.identity_containment.intent_service import IdentityContainmentIntentService
from exoarmur.safety import GateDecision

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
        v2_diagnostics = load_v2_diagnostics()
        gate_result = await v2_diagnostics.enforce_execution_gate(
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
        
        # Create V2 ExecutionRequest for containment apply
        v2_entry_gate = load_v2_entry_gate()
        v2_core_types = load_v2_core_types()
        
        execution_request = v2_entry_gate.ExecutionRequest(
            module_id=v2_core_types.ModuleID("identity_containment_apply"),
            execution_context=v2_core_types.ModuleExecutionContext(
                execution_id=v2_core_types.ExecutionID(intent.intent_id[:26] + "0" * (26 - len(intent.intent_id[:26]))),
                module_id=v2_core_types.ModuleID("identity_containment_apply"),
                module_version=v2_core_types.ModuleVersion(1, 0, 0),
                deterministic_seed=v2_core_types.DeterministicSeed(hash(intent.intent_id) % (2**63)),
                logical_timestamp=int(self.clock.now().timestamp()),
                dependency_hash=intent.metadata.get("intent_hash")
            ),
            action_data={
                'action_class': 'identity_containment',
                'action_type': 'containment_apply',
                'subject': intent.subject_id,
                'parameters': {
                    'intent_hash': intent.metadata.get("intent_hash"),
                    'intent_id': intent.intent_id,
                    'scope': intent.scope.value,
                    'provider': intent.provider,
                    'approval_id': approval_id
                }
            },
            correlation_id=intent.metadata.get("correlation_id", "")
        )

        # Execute through V2 Entry Gate - ONLY ALLOWED PATH
        result = v2_entry_gate.execute_module(execution_request)
        
        if not result.success:
            logger.error(f"V2 Entry Gate blocked containment apply: {result.error}")
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
            # Execute containment through effector (only after V2 validation)
            applied_record = self.effector.apply(intent, approval_id)
            
            logger.info(f"Successfully executed containment apply for intent {intent.intent_id} via V2 Entry Gate")
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
        """Execute containment revert through V2 Entry Gate - ONLY ALLOWED PATH"""
        # Get intent by hash
        intent = self.intent_service.get_intent(intent_hash)
        if not intent:
            logger.error(f"No intent found for hash {intent_hash}")
            return None
        
        try:
            # Create V2 ExecutionRequest for containment revert
            v2_entry_gate = load_v2_entry_gate()
            v2_core_types = load_v2_core_types()

            execution_request = v2_entry_gate.ExecutionRequest(
                module_id=v2_core_types.ModuleID("identity_containment_revert"),
                execution_context=v2_core_types.ModuleExecutionContext(
                    execution_id=v2_core_types.ExecutionID(intent.intent_id[:26] + "0" * (26 - len(intent.intent_id[:26]))),
                    module_id=v2_core_types.ModuleID("identity_containment_revert"),
                    module_version=v2_core_types.ModuleVersion(1, 0, 0),
                    deterministic_seed=v2_core_types.DeterministicSeed(hash(intent.intent_id + reason) % (2**63)),
                    logical_timestamp=int(self.clock.now().timestamp()),
                    dependency_hash=intent_hash
                ),
                action_data={
                    'action_class': 'identity_containment',
                    'action_type': 'containment_revert',
                    'subject': intent.subject_id,
                    'parameters': {
                        'intent_hash': intent_hash,
                        'intent_id': intent.intent_id,
                        'reason': reason
                    }
                },
                correlation_id=intent.correlation_id
            )

            # Execute through V2 Entry Gate - ONLY ALLOWED PATH
            result = v2_entry_gate.execute_module(execution_request)
            
            if not result.success:
                logger.error(f"V2 Entry Gate blocked containment revert: {result.error}")
                return None
            
            # Execute revert through effector (only after V2 validation)
            reverted_record = self.effector.revert(intent, reason)
            
            logger.info(f"Successfully executed containment revert for intent {intent.intent_id} via V2 Entry Gate")
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
        """Process expired containments through V2 Entry Gate - ONLY ALLOWED PATH"""
        try:
            # Create V2 ExecutionRequest for expiration processing
            v2_entry_gate = load_v2_entry_gate()
            v2_core_types = load_v2_core_types()

            execution_request = v2_entry_gate.ExecutionRequest(
                module_id=v2_core_types.ModuleID("identity_containment_expire"),
                execution_context=v2_core_types.ModuleExecutionContext(
                    execution_id=v2_core_types.ExecutionID("expiration_processing" + "0" * 8),
                    module_id=v2_core_types.ModuleID("identity_containment_expire"),
                    module_version=v2_core_types.ModuleVersion(1, 0, 0),
                    deterministic_seed=v2_core_types.DeterministicSeed(hash("expiration_processing") % (2**63)),
                    logical_timestamp=int(self.clock.now().timestamp()),
                    dependency_hash="system_expiration"
                ),
                action_data={
                    'action_class': 'identity_containment',
                    'action_type': 'process_expirations',
                    'subject': 'system',
                    'parameters': {'batch_processing': True}
                },
                correlation_id="system"
            )

            # Execute through V2 Entry Gate - ONLY ALLOWED PATH
            result = v2_entry_gate.execute_module(execution_request)
            
            if not result.success:
                logger.error(f"V2 Entry Gate blocked expiration processing: {result.error}")
                return 0
            
            # Process expirations through effector (only after V2 validation)
            reverted_records = self.effector.process_expirations()
            
            logger.info(f"Processed {len(reverted_records)} expired containments via V2 Entry Gate")
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
