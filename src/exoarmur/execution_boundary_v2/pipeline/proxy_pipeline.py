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
    """Minimal proxy pipeline using V1 primitives for execution governance."""
    
    def __init__(
        self,
        pdp: PolicyDecisionPoint,
        safety_gate: SafetyGate,
        executor: ExecutorPlugin,
        audit_emitter: AuditEmitter
    ):
        """Initialize proxy pipeline with required components."""
        self.pdp = pdp
        self.safety_gate = safety_gate
        self.executor = executor
        self.audit_emitter = audit_emitter
        logger.info("ProxyPipeline initialized")
    
    def execute(self, intent: ActionIntent) -> Union[ExecutionResult, ExecutionDispatch]:
        """Execute intent through governance pipeline.
        
        Args:
            intent: ActionIntent to execute
            
        Returns:
            ExecutionResult for immediate outcomes or ExecutionDispatch for async flows
        """
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
            
            # Step 4: Execute action
            execution_result = self.executor.execute(intent)
            
            self.audit_emitter.emit_audit_record(
                intent_id=intent.intent_id,
                event_type="execution",
                outcome="success" if execution_result.success else "failed",
                details={
                    "executor_name": self.executor.name(),
                    "execution_success": execution_result.success,
                    "execution_error": execution_result.error
                }
            )
            
            return execution_result
        
        # Default fallback
        return ExecutionResult(
            success=False,
            output={},
            error="UNKNOWN_POLICY_VERDICT",
            evidence={"policy_verdict": policy_decision.verdict.value}
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
