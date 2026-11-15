"""
ExoArmur Core FastAPI service — deterministic governance and replayable audit layer for execution
Thin vertical slice: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

# Add contracts to path

# Import clock for deterministic time handling
from exoarmur.clock import utc_now

# Import contract models
from spec.contracts.models_v1 import TelemetryEventV1, AuditRecordV1

# Import ICW API
try:
    from identity_containment.icw_api import get_icw_api
except ImportError:
    # Fallback if ICW API not available
    def get_icw_api():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ICW API not initialized")

# Import API models
from exoarmur.api_models import TelemetryIngestResponseV1, AuditResponseV1, ErrorResponseV1, ApprovalActionRequestV1, ApprovalResponseV1, ApprovalStatusResponseV1

# Import internal modules
from exoarmur.perception.validator import TelemetryValidator
from exoarmur.analysis.facts_deriver import FactsDeriver
from exoarmur.decision.local_decider import LocalDecider
from exoarmur.beliefs.belief_generator import BeliefGenerator
from exoarmur.collective_confidence.aggregator import CollectiveConfidenceAggregator
from exoarmur.safety.safety_gate import SafetyGate
from exoarmur.safety.execution_gate import ExecutionGate
from exoarmur.execution.execution_kernel import ExecutionKernel
from exoarmur.audit.audit_logger import AuditLogger
from exoarmur.nats_client import ExoArmurNATSClient, NATSConfig
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.control_plane.intent_store import IntentStore
from exoarmur.auth.auth_service import (
    AuthService,
    AuthError,
    Permission,
    import_key_store_records,
)
from exoarmur.policy.operator_policy import (
    OperatorPolicy,
    OperatorPolicyDecisionPoint,
    load_operator_policy,
    PolicyUnavailableError,
    PolicyVerificationError,
)
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, TrustedSafetyContext
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# Global components (will be initialized on startup)
nats_client: Optional[ExoArmurNATSClient] = None
telemetry_validator: Optional[TelemetryValidator] = None
facts_deriver: Optional[FactsDeriver] = None
local_decider: Optional[LocalDecider] = None
belief_generator: Optional[BeliefGenerator] = None
collective_aggregator: Optional[CollectiveConfidenceAggregator] = None
safety_gate: Optional[SafetyGate] = None
execution_gate: Optional[ExecutionGate] = None
execution_kernel: Optional[ExecutionKernel] = None
audit_logger: Optional[AuditLogger] = None
approval_service: Optional[ApprovalService] = None
intent_store: Optional[IntentStore] = None
operator_policy: Optional[OperatorPolicy] = None
auth_service: Optional[AuthService] = None
background_tasks = set()  # Track background tasks for deterministic shutdown


def _load_api_key_store() -> AuthService:
    """Build the AuthService, loading operator-provisioned key records.

    EXOARMUR_API_KEY_STORE points to a JSON file of serialized APIKey
    records (hashes only — produced by the bootstrap procedure). Missing
    or unreadable store yields an empty key store: every authenticated
    request then fails explicitly. No default or test credentials exist.
    """
    service = AuthService()
    path = os.environ.get("EXOARMUR_API_KEY_STORE", "").strip()
    if not path:
        return service
    try:
        with open(path, "r", encoding="utf-8") as fh:
            records = json.load(fh)
        if not isinstance(records, list):
            raise ValueError("key store file must contain a JSON list")
        count = import_key_store_records(service.key_store, records)
        logger.info("Loaded %d API key records from %s", count, path)
    except (OSError, ValueError) as exc:
        logger.error("API key store %s unavailable; all requests will fail auth: %s", path, exc)
    return service


async def _authenticate(
    api_key: Optional[str],
    permission: Permission,
    tenant_id: str,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    """Authenticate and authorize a request; raises HTTPException on failure."""
    if auth_service is None:
        raise HTTPException(status_code=503, detail="Authentication service not initialized")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    try:
        auth_context = await auth_service.authenticate(api_key)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    try:
        return await auth_service.authorize(auth_context, permission, tenant_id)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


# V1 action class -> required execution permission for dispatch
_EXECUTE_PERMISSION_BY_CLASS = {
    "A0_observe": Permission.EXECUTE_A0,
    "A1_soft_containment": Permission.EXECUTE_A1,
    "A2_hard_containment": Permission.EXECUTE_A2,
    "A3_irreversible": Permission.EXECUTE_A3,
}


def _load_operator_policy() -> Optional[OperatorPolicy]:
    """Load the operator-approved policy, fail-closed.

    Requires both EXOARMUR_POLICY_FILE (operator-controlled path) and
    EXOARMUR_POLICY_SHA256 (independently pinned digest). Any missing or
    invalid input yields None — policy evaluation then denies by default.
    """
    path = os.environ.get("EXOARMUR_POLICY_FILE", "").strip()
    digest = os.environ.get("EXOARMUR_POLICY_SHA256", "").strip()
    if not path and not digest:
        return None
    try:
        return load_operator_policy(path, digest)
    except (PolicyUnavailableError, PolicyVerificationError) as exc:
        logger.error("Operator policy unavailable; execution policy denies by default: %s", exc)
        return None


class _ExecutionIntentRecorder:
    def __init__(self, kernel: ExecutionKernel, execution_intent):
        self._kernel = kernel
        self._execution_intent = execution_intent

    def name(self) -> str:
        return "execution-intent-recorder"

    def capabilities(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "actions": ["execution_intent.record"],
            "mode": "local_deterministic"
        }

    def execute(self, intent: ActionIntent) -> ExecutorResult:
        status = "duplicate"
        if self._execution_intent.idempotency_key not in self._kernel.executed_intents:
            self._kernel.executed_intents[self._execution_intent.idempotency_key] = self._execution_intent
            status = "recorded"

        return ExecutorResult(
            success=True,
            output={
                "intent_id": self._execution_intent.intent_id,
                "action_class": self._execution_intent.action_class,
                "status": status,
            },
            evidence={
                "side_effect": "execution_intent_recorded",
                "idempotency_key": self._execution_intent.idempotency_key,
            },
        )


class _BufferedPipelineAuditEmitter:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def emit_audit_record(
        self,
        intent_id: str,
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        tenant_id: str | None = None,
        cell_id: str | None = None,
    ):
        event = {
            "intent_id": intent_id,
            "event_type": event_type,
            "outcome": outcome,
            "details": details,
            "tenant_id": tenant_id,
            "cell_id": cell_id,
        }
        self.events.append(event)
        return event


def _deterministic_audit_retrieved_at(audit_records: List[AuditRecordV1]) -> datetime:
    if audit_records:
        return max(record.recorded_at for record in audit_records)
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _to_action_intent(execution_intent, actor_id: Optional[str] = None) -> ActionIntent:
    subject = execution_intent.subject or {}
    subject_id = str(subject.get("subject_id", execution_intent.intent_id))
    subject_type = str(subject.get("subject_type", "subject"))
    # actor_id is the authenticated principal when supplied; the telemetry
    # subject is monitored data, not caller identity.
    actor = actor_id if actor_id is not None else subject_id
    return ActionIntent(
        intent_id=execution_intent.intent_id,
        actor_id=actor,
        actor_type=subject_type,
        action_type=execution_intent.intent_type,
        target=f"exoarmur://execution-intent/{subject_id}",
        parameters=dict(execution_intent.parameters),
        safety_context=dict(execution_intent.safety_context),
        timestamp=execution_intent.requested_at,
        tenant_id=execution_intent.tenant_id,
        cell_id=execution_intent.cell_id,
    )


def _operator_trust_score() -> Optional[float]:
    """Explicitly configured operator trust score for the pilot deployment.

    This is configured trust for the deployment principal — not a measured
    score. Returns None when not configured; callers must treat that as
    unavailable and block execution rather than inventing a value.
    """
    raw = os.environ.get("EXOARMUR_OPERATOR_TRUST_SCORE")
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError:
        logger.error("EXOARMUR_OPERATOR_TRUST_SCORE is not a valid float: %r", raw)
        return None
    if not 0.0 <= value <= 1.0:
        logger.error("EXOARMUR_OPERATOR_TRUST_SCORE out of range [0,1]: %r", raw)
        return None
    return value


async def _execute_intent_via_proxy_pipeline(execution_intent, trusted_context: TrustedSafetyContext, actor_id: Optional[str] = None) -> bool:
    if execution_kernel is None or audit_logger is None:
        raise RuntimeError("Execution runtime is not initialized")

    pipeline_audit_emitter = _BufferedPipelineAuditEmitter()

    pipeline = ProxyPipeline(
        OperatorPolicyDecisionPoint(operator_policy),
        safety_gate if safety_gate is not None else SafetyGate(),
        _ExecutionIntentRecorder(execution_kernel, execution_intent),
        pipeline_audit_emitter,
        execution_gate=execution_gate if execution_gate is not None else ExecutionGate(nats_client=nats_client),
        trusted_safety_context=trusted_context,
    )
    result, _trace = await pipeline.execute_with_trace_async(_to_action_intent(execution_intent, actor_id=actor_id))

    for event in pipeline_audit_emitter.events:
        await audit_logger.emit_audit_record_async(
            event_kind=event["event_type"],
            payload_ref={
                "kind": "inline",
                "ref": {
                    "intent_id": event["intent_id"],
                    "outcome": event["outcome"],
                    "details": event["details"],
                },
            },
            correlation_id=execution_intent.correlation_id,
            trace_id=execution_intent.trace_id,
            tenant_id=execution_intent.tenant_id,
            cell_id=execution_intent.cell_id,
            idempotency_key=f"{execution_intent.idempotency_key}:{event['event_type']}:{event['outcome']}",
        )

    return getattr(result, "success", False)


def initialize_components(nats_client_instance: Optional[ExoArmurNATSClient] = None):
    """Initialize ExoArmur Core components"""
    global nats_client, telemetry_validator, facts_deriver, local_decider
    global belief_generator, collective_aggregator, safety_gate, execution_gate, execution_kernel, audit_logger, approval_service, intent_store
    global operator_policy, auth_service

    nats_client = nats_client_instance
    operator_policy = _load_operator_policy()
    auth_service = _load_api_key_store()
    
    # Initialize internal modules
    telemetry_validator = TelemetryValidator()
    facts_deriver = FactsDeriver()
    local_decider = LocalDecider()
    belief_generator = BeliefGenerator(nats_client)
    collective_aggregator = CollectiveConfidenceAggregator(nats_client)
    safety_gate = SafetyGate()
    execution_gate = ExecutionGate(nats_client)
    approval_service = ApprovalService()
    intent_store = IntentStore()
    execution_kernel = ExecutionKernel(nats_client, approval_service, intent_store)
    audit_logger = AuditLogger(nats_client)
    
    logger.info("ExoArmur Core components initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup components on app lifespan."""
    global nats_client, background_tasks
    logger.info("Starting ExoArmur Core service")

    # Initialize NATS client
    nats_config = NATSConfig(url=os.getenv("NATS_URL", "nats://localhost:4222"))
    nats_client_instance = ExoArmurNATSClient(nats_config)
    await nats_client_instance.connect()
    await nats_client_instance.ensure_streams()

    # Initialize components with NATS client
    initialize_components(nats_client_instance)

    # Start background consumers with tracking
    if collective_aggregator:
        task1 = asyncio.create_task(collective_aggregator.start_consumer())
        task1.add_done_callback(background_tasks.discard)
        background_tasks.add(task1)

    if audit_logger:
        task2 = asyncio.create_task(audit_logger.start_consumer())
        task2.add_done_callback(background_tasks.discard)
        background_tasks.add(task2)

    logger.info("ExoArmur Core service started successfully")

    try:
        yield
    finally:
        # Cancel all background tasks
        if background_tasks:
            logger.info(f"Cancelling {len(background_tasks)} background tasks")
            for task in background_tasks:
                task.cancel()

            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*background_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Background tasks did not complete within timeout")
            finally:
                background_tasks.clear()

        if nats_client:
            await nats_client.disconnect()

        logger.info("ExoArmur Core service stopped")


# Create FastAPI app
app = FastAPI(
    title="ExoArmur Core v1 API",
    description="Deterministic governance and replayable audit layer for execution",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check accessed")
    return {"status": "healthy", "service": "ExoArmur Core"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ExoArmur Core - Workflow 1 Implementation"}


@app.post("/v1/telemetry/ingest", response_model=TelemetryIngestResponseV1)
async def ingest_telemetry(
    event: TelemetryEventV1,
    x_api_key: Optional[str] = Header(default=None),
):
    """Ingest telemetry event and process through ADMO loop"""
    global telemetry_validator, facts_deriver, local_decider, belief_generator
    global collective_aggregator, safety_gate, execution_kernel, audit_logger

    # Initialize components if not already done (for testing)
    if telemetry_validator is None:
        initialize_components()

    # Authenticate the caller before any processing. The API key identifies
    # the authenticated principal; the telemetry subject_id is monitored
    # data and is never used as caller identity.
    auth_context = await _authenticate(
        x_api_key,
        Permission.EXECUTE_A0,
        event.tenant_id,
        correlation_id=event.correlation_id,
        trace_id=event.trace_id,
    )
    authenticated_principal_id = auth_context.principal_id

    try:
        logger.info(f"Ingesting telemetry event {event.event_id}")
        
        # Generate idempotency key for this processing
        idempotency_key = f"{event.event_id}:{event.correlation_id}"
        
        # Step 1: Perception - validate and normalize telemetry
        validated_event = telemetry_validator.validate_event(event)
        normalized_event = telemetry_validator.normalize_event(validated_event)
        
        # Audit: telemetry ingested
        audit_logger.emit_audit_record(
            event_kind="telemetry_ingested",
            payload_ref={"kind": "inline", "ref": event.model_dump()},
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
            tenant_id=event.tenant_id,
            cell_id=event.cell_id,
            idempotency_key=idempotency_key
        )
        
        # Step 2: Analysis - derive signal facts
        facts = facts_deriver.derive_facts(normalized_event)
        
        # Step 3: Decision - generate local decision
        local_decision = local_decider.decide(facts)
        
        # Step 4: Beliefs - generate and publish belief
        belief = belief_generator.generate_belief(local_decision)
        await belief_generator.publish_belief(belief)
        
        # Add belief to collective aggregator
        collective_aggregator.add_belief(belief)
        
        # Step 5: Collective confidence - compute collective state
        collective_state = collective_aggregator.compute_collective_state(belief)
        
        # Step 6: Safety - evaluate safety gate with arbitration.
        # Only authoritative sources are used: local_decision and
        # collective_state are produced above. Inputs with no source are
        # represented honestly rather than fabricated:
        #   - policy_verified: True only when a digest-verified operator
        #     policy is loaded; per-intent authorization is still enforced
        #     by OperatorPolicyDecisionPoint at dispatch.
        #   - trust: explicit operator configuration only
        #     (EXOARMUR_OPERATOR_TRUST_SCORE); unavailable -> blocked verdict.
        #   - degraded_mode=True: no degraded-mode monitoring exists, so the
        #     conservative value is assumed.
        #   - kill_switch_*: advisory for the V1 gate rules only; the
        #     authoritative check is ExecutionGate immediately before dispatch.
        from exoarmur.safety.safety_gate import PolicyState, TrustState, EnvironmentState, SafetyVerdict

        policy_state = PolicyState(
            policy_verified=operator_policy is not None,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )

        operator_trust = _operator_trust_score()
        if operator_trust is None:
            safety_verdict = SafetyVerdict(
                verdict="require_human",
                rationale=(
                    "Operator trust score is not configured "
                    "(EXOARMUR_OPERATOR_TRUST_SCORE); execution blocked"
                ),
                rule_ids=["SG-TRUST-UNAVAILABLE"],
            )
        else:
            trust_state = TrustState(emitter_trust_score=operator_trust)
            environment_state = EnvironmentState(degraded_mode=True)
            safety_verdict = safety_gate.evaluate_safety(
                intent=None,  # Will be created in execution step
                local_decision=local_decision,
                collective_state=collective_state,
                policy_state=policy_state,
                trust_state=trust_state,
                environment_state=environment_state
            )
        
        # Audit: safety gate evaluated
        audit_logger.emit_audit_record(
            event_kind="safety_gate_evaluated",
            payload_ref={"kind": "inline", "ref": {
                "verdict": safety_verdict.verdict,
                "rationale": safety_verdict.rationale,
                "rule_ids": safety_verdict.rule_ids
            }},
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
            tenant_id=event.tenant_id,
            cell_id=event.cell_id,
            idempotency_key=idempotency_key
        )
        
        # Step 7: Execution - create and execute intent if allowed
        execution_intent = None
        approval_id = None
        
        # Always create the candidate execution intent first
        execution_intent = execution_kernel.create_execution_intent(
            local_decision=local_decision,
            safety_verdict=safety_verdict,
            idempotency_identifier=idempotency_key
        )
        
        if safety_verdict.verdict == "allow":
            # Identity constraint: operator policy rules bind an authenticated
            # principal. The API key above supplies it; the telemetry
            # subject_id is data about the observed subject, not caller
            # identity, and is never used for policy matching.
            policy_rule = None
            if operator_policy is not None:
                policy_rule = operator_policy.matching_rule(
                    execution_intent.tenant_id,
                    authenticated_principal_id,
                    execution_intent.intent_type,
                )

            if policy_rule is None:
                audit_logger.emit_audit_record(
                    event_kind="execution_blocked",
                    payload_ref={"kind": "inline", "ref": {
                        "reason": "no_policy_rule_for_principal",
                        "verdict": safety_verdict.verdict,
                        "principal_id": authenticated_principal_id,
                    }},
                    correlation_id=event.correlation_id,
                    trace_id=event.trace_id,
                    tenant_id=event.tenant_id,
                    cell_id=event.cell_id,
                    idempotency_key=idempotency_key
                )
            else:
                # The resolved action class requires its specific execute
                # permission; a baseline ingest grant is not sufficient.
                resolved_class = policy_rule.resolve_action_class(execution_intent.intent_type)
                required_permission = _EXECUTE_PERMISSION_BY_CLASS.get(resolved_class)
                if required_permission is None or required_permission not in auth_context.permissions:
                    audit_logger.emit_audit_record(
                        event_kind="execution_blocked",
                        payload_ref={"kind": "inline", "ref": {
                            "reason": "missing_execute_permission",
                            "resolved_action_class": resolved_class,
                            "required_permission": required_permission.value if required_permission else None,
                            "principal_id": authenticated_principal_id,
                        }},
                        correlation_id=event.correlation_id,
                        trace_id=event.trace_id,
                        tenant_id=event.tenant_id,
                        cell_id=event.cell_id,
                        idempotency_key=idempotency_key
                    )
                else:
                    # Execute intent. The trusted safety context reuses the real
                    # upstream artifacts and the matched operator policy rule —
                    # never caller-supplied values.
                    trusted_context = TrustedSafetyContext(
                        local_decision=local_decision,
                        tenant_id=execution_intent.tenant_id,
                        actor_id=authenticated_principal_id,
                        trust_score=operator_trust,
                        collective_state=collective_state,
                        policy_verified=True,
                        kill_switch_global=policy_state.kill_switch_global,
                        kill_switch_tenant=policy_state.kill_switch_tenant,
                        required_approval=policy_rule.required_approval,
                        degraded_mode=environment_state.degraded_mode,
                        action_classes=dict(policy_rule.action_classes),
                        default_action_class=policy_rule.default_action_class,
                    )
                    executed = await _execute_intent_via_proxy_pipeline(
                        execution_intent, trusted_context, actor_id=authenticated_principal_id
                    )

                    # Audit: intent executed (only on actual executor success)
                    audit_logger.emit_audit_record(
                        event_kind="intent_executed" if executed else "execution_blocked",
                        payload_ref={"kind": "inline", "ref": {
                            "intent_id": execution_intent.intent_id,
                            "executed": executed,
                            "principal_id": authenticated_principal_id,
                        }},
                        correlation_id=event.correlation_id,
                        trace_id=event.trace_id,
                        tenant_id=event.tenant_id,
                        cell_id=event.cell_id,
                        idempotency_key=idempotency_key
                    )
        elif safety_verdict.verdict in ["require_human", "require_quorum"]:
            # Requesting an approval requires the approval:request permission
            if Permission.REQUEST_APPROVAL not in auth_context.permissions:
                audit_logger.emit_audit_record(
                    event_kind="execution_blocked",
                    payload_ref={"kind": "inline", "ref": {
                        "reason": "missing_approval_request_permission",
                        "verdict": safety_verdict.verdict,
                        "principal_id": authenticated_principal_id,
                    }},
                    correlation_id=event.correlation_id,
                    trace_id=event.trace_id,
                    tenant_id=event.tenant_id,
                    cell_id=event.cell_id,
                    idempotency_key=idempotency_key
                )
            else:
                # Create approval request and freeze intent
                approval_id = approval_service.create_request(
                    correlation_id=event.correlation_id,
                    trace_id=event.trace_id,
                    tenant_id=event.tenant_id,
                    cell_id=event.cell_id,
                    idempotency_key=idempotency_key,
                    requested_action_class=execution_intent.action_class,
                    payload_ref={"local_decision": local_decision.model_dump()}
                )
            
                # Compute intent hash and bind to approval
                intent_hash = intent_store.compute_intent_hash(execution_intent)
                approval_service.bind_intent(
                    approval_id, 
                    execution_intent.intent_id, 
                    execution_intent.idempotency_key, 
                    intent_hash
                )
            
                # Freeze the intent
                intent_store.freeze_intent(approval_id, execution_intent)
            
                # Audit: approval requested with intent binding
                audit_logger.emit_audit_record(
                    event_kind="approval_requested",
                    payload_ref={"kind": "inline", "ref": {
                        "approval_id": approval_id,
                        "intent_id": execution_intent.intent_id,
                        "intent_hash": intent_hash,
                        "verdict": safety_verdict.verdict,
                        "rationale": safety_verdict.rationale,
                        "principal_id": authenticated_principal_id
                    }},
                    correlation_id=event.correlation_id,
                    trace_id=event.trace_id,
                    tenant_id=event.tenant_id,
                    cell_id=event.cell_id,
                    idempotency_key=idempotency_key
                )
        else:
            # Audit: intent denied/escalated
            audit_logger.emit_audit_record(
                event_kind="intent_denied",
                payload_ref={"kind": "inline", "ref": {
                    "verdict": safety_verdict.verdict,
                    "rationale": safety_verdict.rationale
                }},
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                tenant_id=event.tenant_id,
                cell_id=event.cell_id,
                idempotency_key=idempotency_key
            )
        
        # Return response
        response = TelemetryIngestResponseV1(
            accepted=True,
            correlation_id=event.correlation_id,
            event_id=event.event_id,
            belief_id=belief.belief_id,
            processed_at=utc_now(),
            trace_id=event.trace_id,
            approval_id=approval_id,
            approval_status="PENDING" if approval_id else None,
            safety_verdict=safety_verdict.verdict if safety_verdict.verdict in ["require_human", "require_quorum"] else None
        )
        
        logger.info(f"Successfully processed telemetry event {event.event_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to process telemetry event {event.event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/audit/{correlation_id}", response_model=AuditResponseV1)
async def get_audit_records(correlation_id: str):
    """Get audit records for a correlation ID"""
    global audit_logger
    
    try:
        logger.info(f"Retrieving audit records for correlation {correlation_id}")
        
        audit_records = audit_logger.get_audit_records(correlation_id)
        
        # Convert AuditRecordV1 instances to dicts for serialization
        audit_records_dicts = [record.model_dump() for record in audit_records]
        
        response = AuditResponseV1(
            correlation_id=correlation_id,
            audit_records=audit_records_dicts,
            total_count=len(audit_records),
            retrieved_at=_deterministic_audit_retrieved_at(audit_records)
        )
        
        logger.info(f"Retrieved {len(audit_records)} audit records for correlation {correlation_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve audit records for correlation {correlation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _authorize_approval_action(
    approval_id: str,
    api_key: Optional[str],
    permission: Permission,
) -> tuple:
    """Authenticate and tenant-authorize an approval action.

    Returns (auth_context, approval_details). The approval's tenant comes
    from the stored request — never from caller-supplied fields.
    """
    details = approval_service.get_approval_details(approval_id)
    if not details:
        raise HTTPException(status_code=404, detail="Approval request not found")
    auth_context = await _authenticate(api_key, permission, details.tenant_id)
    return auth_context, details


@app.post("/v1/approvals/{approval_id}/approve", response_model=ApprovalResponseV1)
async def approve_approval(
    approval_id: str,
    request: ApprovalActionRequestV1,
    x_api_key: Optional[str] = Header(default=None),
):
    """Approve an approval request"""
    global approval_service

    try:
        auth_context, details = await _authorize_approval_action(
            approval_id, x_api_key, Permission.GRANT_APPROVAL
        )

        # The recorded approver is the authenticated principal; a
        # request-supplied operator_id that differs is impersonation.
        if request.operator_id != auth_context.principal_id:
            raise HTTPException(
                status_code=403,
                detail="operator_id does not match the authenticated principal",
            )

        logger.info(f"Approving request {approval_id} by operator {auth_context.principal_id}")

        # Approve the request
        status = approval_service.approve(approval_id, auth_context.principal_id)
        
        # Get approval details
        details = approval_service.get_approval_details(approval_id)
        if not details:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        response = ApprovalResponseV1(
            approval_id=approval_id,
            status=status,
            created_at=details.created_at
        )
        
        logger.info(f"Approved request {approval_id} with status {status}")
        return response
        
    except ValueError as e:
        logger.error(f"Failed to approve request {approval_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve request {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/approvals/{approval_id}/deny", response_model=ApprovalResponseV1)
async def deny_approval(
    approval_id: str,
    request: ApprovalActionRequestV1,
    x_api_key: Optional[str] = Header(default=None),
):
    """Deny an approval request"""
    global approval_service

    # Check if reason is provided for denial (outside try block to avoid catching HTTPException)
    if not request.reason or request.reason.strip() == "":
        raise HTTPException(status_code=422, detail="Reason is required for denial")

    try:
        auth_context, details = await _authorize_approval_action(
            approval_id, x_api_key, Permission.DENY_APPROVAL
        )

        # The recorded denier is the authenticated principal; a
        # request-supplied operator_id that differs is impersonation.
        if request.operator_id != auth_context.principal_id:
            raise HTTPException(
                status_code=403,
                detail="operator_id does not match the authenticated principal",
            )

        logger.info(f"Denying request {approval_id} by operator {auth_context.principal_id}")

        # Deny the request
        status = approval_service.deny(approval_id, auth_context.principal_id, request.reason)
        
        # Get approval details
        details = approval_service.get_approval_details(approval_id)
        if not details:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        response = ApprovalResponseV1(
            approval_id=approval_id,
            status=status,
            created_at=details.created_at
        )
        
        logger.info(f"Denied request {approval_id} with status {status}")
        return response

    except ValueError as e:
        logger.error(f"Failed to deny request {approval_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deny request {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/approvals/{approval_id}", response_model=ApprovalStatusResponseV1)
async def get_approval_status(
    approval_id: str,
    x_api_key: Optional[str] = Header(default=None),
):
    """Get approval status"""
    global approval_service

    try:
        await _authorize_approval_action(approval_id, x_api_key, Permission.VIEW_STATUS)
        logger.info(f"Retrieving approval status for {approval_id}")
        
        # Get approval details
        details = approval_service.get_approval_details(approval_id)
        if not details:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        response = ApprovalStatusResponseV1(
            approval_id=details.approval_id,
            status=details.status,
            created_at=details.created_at,
            requested_action_class=details.requested_action_class,
            correlation_id=details.correlation_id
        )
        
        logger.info(f"Retrieved approval status for {approval_id}: {details.status}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve approval status for {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ICW API Routes (V2 Feature-Flagged Endpoints)
@app.get("/api/v2/identity_containment/status")
async def get_containment_status(subject_id: str = Query(...), provider: str = Query(...)):
    """Get containment status for a subject"""
    try:
        icw_api = get_icw_api()
        return await icw_api.get_containment_status(subject_id, provider)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to get containment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/identity_containment/recommendations")
async def create_recommendation(request: Dict[str, Any]):
    """Create containment recommendation"""
    try:
        icw_api = get_icw_api()
        return await icw_api.create_recommendation(request)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to create recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/identity_containment/intents/from_recommendation")
async def create_intent_from_recommendation(request: Dict[str, Any]):
    """Create intent from recommendation"""
    try:
        icw_api = get_icw_api()
        return await icw_api.create_intent_from_recommendation(request)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to create intent from recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/identity_containment/intents/{intent_id}")
async def get_intent(intent_id: str):
    """Get intent details"""
    try:
        icw_api = get_icw_api()
        return await icw_api.get_intent(intent_id)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to get intent {intent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/identity_containment/tick")
async def tick():
    """Process expirations and revert expired containments"""
    try:
        icw_api = get_icw_api()
        return await icw_api.tick()
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to process tick: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/identity_containment/execute/{approval_id}")
async def execute_approval(approval_id: str):
    """Execute containment with approval"""
    try:
        icw_api = get_icw_api()
        return await icw_api.execute_approval(approval_id)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        logger.error(f"Failed to execute approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting ExoArmur FastAPI service")
    uvicorn.run(app, host=os.getenv("EXOARMUR_HOST", "127.0.0.1"), port=8000)