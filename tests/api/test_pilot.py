"""
Pilot governed-workflow tests — real PostgreSQL + real FileSystemExecutor.

Requires EXOARMUR_TEST_DATABASE_URL pointing at a disposable Postgres
database. Skipped entirely when unset; mocked results are never presented
as end-to-end evidence.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

DSN = os.getenv("EXOARMUR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="EXOARMUR_TEST_DATABASE_URL not set")

WORKSPACE = Path("/tmp/exoarmur_pilot_test_ws")
POLICY_PATH = Path("/tmp/exoarmur_pilot_test_policy.json")

AGENT_KEY = "exk_test_agent_0001"
APPROVER_KEY = "exk_test_approver_0002"
VIEWER_KEY = "exk_test_viewer_0003"
OTHER_KEY = "exk_test_other_0004"


def _key_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _write_policy() -> str:
    policy = {
        "version": 1,
        "rules": [
            {
                "tenant_id": "tenant-1",
                "principal_id": "agent-1",
                "operations": ["fs.create_file", "fs.modify_file"],
                "action_classes": {
                    "fs.create_file": "A1_soft_containment",
                    "fs.modify_file": "A2_hard_containment",
                },
                "required_approval": "human",
                "trust_score": 0.9,
            },
            {
                "tenant_id": "tenant-2",
                "principal_id": "agent-2",
                "operations": ["fs.create_file"],
                "action_classes": {"fs.create_file": "A1_soft_containment"},
                "required_approval": "none",
                "trust_score": 0.8,
            },
        ],
    }
    raw = json.dumps(policy, indent=2, sort_keys=True).encode()
    POLICY_PATH.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@pytest_asyncio.fixture
async def pilot_env(tmp_path, monkeypatch):
    """Real DB + workspace + pinned policy; yields (client, helpers)."""
    import asyncpg

    from exoarmur.api import db as api_db
    from exoarmur.api.routes import pilot as pilot_routes
    from exoarmur.api.server import create_app

    # Fresh workspace per test module run
    ws = tmp_path / "workspace"
    ws.mkdir()
    digest = _write_policy()

    monkeypatch.setenv("EXOARMUR_DATABASE_URL", DSN)
    monkeypatch.setenv("EXOARMUR_WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("EXOARMUR_POLICY_FILE", str(POLICY_PATH))
    monkeypatch.setenv("EXOARMUR_POLICY_SHA256", digest)
    monkeypatch.setenv("EXOARMUR_APPROVAL_TTL_HOURS", "24")

    pool = await api_db.init_db(DSN)
    assert pool is not None
    async with pool.acquire() as conn:
        for t in ("governed_actions", "execution_pauses", "api_keys",
                  "operator_sessions", "audit_records"):
            await conn.execute(f"DELETE FROM {t}")
        for kh, pid, tenants, perms in [
            (_key_hash(AGENT_KEY), "agent-1", ["tenant-1"],
             ["action:submit", "action:read", "action:resume"]),
            (_key_hash(APPROVER_KEY), "operator-1", ["tenant-1"],
             ["approval:grant", "approval:deny", "action:read", "evidence:read"]),
            (_key_hash(VIEWER_KEY), "viewer-1", ["tenant-1"], ["action:read"]),
            (_key_hash(OTHER_KEY), "agent-2", ["tenant-2"],
             ["action:submit", "action:read", "action:resume"]),
        ]:
            await conn.execute(
                "INSERT INTO api_keys (key_hash, principal_id, tenant_ids, permissions)"
                " VALUES ($1,$2,$3,$4)",
                kh, pid, tenants, perms,
            )

    pilot_routes._service = None
    pilot_routes._service_error = None

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, ws

    await api_db.close_db()
    pilot_routes._service = None


def _auth(key: str) -> dict:
    return {"X-API-Key": key, "x-exoarmur-request": "1"}


async def _submit(client, key=AGENT_KEY, op="create_file",
                  path="out/hello.txt", content="hello pilot"):
    return await client.post(
        "/api/pilot/actions",
        json={"operation": op, "path": path, "content": content},
        headers=_auth(key),
    )


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


async def test_submit_requires_api_key(pilot_env):
    client, _ = pilot_env
    r = await client.post("/api/pilot/actions", json={
        "operation": "create_file", "path": "a.txt", "content": "x"})
    assert r.status_code == 401


async def test_submit_invalid_key(pilot_env):
    client, _ = pilot_env
    r = await _submit(client, key="exk_wrong")
    assert r.status_code == 401


async def test_submit_missing_permission(pilot_env):
    client, _ = pilot_env
    r = await _submit(client, key=VIEWER_KEY)
    assert r.status_code == 403


async def test_approve_requires_grant_permission(pilot_env):
    client, ws = pilot_env
    r = await _submit(client)
    aid = r.json()["action"]["action_id"]
    r2 = await client.post(f"/api/pilot/actions/{aid}/approve",
                           headers=_auth(VIEWER_KEY))
    assert r2.status_code == 403
    assert not (ws / "out" / "hello.txt").exists()


# ---------------------------------------------------------------------------
# Governed workflow
# ---------------------------------------------------------------------------


async def test_approval_required_then_execute(pilot_env):
    client, ws = pilot_env
    r = await _submit(client)
    assert r.status_code == 201
    action = r.json()["action"]
    assert action["status"] == "PENDING_APPROVAL"
    assert action["action_class"] == "A1_soft_containment"
    assert not (ws / "out" / "hello.txt").exists()

    r2 = await client.post(f"/api/pilot/actions/{action['action_id']}/approve",
                           headers=_auth(APPROVER_KEY))
    assert r2.status_code == 200
    final = r2.json()["action"]
    assert final["status"] == "EXECUTED"
    assert final["approved_by"] == "operator-1"
    assert (ws / "out" / "hello.txt").read_text() == "hello pilot"


async def test_deny_blocks_execution(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="denied.txt")
    aid = r.json()["action"]["action_id"]
    r2 = await client.post(f"/api/pilot/actions/{aid}/deny",
                           json={"reason": "not now"}, headers=_auth(APPROVER_KEY))
    assert r2.status_code == 200
    assert r2.json()["action"]["status"] == "DENIED"
    assert not (ws / "denied.txt").exists()


async def test_duplicate_submit_is_idempotent(pilot_env):
    client, _ = pilot_env
    r1 = await _submit(client)
    r2 = await _submit(client)
    assert r1.json()["action"]["action_id"] == r2.json()["action"]["action_id"]
    assert r2.json()["created"] is False


async def test_resume_without_approval_rejected(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="resume.txt")
    aid = r.json()["action"]["action_id"]
    # agent key lacks approval:grant; approver key lacks action:resume
    r2 = await client.post(f"/api/pilot/actions/{aid}/resume",
                           headers=_auth(APPROVER_KEY))
    assert r2.status_code == 403
    assert not (ws / "resume.txt").exists()


async def test_policy_deny_no_matching_rule(pilot_env):
    """agent-2/tenant-2 has a rule only for create_file with approval none;
    modify_file is unmapped -> deny, no file."""
    client, ws = pilot_env
    r = await _submit(client, key=OTHER_KEY, op="modify_file",
                      path="x.txt", content="y")
    action = r.json()["action"]
    assert action["status"] in ("DENIED", "BLOCKED")
    assert not (ws / "x.txt").exists()


async def test_policy_allow_executes_without_approval(pilot_env):
    """tenant-2 create_file rule has required_approval=none -> direct exec."""
    client, ws = pilot_env
    r = await _submit(client, key=OTHER_KEY, op="create_file",
                      path="auto.txt", content="auto")
    assert r.status_code == 201
    action = r.json()["action"]
    assert action["status"] == "EXECUTED"
    assert (ws / "auto.txt").read_text() == "auto"


async def test_path_traversal_rejected(pilot_env):
    client, _ = pilot_env
    for bad in ("../escape.txt", "/etc/passwd", "a/../../b.txt"):
        r = await _submit(client, path=bad)
        assert r.status_code == 422, bad


async def test_cross_tenant_access_denied(pilot_env):
    client, _ = pilot_env
    r = await _submit(client)
    aid = r.json()["action"]["action_id"]
    r2 = await client.get(f"/api/pilot/actions/{aid}", headers=_auth(OTHER_KEY))
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Pauses
# ---------------------------------------------------------------------------


async def test_global_pause_blocks_approved_action(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="paused.txt")
    aid = r.json()["action"]["action_id"]
    # pause globally as approver? approver lacks pause:control; use agent? agent lacks it too.
    # Grant pause via direct DB update is not the API path — use a key with
    # pause:control: create one inline.
    import asyncpg
    from exoarmur.api import db as api_db

    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (key_hash, principal_id, tenant_ids, permissions)"
            " VALUES ($1,'op-2',ARRAY['tenant-1'],ARRAY['pause:control','action:read'])"
            " ON CONFLICT (key_hash) DO NOTHING",
            _key_hash("exk_pauser"),
        )
    r3 = await client.put("/api/pilot/pauses",
                          json={"scope": "global", "paused": True},
                          headers=_auth("exk_pauser"))
    assert r3.status_code == 200

    r4 = await client.post(f"/api/pilot/actions/{aid}/approve",
                           headers=_auth(APPROVER_KEY))
    assert r4.status_code == 200
    assert r4.json()["action"]["status"] == "BLOCKED"
    assert not (ws / "paused.txt").exists()

    # unpause -> explicit resume still blocked? status is BLOCKED terminal.
    await client.put("/api/pilot/pauses",
                     json={"scope": "global", "paused": False},
                     headers=_auth("exk_pauser"))


async def test_tenant_pause_blocks_only_that_tenant(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="tp.txt")
    aid = r.json()["action"]["action_id"]
    import asyncpg
    from exoarmur.api import db as api_db

    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (key_hash, principal_id, tenant_ids, permissions)"
            " VALUES ($1,'op-3',ARRAY['tenant-1'],ARRAY['pause:control'])"
            " ON CONFLICT (key_hash) DO NOTHING",
            _key_hash("exk_pauser2"),
        )
    await client.put("/api/pilot/pauses",
                     json={"scope": "tenant", "tenant_id": "tenant-1",
                           "paused": True},
                     headers=_auth("exk_pauser2"))
    r2 = await client.post(f"/api/pilot/actions/{aid}/approve",
                           headers=_auth(APPROVER_KEY))
    assert r2.json()["action"]["status"] == "BLOCKED"
    assert not (ws / "tp.txt").exists()


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


async def test_evidence_verify_and_tamper(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="ev.txt", content="evidence")
    aid = r.json()["action"]["action_id"]
    await client.post(f"/api/pilot/actions/{aid}/approve",
                      headers=_auth(APPROVER_KEY))

    v = await client.get(f"/api/pilot/actions/{aid}/verify",
                         headers=_auth(APPROVER_KEY))
    assert v.status_code == 200
    assert v.json()["overall"] == "VERIFIED"

    # Tamper with stored evidence -> verification must fail
    from exoarmur.api import db as api_db

    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE governed_actions SET evidence = evidence || "
            "'{\"tampered\": true}'::jsonb WHERE action_id=$1", aid)
    v2 = await client.get(f"/api/pilot/actions/{aid}/verify",
                          headers=_auth(APPROVER_KEY))
    assert v2.json()["overall"] == "MISMATCH"


async def test_restart_preserves_state(pilot_env):
    """A fresh service instance reads the same durable rows (no re-dispatch)."""
    client, ws = pilot_env
    r = await _submit(client, path="persist.txt", content="durable")
    aid = r.json()["action"]["action_id"]
    await client.post(f"/api/pilot/actions/{aid}/approve",
                      headers=_auth(APPROVER_KEY))

    from exoarmur.api import db as api_db
    from exoarmur.api.pilot_service import PilotService
    from exoarmur.api.policy_source import load_operator_policy
    import os

    svc2 = PilotService(
        os.environ["EXOARMUR_WORKSPACE_ROOT"],
        __import__("exoarmur.api.policy_source", fromlist=["x"]).OperatorPolicyDecisionPoint(
            load_operator_policy(os.environ["EXOARMUR_POLICY_FILE"],
                                 os.environ["EXOARMUR_POLICY_SHA256"])),
    )
    rec = await svc2.get_action(aid)
    assert rec is not None and rec.status == "EXECUTED"
    assert (ws / "persist.txt").read_text() == "durable"


async def test_expired_approval_blocks_execution(pilot_env):
    client, ws = pilot_env
    r = await _submit(client, path="expired.txt")
    aid = r.json()["action"]["action_id"]

    import asyncpg
    from exoarmur.api import db as api_db
    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE governed_actions SET expires_at = now() - interval '1 hour'"
            " WHERE action_id=$1", aid)

    r2 = await client.post(f"/api/pilot/actions/{aid}/approve",
                           headers=_auth(APPROVER_KEY))
    assert r2.status_code >= 400
    assert not (ws / "expired.txt").exists()
    detail = await client.get(f"/api/pilot/actions/{aid}",
                              headers=_auth(APPROVER_KEY))
    assert detail.json()["status"] == "EXPIRED"


async def test_changed_parameters_require_separate_approval(pilot_env):
    """Approval binds to the frozen action; a different proposal is a new
    action that stays pending until its own approval."""
    client, ws = pilot_env
    r1 = await _submit(client, path="same.txt", content="version-one")
    a1 = r1.json()["action"]["action_id"]
    r2 = await _submit(client, path="same.txt", content="version-two")
    a2 = r2.json()["action"]["action_id"]
    assert a1 != a2

    await client.post(f"/api/pilot/actions/{a1}/approve",
                      headers=_auth(APPROVER_KEY))
    assert (ws / "same.txt").read_text() == "version-one"

    pending = await client.get(f"/api/pilot/actions/{a2}",
                               headers=_auth(APPROVER_KEY))
    assert pending.json()["status"] == "PENDING_APPROVAL"
    assert (ws / "same.txt").read_text() == "version-one"


# ---------------------------------------------------------------------------
# App isolation + session-key binding
# ---------------------------------------------------------------------------


async def test_pilot_app_excludes_legacy_routes(pilot_env):
    """create_pilot_app mounts only health + /api/pilot/*."""
    from exoarmur.api.server import create_pilot_app

    app = create_pilot_app()
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as c:
        assert (await c.get("/health")).status_code == 200
        assert (await c.get("/api/pilot/status",
                            headers=_auth(AGENT_KEY))).status_code == 200
        # Legacy/demo routers must be absent
        assert (await c.get("/v1/approvals/x")).status_code == 404
        assert (await c.post("/api/cli/replay", json={})).status_code == 404
        assert (await c.get("/api/v2/visibility/statistics")).status_code == 404
        # Unauthenticated admin endpoint must also be absent from pilot
        assert (await c.get("/admin/consistency")).status_code == 404
        # FastAPI schema/docs endpoints are intentionally enabled
        assert (await c.get("/openapi.json")).status_code == 200
        assert (await c.get("/docs")).status_code == 200
        # And the full app still serves them (unchanged behavior)
    from exoarmur.api.server import create_app
    app2 = create_app()
    async with AsyncClient(transport=ASGITransport(app=app2),
                           base_url="http://test") as c:
        # Route exists on the full app (any non-404 response proves mounting)
        assert (await c.post("/api/cli/replay", json={})).status_code != 404
        assert (await c.get("/api/v2/visibility/statistics")).status_code != 404
        assert (await c.get("/admin/consistency")).status_code != 404


async def _login(client, key: str):
    return await client.post("/api/pilot/auth/login", json={"api_key": key})


async def test_session_invalidated_on_key_revoke(pilot_env):
    client, _ = pilot_env
    r = await _login(client, APPROVER_KEY)
    assert r.status_code == 200
    assert (await client.get("/api/pilot/status")).status_code == 200

    from exoarmur.api import db as api_db
    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET revoked = TRUE WHERE principal_id = 'operator-1'")
    assert (await client.get("/api/pilot/status")).status_code == 401


async def test_session_invalidated_on_key_expiry(pilot_env):
    client, _ = pilot_env
    r = await _login(client, APPROVER_KEY)
    assert r.status_code == 200
    assert (await client.get("/api/pilot/status")).status_code == 200

    from exoarmur.api import db as api_db
    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET expires_at = NOW() - interval '1 hour'"
            " WHERE principal_id = 'operator-1'")
    assert (await client.get("/api/pilot/status")).status_code == 401


async def test_session_invalidated_on_session_expiry(pilot_env):
    client, _ = pilot_env
    r = await _login(client, APPROVER_KEY)
    assert r.status_code == 200
    assert (await client.get("/api/pilot/status")).status_code == 200

    from exoarmur.api import db as api_db
    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE operator_sessions SET expires_at = NOW() - interval '1 hour'")
    assert (await client.get("/api/pilot/status")).status_code == 401


async def test_session_permissions_bound_to_issuing_key(pilot_env):
    """Two api_keys rows for the same principal must not share grants:
    a session issued by key A resolves permissions only from key A."""
    client, _ = pilot_env
    KEY2 = "exk_test_agent1_alt_key"

    from exoarmur.api import db as api_db
    pool = await api_db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (key_hash, principal_id, tenant_ids, permissions)"
            " VALUES ($1,'agent-1',ARRAY['tenant-2'],"
            " ARRAY['action:submit','action:read','action:resume',"
            "       'approval:grant','approval:deny'])",
            _key_hash(KEY2))

    # Session issued by AGENT_KEY (tenant-1, NO approval:grant)
    r = await _login(client, AGENT_KEY)
    assert r.status_code == 200
    assert "approval:grant" not in r.json()["permissions"]

    # Pending action in tenant-1
    r2 = await _submit(client)
    aid = r2.json()["action"]["action_id"]

    # Cookie-session approve attempt: must fail on missing permission from
    # the ISSUING key — not silently resolve the other key's approval:grant.
    r3 = await client.post(
        f"/api/pilot/actions/{aid}/approve",
        headers={"x-exoarmur-request": "1"},
    )
    assert r3.status_code == 403
    assert "approval:grant" in r3.json()["detail"]


async def test_gui_served(pilot_env):
    client, _ = pilot_env
    r = await client.get("/api/pilot/gui")
    assert r.status_code == 200
    assert "ExoArmur Pilot Console" in r.text
