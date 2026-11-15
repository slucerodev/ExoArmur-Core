"""
Milestone 1: authenticated callers through policy-controlled execution.

Exercises the real AuthService/API-key store, OperatorPolicy (digest-
pinned), SafetyGate, kill-switch ExecutionGate, and the FastAPI routes
with a counting-style recorder executor (ExecutionKernel.executed_intents).
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import exoarmur.main as runtime_main
from exoarmur.auth.auth_service import Permission, export_key_store_records, import_key_store_records, APIKeyStore
from exoarmur.spec.contracts.models_v1 import TelemetryEventV1


RAW_KEY = "test-milestone-key-0123456789abcdef"


def _key_record(key_id, raw_key, principal_id, tenant_ids, permissions, **overrides):
    rec = {
        "key_id": key_id,
        "key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
        "tenant_ids": tenant_ids,
        "permissions": sorted(p.value for p in permissions),
        "principal_id": principal_id,
        "created_at": "2024-01-01T00:00:00+00:00",
        "expires_at": None,
        "is_active": True,
        "description": None,
        "last_used_at": None,
    }
    rec.update(overrides)
    return rec


def _setup(tmp_path, monkeypatch, records, policy_doc=None):
    """Write key store (+ optional policy) and initialize app components."""
    store_path = tmp_path / "api_keys.json"
    store_path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setenv("EXOARMUR_API_KEY_STORE", str(store_path))

    monkeypatch.delenv("EXOARMUR_POLICY_FILE", raising=False)
    monkeypatch.delenv("EXOARMUR_POLICY_SHA256", raising=False)
    if policy_doc is not None:
        policy_path = tmp_path / "policy.json"
        raw = json.dumps(policy_doc).encode()
        policy_path.write_bytes(raw)
        monkeypatch.setenv("EXOARMUR_POLICY_FILE", str(policy_path))
        monkeypatch.setenv("EXOARMUR_POLICY_SHA256", hashlib.sha256(raw).hexdigest())

    runtime_main.initialize_components(None)
    return TestClient(runtime_main.app)


def _telemetry(tenant_id="tenant-1", severity="low", suffix=""):
    return TelemetryEventV1(
        schema_version="1.0.0",
        event_id="3EDW0S2AFBGFZ0T10NPVFXFT77",
        tenant_id=tenant_id,
        cell_id="cell-1",
        observed_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        source={"kind": "edr", "name": "test", "host": "h1", "sensor_id": "s1"},
        event_type="process_start",
        severity=severity,
        attributes={"process_name": "notepad.exe"},
        entity_refs=None,
        correlation_id=f"corr-auth{suffix}",
        trace_id=f"trace-auth{suffix}",
    )


def _headers(key=RAW_KEY):
    return {"X-API-Key": key} if key else {}


ALL_PERMS = list(Permission)


class TestIngestAuthentication:
    def test_missing_api_key_rejected(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-1"], ALL_PERMS),
        ])
        resp = client.post("/v1/telemetry/ingest", json=_telemetry().model_dump())
        assert resp.status_code == 401

    def test_invalid_api_key_rejected(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-1"], ALL_PERMS),
        ])
        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry().model_dump(),
            headers=_headers("wrong-key"),
        )
        assert resp.status_code == 401

    def test_expired_and_inactive_keys_rejected(self, tmp_path, monkeypatch):
        expired = _key_record(
            "k-exp", "expired-key", "agent-001", ["tenant-1"], ALL_PERMS,
            expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        )
        inactive = _key_record("k-inact", "inactive-key", "agent-001", ["tenant-1"], ALL_PERMS,
                               is_active=False)
        client = _setup(tmp_path, monkeypatch, [expired, inactive])
        for key in ("expired-key", "inactive-key"):
            resp = client.post(
                "/v1/telemetry/ingest",
                json=_telemetry(suffix=key).model_dump(),
                headers=_headers(key),
            )
            assert resp.status_code == 401, key

    def test_unauthorized_tenant_rejected(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-OTHER"], ALL_PERMS),
        ])
        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry(tenant_id="tenant-1").model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 403

    def test_missing_execute_permission_rejected(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-1"],
                        [Permission.VIEW_STATUS]),
        ])
        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry().model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 403


class TestAuthenticatedExecutionPath:
    POLICY = {
        "version": 1,
        "rules": [
            {
                "tenant_id": "tenant-1",
                "principal_id": "agent-001",
                "operations": ["isolate_host"],
                "action_classes": {"isolate_host": "A0_observe"},
                "required_approval": "none",
            }
        ],
    }

    def _records(self, **kw):
        return [_key_record("k1", RAW_KEY, "agent-001", ["tenant-1"], ALL_PERMS, **kw)]

    def test_authorized_principal_reaches_execution_boundary(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, self._records(), policy_doc=self.POLICY)
        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry().model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        # The recorder executor ran: intent was recorded by ExecutionKernel
        assert len(runtime_main.execution_kernel.executed_intents) >= 1

        # Audit records carry the authenticated principal, not the subject
        records = runtime_main.audit_logger.get_audit_records("corr-auth")
        executed = [r for r in records if r.event_kind == "intent_executed"]
        assert executed, "expected intent_executed audit record"
        ref = executed[0].payload_ref["ref"]
        assert ref["principal_id"] == "agent-001"
        assert ref["executed"] is True

    def test_policy_rule_for_other_principal_blocks(self, tmp_path, monkeypatch):
        """Authenticated but unmatched principal: policy denies, no dispatch."""
        policy = {
            "version": 1,
            "rules": [dict(self.POLICY["rules"][0], principal_id="agent-OTHER")],
        }
        client = _setup(tmp_path, monkeypatch, self._records(), policy_doc=policy)
        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry().model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert len(runtime_main.execution_kernel.executed_intents) == 0
        records = runtime_main.audit_logger.get_audit_records("corr-auth")
        blocked = [r for r in records if r.event_kind == "execution_blocked"]
        assert blocked
        assert blocked[0].payload_ref["ref"]["principal_id"] == "agent-001"

    def test_request_cannot_impersonate_principal_via_subject(self, tmp_path, monkeypatch):
        """Telemetry attributes cannot act as caller identity for policy."""
        # Policy only authorizes agent-OTHER; the event's entity/subject
        # fields claim agent-OTHER, but the API key principal is agent-001.
        policy = {
            "version": 1,
            "rules": [dict(self.POLICY["rules"][0], principal_id="agent-OTHER")],
        }
        client = _setup(tmp_path, monkeypatch, self._records(), policy_doc=policy)
        event = _telemetry()
        event.attributes["claimed_principal"] = "agent-OTHER"
        resp = client.post(
            "/v1/telemetry/ingest",
            json=event.model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert len(runtime_main.execution_kernel.executed_intents) == 0


class _MockKVStore:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.data = {}

    async def get(self, key):
        if key in self.data:
            return self.data[key]
        raise KeyError(key)

    async def put(self, key, value):
        self.data[key] = value.encode() if isinstance(value, str) else value


class _MockJS:
    def __init__(self):
        self.stores = {}

    async def create_key_value(self, bucket, description=None):
        if bucket not in self.stores:
            self.stores[bucket] = _MockKVStore(bucket)
        return self.stores[bucket]


class _MockNATS:
    def __init__(self):
        self.js = _MockJS()

    async def publish(self, subject, data):
        pass


class TestKillSwitchStillBlocks:
    @pytest.mark.usefixtures("kill_switch_test_mode")
    def test_active_tenant_switch_blocks_authenticated_caller(self, tmp_path, monkeypatch):
        from exoarmur.safety.execution_gate import ExecutionGate

        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-1"], ALL_PERMS),
        ], policy_doc=TestAuthenticatedExecutionPath.POLICY)

        gate = ExecutionGate(nats_client=_MockNATS())
        asyncio.run(gate._ensure_kv_stores())
        asyncio.run(gate._global_kill_switch_kv.put("switch_all_execution", "inactive"))
        asyncio.run(gate._tenant_kill_switch_kv.put("tenant-1_switch_all_execution", "active"))
        runtime_main.execution_gate = gate

        resp = client.post(
            "/v1/telemetry/ingest",
            json=_telemetry().model_dump(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert len(runtime_main.execution_kernel.executed_intents) == 0
        records = runtime_main.audit_logger.get_audit_records("corr-auth")
        assert any(r.event_kind == "kill_switch_block" for r in records)


class TestApprovalEndpoints:
    def _make_approval(self):
        return runtime_main.approval_service.create_request(
            correlation_id="corr-appr",
            trace_id="trace-appr",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="idem-appr",
            requested_action_class="A1_soft_containment",
            payload_ref={},
        )

    def _client_with_granter(self, tmp_path, monkeypatch, permissions):
        return _setup(tmp_path, monkeypatch, [
            _key_record("k-grant", "grant-key", "operator-1", ["tenant-1"], permissions),
        ])

    def test_approve_requires_auth_and_grant_permission(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k1", RAW_KEY, "agent-001", ["tenant-1"],
                        [Permission.EXECUTE_A0]),
        ])
        approval_id = self._make_approval()

        # No key -> 401
        resp = client.post(f"/v1/approvals/{approval_id}/approve",
                           json={"operator_id": "agent-001"})
        assert resp.status_code == 401

        # Key without approval:grant -> 403
        resp = client.post(f"/v1/approvals/{approval_id}/approve",
                           json={"operator_id": "agent-001"},
                           headers=_headers())
        assert resp.status_code == 403

    def test_approve_records_authenticated_operator(self, tmp_path, monkeypatch):
        client = self._client_with_granter(tmp_path, monkeypatch,
                                           [Permission.GRANT_APPROVAL, Permission.VIEW_STATUS])
        approval_id = self._make_approval()

        resp = client.post(
            f"/v1/approvals/{approval_id}/approve",
            json={"operator_id": "operator-1"},
            headers=_headers("grant-key"),
        )
        assert resp.status_code == 200
        details = runtime_main.approval_service.get_approval_details(approval_id)
        assert details.status == "APPROVED"
        assert details.approved_by == "operator-1"

    def test_impersonation_rejected(self, tmp_path, monkeypatch):
        client = self._client_with_granter(tmp_path, monkeypatch,
                                           [Permission.GRANT_APPROVAL])
        approval_id = self._make_approval()

        # operator_id claims someone else -> 403, approval stays PENDING
        resp = client.post(
            f"/v1/approvals/{approval_id}/approve",
            json={"operator_id": "operator-OTHER"},
            headers=_headers("grant-key"),
        )
        assert resp.status_code == 403
        details = runtime_main.approval_service.get_approval_details(approval_id)
        assert details.status == "PENDING"
        assert details.approved_by is None

    def test_deny_requires_permission_and_records_principal(self, tmp_path, monkeypatch):
        client = _setup(tmp_path, monkeypatch, [
            _key_record("k-deny", "deny-key", "operator-2", ["tenant-1"],
                        [Permission.DENY_APPROVAL]),
        ])
        approval_id = self._make_approval()

        resp = client.post(
            f"/v1/approvals/{approval_id}/deny",
            json={"operator_id": "operator-2", "reason": "too risky"},
            headers=_headers("deny-key"),
        )
        assert resp.status_code == 200
        details = runtime_main.approval_service.get_approval_details(approval_id)
        assert details.status == "DENIED"
        assert details.approved_by == "operator-2"

    def test_approval_status_requires_auth(self, tmp_path, monkeypatch):
        client = self._client_with_granter(tmp_path, monkeypatch,
                                           [Permission.VIEW_STATUS])
        approval_id = self._make_approval()

        resp = client.get(f"/v1/approvals/{approval_id}")
        assert resp.status_code == 401
        resp = client.get(f"/v1/approvals/{approval_id}", headers=_headers("grant-key"))
        assert resp.status_code == 200
