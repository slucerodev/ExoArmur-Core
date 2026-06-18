"""Core API routes — health, version, and readiness checks."""

from fastapi import APIRouter

from exoarmur import __version__ as core_version
from exoarmur.api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="exoarmur-api",
        version=core_version,
    )
