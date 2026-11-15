"""
FastAPI application factory for the ExoArmur API.

Provides CORS, structured error handling, request-ID injection, and
health-check middleware.  All routes are registered from sub-modules
so the file stays small and navigable.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from exoarmur import __version__ as core_version
from exoarmur.api.models import ErrorEnvelope


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown — optional PostgreSQL pool."""
    from exoarmur.api.db import init_db, close_db, get_dsn

    dsn = get_dsn()
    if dsn:
        pool = await init_db(dsn)
        if pool:
            print(f"[startup] PostgreSQL pool connected: {dsn.split('@')[-1]}")
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ExoArmur API",
        description="Deterministic governance kernel HTTP API",
        version=core_version,
        lifespan=_lifespan,
    )

    # CORS — dashboard runs on :3000, API on :8000
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-ID middleware + timing
    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Callable) -> Any:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(int((time.time() - start) * 1000))
        return response

    # Global exception handler → ErrorEnvelope
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        envelope = ErrorEnvelope(
            code="INTERNAL_ERROR",
            http_status=500,
            message=str(exc),
            severity="fatal",
            endpoint=request.url.path,
            request_id=request_id,
            at=_utc_now(),
        )
        return JSONResponse(status_code=500, content=envelope.model_dump())

    # Register route modules
    from exoarmur.api.routes import core, bridge, v1, v2, pilot

    app.include_router(core.router, tags=["Core"])
    app.include_router(bridge.router, prefix="/api/cli", tags=["Bridge"])
    app.include_router(v1.router, prefix="/v1", tags=["V1"])
    app.include_router(v2.router, prefix="/api/v2", tags=["V2"])
    app.include_router(pilot.router, prefix="/api/pilot", tags=["Pilot"])

    return app


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
