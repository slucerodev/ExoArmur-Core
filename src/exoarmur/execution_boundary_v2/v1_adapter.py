"""
V1 Adapter Layer for clean V1/V2 decoupling.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

This module provides a dedicated adapter layer that converts between V2-native
structures and V1 compatibility structures. All V1 interactions are isolated
here to maintain clean separation between V1 and V2 architectures.

Key responsibilities:
- Convert V2 audit events to V1 AuditRecordV1
- Convert V2 policy decisions to V1 LocalDecisionV1
- Convert V2 execution intents to V1 ExecutionIntentV1
- Convert V2 safety states to V1 PolicyState/TrustState/EnvironmentState
- Provide V1 compatibility without V2 modules importing V1 directly
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from exoarmur.clock import utc_now
from exoarmur.ids import make_audit_id, make_id

# Import V2-native structures
from .models.action_intent import ActionIntent
from .models.policy_decision import PolicyDecision
from .models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
from .models.execution_dispatch import ExecutionDispatch
from .utils.verdict_resolution import FinalVerdict

# Import V1 structures ONLY in this adapter
from spec.contracts.models_v1 import (
    AuditRecordV1,
    LocalDecisionV1,
    ExecutionIntentV1,
)


class V1AuditAdapter:
    """Adapter for converting V2 audit events to V1 AuditRecordV1."""
    
    @staticmethod
    def create_audit_record_v1(
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AuditRecordV1:
        """Create V1 AuditRecordV1 from V2 audit event data."""
        if correlation_id is None:
            correlation_id = intent_id
        if trace_id is None:
            trace_id = intent_id
            
        audit_id = make_audit_id(intent_id, event_type, outcome)
        
        # Create canonical hash for V1 compatibility
        canonical_data = {
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details
        }
        canonical_json = __import__('json').dumps(
            canonical_data,
            sort_keys=True,
            separators=(",", ":")
        )
        audit_hash = __import__('hashlib').sha256(canonical_json.encode()).hexdigest()
        
        _event_kind_map = {
            "action_executed": "execution",
            "intent_executed": "execution",
            "policy_denial": "policy_denial",
            "policy_deferral": "policy_deferral",
            "safety_gate_block": "safety_gate_block",
            "approval_required": "approval_required",
        }
        normalized_event_kind = _event_kind_map.get(event_type, event_type)

        return AuditRecordV1(
            schema_version="1.0.0",
            audit_id=audit_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=f"audit-{correlation_id}",
            recorded_at=utc_now(),
            event_kind=normalized_event_kind,
            payload_ref={
                "kind": "inline",
                "ref": correlation_id,
                "outcome": outcome,
                "details": details
            },
            hashes={"sha256": audit_hash},
            correlation_id=correlation_id,
            trace_id=trace_id
        )
    
    @staticmethod
    def convert_trace_to_v1_audit_records(
        trace: ExecutionTrace,
        tenant_id: str,
        cell_id: str
    ) -> List[AuditRecordV1]:
        """Convert V2 ExecutionTrace to V1 AuditRecordV1 list."""
        audit_records = []
        
        for event in trace.events:
            audit_record = V1AuditAdapter.create_audit_record_v1(
                intent_id=trace.intent_id,
                event_type=event.stage.value,
                outcome="success" if event.ok else "failure",
                details=event.details,
                tenant_id=tenant_id,
                cell_id=cell_id,
                correlation_id=trace.intent_id,
                trace_id=trace.trace_id
            )
            audit_records.append(audit_record)
        
        return audit_records


class V1PolicyAdapter:
    """Adapter for converting V2 policy decisions to V1 LocalDecisionV1."""
    
    @staticmethod
    def create_local_decision_v1(
        intent: ActionIntent,
        policy_decision: PolicyDecision
    ) -> LocalDecisionV1:
        """Create V1 LocalDecisionV1 from V2 PolicyDecision."""
        decision_id = make_id("local-decision")
        
        return LocalDecisionV1(
            schema_version="1.0.0",
            decision_id=decision_id,
            tenant_id=intent.tenant_id or "default-tenant",
            cell_id=intent.cell_id or "default-cell",
            subject={
                "subject_type": intent.actor_type,
                "subject_id": intent.actor_id
            },
            classification="benign",  # Default classification for V1 compatibility
            severity="low",  # Default severity for V1 compatibility
            confidence=policy_decision.confidence if policy_decision.confidence is not None else 1.0,
            recommended_intents=[],  # Empty for V1 compatibility
            evidence_refs=policy_decision.evidence,
            correlation_id=intent.intent_id,
            trace_id=intent.intent_id
        )


class V1ExecutionIntentAdapter:
    """Adapter for converting V2 ActionIntent to V1 ExecutionIntentV1."""
    
    @staticmethod
    def create_execution_intent_v1(intent: ActionIntent) -> ExecutionIntentV1:
        """Create V1 ExecutionIntentV1 from V2 ActionIntent."""
        intent_id = make_id("execution-intent")
        
        return ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id=intent_id,
            tenant_id=intent.tenant_id or "default-tenant",
            cell_id=intent.cell_id or "default-cell",
            idempotency_key=f"intent-{intent.intent_id}",
            subject={
                "subject_type": intent.actor_type,
                "subject_id": intent.actor_id
            },
            intent_type=intent.action_type,
            action_class="A1_soft_containment",  # Default action class for V1 compatibility
            requested_at=utc_now(),
            ttl_seconds=None,
            parameters=intent.parameters,
            policy_context={},
            safety_context=intent.safety_context,
            trace_id=intent.intent_id,
            correlation_id=intent.intent_id
        )


class V1SafetyStateAdapter:
    """Adapter for creating V1 safety states from V2 data."""
    
    @staticmethod
    def create_policy_state(
        policy_verified: bool = True,
        kill_switch_global: bool = False,
        kill_switch_tenant: bool = False,
        required_approval: str = "none"
    ) -> Dict[str, Any]:
        """Create V1 PolicyState structure."""
        return {
            "policy_verified": policy_verified,
            "kill_switch_global": kill_switch_global,
            "kill_switch_tenant": kill_switch_tenant,
            "required_approval": required_approval
        }
    
    @staticmethod
    def create_trust_state(
        emitter_trust_score: float = 0.8
    ) -> Dict[str, Any]:
        """Create V1 TrustState structure."""
        return {
            "emitter_trust_score": emitter_trust_score
        }
    
    @staticmethod
    def create_environment_state(
        cell_load: float = 0.5,
        network_health: float = 0.9,
        resource_availability: float = 0.8
    ) -> Dict[str, Any]:
        """Create V1 EnvironmentState structure."""
        return {
            "cell_load": cell_load,
            "network_health": network_health,
            "resource_availability": resource_availability
        }


class V1CompatibilityLayer:
    """Main V1 compatibility layer that coordinates all adapters."""
    
    def __init__(self):
        self.audit_adapter = V1AuditAdapter()
        self.policy_adapter = V1PolicyAdapter()
        self.execution_intent_adapter = V1ExecutionIntentAdapter()
        self.safety_state_adapter = V1SafetyStateAdapter()
    
    def create_v1_audit_record(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AuditRecordV1:
        """Create V1 audit record using the audit adapter."""
        return self.audit_adapter.create_audit_record_v1(
            intent_id=intent_id,
            event_type=event_type,
            outcome=outcome,
            details=details,
            tenant_id=tenant_id,
            cell_id=cell_id,
            correlation_id=correlation_id,
            trace_id=trace_id
        )
    
    def convert_v2_trace_to_v1_audit_records(
        self,
        trace: ExecutionTrace,
        tenant_id: str,
        cell_id: str
    ) -> List[AuditRecordV1]:
        """Convert V2 trace to V1 audit records."""
        return self.audit_adapter.convert_trace_to_v1_audit_records(
            trace=trace,
            tenant_id=tenant_id,
            cell_id=cell_id
        )
    
    def create_v1_local_decision(
        self,
        intent: ActionIntent,
        policy_decision: PolicyDecision
    ) -> LocalDecisionV1:
        """Create V1 local decision from V2 policy decision."""
        return self.policy_adapter.create_local_decision_v1(
            intent=intent,
            policy_decision=policy_decision
        )
    
    def create_v1_execution_intent(
        self,
        intent: ActionIntent
    ) -> ExecutionIntentV1:
        """Create V1 execution intent from V2 action intent."""
        return self.execution_intent_adapter.create_execution_intent_v1(intent)
    
    def create_v1_safety_states(
        self,
        policy_verified: bool = True,
        kill_switch_global: bool = False,
        kill_switch_tenant: bool = False,
        required_approval: str = "none",
        emitter_trust_score: float = 0.8,
        cell_load: float = 0.5,
        network_health: float = 0.9,
        resource_availability: float = 0.8
    ) -> Dict[str, Any]:
        """Create all V1 safety states."""
        return {
            "policy_state": self.safety_state_adapter.create_policy_state(
                policy_verified=policy_verified,
                kill_switch_global=kill_switch_global,
                kill_switch_tenant=kill_switch_tenant,
                required_approval=required_approval
            ),
            "trust_state": self.safety_state_adapter.create_trust_state(
                emitter_trust_score=emitter_trust_score
            ),
            "environment_state": self.safety_state_adapter.create_environment_state(
                cell_load=cell_load,
                network_health=network_health,
                resource_availability=resource_availability
            )
        }


# Global compatibility layer instance
v1_compatibility = V1CompatibilityLayer()
