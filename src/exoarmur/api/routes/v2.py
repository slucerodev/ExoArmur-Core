"""
V2 Visibility API routes — observations, beliefs, federates, arbitrations,
statistics, timeline, and containment status.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from exoarmur.api.models import (
    ArbitrationInfo,
    BeliefInfo,
    FederateInfo,
    ObservationInfo,
    TimelineInfo,
    VisibilityStats,
)
from exoarmur.api.stores import (
    approval_store,
    arbitration_store,
    audit_store,
    belief_store,
    benchmark_history,
    federate_store,
    observation_store,
)

router = APIRouter()


@router.get("/visibility/statistics", response_model=VisibilityStats)
async def visibility_statistics() -> VisibilityStats:
    """Aggregate counts from all in-memory stores."""
    return VisibilityStats(
        ingest_statistics={
            "total_ingested": await observation_store.count(),
            "total_signals": await observation_store.count(),
            "safety_evaluations": await audit_store.count(),
            "total_executed": await benchmark_history.count(),
        },
        belief_statistics={
            "total_beliefs": await belief_store.count(),
            "collective_count": await belief_store.count(),
        },
        store_statistics={
            "total_records": await audit_store.count(),
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
        arbitration_statistics={
            "total_arbitrations": await arbitration_store.count(),
            "pending_arbitrations": len(
                [a for a in await arbitration_store.list() if a.status == "PENDING"]
            ),
        },
    )


@router.get("/visibility/observations", response_model=list[ObservationInfo])
async def visibility_observations(
    limit: int = Query(default=25, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ObservationInfo]:
    """Return recent observations from the in-memory store."""
    return await observation_store.list(limit=limit, offset=offset)


@router.get("/visibility/timeline/{correlation_id}", response_model=TimelineInfo)
async def visibility_timeline(correlation_id: str) -> TimelineInfo:
    """Join observations and beliefs for a given correlation ID."""
    observations = await observation_store.get_by_correlation(correlation_id)
    beliefs = await belief_store.get_by_correlation(correlation_id)
    return TimelineInfo(
        correlation_id=correlation_id,
        observations=observations,
        beliefs=beliefs,
    )


@router.get("/visibility/beliefs", response_model=list[BeliefInfo])
async def visibility_beliefs(
    limit: int = Query(default=25, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[BeliefInfo]:
    """Return recent beliefs from the in-memory store."""
    return await belief_store.list(limit=limit, offset=offset)


@router.get("/visibility/federates", response_model=list[FederateInfo])
async def visibility_federates() -> list[FederateInfo]:
    """Return all registered federates."""
    return await federate_store.list()


@router.get("/visibility/arbitrations", response_model=list[ArbitrationInfo])
async def visibility_arbitrations(
    limit: int = Query(default=25, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ArbitrationInfo]:
    """Return recent arbitrations from the in-memory store."""
    return await arbitration_store.list(limit=limit, offset=offset)
