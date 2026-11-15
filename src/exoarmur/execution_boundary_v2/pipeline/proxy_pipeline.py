"""
Proxy Pipeline for execution governance boundary.

Minimal orchestration using existing V1 primitives without modifying V1 behavior.
"""

import asyncio
import logging
import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Union, Tuple, Optional
import ulid

from ..interfaces.policy_decision_point import PolicyDecisionPoint
from ..interfaces.executor_plugin import ExecutorPlugin, ExecutorResult
from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision, PolicyVerdict
from ..models.execution_dispatch import ExecutionDispatch, DispatchStatus
from ..models.execution_trace import ExecutionTrace, TraceEvent, TraceStage

# Import V1 primitives for integration
from spec.contracts.models_v1 import AuditRecordV1, LocalDecisionV1, ExecutionIntentV1
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState
from exoarmur.safety.execution_gate import (
    ExecutionGate,
    ExecutionContext,
    ExecutionActionType,
    GateDecision,
    GateResult,
    DenialReason,
    get_execution_gate,
)
from exoarmur.collective_confidence.aggregator import CollectiveState

logger = logging.getLogger(__name__)


def _deterministic_timestamp() -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


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


# V1 action classes accepted by SafetyGate/ExecutionIntentV1. Anything else
# must fail closed rather than be silently treated as benign observation.
_V1_ACTION_CLASSES = frozenset(
    {"A0_observe", "A1_soft_containment", "A2_hard_containment", "A3_irreversible"}
)


def _deterministic_safety_intent_id(intent: ActionIntent) -> str:
    canonical = json.dumps(
        {
            "intent_id": intent.intent_id,
            "actor_id": intent.actor_id,
            "action_type": intent.action_type,
            "action_class": intent.safety_context.get("action_class"),
            "target": intent.target,
            "timestamp": intent.timestamp.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return str(ulid.ULID.from_bytes(digest[:16]))


# Shared daemon loop used only to bridge synchronous callers that invoke the
# pipeline from inside a running event loop. Async callers must use the
# *_async entry points so loop-bound resources (e.g. a NATS client and its
# kill-switch KV stores) are always awaited on their owning loop. One loop
# per process; no per-call or per-action threads are created.
_bridge_loop: Optional[asyncio.AbstractEventLoop] = None
_bridge_loop_lock = threading.Lock()


def _get_bridge_loop() -> asyncio.AbstractEventLoop:
    global _bridge_loop
    with _bridge_loop_lock:
        if _bridge_loop is not None and _bridge_loop.is_running():
            return _bridge_loop
        ready = threading.Event()

        def _run() -> None:
            global _bridge_loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _bridge_loop = loop
            ready.set()
            loop.run_forever()

        thread = threading.Thread(target=_run, daemon=True, name="proxy-pipeline-bridge")
        thread.start()
        ready.wait(timeout=5)
        if _bridge_loop is None:
            raise RuntimeError("Failed to start proxy pipeline bridge loop")
        return _bridge_loop


def _run_coroutine_sync(coro) -> Any:
    """Run a pipeline coroutine for synchronous callers.

    With no running event loop the coroutine executes directly via
    asyncio.run. Inside a running loop it is scheduled on the shared bridge
    loop; synchronous callers in async contexts should prefer the native
    async entry points instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return asyncio.run_coroutine_threadsafe(coro, _get_bridge_loop()).result(timeout=60)


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
            recorded_at=recorded_at or _deterministic_timestamp(),
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


@dataclass(frozen=True)
class TrustedSafetyContext:
    """Trusted SafetyGate evaluation inputs supplied by the hosting application.

    These values must come from the application's trusted decision/trust/
    collective sources or operator configuration — never from the
    ActionIntent itself. An agent's raw request cannot establish its own
    trust score, confidence, or action privilege.

    action_classes maps intent.action_type to a V1 action class; the "*"
    key acts as an operator-configured wildcard. default_action_class is an
    explicit operator fallback. Caller-supplied safety_context values are
    never consulted for classification.

    tenant_id/actor_id bind this context to a single tenant/principal: an
    intent whose tenant or actor does not match is rejected. trust_score is
    an explicitly configured operator trust value for that principal — not
    a measured score — and None means unavailable (execution blocks). A
    None degraded_mode is treated conservatively as degraded.
    """

    local_decision: LocalDecisionV1
    tenant_id: str
    actor_id: str
    trust_score: Optional[float]
    collective_state: CollectiveState
    policy_verified: bool
    kill_switch_global: bool
    kill_switch_tenant: bool
    required_approval: str
    degraded_mode: Optional[bool]
    action_classes: Dict[str, str]
    default_action_class: Optional[str] = None

    def __post_init__(self):
        if self.trust_score is not None and not 0.0 <= self.trust_score <= 1.0:
            raise ValueError(f"trust_score must be in [0.0, 1.0] or None, got {self.trust_score}")
        if self.required_approval not in ("none", "quorum", "human"):
            raise ValueError(f"required_approval must be none|quorum|human, got {self.required_approval!r}")
        mapped = list(self.action_classes.values())
        if self.default_action_class is not None:
            mapped.append(self.default_action_class)
        for action_class in mapped:
            if action_class not in _V1_ACTION_CLASSES:
                raise ValueError(f"Unsupported action_class {action_class!r} in trusted safety context")

    def resolve_action_class(self, action_type: str) -> Optional[str]:
        """Resolve the trusted V1 action class for an intent action_type."""
        return (
            self.action_classes.get(action_type)
            or self.action_classes.get("*")
            or self.default_action_class
        )


class ProxyPipeline:
    """Proxy execution pipeline that orchestrates policy, safety, and execution."""
    
    def __init__(
        self,
        pdp: PolicyDecisionPoint,
        safety_gate: SafetyGate,
        executor: ExecutorPlugin,
        audit_emitter: AuditEmitter,
        execution_gate: ExecutionGate = None,
        trusted_safety_context: Optional[TrustedSafetyContext] = None
    ):
        """Initialize the proxy pipeline with required components."""
        self.pdp = pdp
        self.safety_gate = safety_gate
        self.executor = executor
        self.audit_emitter = audit_emitter
        # Durable kill-switch enforcement; fail-closed by default
        self.execution_gate = execution_gate or get_execution_gate()
        # Trusted safety evaluation context; missing context fails closed
        self.trusted_safety_context = trusted_safety_context
        logger.info("ProxyPipeline initialized")
    
    def execute(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
        """Execute an intent through governance pipeline (backward compatibility)."""
        logger.info(f"Executing intent {intent.intent_id} through proxy pipeline (legacy method)")
        result, trace = self.execute_with_trace(intent)
        return result
    
    def execute_with_trace(self, intent: ActionIntent) -> Tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
        """Synchronous entry point (bridged; prefer execute_with_trace_async in async code)."""
        return _run_coroutine_sync(self._execute_with_trace_impl(intent))

    async def execute_with_trace_async(self, intent: ActionIntent) -> Tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
        """Native async entry point; kill-switch state is read on the caller's loop."""
        return await self._execute_with_trace_impl(intent)

    async def _execute_with_trace_impl(self, intent: ActionIntent) -> Tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
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
            
            # Step 3b: Kill-switch enforcement immediately before dispatch
            kill_switch_result = await self._enforce_kill_switch_async(intent)
            block_result, trace = self._record_kill_switch_check(intent, kill_switch_result, trace)
            if block_result is not None:
                return block_result, trace

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
        """Synchronous entry point (bridged; prefer check_approval_and_execute_async in async code)."""
        return _run_coroutine_sync(self._check_approval_and_execute_impl(intent))

    async def check_approval_and_execute_async(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
        """Native async entry point; kill-switch state is re-read on the caller's loop at dispatch."""
        return await self._check_approval_and_execute_impl(intent)

    async def _check_approval_and_execute_impl(self, intent: ActionIntent) -> Union[ExecutorResult, ExecutionDispatch]:
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
            result, execution_trace = await self._execute_with_trace_impl(intent)
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
                
                # Step 3b: Kill-switch enforcement immediately before dispatch
                kill_switch_result = await self._enforce_kill_switch_async(intent)
                block_result, trace = self._record_kill_switch_check(intent, kill_switch_result, trace)
                if block_result is not None:
                    return block_result, trace

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
    
    async def _enforce_kill_switch_async(self, intent: ActionIntent) -> Optional[GateResult]:
        """Check trusted global/tenant kill-switch state immediately before dispatch.

        Returns a denying GateResult when execution must be blocked, or None
        when both switches are explicitly inactive. Any failure to obtain a
        trustworthy state read is itself a denial (fail closed).
        """
        context = ExecutionContext(
            action_type=ExecutionActionType.PROXY_PIPELINE_EXECUTION,
            tenant_id=intent.tenant_id or None,
            correlation_id=intent.intent_id,
            trace_id=intent.intent_id,
            principal_id=intent.actor_id,
            additional_context={
                "action_type": intent.action_type,
                "target": intent.target,
            },
        )
        try:
            result = await self.execution_gate.evaluate_execution(context)
        except Exception as e:
            logger.error(f"Kill-switch evaluation failed for intent {intent.intent_id}: {e}")
            return GateResult(
                decision=GateDecision.DENY,
                reason=DenialReason.SYSTEM_ERROR,
                message=f"Kill-switch state could not be evaluated: {e}",
            )
        if result.decision == GateDecision.DENY:
            return result
        return None

    def _kill_switch_block_result(
        self,
        intent: ActionIntent,
        gate_result: GateResult,
        trace: ExecutionTrace,
    ) -> Tuple[ExecutorResult, ExecutionTrace]:
        """Record a kill-switch block in the trace and audit output."""
        reason = gate_result.reason.value if gate_result.reason else "unknown"
        trace.events.append(TraceEvent(
            stage=TraceStage.KILL_SWITCH_CHECKED,
            ok=False,
            code="DENY",
            details={
                "denial_reason": reason,
                "denial_message": gate_result.message,
            }
        ))
        trace.final_status = "KILL_SWITCH_BLOCKED"
        trace.evidence = {
            "denial_reason": reason,
            "denial_message": gate_result.message,
        }

        self.audit_emitter.emit_audit_record(
            intent_id=intent.intent_id,
            event_type="kill_switch_block",
            outcome="blocked",
            details={
                "denial_reason": reason,
                "denial_message": gate_result.message,
            },
            tenant_id=intent.tenant_id,
            cell_id=intent.cell_id,
        )

        return ExecutorResult(
            success=False,
            output={},
            error="KILL_SWITCH_BLOCKED",
            evidence={"denial_reason": reason}
        ), trace

    def _record_kill_switch_check(
        self,
        intent: ActionIntent,
        gate_result: Optional[GateResult],
        trace: ExecutionTrace,
    ) -> Tuple[Optional[ExecutorResult], ExecutionTrace]:
        """Record the kill-switch check outcome; return a block result on deny."""
        if gate_result is None:
            trace.events.append(TraceEvent(
                stage=TraceStage.KILL_SWITCH_CHECKED,
                ok=True,
                code="ALLOW",
                details={"denial_reason": None}
            ))
            return None, trace
        block_result, trace = self._kill_switch_block_result(intent, gate_result, trace)
        return block_result, trace

    def _evaluate_safety_gate(self, intent: ActionIntent) -> SafetyVerdict:
        """Evaluate the real SafetyGate with explicit trusted context.

        All evaluation inputs come from the TrustedSafetyContext supplied by
        the hosting application — never from the ActionIntent. Missing
        context, an unmapped action_type, or an unsupported resolved class
        all fail closed with an explicit deny verdict.
        """
        ctx = self.trusted_safety_context
        if ctx is None:
            return SafetyVerdict(
                verdict="deny",
                rationale=(
                    f"Intent {intent.intent_id} cannot be safety-evaluated: "
                    "no trusted safety context configured; failing closed"
                ),
                rule_ids=["SG-V2-NO-CONTEXT"],
            )

        # The trusted context is bound to a specific tenant/principal; an
        # intent for a different tenant or actor cannot use it.
        if intent.tenant_id != ctx.tenant_id or intent.actor_id != ctx.actor_id:
            return SafetyVerdict(
                verdict="deny",
                rationale=(
                    f"Intent {intent.intent_id} tenant/actor does not match the "
                    "trusted safety context binding; failing closed"
                ),
                rule_ids=["SG-V2-CONTEXT-MISMATCH"],
            )

        # Configured operator trust is required; unavailable trust blocks.
        if ctx.trust_score is None:
            return SafetyVerdict(
                verdict="deny",
                rationale=(
                    f"Intent {intent.intent_id} cannot be safety-evaluated: "
                    "operator trust score is not configured; failing closed"
                ),
                rule_ids=["SG-V2-TRUST-UNAVAILABLE"],
            )

        # Resolve the V1 action class from the operator-configured mapping.
        # The caller's safety_context is never consulted, so a request cannot
        # downgrade a destructive action by declaring A0_observe.
        action_class = ctx.resolve_action_class(intent.action_type)
        if action_class is None:
            return SafetyVerdict(
                verdict="deny",
                rationale=(
                    f"Intent {intent.intent_id} has no trusted action_class "
                    f"mapping for action_type {intent.action_type!r}; failing closed"
                ),
                rule_ids=["SG-V2-UNMAPPED"],
            )
        if action_class not in _V1_ACTION_CLASSES:
            return SafetyVerdict(
                verdict="deny",
                rationale=(
                    f"Intent {intent.intent_id} resolved to unsupported "
                    f"action_class {action_class!r}; failing closed"
                ),
                rule_ids=["SG-V2-UNSUPPORTED"],
            )

        policy_state = PolicyState(
            policy_verified=ctx.policy_verified,
            kill_switch_global=ctx.kill_switch_global,
            kill_switch_tenant=ctx.kill_switch_tenant,
            required_approval=ctx.required_approval
        )
        trust_state = TrustState(emitter_trust_score=ctx.trust_score)
        # No degraded-mode monitoring source exists; unavailable means
        # conservatively degraded.
        environment_state = EnvironmentState(
            degraded_mode=True if ctx.degraded_mode is None else ctx.degraded_mode
        )

        # Adapt the ActionIntent to the V1 ExecutionIntentV1 shape the
        # SafetyGate evaluates (intent_id + action_class). The V1 contract is
        # unchanged; this only constructs a compatible view of the intent.
        safety_intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id=_deterministic_safety_intent_id(intent),
            tenant_id=intent.tenant_id,
            cell_id=intent.cell_id,
            idempotency_key=intent.intent_id,
            subject={
                "subject_type": intent.actor_type,
                "subject_id": intent.actor_id,
            },
            intent_type=intent.action_type,
            action_class=action_class,
            requested_at=intent.timestamp,
            parameters=intent.parameters,
            policy_context={},
            safety_context=dict(intent.safety_context),
            correlation_id=intent.intent_id,
            trace_id=intent.intent_id,
        )

        # Evaluate safety gate
        safety_verdict = self.safety_gate.evaluate_safety(
            intent=safety_intent,
            local_decision=ctx.local_decision,
            collective_state=ctx.collective_state,
            policy_state=policy_state,
            trust_state=trust_state,
            environment_state=environment_state
        )

        return safety_verdict
