"""
Execution Gate - Single Authoritative Enforcement Point
Phase 5 Operational Safety Hardening
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ExecutionActionType(str, Enum):
    """Execution action types requiring gate enforcement"""
    IDENTITY_CONTAINMENT_APPLY = "identity_containment_apply"
    IDENTITY_CONTAINMENT_REVERT = "identity_containment_revert"
    IDENTITY_CONTAINMENT_EXPIRE = "identity_containment_expire"
    EXECUTION_KERNEL_INTENT = "execution_kernel_intent"
    FEDERATION_JOIN = "federation_join"
    APPROVAL_GRANT = "approval_grant"
    APPROVAL_DENY = "approval_deny"


class GateDecision(str, Enum):
    """Gate decision outcomes"""
    ALLOW = "ALLOW"
    DENY = "DENY"


class DenialReason(str, Enum):
    """Denial reason codes for audit"""
    GLOBAL_KILL_SWITCH_ACTIVE = "global_kill_switch_active"
    TENANT_KILL_SWITCH_ACTIVE = "tenant_kill_switch_active"
    MISSING_TENANT_CONTEXT = "missing_tenant_context"
    UNKNOWN_ACTION_TYPE = "unknown_action_type"
    SYSTEM_ERROR = "system_error"


@dataclass
class ExecutionContext:
    """Context for execution gate evaluation"""
    action_type: ExecutionActionType
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    principal_id: Optional[str] = None  # Who is requesting execution
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class GateResult:
    """Result of execution gate evaluation"""
    decision: GateDecision
    reason: Optional[DenialReason] = None
    message: Optional[str] = None
    evaluated_at: datetime = None
    
    def __post_init__(self):
        if self.evaluated_at is None:
            self.evaluated_at = datetime.now(timezone.utc)


class ExecutionGate:
    """
    Single Authoritative Enforcement Point for all execution paths
    
    Enforces kill switches, tenant context requirements, and audit requirements
    before any side-effect execution can proceed.
    
    Phase 5: Enhanced with tenant isolation enforcement.
    """
    
    def __init__(self, nats_client=None):
        """Initialize execution gate
        
        Args:
            nats_client: NATS client for durable kill switch storage
        """
        self.nats_client = nats_client
        self._global_kill_switch_kv = None
        self._tenant_kill_switch_kv = None
        
        logger.info("ExecutionGate initialized - FAIL CLOSED by default")
    
    async def _ensure_kv_stores(self) -> None:
        """Ensure kill switch KV stores exist"""
        if not self.nats_client:
            logger.warning("No NATS client available - using in-memory defaults (DENY)")
            return
        
        try:
            # Global kill switch KV store
            if not self._global_kill_switch_kv:
                self._global_kill_switch_kv = await self.nats_client.js.create_key_value(
                    bucket="EXOARMUR_KILL_SWITCH_GLOBAL",
                    description="Global execution kill switches"
                )
            
            # Tenant kill switch KV store  
            if not self._tenant_kill_switch_kv:
                self._tenant_kill_switch_kv = await self.nats_client.js.create_key_value(
                    bucket="EXOARMUR_KILL_SWITCH_TENANT", 
                    description="Per-tenant execution kill switches"
                )
                
        except Exception as e:
            logger.error(f"Failed to ensure KV stores: {e}")
            # Continue with in-memory defaults (DENY)
    
    async def get_global_kill_switch_status(self, switch_name: str) -> bool:
        """Get global kill switch status
        
        Args:
            switch_name: Name of the kill switch (e.g., "all_execution")
            
        Returns:
            True if kill switch is ACTIVE (execution blocked), False if inactive
        """
        await self._ensure_kv_stores()
        
        if not self._global_kill_switch_kv:
            # Default to ACTIVE (DENY) if no durable storage available
            logger.warning("Global kill switch storage unavailable - defaulting to ACTIVE (DENY)")
            return True
        
        try:
            value = await self._global_kill_switch_kv.get(f"switch_{switch_name}")
            status = value.decode('utf-8').lower() == "active"
            logger.debug(f"Global kill switch '{switch_name}' status: {status}")
            return status
        except KeyError:
            # Default to ACTIVE (DENY) if not set
            logger.info(f"Global kill switch '{switch_name}' not set - defaulting to ACTIVE (DENY)")
            return True
        except Exception as e:
            logger.error(f"Error checking global kill switch '{switch_name}': {e}")
            return True  # Fail closed
    
    async def get_tenant_kill_switch_status(self, tenant_id: str, switch_name: str) -> bool:
        """Get tenant-specific kill switch status
        
        Args:
            tenant_id: Tenant identifier
            switch_name: Name of the kill switch (e.g., "all_execution")
            
        Returns:
            True if kill switch is ACTIVE (execution blocked), False if inactive
        """
        await self._ensure_kv_stores()
        
        if not self._tenant_kill_switch_kv:
            # Default to ACTIVE (DENY) if no durable storage available
            logger.warning("Tenant kill switch storage unavailable - defaulting to ACTIVE (DENY)")
            return True
        
        try:
            key = f"{tenant_id}_switch_{switch_name}"
            value = await self._tenant_kill_switch_kv.get(key)
            status = value.decode('utf-8').lower() == "active"
            logger.debug(f"Tenant '{tenant_id}' kill switch '{switch_name}' status: {status}")
            return status
        except KeyError:
            # Default to ACTIVE (DENY) if not set
            logger.info(f"Tenant '{tenant_id}' kill switch '{switch_name}' not set - defaulting to ACTIVE (DENY)")
            return True
        except Exception as e:
            logger.error(f"Error checking tenant kill switch '{tenant_id}/{switch_name}': {e}")
            return True  # Fail closed
    
    async def evaluate_execution(self, context: ExecutionContext) -> GateResult:
        """
        Evaluate execution request against all safety policies
        
        This is the SINGLE AUTHORITATIVE ENFORCEMENT POINT.
        All side-effect execution paths must call this before proceeding.
        
        Args:
            context: Execution context with all required information
            
        Returns:
            GateResult with ALLOW/DENY decision and reasoning
        """
        logger.debug(f"Evaluating execution: {context.action_type} for tenant {context.tenant_id}")
        
        # Rule R3: Tenant context is mandatory for side effects
        if not context.tenant_id:
            logger.warning("Execution DENIED: missing tenant context")
            return GateResult(
                decision=GateDecision.DENY,
                reason=DenialReason.MISSING_TENANT_CONTEXT,
                message="Tenant context is required for execution"
            )
        
        # Validate tenant ID format
        if not context.tenant_id.strip():
            logger.warning("Execution DENIED: empty tenant ID")
            return GateResult(
                decision=GateDecision.DENY,
                reason=DenialReason.MISSING_TENANT_CONTEXT,
                message="Tenant ID cannot be empty"
            )
        
        # Rule R1: Check global kill switch (FAIL CLOSED)
        global_kill_active = await self.get_global_kill_switch_status("all_execution")
        if global_kill_active:
            logger.warning(f"Execution DENIED: global kill switch active for tenant {context.tenant_id}")
            return GateResult(
                decision=GateDecision.DENY,
                reason=DenialReason.GLOBAL_KILL_SWITCH_ACTIVE,
                message="Global execution kill switch is active"
            )
        
        # Rule R1: Check tenant-specific kill switch (FAIL CLOSED)
        tenant_kill_active = await self.get_tenant_kill_switch_status(context.tenant_id, "all_execution")
        if tenant_kill_active:
            logger.warning(f"Execution DENIED: tenant kill switch active for tenant {context.tenant_id}")
            return GateResult(
                decision=GateDecision.DENY,
                reason=DenialReason.TENANT_KILL_SWITCH_ACTIVE,
                message=f"Tenant {context.tenant_id} execution kill switch is active"
            )
        
        # All checks passed - ALLOW execution
        logger.info(f"Execution ALLOWED: {context.action_type} for tenant {context.tenant_id}")
        return GateResult(decision=GateDecision.ALLOW)
    
    async def emit_denial_audit(self, context: ExecutionContext, result: GateResult) -> None:
        """
        Emit audit event for execution denial
        
        Rule R6: Every denial must be audited with deterministic replay
        """
        if self.nats_client:
            try:
                audit_record = {
                    "event_type": "execution_denied",
                    "action_type": context.action_type.value,
                    "tenant_id": context.tenant_id,
                    "principal_id": context.principal_id,
                    "correlation_id": context.correlation_id,
                    "trace_id": context.trace_id,
                    "denial_reason": result.reason.value if result.reason else "unknown",
                    "denial_message": result.message,
                    "evaluated_at": result.evaluated_at.isoformat().replace('+00:00', 'Z'),
                    "additional_context": context.additional_context or {}
                }
                
                # Emit to tenant-scoped audit stream
                audit_subject = f"exoarmur.{context.tenant_id}.audit.append.v1"
                await self.nats_client.publish(audit_subject, audit_record)
                
                logger.info(f"Audit event emitted for execution denial: {result.reason.value}")
                
            except Exception as e:
                logger.error(f"Failed to emit denial audit: {e}")
        else:
            logger.warning("No audit storage available for denial event")


# Global singleton instance for use across the system
_execution_gate: Optional[ExecutionGate] = None


def get_execution_gate() -> ExecutionGate:
    """Get the global execution gate instance"""
    global _execution_gate
    if _execution_gate is None:
        _execution_gate = ExecutionGate()
    return _execution_gate


async def enforce_execution_gate(
    action_type: ExecutionActionType,
    tenant_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    principal_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> GateResult:
    """
    Convenience function for enforcing execution gate
    
    This is the PRIMARY interface that all execution paths should use.
    """
    gate = get_execution_gate()
    
    context = ExecutionContext(
        action_type=action_type,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=trace_id,
        principal_id=principal_id,
        additional_context=additional_context
    )
    
    result = await gate.evaluate_execution(context)
    
    # Emit audit for denials
    if result.decision == GateDecision.DENY:
        await gate.emit_denial_audit(context, result)
    
    return result
