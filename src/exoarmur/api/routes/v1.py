"""
V1 API routes — telemetry ingest, audit, and approvals.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Header

from exoarmur.api.models import (
    ApprovalResponse,
    ApprovalStatusResponse,
    AuditRecord,
    AuditResponse,
    BeliefInfo,
    ObservationInfo,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)
from exoarmur.api.stores import (
    approval_store,
    audit_store,
    belief_store,
    observation_store,
)
from exoarmur.kernel.clock import utc_now
from exoarmur.kernel.ids import make_audit_id, make_intent_id

router = APIRouter()


# ============================================================================
# Audit
# ============================================================================


@router.get("/audit/{correlation_id}", response_model=AuditResponse)
async def get_audit_by_correlation(correlation_id: str) -> AuditResponse:
    """Return all audit records for a given correlation ID."""
    records = await audit_store.get_by_correlation(correlation_id)
    return AuditResponse(
        correlation_id=correlation_id,
        audit_records=records,
        total_count=len(records),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


# ============================================================================
# Approvals
# ============================================================================


@router.get("/approvals/{approval_id}", response_model=ApprovalStatusResponse)
async def get_approval(approval_id: str) -> ApprovalStatusResponse:
    """Get the current status of an approval."""
    approval = await approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


class ApproveRequest:
    pass


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: str,
    operator_id: Optional[str] = Header(default=None),
) -> ApprovalResponse:
    """Approve a pending request."""
    if not operator_id:
        raise HTTPException(status_code=401, detail="operator_id header required")
    try:
        updated = await approval_store.update_status(
            approval_id, "APPROVED", operator_id
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Emit audit record
    await audit_store.append(
        AuditRecord(
            audit_id=make_audit_id(approval_id, "approval", "approved"),
            event_kind="approval_resolved",
            payload_ref={
                "approval_id": approval_id,
                "operator_id": operator_id,
                "resolution": "APPROVED",
            },
            correlation_id=updated.correlation_id,
            trace_id="",
            tenant_id="default",
            cell_id="default",
            idempotency_key=f"{approval_id}-approve",
            created_at=utc_now().isoformat(),
        )
    )

    # update_status guarantees APPROVED or DENIED; cast for the response model
    status: Literal["APPROVED", "DENIED"] = updated.status  # type: ignore[assignment]
    return ApprovalResponse(
        approval_id=updated.approval_id,
        status=status,
        created_at=updated.created_at,
    )


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalResponse)
async def deny_request(
    approval_id: str,
    reason: str = Header(...),
    operator_id: Optional[str] = Header(default=None),
) -> ApprovalResponse:
    """Deny a pending request (reason required)."""
    if not operator_id:
        raise HTTPException(status_code=401, detail="operator_id header required")
    if not reason or not reason.strip():
        raise HTTPException(status_code=422, detail="Denial reason required")
    try:
        updated = await approval_store.update_status(
            approval_id, "DENIED", operator_id, reason=reason
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Emit audit record
    await audit_store.append(
        AuditRecord(
            audit_id=make_audit_id(approval_id, "approval", "denied"),
            event_kind="approval_resolved",
            payload_ref={
                "approval_id": approval_id,
                "operator_id": operator_id,
                "resolution": "DENIED",
                "reason": reason,
            },
            correlation_id=updated.correlation_id,
            trace_id="",
            tenant_id="default",
            cell_id="default",
            idempotency_key=f"{approval_id}-deny",
            created_at=utc_now().isoformat(),
        )
    )

    status: Literal["APPROVED", "DENIED"] = updated.status  # type: ignore[assignment]
    return ApprovalResponse(
        approval_id=updated.approval_id,
        status=status,
        created_at=updated.created_at,
    )


# ============================================================================
# Telemetry ingest + belief derivation (Phase 3)
# ============================================================================


def _action_class_from_observation(obs: TelemetryIngestRequest) -> str:
    """Map observation to ActionClass for approval workflow."""
    if obs.confidence > 0.85 or obs.observation_type in ("anomaly", "threat"):
        return "A2_HARD_CONTAINMENT"
    if obs.confidence > 0.60:
        return "A1_SOFT_CONTAINMENT"
    return "A0_OBSERVE"


def _derive_belief_from_observation(obs: ObservationInfo) -> Optional[BeliefInfo]:
    """
    Deterministic rule-based belief derivation — no ML.
    Same observation always yields the same belief type and confidence.
    """
    if obs.observation_type == "anomaly" and obs.confidence > 0.90:
        return BeliefInfo(
            belief_id=make_intent_id(obs.observation_id, "belief", "confirmed"),
            belief_type="anomaly_confirmed",
            confidence=round(obs.confidence, 4),
            source_observations=[obs.observation_id],
            derived_at=obs.timestamp_utc,
            correlation_id=obs.correlation_id,
            evidence_summary=f"High-confidence anomaly from {obs.source_federate_id}",
            conflicts=[],
            metadata={"rule": "anomaly_confirmed_threshold"},
        )
    if obs.observation_type == "anomaly" and obs.confidence > 0.70:
        return BeliefInfo(
            belief_id=make_intent_id(obs.observation_id, "belief", "suspected"),
            belief_type="anomaly_suspected",
            confidence=round(obs.confidence - 0.10, 4),
            source_observations=[obs.observation_id],
            derived_at=obs.timestamp_utc,
            correlation_id=obs.correlation_id,
            evidence_summary=f"Suspected anomaly from {obs.source_federate_id}",
            conflicts=[],
            metadata={"rule": "anomaly_suspected_threshold"},
        )
    if obs.observation_type == "threat" and obs.confidence > 0.80:
        return BeliefInfo(
            belief_id=make_intent_id(obs.observation_id, "belief", "threat"),
            belief_type="threat_detected",
            confidence=round(obs.confidence, 4),
            source_observations=[obs.observation_id],
            derived_at=obs.timestamp_utc,
            correlation_id=obs.correlation_id,
            evidence_summary=f"Threat detected by {obs.source_federate_id}",
            conflicts=[],
            metadata={"rule": "threat_detected_threshold"},
        )
    # Default: low-confidence observation-derived belief
    return BeliefInfo(
        belief_id=make_intent_id(obs.observation_id, "belief", "derived"),
        belief_type="observation_derived",
        confidence=round(obs.confidence * 0.5, 4),
        source_observations=[obs.observation_id],
        derived_at=obs.timestamp_utc,
        correlation_id=obs.correlation_id,
        evidence_summary=f"Derived from {obs.observation_type} observation",
        conflicts=[],
        metadata={"rule": "default_derivation"},
    )


@router.post("/telemetry/ingest", response_model=TelemetryIngestResponse)
async def telemetry_ingest(
    request: TelemetryIngestRequest,
    operator_id: Optional[str] = Header(default=None),
) -> TelemetryIngestResponse:
    """Ingest telemetry, derive beliefs, and create approvals when required."""
    now = utc_now().isoformat()
    correlation_id = request.correlation_id or make_intent_id(
        request.source_federate_id, request.observation_type, "auto"
    )

    # Create observation
    observation = ObservationInfo(
        observation_id=make_audit_id(correlation_id, "observation", "ingested"),
        source_federate_id=request.source_federate_id,
        timestamp_utc=now,
        correlation_id=correlation_id,
        observation_type=request.observation_type,
        confidence=request.confidence,
        evidence_refs=request.evidence_refs,
        payload_type=request.payload_type,
        payload_data=request.payload_data,
    )
    await observation_store.add(observation)

    # Derive belief deterministically from observation
    belief = _derive_belief_from_observation(observation)
    if belief:
        await belief_store.add(belief)

    # Determine action class
    action_class = _action_class_from_observation(request)

    # Create approval if required (A2 / A3)
    approval_required = action_class in ("A2_HARD_CONTAINMENT", "A3_IRREVERSIBLE")
    approval_id: Optional[str] = None

    if approval_required:
        approval_id = make_intent_id(correlation_id, action_class, "approval")
        await approval_store.create(
            ApprovalStatusResponse(
                approval_id=approval_id,
                status="PENDING",
                created_at=now,
                requested_action_class=action_class,
                correlation_id=correlation_id,
            )
        )

    # Emit audit record
    await audit_store.append(
        AuditRecord(
            audit_id=make_audit_id(correlation_id, "telemetry", "ingested"),
            event_kind="telemetry_ingest",
            payload_ref={
                "observation_id": observation.observation_id,
                "action_class": action_class,
                "approval_required": approval_required,
                "operator_id": operator_id or "system",
            },
            correlation_id=correlation_id,
            trace_id="",
            tenant_id="default",
            cell_id="default",
            idempotency_key=observation.observation_id,
            created_at=now,
        )
    )

    return TelemetryIngestResponse(
        observation_id=observation.observation_id,
        status="ingested",
        approval_required=approval_required,
        approval_id=approval_id,
    )
