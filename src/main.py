"""
ExoArmur FastAPI Service - Workflow 1 Implementation
Thin vertical slice: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import logging
import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

# Add contracts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

# Import clock for deterministic time handling
sys.path.append(os.path.join(os.path.dirname(__file__)))
from clock import utc_now

# Import contract models
from models_v1 import TelemetryEventV1, AuditRecordV1

# Import ICW API
try:
    from identity_containment.icw_api import get_icw_api
except ImportError:
    # Fallback if ICW API not available
    def get_icw_api():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ICW API not initialized")

# Import API models
from api_models import TelemetryIngestResponseV1, AuditResponseV1, ErrorResponseV1, ApprovalActionRequestV1, ApprovalResponseV1, ApprovalStatusResponseV1

# Import internal modules
from perception.validator import TelemetryValidator
from analysis.facts_deriver import FactsDeriver
from decision.local_decider import LocalDecider
from beliefs.belief_generator import BeliefGenerator
from collective_confidence.aggregator import CollectiveConfidenceAggregator
from safety.safety_gate import SafetyGate
from execution.execution_kernel import ExecutionKernel
from audit.audit_logger import AuditLogger
from nats_client import ExoArmurNATSClient, NATSConfig
from control_plane.approval_service import ApprovalService
from control_plane.intent_store import IntentStore

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ExoArmur ADMO v1 API",
    description="Autonomous Defense Mesh Organism v1 - Thin Vertical Slice API",
    version="1.0.0"
)

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


def initialize_components(nats_client_instance: Optional[ExoArmurNATSClient] = None):
    """Initialize ADMO components"""
    global nats_client, telemetry_validator, facts_deriver, local_decider
    global belief_generator, collective_aggregator, safety_gate, execution_kernel, audit_logger, approval_service, intent_store
    
    nats_client = nats_client_instance
    
    # Initialize internal modules
    telemetry_validator = TelemetryValidator()
    facts_deriver = FactsDeriver()
    local_decider = LocalDecider()
    belief_generator = BeliefGenerator(nats_client)
    collective_aggregator = CollectiveConfidenceAggregator(nats_client)
    safety_gate = SafetyGate()
    approval_service = ApprovalService()
    intent_store = IntentStore()
    execution_kernel = ExecutionKernel(nats_client, approval_service, intent_store)
    audit_logger = AuditLogger(nats_client)
    
    logger.info("ADMO components initialized")


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting ExoArmur ADMO service")
    
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
    
    logger.info("ExoArmur ADMO service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global nats_client, background_tasks
    
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
    
    logger.info("ExoArmur ADMO service stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check accessed")
    return {"status": "healthy", "service": "ExoArmur ADMO"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ExoArmur ADMO - Workflow 1 Implementation"}


@app.post("/v1/telemetry/ingest", response_model=TelemetryIngestResponseV1)
async def ingest_telemetry(event: TelemetryEventV1):
    """Ingest telemetry event and process through ADMO loop"""
    global telemetry_validator, facts_deriver, local_decider, belief_generator
    global collective_aggregator, safety_gate, execution_kernel, audit_logger
    
    # Initialize components if not already done (for testing)
    if telemetry_validator is None:
        initialize_components()
    
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
        from safety.safety_gate import PolicyState, TrustState, EnvironmentState
        
        policy_state = PolicyState(
            policy_verified=True,  # TODO: implement actual policy verification
            kill_switch_global=False,  # TODO: implement actual kill switch checks
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        trust_state = TrustState(emitter_trust_score=0.85)  # TODO: implement actual trust scoring
        
        environment_state = EnvironmentState(degraded_mode=False)  # TODO: implement actual degraded mode detection
        
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
            # Execute intent immediately
            await execution_kernel.execute_intent(execution_intent)
            
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
            retrieved_at=datetime.utcnow()
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
    logger.info("Starting ExoArmur FastAPI service")
    uvicorn.run(app, host="0.0.0.0", port=8000)