"""
Pilot governed-workflow routes (2.2.0).

Authenticated, policy-controlled file-write actions with human approval,
durable pauses, and verifiable evidence. All identity comes from validated
API keys or operator sessions — never from request-supplied operator fields.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from exoarmur.api import auth
from exoarmur.api.auth import Principal, resolve_principal
from exoarmur.api.pilot_service import (
    PilotService,
    PilotStoreError,
    PilotUnavailableError,
)

router = APIRouter()

_service: Optional[PilotService] = None
_service_error: Optional[str] = None


def get_service() -> PilotService:
    global _service, _service_error
    if _service is None:
        try:
            _service = PilotService.from_env()
            _service_error = getattr(_service, "policy_load_error", None)
        except PilotUnavailableError as e:
            _service_error = str(e)
            raise HTTPException(status_code=503, detail=str(e))
    return _service


def _check(principal: Principal, permission: str) -> None:
    if not principal.allows(permission):
        raise HTTPException(
            status_code=403, detail=f"Missing permission: {permission}"
        )


async def _principal(request: Request) -> Principal:
    return await resolve_principal(
        request,
        x_api_key=request.headers.get("x-api-key"),
    )


def _tenant_or_403(principal: Principal, tenant_id: str) -> None:
    if not principal.allows_tenant(tenant_id):
        raise HTTPException(status_code=403, detail="Tenant not authorized")


# ---------------------------------------------------------------------------
# Auth (GUI session bootstrap)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    api_key: str = Field(..., min_length=1)


@router.post("/auth/login")
async def login(body: LoginRequest, response: Response) -> dict:
    """Exchange a validated API key for a short-lived HttpOnly session cookie."""
    principal = await auth.authenticate_api_key(body.api_key)
    token = await auth.issue_session(principal, auth.hash_key(body.api_key))
    auth.set_session_cookie(response, token)
    return {
        "principal_id": principal.principal_id,
        "tenant_ids": list(principal.tenant_ids),
        "permissions": sorted(principal.permissions),
    }


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> dict:
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"status": "logged_out"}


# ---------------------------------------------------------------------------
# Status / policy
# ---------------------------------------------------------------------------


@router.get("/status")
async def status(request: Request) -> dict:
    principal = await _principal(request)
    svc = get_service()
    tenant_id = principal.tenant_ids[0] if principal.tenant_ids else ""
    try:
        pauses = await svc.pause_state(tenant_id) if tenant_id else {
            "global": False, "tenant": False, "detail": {}
        }
    except PilotStoreError as e:
        pauses = {"error": str(e)}
    pol = svc.policy.policy
    return {
        "service": "exoarmur-pilot",
        "workspace_root": str(svc.workspace_root),
        "policy_loaded": pol is not None,
        "policy_version": svc.policy.policy_version,
        "policy_error": _service_error,
        "pauses": pauses,
        "supported_operations": ["create_file", "modify_file"],
    }


@router.get("/policy")
async def policy_info(request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "action:read")
    svc = get_service()
    pol = svc.policy.policy
    if pol is None:
        return {"loaded": False, "error": _service_error}
    return {
        "loaded": True,
        "version": pol.version,
        "sha256": pol.sha256,
        "rules": [
            {
                "tenant_id": r.tenant_id,
                "principal_id": r.principal_id,
                "operations": r.operations,
                "action_classes": r.action_classes,
                "default_action_class": r.default_action_class,
                "required_approval": r.required_approval,
            }
            for r in pol.rules
        ],
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class ActionSubmitRequest(BaseModel):
    operation: str = Field(..., pattern="^(create_file|modify_file)$")
    path: str = Field(..., min_length=1, max_length=1024)
    content: str = Field(..., max_length=1_000_000)
    tenant_id: Optional[str] = None


def _action_dict(r) -> dict:
    return {
        "action_id": r.action_id,
        "tenant_id": r.tenant_id,
        "principal_id": r.principal_id,
        "operation": r.operation,
        "path": r.parameters.get("path"),
        "target_path": r.target_path,
        "content_preview": (r.parameters.get("payload", {}).get("content") or "")[:500],
        "content_length": len(r.parameters.get("payload", {}).get("content") or ""),
        "params_sha256": r.params_sha256,
        "action_class": r.action_class,
        "policy_version": r.policy_version,
        "status": r.status,
        "approval_id": r.approval_id,
        "approved_by": r.approved_by,
        "expires_at": r.expires_at,
        "result": r.result,
        "evidence_sha256": r.evidence_sha256,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


@router.post("/actions", status_code=201)
async def submit_action(body: ActionSubmitRequest, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "action:submit")
    auth.require_csrf(request)
    svc = get_service()
    try:
        record, created = await svc.submit(
            principal, body.operation, body.path, body.content, body.tenant_id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"created": created, "action": _action_dict(record)}


@router.get("/actions")
async def list_actions(request: Request, status: Optional[str] = None) -> dict:
    principal = await _principal(request)
    _check(principal, "action:read")
    svc = get_service()
    tenant_id = principal.tenant_ids[0] if principal.tenant_ids else ""
    if not tenant_id:
        return {"actions": []}
    try:
        records = await svc.list_actions(tenant_id, status=status)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"actions": [_action_dict(r) for r in records]}


@router.get("/actions/{action_id}")
async def get_action(action_id: str, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "action:read")
    svc = get_service()
    try:
        record = await svc.get_action(action_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if record is None:
        raise HTTPException(status_code=404, detail="Action not found")
    _tenant_or_403(principal, record.tenant_id)
    d = _action_dict(record)
    d["parameters"] = record.parameters
    d["evidence"] = record.evidence
    return d


@router.get("/actions/{action_id}/verify")
async def verify_action(action_id: str, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "evidence:read")
    svc = get_service()
    try:
        record = await svc.get_action(action_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if record is None:
        raise HTTPException(status_code=404, detail="Action not found")
    _tenant_or_403(principal, record.tenant_id)
    try:
        return await svc.verify_action(action_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))


class DenyRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "approval:grant")
    auth.require_csrf(request)
    svc = get_service()
    try:
        record = await svc.approve(action_id, principal)
    except KeyError:
        raise HTTPException(status_code=404, detail="Action not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"action": _action_dict(record)}


@router.post("/actions/{action_id}/deny")
async def deny_action(action_id: str, body: DenyRequest, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "approval:deny")
    auth.require_csrf(request)
    svc = get_service()
    try:
        record = await svc.deny(action_id, principal, body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Action not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"action": _action_dict(record)}


@router.post("/actions/{action_id}/resume")
async def resume_action(action_id: str, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "action:resume")
    auth.require_csrf(request)
    svc = get_service()
    try:
        record = await svc.get_action(action_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if record is None:
        raise HTTPException(status_code=404, detail="Action not found")
    _tenant_or_403(principal, record.tenant_id)
    try:
        record = await svc.resume(action_id, principal)
    except KeyError:
        raise HTTPException(status_code=404, detail="Action not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"action": _action_dict(record)}


# ---------------------------------------------------------------------------
# Pauses
# ---------------------------------------------------------------------------


class PauseRequest(BaseModel):
    paused: bool
    scope: str = Field(default="global", pattern="^(global|tenant)$")
    tenant_id: Optional[str] = None


@router.get("/pauses")
async def get_pauses(request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "pause:control")
    svc = get_service()
    tenant_id = principal.tenant_ids[0] if principal.tenant_ids else ""
    try:
        return await svc.pause_state(tenant_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.put("/pauses")
async def set_pause(body: PauseRequest, request: Request) -> dict:
    principal = await _principal(request)
    _check(principal, "pause:control")
    auth.require_csrf(request)
    svc = get_service()
    scope_key = ""
    if body.scope == "tenant":
        scope_key = body.tenant_id or (
            principal.tenant_ids[0] if principal.tenant_ids else ""
        )
        if not scope_key:
            raise HTTPException(status_code=422, detail="tenant_id required")
        _tenant_or_403(principal, scope_key)
    try:
        await svc.set_pause(body.scope, scope_key, body.paused,
                            principal.principal_id)
    except PilotStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"scope": body.scope, "scope_key": scope_key, "paused": body.paused}


# ---------------------------------------------------------------------------
# Operator GUI (server-served, cookie session)
# ---------------------------------------------------------------------------


@router.get("/gui", response_class=HTMLResponse)
async def gui() -> HTMLResponse:
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1] / "gui" / "index.html"
    ).read_text()
    return HTMLResponse(html)
