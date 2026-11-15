"""Core API routes — health, version, and readiness checks."""

from typing import List

from fastapi import APIRouter

from exoarmur import __version__ as core_version
from exoarmur.api.models import ConsistencyCheckResponse, HealthResponse
from exoarmur.api.stores import (
    approval_store,
    arbitration_store,
    audit_store,
    belief_store,
    benchmark_history,
    federate_store,
    observation_store,
)

health_router = APIRouter()
router = APIRouter()
router.include_router(health_router)


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="exoarmur-api",
        version=core_version,
    )


@router.get("/admin/consistency", response_model=List[ConsistencyCheckResponse])
async def consistency_check() -> List[ConsistencyCheckResponse]:
    """Compare in-memory vs DB counts for each store (dual-write verification)."""
    from datetime import datetime, timezone

    stores = {
        "observations": observation_store,
        "beliefs": belief_store,
        "audit_records": audit_store,
        "approvals": approval_store,
        "federates": federate_store,
        "arbitrations": arbitration_store,
        "benchmark_runs": benchmark_history,
    }

    results = []
    for name, store in stores.items():
        mem_count = await store.count()
        db_count = await store._repository().count()
        results.append(
            ConsistencyCheckResponse(
                store_name=name,
                memory_count=mem_count,
                db_count=db_count,
                consistent=mem_count == db_count,
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    return results
