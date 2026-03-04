"""
Proxy Pipeline for execution governance boundary.

Minimal orchestration using existing V1 primitives without modifying V1 behavior.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Union

from ..interfaces.policy_decision_point import PolicyDecisionPoint
from ..interfaces.executor_plugin import ExecutorPlugin, ExecutionResult
from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision, PolicyVerdict
from ..models.execution_dispatch import ExecutionDispatch, DispatchStatus

# Import V1 primitives for integration
from spec.contracts.models_v1 import AuditRecordV1, LocalDecisionV1
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState

logger = logging.getLogger(__name__)


class AuditEmitter:
    """Minimal adapter for emitting V1 audit records from V2 pipeline."""
    
    def __init__(self):
        self.audit_records: list[AuditRecordV1] = []
    
    def emit_audit_record(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any]
    ) -> AuditRecordV1:
        """Create and emit a V1 audit record."""
        # Generate placeholder ULID for audit_id (will be deterministic in later phases)
        audit_id = "01H2X6VZB5Z2Z2Z2Z2Z2Z2Z2Z2"
        
        audit_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id=audit_id,
            tenant_id="test-tenant",  # Placeholder
            cell_id="test-cell",  # Placeholder
            idempotency_key=f"audit-{intent_id}",
            recorded_at=datetime.now(timezone.utc),
            event_kind=event_type,
            payload_ref={
                "kind": "inline",
                "ref": intent_id,
                "outcome": outcome,
                "details": details
            },
            hashes={
                "sha256": "placeholder-hash"
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
    
    def execute(self, intent: ActionIntent) -> Union[ExecutionResult, ExecutionDispatch]:
        """Execute an intent through the governance pipeline."""
        logger.info(f"Executing intent {intent.intent_id} through proxy pipeline")
        
        # Step 1: Policy evaluation
        policy_decision = self.pdp.evaluate(intent)
        
        # Step 2: Handle policy verdicts
        if policy_decision.verdict == PolicyVerdict.DENY:
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_denial",
                outcome="denied",
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version
                }
            )
            return ExecutionResult(
                success=False,
                output={},
                error="DENIED",
                evidence={"policy_decision": policy_decision.verdict.value}
            )
        
        if policy_decision.verdict in [PolicyVerdict.REQUIRE_APPROVAL, PolicyVerdict.DEFER]:
            status = DispatchStatus.APPROVAL_PENDING if policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL else DispatchStatus.BLOCKED
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="policy_deferral",
                outcome=status.value,
                details={
                    "rationale": policy_decision.rationale,
                    "policy_version": policy_decision.policy_version,
                    "approval_required": policy_decision.approval_required
                }
            )
            
            return ExecutionDispatch(
                intent_id=intent.intent_id,
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                details={"policy_decision": policy_decision.verdict.value}
            )
        
        # Step 3: For ALLOW verdict, run safety gate evaluation
        if policy_decision.verdict == PolicyVerdict.ALLOW:
            safety_verdict = self._evaluate_safety_gate(intent)
            
            if safety_verdict.verdict != "allow":
                self.audit_emitter.emit_audit_record(
                    intent_id=intent.intent_id,
                    event_type="safety_gate_block",
                    outcome="blocked",
                    details={
                        "safety_verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale,
                        "rule_ids": safety_verdict.rule_ids
                    }
                )
                
                return ExecutionResult(
                    success=False,
                    output={},
                    error="SAFETY_GATE_BLOCKED",
                    evidence={"safety_verdict": safety_verdict.verdict}
                )
            
            # Step 4: Execute the intent
            execution_result = self.executor.execute(intent)
            
            # Step 5: Emit execution audit record
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="execution",
                outcome="success" if execution_result.success else "failed",
                details={
                    "execution_success": execution_result.success,
                    "executor_name": self.executor.name(),
                    "execution_error": execution_result.error
                }
            )
            
            return execution_result
        
        # Default case
        return ExecutionResult(
            success=False,
            output={},
            error="UNKNOWN_POLICY_VERDICT",
            evidence={"policy_verdict": policy_decision.verdict.value}
        )
    
    def check_approval_and_execute(self, intent: ActionIntent) -> Union[ExecutionResult, ExecutionDispatch]:
        """Check approval status and execute if approved.
        
        This method can be called explicitly in tests to re-check approval status
        and proceed with execution if approved. No automatic polling or background checks.
        """
        logger.info(f"Checking approval status for intent {intent.intent_id}")
        
        # Check approval status
        approval_status = self.pdp.approval_status(intent.intent_id)
        
        if approval_status == "not_required":
            # No approval needed, proceed with normal execution
            return self.execute(intent)
        
        elif approval_status == "pending":
            # Still pending, return approval pending dispatch
            return ExecutionDispatch(
                intent_id=intent.intent_id,
                status=DispatchStatus.APPROVAL_PENDING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                details={"approval_status": "pending"}
            )
        
        elif approval_status == "denied":
            # Approval denied, return execution result with error
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="approval_denied",
                outcome="denied",
                details={"approval_status": "denied"}
            )
            return ExecutionResult(
                success=False,
                output={},
                error="APPROVAL_DENIED",
                evidence={"approval_status": "denied"}
            )
        
        elif approval_status == "approved":
            # Approval granted, proceed with execution
            logger.info(f"Approval granted for intent {intent.intent_id}, proceeding with execution")
            
            # Use approval bypass evaluation to proceed with execution
            from ..models.policy_decision import PolicyVerdict
            policy_decision = self.pdp.evaluate_with_approval_bypass(intent)
            
            if policy_decision.verdict == PolicyVerdict.ALLOW:
                # Proceed with safety gate and execution
                safety_verdict = self._evaluate_safety_gate(intent)
                
                if safety_verdict.verdict != "allow":
                    self.audit_emitter.emit_audit_record(
                        intent_id=intent.intent_id,
                        event_type="safety_gate_block",
                        outcome="blocked",
                        details={
                            "safety_verdict": safety_verdict.verdict,
                            "rationale": safety_verdict.rationale,
                            "rule_ids": safety_verdict.rule_ids
                        }
                    )
                    return ExecutionResult(
                        success=False,
                        output={},
                        error="SAFETY_GATE_BLOCKED",
                        evidence={"safety_verdict": safety_verdict.verdict}
                    )
                
                # Execute the intent
                execution_result = self.executor.execute(intent)
                
                # Emit execution audit record
                self.audit_emitter.emit_audit_record(
                    intent_id=intent.intent_id,
                    event_type="execution",
                    outcome="success" if execution_result.success else "failed",
                    details={
                        "execution_success": execution_result.success,
                        "executor_name": self.executor.name(),
                        "execution_error": execution_result.error,
                        "approval_bypassed": True
                    }
                )
                
                return execution_result
            else:
                # Something went wrong with the bypass
                return ExecutionResult(
                    success=False,
                    output={},
                    error="APPROVAL_BYPASS_FAILED",
                    evidence={"policy_verdict": policy_decision.verdict.value}
                )
        
        else:
            # Unknown status
            return ExecutionResult(
                success=False,
                output={},
                error="UNKNOWN_APPROVAL_STATUS",
                evidence={"approval_status": approval_status}
            )
    
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
            decision_id="01H2X6VZB5Z2Z2Z2Z2Z2Z2Z2Z2",  # Placeholder ULID
            tenant_id="test-tenant",
            cell_id="test-cell",
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
            intent=None,  # No V1 intent available in V2 context
            local_decision=local_decision,
            collective_state=None,  # Not used in minimal implementation
            policy_state=policy_state,
            trust_state=trust_state,
            environment_state=environment_state
        )
        
        return safety_verdict
