"""
ExoArmur Core FastAPI service — deterministic governance and replayable audit layer for execution
Thin vertical slice: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
import os
import asyncio
from exoarmur.clock import utc_now
from typing import Dict, Any, List, Optional
import uuid

# Add contracts to path

# Import clock for deterministic time handling
from exoarmur.clock import deterministic_timestamp
from exoarmur.stability.asyncio_policy import ensure_default_event_loop_policy

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
from exoarmur.execution.execution_kernel import ExecutionKernel
from exoarmur.audit.audit_logger import AuditLogger
from exoarmur.nats_client import ExoArmurNATSClient, NATSConfig
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.control_plane.intent_store import IntentStore
from exoarmur.feature_flags.resolver import (
    load_v2_core_types,
    load_v2_diagnostics,
    load_v2_entry_gate,
    load_v2_safety_models,
)

# Import V2 detection functions
from exoarmur.execution_boundary_v2.detection.execution_violation_detector import check_domain_logic_access, ViolationSeverity

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

ensure_default_event_loop_policy()

logger = logging.getLogger(__name__)

# Global components (will be initialized on startup)
nats_client: Optional[ExoArmurNATSClient] = None
telemetry_validator: Optional[TelemetryValidator] = None
facts_deriver: Optional[FactsDeriver] = None
local_decider: Optional[LocalDecider] = None
belief_generator: Optional[BeliefGenerator] = None
collective_aggregator: Optional[CollectiveConfidenceAggregator] = None
safety_gate: Optional[SafetyGate] = None
execution_kernel: Optional[ExecutionKernel] = None
audit_logger: Optional[AuditLogger] = None
approval_service: Optional[ApprovalService] = None
intent_store: Optional[IntentStore] = None
background_tasks = set()  # Track background tasks for deterministic shutdown


class _AllowPolicyDecisionPoint:
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale="allow_path_adapter",
            confidence=1.0,
            approval_required=False,
            policy_version="v1-ingest-adapter"
        )

    def approval_status(self, intent_id: str) -> str:
        return "not_required"


class _FixedSafetyGate:
    def __init__(self, safety_verdict):
        self._safety_verdict = safety_verdict

    def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
        return self._safety_verdict


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


def _to_action_intent(execution_intent) -> ActionIntent:
    subject = execution_intent.subject or {}
    subject_id = str(subject.get("subject_id", execution_intent.intent_id))
    subject_type = str(subject.get("subject_type", "subject"))
    return ActionIntent(
        intent_id=execution_intent.intent_id,
        actor_id=subject_id,
        actor_type=subject_type,
        action_type=execution_intent.intent_type,
        target=f"exoarmur://execution-intent/{subject_id}",
        parameters=dict(execution_intent.parameters),
        safety_context=dict(execution_intent.safety_context),
        timestamp=execution_intent.requested_at,
        tenant_id=execution_intent.tenant_id,
        cell_id=execution_intent.cell_id,
    )


async def _execute_intent_via_v2_entry_gate(execution_intent, safety_verdict) -> bool:
    """Execute intent through V2 Entry Gate - SINGLE MANDATORY ENTRY POINT"""
    if execution_kernel is None or audit_logger is None:
        raise RuntimeError("Execution runtime is not initialized")

    # Create V2 ExecutionRequest
    v2_entry_gate = load_v2_entry_gate()
    v2_core_types = load_v2_core_types()
    
    execution_request = v2_entry_gate.ExecutionRequest(
        module_id=v2_core_types.ModuleID(execution_intent.intent_id[:26]),  # Ensure 26 chars
        execution_context=v2_core_types.ModuleExecutionContext(
            execution_id=v2_core_types.ExecutionID(execution_intent.intent_id[:26]),
            module_id=v2_core_types.ModuleID(execution_intent.intent_id[:26]),
            module_version=v2_core_types.ModuleVersion(1, 0, 0),
            deterministic_seed=v2_core_types.DeterministicSeed(hash(execution_intent.intent_id) % (2**63)),
            logical_timestamp=int(utc_now().timestamp()),
            dependency_hash=execution_intent.correlation_id or "default"
        ),
        action_data={
            'action_class': execution_intent.action_class,
            'action_type': execution_intent.action_type,
            'subject': execution_intent.subject,
            'parameters': execution_intent.action_parameters,
            'safety_verdict': safety_verdict.verdict
        },
        correlation_id=execution_intent.correlation_id
    )

    # Execute through V2 Entry Gate - ONLY ALLOWED PATH
    result = v2_entry_gate.execute_module(execution_request)
    
    # Record execution in kernel for idempotency
    if result.success:
        execution_kernel.executed_intents[execution_intent.intent_id] = execution_intent
        logger.info(f"Intent executed via V2 Entry Gate: {execution_intent.intent_id}")
        return True
    else:
        logger.error(f"V2 Entry Gate execution failed: {result.error}")
        return False


def bootstrap_system_via_v2_entry_gate(nats_client_config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Bootstrap ExoArmur system through V2EntryGate.
    
    This is the ONLY legitimate path for system initialization.
    All component initialization happens through V2EntryGate governance.
    
    Args:
        nats_client_config: Optional NATS client configuration
        
    Returns:
        True if bootstrap successful, False otherwise
    """
        # Load V2 models through resolver
    v2_safety_models = load_v2_safety_models()
    ActionIntent = v2_safety_models.ActionIntent
    PolicyDecision = v2_safety_models.PolicyDecision
    PolicyVerdict = v2_safety_models.PolicyVerdict
    ExecutorResult = v2_safety_models.ExecutorResult
    from exoarmur.clock import utc_now
    import hashlib
    import ulid
    
    logger.info("Initiating system bootstrap through V2EntryGate")
    
    # Generate proper ULIDs for bootstrap
    bootstrap_ulid = str(ulid.ULID())
    execution_ulid = str(ulid.ULID())
    
    # Create bootstrap execution request
    bootstrap_request = ExecutionRequest(
        module_id=ModuleID(bootstrap_ulid),
        execution_context=ModuleExecutionContext(
            execution_id=ExecutionID(execution_ulid),
            module_id=ModuleID(bootstrap_ulid),
            module_version=ModuleVersion(1, 0, 0),
            deterministic_seed=DeterministicSeed(hash("system_bootstrap") % (2**63)),
            logical_timestamp=int(utc_now().timestamp()),
            dependency_hash="system_bootstrap"
        ),
        action_data={
            'intent_type': 'SYSTEM_BOOTSTRAP',
            'action_class': 'system_operation',
            'action_type': 'bootstrap',
            'subject': 'exosystem',
            'parameters': {
                'nats_client_config': nats_client_config
            }
        },
        correlation_id="system_bootstrap"
    )
    
    # Execute bootstrap through V2EntryGate
    try:
        result = execute_module(bootstrap_request)
        
        if result.success:
            logger.info("System bootstrap completed successfully through V2EntryGate")
            logger.info(f"Bootstrap result: {result.result_data}")
            return True
        else:
            logger.error(f"System bootstrap failed: {result.result_data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"System bootstrap exception: {e}")
        return False


def initialize_components(nats_client_instance: Optional[ExoArmurNATSClient] = None):
    """
    [DEPRECATED] Initialize ExoArmur Core components
    
    CRITICAL: This function is a VIOLATION of V2 governance boundaries.
    Direct component instantiation bypasses V2EntryGate enforcement.
    
    This function is blocked to prevent unauthorized domain logic access.
    All component initialization MUST occur through V2EntryGate.
    
    For system startup: Use the FastAPI lifespan() function (already V2-compliant)
    For testing: Use V2EntryGate.execute_module() with proper ExecutionRequest
    For CLI: Commands must route through V2EntryGate, not call this directly
    """
        # Load V2 components through resolver
    v2_entry_gate = load_v2_entry_gate()
    v2_core_types = load_v2_core_types()
    
    execute_module = v2_entry_gate.execute_module
    ExecutionRequest = v2_entry_gate.ExecutionRequest
    ModuleID = v2_core_types.ModuleID
    ExecutionID = v2_core_types.ExecutionID
    DeterministicSeed = v2_core_types.DeterministicSeed
    ModuleExecutionContext = v2_core_types.ModuleExecutionContext
    ModuleVersion = v2_core_types.ModuleVersion
    
    # DETECTION: Log violation attempt
    check_domain_logic_access("main", "initialize_components", ViolationSeverity.CRITICAL)
    
    # ENFORCEMENT: Block direct component instantiation
    raise RuntimeError(
        "VIOLATION: initialize_components() bypasses V2EntryGate governance.\n"
        "This function has been eliminated to prevent unauthorized domain logic access.\n"
        "\n"
        "SOLUTION:\n"
        "• For system startup: Use FastAPI lifespan() (V2-compliant)\n"
        "• For domain logic: Route through V2EntryGate.execute_module()\n"
        "• For testing: Use V2EntryGate for component access\n"
        "• For CLI: Commands must use V2EntryGate, not direct initialization\n"
        "\n"
        "All domain logic MUST pass through V2EntryGate. No exceptions."
    )


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

    # Initialize components with NATS client (V2 bootstrap through V2EntryGate)
    nats_config_dict = {
        'url': nats_config.url
    }
    
    # Bootstrap system through V2EntryGate
    bootstrap_success = bootstrap_system_via_v2_entry_gate(nats_config_dict)
    if not bootstrap_success:
        raise RuntimeError("System bootstrap failed through V2EntryGate")

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
    """Health check endpoint - READ-ONLY (No V2 routing required)"""
    logger.info("Health check accessed")
    return {"status": "healthy", "service": "ExoArmur Core"}


@app.get("/")
async def root():
    """Root endpoint - READ-ONLY (No V2 routing required)"""
    return {"message": "ExoArmur Core - deterministic governance runtime"}


@app.post("/v1/telemetry/ingest", response_model=TelemetryIngestResponseV1)
async def ingest_telemetry(event: TelemetryEventV1):
    """Ingest telemetry event into the governed decision and audit pipeline"""
    global telemetry_validator, facts_deriver, local_decider, belief_generator
    global collective_aggregator, safety_gate, execution_kernel, audit_logger
    
    # Initialize components if not already done (V2 bootstrap through V2EntryGate)
    if telemetry_validator is None:
        bootstrap_success = bootstrap_system_via_v2_entry_gate()
        if not bootstrap_success:
            raise RuntimeError("System bootstrap failed during telemetry ingestion")
    
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
        
        # Step 6: Safety - evaluate safety gate with arbitration
        from exoarmur.safety.safety_gate import PolicyState, TrustState, EnvironmentState
        from exoarmur.safety.policy_evaluator import PolicyEvaluator
        from exoarmur.safety.trust_evaluator import TrustEvaluator
        from exoarmur.safety.environment_monitor import EnvironmentMonitor
        
        # Initialize policy evaluator
        policy_evaluator = PolicyEvaluator()
        
        # Evaluate policy state with safe fallback to preserve current behavior
        policy_state = policy_evaluator.evaluate_policy(
            intent=None,  # Will be created in execution step
            tenant_id=event.tenant_id,
            cell_id=event.cell_id
        )
        
        # Evaluate trust state with safe fallback to preserve current behavior
        trust_evaluator = TrustEvaluator()
        trust_score = trust_evaluator.evaluate_trust(
            event_source=event.source,
            emitter_id=event.source.get("sensor_id"),
            tenant_id=event.tenant_id
        )
        trust_state = TrustState(emitter_trust_score=trust_score)
        
        # Monitor environment state for observational purposes only
        environment_monitor = EnvironmentMonitor()
        environment_observation = environment_monitor.monitor_environment(
            tenant_id=event.tenant_id,
            cell_id=event.cell_id,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id
        )
        
        # Extract degraded mode state (observational only - never influences decisions)
        degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
        environment_state = EnvironmentState(degraded_mode=degraded_mode)
        
        # Emit environment telemetry for observability (strictly observational)
        from exoarmur.safety.environment_monitor import EnvironmentMonitoringContext
        monitoring_context = EnvironmentMonitoringContext(
            tenant_id=event.tenant_id,
            cell_id=event.cell_id,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
            timestamp=None
        )
        environment_monitor.emit_environment_telemetry(environment_observation, monitoring_context)
        
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
            # Execute intent through V2 Entry Gate - SINGLE MANDATORY PATH
            await _execute_intent_via_v2_entry_gate(execution_intent, safety_verdict)
            
            # Audit: intent executed
            audit_logger.emit_audit_record(
                event_kind="intent_executed",
                payload_ref={"kind": "inline", "ref": execution_intent.model_dump()},
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                tenant_id=event.tenant_id,
                cell_id=event.cell_id,
                idempotency_key=idempotency_key
            )
        elif safety_verdict.verdict in ["require_human", "require_quorum"]:
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
                    "rationale": safety_verdict.rationale
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
            processed_at=deterministic_timestamp(
                event.event_id,
                event.correlation_id,
                event.trace_id,
                belief.belief_id,
                safety_verdict.verdict,
                approval_id,
                "processed_at",
            ),
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
    """Get audit records for a correlation ID - READ-ONLY (No V2 routing required)"""
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


@app.post("/v1/approvals/{approval_id}/approve", response_model=ApprovalResponseV1)
async def approve_approval(approval_id: str, request: ApprovalActionRequestV1):
    """Approve an approval request"""
    global approval_service
    
    try:
        logger.info(f"Approving request {approval_id} by operator {request.operator_id}")
        
        # Approve the request
        status = approval_service.approve(approval_id, request.operator_id)
        
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
    except Exception as e:
        logger.error(f"Failed to approve request {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/approvals/{approval_id}/deny", response_model=ApprovalResponseV1)
async def deny_approval(approval_id: str, request: ApprovalActionRequestV1):
    """Deny an approval request"""
    global approval_service
    
    # Check if reason is provided for denial (outside try block to avoid catching HTTPException)
    if not request.reason or request.reason.strip() == "":
        raise HTTPException(status_code=422, detail="Reason is required for denial")
    
    try:
        logger.info(f"Denying request {approval_id} by operator {request.operator_id}")
        
        # Deny the request
        status = approval_service.deny(approval_id, request.operator_id, request.reason)
        
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
    except Exception as e:
        logger.error(f"Failed to deny request {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/approvals/{approval_id}", response_model=ApprovalStatusResponseV1)
async def get_approval_status(approval_id: str):
    """Get approval status"""
    global approval_service
    
    try:
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
    import sys
    
    # Handle help/usage commands without starting server
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("ExoArmur Core FastAPI service")
        print("Usage: python -m exoarmur.main [options]")
        print("Options:")
        print("  --help, -h    Show this help message")
        print("  --version     Show version information")
        print("")
        print("Environment variables:")
        print("  EXOARMUR_HOST    Host to bind to (default: 127.0.0.1)")
        print("  EXOARMUR_PORT    Port to bind to (default: 8000)")
        sys.exit(0)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print("ExoArmur Core v2.0.0")
        sys.exit(0)
    
    logger.info("Starting ExoArmur FastAPI service")
    uvicorn.run(app, host=os.getenv("EXOARMUR_HOST", "127.0.0.1"), port=int(os.getenv("EXOARMUR_PORT", "8000")))