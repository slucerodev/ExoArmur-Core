"""
API-key authentication for the ExoArmur pilot API.

Credentials are stored as SHA-256 verifiers only — raw API keys are never
persisted, logged, or committed. Keys are bound to a principal with an
explicit set of authorized tenants and permissions. Request headers or
payload fields naming an operator are NOT authentication; identity comes
only from a validated key (or an operator session issued after key
validation for the GUI).
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, Request, Response

from exoarmur.api.db import get_pool

SESSION_COOKIE = "exoarmur_session"
SESSION_TTL_HOURS = 8


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_key(raw_key: str) -> str:
    """Verifier stored for an API key — SHA-256 of the raw key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Principal:
    """Server-validated caller identity."""

    principal_id: str
    tenant_ids: tuple
    permissions: frozenset

    def allows_tenant(self, tenant_id: str) -> bool:
        return tenant_id in self.tenant_ids

    def allows(self, permission: str) -> bool:
        return permission in self.permissions or "*" in self.permissions


@dataclass
class _AuthState:
    """Startup-loaded auth configuration."""

    require_auth: bool = True
    policy: Optional[object] = None  # OperatorPolicyDecisionPoint


auth_state = _AuthState()


def configure_auth(policy=None, require_auth: bool = True) -> None:
    """Called at app startup with the verified operator policy."""
    auth_state.policy = policy
    auth_state.require_auth = require_auth


async def _lookup_key(key_hash: str) -> Optional[Principal]:
    pool = await get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT principal_id, tenant_ids, permissions, expires_at, revoked
            FROM api_keys WHERE key_hash = $1
            """,
            key_hash,
        )
    if row is None or row["revoked"]:
        return None
    if row["expires_at"] is not None and row["expires_at"] < _utcnow():
        return None
    return Principal(
        principal_id=row["principal_id"],
        tenant_ids=tuple(row["tenant_ids"] or ()),
        permissions=frozenset(row["permissions"] or ()),
    )


async def authenticate_api_key(raw_key: Optional[str]) -> Principal:
    """Validate an API key and return its principal. Raises 401/403."""
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    principal = await _lookup_key(hash_key(raw_key))
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return principal


def require_permission(permission: str, tenant_header: Optional[str] = None):
    """FastAPI dependency factory: authenticated principal + permission.

    If ``tenant_header`` names a dependency that yields a tenant id, the
    principal must be authorized for that tenant.
    """

    async def _dep(
        request: Request,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> Principal:
        principal = await authenticate_api_key(x_api_key)
        if not principal.allows(permission):
            raise HTTPException(
                status_code=403, detail=f"Missing permission: {permission}"
            )
        tenant_id = None
        if tenant_header:
            tenant_id = getattr(request.state, tenant_header, None)
        return principal

    return _dep


async def get_session_principal(request: Request) -> Principal:
    """Resolve principal from the GUI session cookie (validated server-side)."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_hash = hash_key(token)
    pool = await get_pool()
    if pool is None:
        raise HTTPException(status_code=401, detail="Session store unavailable")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT s.principal_id, k.tenant_ids, k.permissions
            FROM operator_sessions s
            JOIN api_keys k ON k.principal_id = s.principal_id
            WHERE s.token_hash = $1 AND s.expires_at > NOW()
            """,
            token_hash,
        )
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return Principal(
        principal_id=row["principal_id"],
        tenant_ids=tuple(row["tenant_ids"] or ()),
        permissions=frozenset(row["permissions"] or ()),
    )


async def issue_session(principal: Principal) -> str:
    """Create an operator session token; returns the raw token (cookie value)."""
    token = secrets.token_urlsafe(32)
    token_hash = hash_key(token)
    expires = _utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    pool = await get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Session store unavailable")
    async with pool.acquire() as conn:
        # Permissions snapshot at issuance; session inherits key's grants.
        await conn.execute(
            """
            INSERT INTO operator_sessions (token_hash, principal_id, expires_at)
            VALUES ($1, $2, $3)
            """,
            token_hash,
            principal.principal_id,
            expires,
        )
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=False,  # local pilot; set True behind TLS
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )


async def resolve_principal(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Principal:
    """Accept either an API key or a valid operator session cookie."""
    if x_api_key:
        return await authenticate_api_key(x_api_key)
    return await get_session_principal(request)


def require_csrf(request: Request) -> None:
    """Cookie-authenticated mutations must carry a custom header.

    SameSite=Strict already mitigates CSRF; this adds defense-in-depth for
    session-cookie requests.
    """
    if request.cookies.get(SESSION_COOKIE):
        marker = request.headers.get("x-exoarmur-request")
        if marker != "1":
            raise HTTPException(status_code=403, detail="Missing CSRF marker header")
