"""
Proxy Pipeline for execution governance boundary.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

Clean V2-native orchestration with V1 compatibility handled through adapter layer.
Enhanced with deterministic verdict resolution, comprehensive governance tracking,
and executor sandboxing with capability enforcement.
"""

from __future__ import annotations

import logging
import hashlib
import json
from typing import Dict, Any, Union, Tuple, Optional
from datetime import datetime
import ulid

from ..interfaces.policy_decision_point import PolicyDecisionPoint
from ..interfaces.executor_plugin import ExecutorPlugin, ExecutorResult, ValidationResult
from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision, PolicyVerdict
from ..models.execution_dispatch import ExecutionDispatch, DispatchStatus
from ..models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
from ..utils.verdict_resolution import FinalVerdict
from exoarmur.clock import utc_now
from exoarmur.ids import make_audit_id

# Import V1 compatibility through adapter layer ONLY
from ..v1_adapter import v1_compatibility

# Import V2-native safety gate
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict

# Import verdict resolution utilities
from ..utils.verdict_resolution import resolve_verdicts, FinalVerdict, create_verdict_resolution_id

logger = logging.getLogger(__name__)


class V2AuditEvent:
    """V2-native audit event structure."""
    
    def __init__(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        self.intent_id = intent_id
        self.event_type = event_type
        self.outcome = outcome
        self.details = details
        self.tenant_id = tenant_id
        self.cell_id = cell_id
        self.correlation_id = correlation_id or intent_id
        self.trace_id = trace_id or intent_id
        self.timestamp = utc_now()


class V2AuditEmitter:
    """V2-native audit emitter that uses adapter for V1 compatibility."""
    
    def __init__(self):
        self.audit_events: list[V2AuditEvent] = []
        self.v1_records = []  # Store V1 records for backward compatibility
    
    def emit_audit_event(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> V2AuditEvent:
        """Emit a V2-native audit event."""
        audit_event = V2AuditEvent(
            intent_id=intent_id,
            event_type=event_type,
            outcome=outcome,
            details=details,
            tenant_id=tenant_id,
            cell_id=cell_id,
            correlation_id=correlation_id,
            trace_id=trace_id
        )
        
        self.audit_events.append(audit_event)
        
        # Convert to V1 record through adapter for compatibility
        v1_record = v1_compatibility.create_v1_audit_record(
            intent_id=intent_id,
            event_type=event_type,
            outcome=outcome,
            details=details,
            tenant_id=tenant_id,
            cell_id=cell_id,
            correlation_id=correlation_id,
            trace_id=trace_id
        )
        self.v1_records.append(v1_record)
        
        logger.info(f"Emitted V2 audit event: {event_type} -> {outcome}")
        return audit_event
    
    # Backward compatibility method
    def emit_audit_record(self, *args, **kwargs):
        """Legacy method for backward compatibility."""
        return self.emit_audit_event(*args, **kwargs)


class V2SafetyState:
    """V2-native safety state structure."""
    
    def __init__(
        self,
        policy_verified: bool = True,
        kill_switch_global: bool = False,
        kill_switch_tenant: bool = False,
        required_approval: str = "none",
        emitter_trust_score: float = 0.8,
        cell_load: float = 0.5,
        network_health: float = 0.9,
        resource_availability: float = 0.8
    ):
        self.policy_verified = policy_verified
        self.kill_switch_global = kill_switch_global
        self.kill_switch_tenant = kill_switch_tenant
        self.required_approval = required_approval
        self.emitter_trust_score = emitter_trust_score
        self.cell_load = cell_load
        self.network_health = network_health
        self.resource_availability = resource_availability


class ProxyPipeline:
    """V2-native proxy pipeline with clean V1/V2 separation.
    
    Orchestrates policy evaluation, safety gate enforcement, and executor dispatch
    while maintaining strict separation of concerns and providing comprehensive
    audit trails. All V1 compatibility is handled through the adapter layer.
    """
    
    def __init__(
        self,
        pdp: PolicyDecisionPoint,
        safety_gate: SafetyGate,
        executor: ExecutorPlugin,
        audit_emitter: V2AuditEmitter
    ):
        """Initialize the V2-native proxy pipeline."""
        self.pdp = pdp
        self.safety_gate = safety_gate
        self.executor = executor
        self.audit_emitter = audit_emitter
        logger.info("V2-native ProxyPipeline initialized with clean V1/V2 separation")
    
    def execute(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
        """Execute an intent through governance pipeline (backward compatibility)."""
        logger.info(f"Executing intent {intent.intent_id} through V2-native proxy pipeline (legacy method)")
        result, trace = self.execute_with_trace(intent)
        return result
    
    def execute_with_trace(self, intent: ActionIntent) -> Tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
        """Execute an intent through V2-native governance pipeline and return trace.
        
        Enhanced with deterministic verdict resolution between PDP and SafetyGate
        according to strict precedence rules for consistent governance behavior.
        Includes executor sandboxing with target validation and capability enforcement.
        All V1 compatibility is handled through the adapter layer.
        """
        logger.info(f"Executing intent {intent.intent_id} through V2-native pipeline with clean V1/V2 separation")
        
        # Initialize execution trace
        trace = ExecutionTrace.create(
            correlation_id=intent.intent_id,
            intent_id=intent.intent_id,
            final_verdict=FinalVerdict.ALLOW  # Will be updated later
        )
        
        # Step 1: Intent received
        trace.add_event(
            stage=TraceStage.INTENT_RECEIVED,
            ok=True,
            code="RECEIVED",
            details={"action_type": intent.action_type, "target": intent.target}
        )
        
        # Step 2: Policy evaluation
        policy_decision = self.pdp.evaluate(intent)
        trace.add_event(
            stage=TraceStage.POLICY_EVALUATED,
            ok=policy_decision.verdict in [PolicyVerdict.ALLOW, PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER],
            code=policy_decision.verdict.value,
            details={
                "decision_id": policy_decision.decision_id,
                "confidence": policy_decision.confidence,
                "approval_required": policy_decision.approval_required
            }
        )
        
        # Step 3: Safety gate evaluation with V2-native states
        # Create V2-native safety state
        v2_safety_state = V2SafetyState()
        
        # Create V2 execution intent through adapter
        v1_execution_intent = v1_compatibility.create_v1_execution_intent(intent)
        
        # Create V1 local decision through adapter
        v1_local_decision = v1_compatibility.create_v1_local_decision(intent, policy_decision)
        
        # Convert V2 safety state to V1 structures through adapter
        v1_safety_states = v1_compatibility.create_v1_safety_states(
            policy_verified=v2_safety_state.policy_verified,
            kill_switch_global=v2_safety_state.kill_switch_global,
            kill_switch_tenant=v2_safety_state.kill_switch_tenant,
            required_approval=v2_safety_state.required_approval,
            emitter_trust_score=v2_safety_state.emitter_trust_score,
            cell_load=v2_safety_state.cell_load,
            network_health=v2_safety_state.network_health,
            resource_availability=v2_safety_state.resource_availability
        )
        
        # Evaluate safety gate (still uses V1 structures internally)
        from exoarmur.safety.safety_gate import PolicyState, TrustState, EnvironmentState
        
        safety_verdict = self.safety_gate.evaluate_safety(
            intent=v1_execution_intent,
            local_decision=v1_local_decision,
            policy_state=PolicyState(**v1_safety_states["policy_state"]),
            trust_state=TrustState(**v1_safety_states["trust_state"]),
            environment_state=EnvironmentState(**v1_safety_states["environment_state"])
        )
        
        trace.add_event(
            stage=TraceStage.SAFETY_EVALUATED,
            ok=safety_verdict.verdict in ["allow", "warn"],
            code=safety_verdict.verdict,
            details={
                "rule_ids": safety_verdict.rule_ids,
                "rationale": safety_verdict.rationale,
                "v2_safety_state": {
                    "policy_verified": v2_safety_state.policy_verified,
                    "emitter_trust_score": v2_safety_state.emitter_trust_score,
                    "cell_load": v2_safety_state.cell_load
                }
            }
        )
        
        # Step 4: Resolve final verdict with precedence
        resolution_id = create_verdict_resolution_id(
            policy_decision_id=policy_decision.decision_id,
            safety_verdict=safety_verdict,
            intent_id=intent.intent_id
        )
        final_verdict, resolution_evidence = resolve_verdicts(
            policy_decision=policy_decision,
            safety_verdict=safety_verdict,
            intent_id=intent.intent_id
        )
        
        trace.add_event(
            stage=TraceStage.VERDICT_RESOLVED,
            ok=True,
            code=final_verdict.value,
            details={
                "final_verdict": final_verdict.value,
                "resolution_rules_applied": resolution_evidence.get("resolution_rules_applied", [])
            }
        )
        
        # Record comprehensive verdict information in trace
        trace.record_verdicts(policy_decision, safety_verdict, final_verdict, resolution_evidence)
        
        # Step 5: Handle final verdict
        if final_verdict == FinalVerdict.DENY:
            trace.final_verdict = final_verdict
            
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="final_denial",
                outcome="denied",
                details={
                    "final_verdict": final_verdict.value,
                    "policy_verdict": policy_decision.verdict.value,
                    "safety_verdict": safety_verdict.verdict,
                    "resolution_evidence": resolution_evidence
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            return ExecutorResult(
                success=False,
                output={},
                error="DENIED",
                evidence={"final_verdict": final_verdict.value}
            ), trace
        
        if final_verdict in [FinalVerdict.REQUIRE_APPROVAL]:
            status = DispatchStatus.APPROVAL_PENDING
            trace.final_verdict = final_verdict
            
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="approval_required",
                outcome="pending",
                details={
                    "final_verdict": final_verdict.value,
                    "policy_verdict": policy_decision.verdict.value,
                    "safety_verdict": safety_verdict.verdict
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutionDispatch.create(
                intent_id=intent.intent_id,
                status=status,
                details={"final_verdict": final_verdict.value}
            ), trace
        
        if final_verdict in [FinalVerdict.REQUIRE_QUORUM, FinalVerdict.REQUIRE_HUMAN]:
            status = DispatchStatus.BLOCKED
            trace.final_verdict = final_verdict
            
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="consensus_required",
                outcome="blocked",
                details={
                    "final_verdict": final_verdict.value,
                    "policy_verdict": policy_decision.verdict.value,
                    "safety_verdict": safety_verdict.verdict
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutionDispatch.create(
                intent_id=intent.intent_id,
                status=status,
                details={"final_verdict": final_verdict.value}
            ), trace
        
        # Step 6: Target validation (ALWAYS called before execution)
        executor_capabilities = self.executor.capabilities()
        validation_result = self.executor.validate_target(intent)
        
        trace.add_event(
            stage=TraceStage.TARGET_VALIDATED,
            ok=validation_result.result.value in ["valid"],
            code=validation_result.result.value,
            details={
                "validation_result": validation_result.result.value,
                "validation_evidence": validation_result.evidence
            }
        )
        
        # Record executor information in trace
        trace.record_executor_info(
            executor_name=executor_capabilities.get("executor_name", "unknown"),
            executor_version=executor_capabilities.get("version", "unknown"),
            executor_capabilities=executor_capabilities.get("capabilities", []),
            target_validation_result=validation_result.result.value,
            validation_evidence=validation_result.evidence,
            executor_failure_evidence={}
        )
        
        # Check if target validation failed
        if validation_result.result.value in ["invalid", "unsupported", "violates_constraints"]:
            trace.final_verdict = FinalVerdict.DENY
            
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="target_validation_failed",
                outcome="denied",
                details={
                    "validation_result": validation_result.result.value,
                    "validation_evidence": validation_result.evidence,
                    "final_verdict": final_verdict.value
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutorResult(
                success=False,
                output={},
                error=f"Target validation failed: {validation_result.result.value}",
                evidence={
                    "validation_result": validation_result.result.value,
                    "validation_evidence": validation_result.evidence
                }
            ), trace
        
        # Step 7: Execute action (only for ALLOW with valid target)
        try:
            governance_context = {
                "final_verdict": final_verdict,
                "policy_decision": policy_decision,
                "safety_verdict": safety_verdict,
                "validation_result": validation_result,
                "v2_safety_state": v2_safety_state.__dict__
            }
            
            executor_result = self.executor.execute(intent, policy_decision, governance_context)
            
            trace.add_event(
                stage=TraceStage.EXECUTOR_DISPATCHED,
                ok=executor_result.success,
                code="EXECUTED" if executor_result.success else "FAILED",
                details={
                    "success": executor_result.success,
                    "error": executor_result.error,
                    "execution_id": getattr(executor_result, 'execution_id', None)
                }
            )
            
            # Update executor failure evidence if execution failed
            if not executor_result.success:
                if trace.executor_trace:
                    trace.executor_trace.executor_failure_evidence = {
                        "execution_error": executor_result.error,
                        "execution_id": getattr(executor_result, 'execution_id', None),
                        "failure_timestamp": None  # Deterministic - no timestamp
                    }
            
            # Emit execution audit event
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="intent_executed",
                outcome="executed" if executor_result.success else "failed",
                details={
                    "success": executor_result.success,
                    "error": executor_result.error,
                    "output": executor_result.output,
                    "final_verdict": final_verdict.value,
                    "execution_id": getattr(executor_result, 'execution_id', None)
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            trace.final_verdict = FinalVerdict.ALLOW if executor_result.success else FinalVerdict.DENY
            
            return executor_result, trace
            
        except Exception as e:
            # Record executor failure
            if trace.executor_trace:
                trace.executor_trace.executor_failure_evidence = {
                    "execution_error": str(e),
                    "exception_type": type(e).__name__,
                    "failure_timestamp": None  # Deterministic - no timestamp
                }
            
            trace.add_event(
                stage=TraceStage.EXECUTOR_DISPATCHED,
                ok=False,
                code="ERROR",
                details={"error": str(e), "exception_type": type(e).__name__}
            )
            
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="execution_error",
                outcome="error",
                details={"error": str(e), "exception_type": type(e).__name__},
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            trace.final_verdict = FinalVerdict.DENY