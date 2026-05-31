"""
Minimal execution boundary for FileSystemExecutor.

This module contains the minimal routing code needed to connect
Intent → Policy → Safety → Executor → Audit.
Extracted from execution_boundary_v2 before deletion.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from exoarmur.kernel.clock import utc_now
from exoarmur.kernel.ids import (
    make_decision_id,
    make_event_id,
    make_intent_id,
    make_trace_id,
)

# ============================================================================
# ACTION CLASS (moved from sdk/public_api.py)
# ============================================================================


class ActionClass(Enum):
    """Action classification for reversibility guarantees."""

    A0_OBSERVE = "A0_observe"
    A1_SOFT_CONTAINMENT = "A1_soft_containment"
    A2_HARD_CONTAINMENT = "A2_hard_containment"
    A3_IRREVERSIBLE = "A3_irreversible"

    def is_reversible(self) -> bool:
        """Check if action class supports rollback."""
        return self in (ActionClass.A0_OBSERVE, ActionClass.A1_SOFT_CONTAINMENT)

    def requires_approval(self) -> bool:
        """Check if action class requires explicit approval."""
        return self in (ActionClass.A2_HARD_CONTAINMENT, ActionClass.A3_IRREVERSIBLE)


# ============================================================================
# ACTION INTENT
# ============================================================================


class ActionIntent:
    """Canonical action intent envelope for execution governance."""

    def __init__(
        self,
        intent_id: str,
        actor_id: str,
        actor_type: str,
        action_type: str,
        target: str,
        parameters: Dict[str, Any],
        safety_context: Dict[str, Any],
        timestamp: datetime,
        tenant_id: str = "",
        cell_id: str = "",
    ):
        self.intent_id = intent_id
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.action_type = action_type
        self.target = target
        self.parameters = parameters
        self.safety_context = safety_context
        self.timestamp = timestamp
        self.tenant_id = tenant_id
        self.cell_id = cell_id

    @classmethod
    def create(
        cls,
        actor_id: str,
        actor_type: str,
        action_type: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        safety_context: Optional[Dict[str, Any]] = None,
        tenant_id: str = "",
        cell_id: str = "",
    ) -> "ActionIntent":
        """Create ActionIntent with deterministic ID and timestamp."""
        if parameters is None:
            parameters = {}
        if safety_context is None:
            safety_context = {}

        timestamp = utc_now()
        intent_id = make_intent_id(actor_id, action_type, target, None)

        return cls(
            intent_id=intent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action_type=action_type,
            target=target,
            parameters=parameters,
            safety_context=safety_context,
            timestamp=timestamp,
            tenant_id=tenant_id,
            cell_id=cell_id,
        )


# ============================================================================
# POLICY DECISION
# ============================================================================


class PolicyVerdict(Enum):
    """Policy verdict enumeration."""

    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    DEFER = "defer"
    ALLOW = "allow"


class PolicyDecision:
    """Policy decision result for intent evaluation."""

    def __init__(
        self,
        decision_id: str,
        verdict: PolicyVerdict,
        rationale: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        approval_required: bool = False,
        policy_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.decision_id = decision_id
        self.verdict = verdict
        self.rationale = rationale
        self.evidence = evidence or {}
        self.confidence = confidence
        self.approval_required = approval_required
        self.policy_version = policy_version
        self.metadata = metadata or {}

    @classmethod
    def create(
        cls,
        intent_id: str,
        verdict: PolicyVerdict,
        rationale: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        approval_required: bool = False,
        policy_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PolicyDecision":
        """Create PolicyDecision with deterministic ID."""
        if evidence is None:
            evidence = {}
        if metadata is None:
            metadata = {}

        decision_id = make_decision_id(intent_id, policy_version)

        return cls(
            decision_id=decision_id,
            verdict=verdict,
            rationale=rationale,
            evidence=evidence,
            confidence=confidence,
            approval_required=approval_required,
            policy_version=policy_version,
            metadata=metadata,
        )


# ============================================================================
# POLICY DECISION POINT INTERFACE
# ============================================================================


class ApprovalStatus(Enum):
    """Approval status enumeration."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class PolicyDecisionPoint(Protocol):
    """Interface for policy decision evaluation."""

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """Evaluate an intent against policy rules."""
        ...

    def approval_status(self, intent_id: str) -> ApprovalStatus:
        """Check approval status for a pending decision."""
        ...


# ============================================================================
# EXECUTOR PLUGIN INTERFACE
# ============================================================================


class ValidationResult(Enum):
    """Target validation result enumeration."""

    VALID = "valid"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"
    VIOLATES_CONSTRAINTS = "violates_constraints"


class ExecutorResult:
    """Result of an execution action with deterministic behavior."""

    def __init__(
        self,
        success: bool,
        output: Dict[str, Any],
        error: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.evidence = evidence or {}
        self.execution_id = execution_id


class ExecutorCapabilities:
    """Standardized executor capability declaration."""

    def __init__(
        self,
        executor_name: str,
        version: str,
        capabilities: List[str],
        constraints: Dict[str, Any],
        supported_targets: Optional[List[str]] = None,
        required_parameters: Optional[List[str]] = None,
    ):
        self.executor_name = executor_name
        self.version = version
        self.capabilities = capabilities
        self.constraints = constraints
        self.supported_targets = supported_targets or []
        self.required_parameters = required_parameters or []


class TargetValidationResult:
    """Result of target validation with evidence."""

    def __init__(
        self,
        result: ValidationResult,
        evidence: Dict[str, Any],
        validation_id: Optional[str] = None,
    ):
        self.result = result
        self.evidence = evidence
        self.validation_id = validation_id


class ExecutorPlugin(Protocol):
    """Interface for executor modules with sandboxing and capability enforcement."""

    def name(self) -> str:
        """Return the executor name."""
        ...

    def capabilities(self) -> Dict[str, Any]:
        """Return executor capabilities with enforcement metadata."""
        ...

    def validate_target(self, intent: ActionIntent) -> TargetValidationResult:
        """Validate target against executor capabilities and constraints."""
        ...

    def execute(
        self,
        intent: ActionIntent,
        policy_decision: Any,
        governance_context: Dict[str, Any],
    ) -> ExecutorResult:
        """Execute an action with proper authorization and deterministic behavior."""
        ...

    def supports_capability(self, capability: str) -> bool:
        """Check if executor supports a specific capability."""
        ...


# ============================================================================
# EXECUTION DISPATCH
# ============================================================================


class DispatchStatus(Enum):
    """Execution dispatch status enumeration."""

    SUBMITTED = "submitted"
    EVALUATING = "evaluating"
    BLOCKED = "blocked"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    EXECUTED = "executed"
    FAILED = "failed"


class ExecutionDispatch:
    """Execution dispatch tracking record."""

    def __init__(
        self,
        dispatch_id: Optional[str],
        intent_id: str,
        status: DispatchStatus,
        created_at: datetime,
        updated_at: datetime,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.dispatch_id = dispatch_id
        self.intent_id = intent_id
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.details = details

    @classmethod
    def create(
        cls,
        intent_id: str,
        status: DispatchStatus = DispatchStatus.SUBMITTED,
        details: Optional[Dict[str, Any]] = None,
    ) -> "ExecutionDispatch":
        """Create ExecutionDispatch with deterministic ID and timestamps."""
        from exoarmur.kernel.ids import make_dispatch_id

        dispatch_id = make_dispatch_id(intent_id)
        now = utc_now()

        return cls(
            dispatch_id=dispatch_id,
            intent_id=intent_id,
            status=status,
            created_at=now,
            updated_at=now,
            details=details,
        )


# ============================================================================
# EXECUTION TRACE
# ============================================================================


class TraceStage(str, Enum):
    """Execution trace stage enumeration."""

    INTENT_RECEIVED = "intent_received"
    POLICY_EVALUATED = "policy_evaluated"
    SAFETY_EVALUATED = "safety_evaluated"
    VERDICT_RESOLVED = "verdict_resolved"
    APPROVAL_CHECKED = "approval_checked"
    TARGET_VALIDATED = "target_validated"
    EXECUTOR_DISPATCHED = "executor_dispatched"
    COMPLETED = "completed"


class TraceEvent:
    """Single event in execution trace."""

    def __init__(
        self,
        event_id: str,
        stage: TraceStage,
        ok: bool,
        code: str,
        details: Dict[str, Any],
        timestamp: Optional[str] = None,
        sequence: int = 0,
        parent_event_id: Optional[str] = None,
        event_hash: Optional[str] = None,
    ):
        self.event_id = event_id
        self.stage = stage
        self.ok = ok
        self.code = code
        self.details = details
        self.timestamp = timestamp
        self.sequence = sequence
        self.parent_event_id = parent_event_id
        self.event_hash = event_hash

    @classmethod
    def create(
        cls,
        trace_id: str,
        stage: TraceStage,
        ok: bool,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        sequence: int = 0,
        parent_event_id: Optional[str] = None,
    ) -> "TraceEvent":
        """Create TraceEvent with deterministic ID."""
        if details is None:
            details = {}

        event_id = make_event_id(trace_id, stage.value, sequence)

        return cls(
            event_id=event_id,
            stage=stage,
            ok=ok,
            code=code,
            details=details,
            sequence=sequence,
            parent_event_id=parent_event_id,
            event_hash=None,
        )


class ExecutionTrace:
    """Execution trace with governance context."""

    def __init__(
        self,
        trace_id: str,
        intent_id: str,
        events: List[TraceEvent],
        final_verdict: str,
        governance_context: Dict[str, Any],
        audit_link: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.intent_id = intent_id
        self.events = events
        self.final_verdict = final_verdict
        self.governance_context = governance_context
        self.audit_link = audit_link

    @classmethod
    def create(cls, intent_id: str) -> "ExecutionTrace":
        """Create ExecutionTrace with deterministic ID."""
        trace_id = make_trace_id(intent_id)

        return cls(
            trace_id=trace_id,
            intent_id=intent_id,
            events=[],
            final_verdict="",
            governance_context={},
            audit_link=None,
        )


# ============================================================================
# SAFETY GATE
# ============================================================================


@dataclass
class SafetyVerdict:
    """Safety gate verdict with precedence ordering."""

    verdict: str  # "allow", "deny", "require_quorum", "require_human"
    rationale: str
    rule_ids: List[str]


@dataclass
class V2PolicyState:
    """Policy verification state for safety evaluation."""

    policy_verified: bool
    kill_switch_global: bool
    kill_switch_tenant: bool
    required_approval: str  # "none", "quorum", "human"


@dataclass
class V2TrustState:
    """Trust constraint state for safety evaluation."""

    emitter_trust_score: float


@dataclass
class V2EnvironmentState:
    """Environment state for safety evaluation."""

    degraded_mode: bool
    cell_load: float
    network_health: float
    resource_availability: float

    def __init__(
        self,
        degraded_mode: bool = False,
        cell_load: float = 0.5,
        network_health: float = 0.9,
        resource_availability: float = 0.8,
    ):
        self.degraded_mode = degraded_mode
        self.cell_load = cell_load
        self.network_health = network_health
        self.resource_availability = resource_availability


class SafetyGate:
    """Safety gate with deterministic verdict resolution."""

    def __init__(self):
        pass

    def evaluate_safety(
        self,
        intent: Optional[ActionIntent],
        policy_state: V2PolicyState,
        trust_state: V2TrustState,
        environment_state: V2EnvironmentState,
    ) -> SafetyVerdict:
        """Evaluate safety with deterministic verdict resolution."""
        # Check kill switches
        if policy_state.kill_switch_global or policy_state.kill_switch_tenant:
            return SafetyVerdict(
                verdict="deny",
                rationale="Kill switch engaged",
                rule_ids=["kill_switch"],
            )

        # Check degraded mode
        if environment_state.degraded_mode:
            return SafetyVerdict(
                verdict="require_human",
                rationale="System in degraded mode",
                rule_ids=["degraded_mode"],
            )

        # Check trust score
        if trust_state.emitter_trust_score < 0.5:
            return SafetyVerdict(
                verdict="deny",
                rationale=f"Insufficient trust score: {trust_state.emitter_trust_score}",
                rule_ids=["trust_threshold"],
            )

        # Check policy verification
        if not policy_state.policy_verified:
            return SafetyVerdict(
                verdict="deny",
                rationale="Policy not verified",
                rule_ids=["policy_verification"],
            )

        # Default to allow
        return SafetyVerdict(
            verdict="allow", rationale="All safety checks passed", rule_ids=[]
        )


# ============================================================================
# PROXY PIPELINE
# ============================================================================


class V2AuditEvent:
    """V2 audit event structure."""

    def __init__(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
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
    """V2 audit emitter."""

    def __init__(self, tenant_id: Optional[str] = None, cell_id: Optional[str] = None):
        self.audit_events: list[V2AuditEvent] = []
        self.tenant_id = tenant_id
        self.cell_id = cell_id

    def emit_audit_event(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str,
        cell_id: str,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> V2AuditEvent:
        """Emit a V2 audit event."""
        audit_event = V2AuditEvent(
            intent_id=intent_id,
            event_type=event_type,
            outcome=outcome,
            details=details,
            tenant_id=tenant_id,
            cell_id=cell_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        self.audit_events.append(audit_event)
        return audit_event


class ProxyPipeline:
    """Minimal proxy pipeline for execution governance."""

    def __init__(
        self,
        policy: PolicyDecisionPoint,
        safety_gate: SafetyGate,
        executor: ExecutorPlugin,
        audit_emitter: V2AuditEmitter,
    ):
        self.policy = policy
        self.safety_gate = safety_gate
        self.executor = executor
        self.audit_emitter = audit_emitter

    def execute_with_trace(
        self, intent: ActionIntent
    ) -> tuple[Union[ExecutorResult, ExecutionDispatch], ExecutionTrace]:
        """Execute intent through governance pipeline with trace."""
        trace = ExecutionTrace.create(intent.intent_id)

        # Stage 1: Intent received
        trace.events.append(
            TraceEvent.create(
                trace.trace_id,
                TraceStage.INTENT_RECEIVED,
                True,
                "received",
                {"intent_id": intent.intent_id},
            )
        )

        # Stage 2: Policy evaluation
        policy_decision = self.policy.evaluate(intent)
        trace.events.append(
            TraceEvent.create(
                trace.trace_id,
                TraceStage.POLICY_EVALUATED,
                True,
                "evaluated",
                {"verdict": policy_decision.verdict.value},
            )
        )

        # Stage 3: Safety evaluation
        policy_state = V2PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none",
        )
        trust_state = V2TrustState(emitter_trust_score=0.85)
        environment_state = V2EnvironmentState()

        safety_verdict = self.safety_gate.evaluate_safety(
            intent, policy_state, trust_state, environment_state
        )
        trace.events.append(
            TraceEvent.create(
                trace.trace_id,
                TraceStage.SAFETY_EVALUATED,
                True,
                "evaluated",
                {"verdict": safety_verdict.verdict},
            )
        )

        # Stage 4: Verdict resolution
        final_verdict = self._resolve_verdict(policy_decision, safety_verdict)
        trace.final_verdict = final_verdict
        trace.events.append(
            TraceEvent.create(
                trace.trace_id,
                TraceStage.VERDICT_RESOLVED,
                True,
                "resolved",
                {"final_verdict": final_verdict},
            )
        )

        # Stage 5: Target validation
        target_validation = self.executor.validate_target(intent)
        trace.events.append(
            TraceEvent.create(
                trace.trace_id,
                TraceStage.TARGET_VALIDATED,
                target_validation.result == ValidationResult.VALID,
                "validated",
                {"result": target_validation.result.value},
            )
        )

        # Stage 6: Executor dispatch
        if (
            final_verdict == "allow"
            and target_validation.result == ValidationResult.VALID
        ):
            governance_context = {
                "final_verdict": final_verdict,
                "policy_decision": policy_decision,
                "safety_verdict": safety_verdict,
            }

            executor_result = self.executor.execute(
                intent, policy_decision, governance_context
            )

            trace.events.append(
                TraceEvent.create(
                    trace.trace_id,
                    TraceStage.EXECUTOR_DISPATCHED,
                    executor_result.success,
                    "dispatched",
                    {"success": executor_result.success},
                )
            )

            # Emit audit event
            self.audit_emitter.emit_audit_event(
                intent_id=intent.intent_id,
                event_type="executor_dispatch",
                outcome="executed" if executor_result.success else "failed",
                details={"success": executor_result.success},
                tenant_id=intent.tenant_id,
                cell_id=intent.cell_id,
                trace_id=trace.trace_id,
            )

            trace.events.append(
                TraceEvent.create(
                    trace.trace_id,
                    TraceStage.COMPLETED,
                    executor_result.success,
                    "completed",
                    {"success": executor_result.success},
                )
            )

            return executor_result, trace
        else:
            # Create dispatch with blocked status
            dispatch = ExecutionDispatch.create(
                intent_id=intent.intent_id,
                status=DispatchStatus.BLOCKED,
                details={"final_verdict": final_verdict},
            )

            trace.events.append(
                TraceEvent.create(
                    trace.trace_id,
                    TraceStage.EXECUTOR_DISPATCHED,
                    False,
                    "blocked",
                    {"final_verdict": final_verdict},
                )
            )

            return dispatch, trace

    def _resolve_verdict(
        self, policy_decision: PolicyDecision, safety_verdict: SafetyVerdict
    ) -> str:
        """Resolve final verdict from policy and safety."""
        # Safety deny takes precedence
        if safety_verdict.verdict == "deny":
            return "deny"

        # Policy deny takes precedence
        if policy_decision.verdict == PolicyVerdict.DENY:
            return "deny"

        # Safety require_human
        if safety_verdict.verdict == "require_human":
            return "require_approval"

        # Policy require_approval
        if policy_decision.verdict == PolicyVerdict.REQUIRE_APPROVAL:
            return "require_approval"

        # Default to allow
        return "allow"
