"""
Proxy Pipeline for execution governance boundary.

Minimal orchestration using existing V1 primitives without modifying V1 behavior.
"""

from __future__ import annotations

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Union, Tuple
import ulid

from ..interfaces.policy_decision_point import PolicyDecisionPoint
from ..interfaces.executor_plugin import ExecutorPlugin, ExecutorResult
from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision, PolicyVerdict
from ..models.execution_dispatch import ExecutionDispatch, DispatchStatus
from ..models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
from exoarmur.clock import utc_now

# Import V1 primitives for integration
from spec.contracts.models_v1 import AuditRecordV1, LocalDecisionV1
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState

logger = logging.getLogger(__name__)
def _deterministic_audit_id(intent_id: str, event_type: str, outcome: str, details: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return str(ulid.ULID.from_bytes(digest[:16]))


def _deterministic_audit_hash(intent_id: str, event_type: str, outcome: str, details: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _deterministic_local_decision_id(intent: ActionIntent) -> str:
    canonical = json.dumps(
        {
            "intent_id": intent.intent_id,
            "actor_id": intent.actor_id,
            "action_type": intent.action_type,
            "target": intent.target,
            "timestamp": intent.timestamp.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return str(ulid.ULID.from_bytes(digest[:16]))


class AuditEmitter:
    """Minimal adapter for emitting V1 audit records from V2 pipeline."""
    
    def __init__(self):
        self.audit_records: list[AuditRecordV1] = []
    
    def emit_audit_record(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        recorded_at: datetime | None = None,
        tenant_id: str = "test-tenant",
        cell_id: str = "test-cell",
    ) -> AuditRecordV1:
        """Create and emit a V1 audit record."""
        # Generate placeholder ULID for audit_id (will be deterministic in later phases)
        audit_id = _deterministic_audit_id(intent_id, event_type, outcome, details)
        
        audit_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id=audit_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=f"audit-{intent_id}",
            recorded_at=recorded_at or utc_now(),
            event_kind=event_type,
            payload_ref={
                "kind": "inline",
                "ref": intent_id,
                "outcome": outcome,
                "details": details
            },
            hashes={
                "sha256": _deterministic_audit_hash(intent_id, event_type, outcome, details)
            },
            correlation_id=intent_id,
            trace_id=intent_id
        )
        
        self.audit_records.append(audit_record)
        logger.info(f"Emitted audit record: {event_type} -> {outcome}")
        return audit_record


class ProxyPipeline:
    """Proxy execution pipeline that orchestrates policy, safety, and execution."""
    
    def __init__(
        self,
        pdp: PolicyDecisionPoint,
        safety_gate: SafetyGate,
        executor: ExecutorPlugin,
        audit_emitter: AuditEmitter
    ):
        """Initialize the proxy pipeline with required components."""
        self.pdp = pdp
        self.safety_gate = safety_gate
        self.executor = executor
        self.audit_emitter = audit_emitter
        logger.info("ProxyPipeline initialized")
    
    def execute(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
        """Execute an intent through governance pipeline (backward compatibility)."""
        logger.info(f"Executing intent {intent.intent_id} through proxy pipeline (legacy method)")
        result, trace = self.execute_with_trace(intent)
        return result
    
    def execute_with_trace(self, intent: ActionIntent) -> Tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
        """Execute an intent through governance pipeline and return trace."""
        logger.info(f"Executing intent {intent.intent_id} through proxy pipeline with trace")
        intent_timestamp = intent.timestamp
        
        # Initialize execution trace
        trace = ExecutionTrace(
            intent_id=intent.intent_id,
            events=[],
            final_status="",
            evidence={}
        )
        
        # Step 1: Intent received
        trace.events.append(TraceEvent(
            stage=TraceStage.INTENT_RECEIVED,
            ok=True,
            code="RECEIVED",
            details={"action_type": intent.action_type, "target": intent.target}
        ))
        
        # Step 2: Policy evaluation
        policy_decision = self.pdp.evaluate(intent)
        trace.events.append(TraceEvent(
            stage=TraceStage.POLICY_EVALUATED,
            ok=policy_decision.verdict in [PolicyVerdict.ALLOW, PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER],
            code=policy_decision.verdict.value,
            details={
                "rationale": policy_decision.rationale,
                "policy_version": policy_decision.policy_version,
                "approval_required": policy_decision.approval_required
            }
        ))
        
        # Step 3: Handle policy verdicts
        if policy_decision.verdict == PolicyVerdict.DENY:
            trace.final_status = "DENIED"
            trace.evidence = {
                "policy_decision": policy_decision.verdict.value,
                "rationale": policy_decision.rationale
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_denial",
                outcome="denied",
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            return ExecutorResult(
                success=False,
                output={},
                error="DENIED",
                evidence={"policy_decision": policy_decision.verdict.value}
            ), trace
        
        if policy_decision.verdict in [PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER]:
            status = DispatchStatus.APPROVAL_PENDING if policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL else DispatchStatus.BLOCKED
            trace.final_status = status.value
            trace.evidence = {
                "policy_decision": policy_decision.verdict.value,
                "rationale": policy_decision.rationale,
                "approval_required": policy_decision.approval_required
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_deferral",
                outcome=status.value,
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version,
                    "approval_required": policy_decision.approval_required
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutionDispatch(
                intent_id=intent.intent_id,
                status=status,
                created_at=intent_timestamp,
                updated_at=intent_timestamp,
                details={"policy_decision": policy_decision.verdict.value}
            ), trace
        
        # Step 3: For ALLOW verdict, run safety gate evaluation
        if policy_decision.verdict == PolicyVerdict.ALLOW:
            safety_verdict = self._evaluate_safety_gate(intent)
            trace.events.append(TraceEvent(
                stage=TraceStage.SAFETY_EVALUATED,
                ok=safety_verdict.verdict == "allow",
                code=safety_verdict.verdict,
                details={
                    "safety_verdict": safety_verdict.verdict,
                    "rationale": safety_verdict.rationale,
                    "rule_ids": safety_verdict.rule_ids
                }
            ))
            
            if safety_verdict.verdict != "allow":
                trace.final_status = "SAFETY_BLOCKED"
                trace.evidence = {
                    "safety_verdict": safety_verdict.verdict,
                    "rationale": safety_verdict.rationale
                }
                
                self.audit_emitter.emit_audit_record(
                    intent_id=intent.intent_id,
                    event_type="safety_gate_block",
                    outcome="blocked",
                    details={
                        "safety_verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale,
                        "rule_ids": safety_verdict.rule_ids
                    },
                    tenant_id=intent.tenant_id,
                    cell_id=intent.cell_id,
                )
                
                return ExecutorResult(
                    success=False,
                    output={},
                    error="SAFETY_GATE_BLOCKED",
                    evidence={"safety_verdict": safety_verdict.verdict}
                ), trace
            
            # Step 4: Execute intent
            execution_result = self.executor.execute(intent)
            executor_capabilities = self.executor.capabilities() or {}
            trace.events.append(TraceEvent(
                stage=TraceStage.EXECUTOR_DISPATCHED,
                ok=execution_result.success,
                code="EXECUTED" if execution_result.success else "FAILED",
                details={
                    "executor_name": self.executor.name(),
                    "executor_capabilities": executor_capabilities,
                    "executor_version": executor_capabilities.get("version", "unknown") if isinstance(executor_capabilities, dict) else "unknown",
                    "execution_success": execution_result.success,
                    "execution_error": execution_result.error
                }
            ))
            
            # Step 5: Emit execution audit record
            trace.final_status = "EXECUTED" if execution_result.success else "FAILED"
            trace.evidence = {
                "executor_name": self.executor.name(),
                "execution_success": execution_result.success,
                "execution_error": execution_result.error
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="execution",
                outcome="success" if execution_result.success else "failed",
                details={
                    "execution_success": execution_result.success,
                    "executor_name": self.executor.name(),
                    "execution_error": execution_result.error
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return execution_result, trace
        
        # Default case
        trace.final_status = "FAILED"
        trace.evidence = {
            "policy_verdict": policy_decision.verdict.value,
            "error": "Unknown policy verdict"
        }
        
        return ExecutorResult(
            success=False,
            output={},
            error="UNKNOWN_POLICY_VERDICT",
            evidence={"policy_verdict": policy_decision.verdict.value}
        ), trace
        
        # Step 2: Policy evaluation
        policy_decision = self.pdp.evaluate(intent)
        trace.events.append(TraceEvent(
            stage=TraceStage.POLICY_EVALUATED,
            ok=policy_decision.verdict in [PolicyVerdict.ALLOW, PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER],
            code=policy_decision.verdict.value,
            details={
                "rationale": policy_decision.rationale,
                "policy_version": policy_decision.policy_version,
                "approval_required": policy_decision.approval_required
            }
        ))
        
        # Step 3: Handle policy verdicts
        if policy_decision.verdict == PolicyVerdict.DENY:
            trace.final_status = "DENIED"
            trace.evidence = {
                "policy_decision": policy_decision.verdict.value,
                "rationale": policy_decision.rationale
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_denial",
                outcome="denied",
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            return ExecutorResult(
                success=False,
                output={},
                error="DENIED",
                evidence={"policy_decision": policy_decision.verdict.value}
            ), trace
        
        if policy_decision.verdict in [PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER]:
            status = DispatchStatus.APPROVAL_PENDING if policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL else DispatchStatus.BLOCKED
            trace.final_status = status.value
            trace.evidence = {
                "policy_decision": policy_decision.verdict.value,
                "rationale": policy_decision.rationale,
                "approval_required": policy_decision.approval_required
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_deferral",
                outcome=status.value,
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version,
                    "approval_required": policy_decision.approval_required
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutionDispatch(
                intent_id=intent.intent_id,
                status=status,
                created_at=intent_timestamp,
                updated_at=intent_timestamp,
                details={"policy_decision": policy_decision.verdict.value}
            ), trace
        
        # Step 3: For ALLOW verdict, run safety gate evaluation
        if policy_decision.verdict == PolicyVerdict.ALLOW:
            safety_verdict = self._evaluate_safety_gate(intent)
            trace.events.append(TraceEvent(
                stage=TraceStage.SAFETY_EVALUATED,
                ok=safety_verdict.verdict == "allow",
                code=safety_verdict.verdict,
                details={
                    "safety_verdict": safety_verdict.verdict,
                    "rationale": safety_verdict.rationale,
                    "rule_ids": safety_verdict.rule_ids
                }
            ))
            
            if safety_verdict.verdict != "allow":
                trace.final_status = "SAFETY_BLOCKED"
                trace.evidence = {
                    "safety_verdict": safety_verdict.verdict,
                    "rationale": safety_verdict.rationale
                }
                
                self.audit_emitter.emit_audit_record(
                    intent_id=intent.intent_id,
                    event_type="safety_gate_block",
                    outcome="blocked",
                    details={
                        "safety_verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale,
                        "rule_ids": safety_verdict.rule_ids
                    },
                    tenant_id=intent.tenant_id,
                    cell_id=intent.cell_id,
                )
                return ExecutorResult(
                    success=False,
                    output={},
                    error="SAFETY_GATE_BLOCKED",
                    evidence={"safety_verdict": safety_verdict.verdict}
                ), trace
            
            # Step 4: Execute intent
            execution_result = self.executor.execute(intent)
            executor_capabilities = self.executor.capabilities() or {}
            trace.events.append(TraceEvent(
                stage=TraceStage.EXECUTOR_DISPATCHED,
                ok=execution_result.success,
                code="EXECUTED" if execution_result.success else "FAILED",
                details={
                    "executor_name": self.executor.name(),
                    "executor_capabilities": executor_capabilities,
                    "executor_version": executor_capabilities.get("version", "unknown") if isinstance(executor_capabilities, dict) else "unknown",
                    "execution_success": execution_result.success,
                    "execution_error": execution_result.error
                }
            ))
            
            # Step 5: Emit execution audit record
            trace.final_status = "EXECUTED" if execution_result.success else "FAILED"
            trace.evidence = {
                "executor_name": self.executor.name(),
                "execution_success": execution_result.success,
                "execution_error": execution_result.error
            }
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="execution",
                outcome="success" if execution_result.success else "failed",
                details={
                    "execution_success": execution_result.success,
                    "executor_name": self.executor.name(),
                    "execution_error": execution_result.error
                },
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return execution_result, trace
        
        # Default case
        trace.final_status = "FAILED"
        trace.evidence = {
            "policy_verdict": policy_decision.verdict.value,
            "error": "Unknown policy verdict"
        }
        
        return ExecutorResult(
            success=False,
            output={},
            error="UNKNOWN_POLICY_VERDICT",
            evidence={"policy_verdict": policy_decision.verdict.value}
        ), trace
    
    def check_approval_and_execute(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
        """Check approval status and execute if approved.
        
        This method can be called explicitly in tests to re-check approval status
        and proceed with execution if approved. No automatic polling or background checks.
        """
        logger.info(f"Checking approval status for intent {intent.intent_id}")
        
        # Initialize execution trace
        trace = ExecutionTrace(
            intent_id=intent.intent_id,
            events=[],
            final_status="",
            evidence={}
        )
        
        # Step 1: Intent received
        trace.events.append(TraceEvent(
            stage=TraceStage.INTENT_RECEIVED,
            ok=True,
            code="RECEIVED",
            details={"action_type": intent.action_type, "target": intent.target}
        ))
        
        # Step 2: Approval checked
        approval_status = self.pdp.approval_status(intent.intent_id)
        trace.events.append(TraceEvent(
            stage=TraceStage.APPROVAL_CHECKED,
            ok=approval_status in ["not_required", "approved"],
            code=approval_status.upper(),
            details={"approval_status": approval_status}
        ))
        
        if approval_status == "not_required":
            # No approval needed, proceed with normal execution
            result, execution_trace = self.execute_with_trace(intent)
            trace.events.extend(execution_trace.events)
            return result
        
        elif approval_status == "pending":
            # Still pending, return approval pending dispatch
            trace.final_status = "APPROVAL_PENDING"
            trace.evidence = {"approval_status": "pending"}
            
            return ExecutionDispatch(
                intent_id=intent.intent_id,
                status=DispatchStatus.APPROVAL_PENDING,
                created_at=intent.timestamp,
                updated_at=intent.timestamp,
                details={"approval_status": "pending"}
            ), trace
        
        elif approval_status == "denied":
            # Approval denied, return execution result with error
            trace.final_status = "APPROVAL_DENIED"
            trace.evidence = {"approval_status": "denied"}
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="approval_denied",
                outcome="denied",
                details={"approval_status": "denied"},
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
            )
            
            return ExecutorResult(
                success=False,
                output={},
                error="APPROVAL_DENIED",
                evidence={"approval_status": "denied"}
            ), trace
        
        elif approval_status == "approved":
            # Approval granted, proceed with execution
            logger.info(f"Approval granted for intent {intent.intent_id}, proceeding with execution")
            
            # Use approval bypass evaluation to proceed with execution
            from ..models.policy_decision import PolicyVerdict
            policy_decision = self.pdp.evaluate_with_approval_bypass(intent)
            
            if policy_decision.verdict == PolicyVerdict.ALLOW:
                # Proceed with safety gate and execution
                safety_verdict = self._evaluate_safety_gate(intent)
                trace.events.append(TraceEvent(
                    stage=TraceStage.SAFETY_EVALUATED,
                    ok=safety_verdict.verdict == "allow",
                    code=safety_verdict.verdict,
                    details={
                        "safety_verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale,
                        "rule_ids": safety_verdict.rule_ids
                    }
                ))
                
                if safety_verdict.verdict != "allow":
                    trace.final_status = "SAFETY_BLOCKED"
                    trace.evidence = {
                        "safety_verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale
                    }
                    
                    self.audit_emitter.emit_audit_record(
                        intent_id=intent.intent_id,
                        event_type="safety_gate_block",
                        outcome="blocked",
                        details={
                            "safety_verdict": safety_verdict.verdict,
                            "rationale": safety_verdict.rationale,
                            "rule_ids": safety_verdict.rule_ids
                        },
                        tenant_id=intent.tenant_id,
                        cell_id=intent.cell_id,
                    )
                    
                    return ExecutorResult(
                        success=False,
                        output={},
                        error="SAFETY_GATE_BLOCKED",
                        evidence={"safety_verdict": safety_verdict.verdict}
                    ), trace
                
                # Step 4: Execute intent
                execution_result = self.executor.execute(intent)
                executor_capabilities = self.executor.capabilities() or {}
                trace.events.append(TraceEvent(
                    stage=TraceStage.EXECUTOR_DISPATCHED,
                    ok=execution_result.success,
                    code="EXECUTED" if execution_result.success else "FAILED",
                    details={
                        "executor_name": self.executor.name(),
                        "executor_capabilities": executor_capabilities,
                        "executor_version": executor_capabilities.get("version", "unknown") if isinstance(executor_capabilities, dict) else "unknown",
                        "execution_success": execution_result.success,
                        "execution_error": execution_result.error
                    }
                ))
                
                # Step 5: Emit execution audit record
                trace.final_status = "EXECUTED" if execution_result.success else "FAILED"
                trace.evidence = {
                    "executor_name": self.executor.name(),
                    "execution_success": execution_result.success,
                    "execution_error": execution_result.error
                }
                
                self.audit_emitter.emit_audit_record(
                    intent_id=intent.intent_id,
                    event_type="execution",
                    outcome="success" if execution_result.success else "failed",
                    details={
                        "execution_success": execution_result.success,
                        "executor_name": self.executor.name(),
                        "execution_error": execution_result.error
                    },
                    tenant_id=intent.tenant_id,
                    cell_id=intent.cell_id,
                )
                
                return execution_result, trace
            else:
                # Something went wrong with the bypass
                trace.final_status = "FAILED"
                trace.evidence = {
                    "policy_verdict": policy_decision.verdict.value,
                    "error": "Approval bypass failed"
                }
                
                return ExecutorResult(
                    success=False,
                    output={},
                    error="APPROVAL_BYPASS_FAILED",
                    evidence={"policy_verdict": policy_decision.verdict.value}
                ), trace
        
        else:
            # Unknown status
            trace.final_status = "FAILED"
            trace.evidence = {
                "approval_status": approval_status,
                "error": "Unknown approval status"
            }
            
            return ExecutorResult(
                success=False,
                output={},
                error="UNKNOWN_APPROVAL_STATUS",
                evidence={"approval_status": approval_status}
            ), trace
    
    def _evaluate_safety_gate(self, intent: ActionIntent) -> SafetyVerdict:
        """Evaluate safety gate using V1 SafetyGate with minimal context."""
        # Create minimal V1 context for safety gate evaluation
        policy_state = PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        trust_state = TrustState(emitter_trust_score=1.0)
        environment_state = EnvironmentState(degraded_mode=False)
        
        # Create a minimal LocalDecisionV1 for compatibility
        # Note: In a real implementation, this would be properly constructed
        local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id=_deterministic_local_decision_id(intent),
            tenant_id=intent.tenant_id,
            cell_id=intent.cell_id,
            subject={
                "subject_type": "agent",
                "subject_id": intent.actor_id
            },
            classification="benign",
            severity="low",
            confidence=1.0,
            recommended_intents=[],
            evidence_refs={},
            correlation_id=intent.intent_id,
            trace_id=intent.intent_id
        )
        
        # Evaluate safety gate
        safety_verdict = self.safety_gate.evaluate_safety(
            intent=intent,  # Pass intent for V2 safety evaluation
            local_decision=local_decision,
            collective_state=None,  # Not used in minimal implementation
            policy_state=policy_state,
            trust_state=trust_state,
            environment_state=environment_state
        )
        
        return safety_verdict
