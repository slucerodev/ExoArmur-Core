"""
Integration tests for the ExoArmur API layer.

These tests use httpx against the actual FastAPI application (via ASGI
transport) so they exercise the real routing, serialisation, and store logic
without requiring a live TCP port.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from exoarmur.api.server import create_app


@pytest.fixture
async def client():
    # Reset in-memory stores before each test to ensure isolation
    from exoarmur.api.stores import (
        observation_store,
        belief_store,
        audit_store,
        approval_store,
        federate_store,
        arbitration_store,
        benchmark_history,
    )

    observation_store._observations.clear()
    belief_store._beliefs.clear()
    audit_store._records.clear()
    approval_store._approvals.clear()
    federate_store._federates.clear()
    arbitration_store._arbitrations.clear()
    benchmark_history._runs.clear()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ============================================================================
# Core / Health
# ============================================================================


@pytest.mark.anyio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["service"] == "exoarmur-api"


# ============================================================================
# Bridge / Determinism
# ============================================================================


@pytest.mark.anyio
async def test_determinism_status_empty(client: AsyncClient) -> None:
    r = await client.get("/api/cli/determinism-status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("PASS", "FAIL")
    assert data["run_id"] == "none"


@pytest.mark.anyio
async def test_benchmark_and_determinism_status(client: AsyncClient) -> None:
    r = await client.get("/api/cli/benchmark?mode=determinism&concurrency=10&runs=50")
    assert r.status_code == 200
    bench = r.json()
    assert bench["mode"] == "determinism"
    assert bench["status"] == "PASS"
    assert bench["unique_hashes"] == 1

    r = await client.get("/api/cli/determinism-status")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == bench["run_id"]
    assert data["unique_hashes"] == 1


@pytest.mark.anyio
async def test_hash_verification(client: AsyncClient) -> None:
    r = await client.get("/api/cli/hash-verification")
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] in ("MATCH", "MISMATCH", "STALE_CORE_VERSION")


# ============================================================================
# Bridge / Live Proof
# ============================================================================


@pytest.mark.anyio
async def test_live_proof(client: AsyncClient) -> None:
    r = await client.post("/api/cli/live-proof", json={"concurrency": 10, "runs": 50})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "PASS"
    assert data["unique_hashes"] == 1


# ============================================================================
# Bridge / Replay
# ============================================================================


@pytest.mark.anyio
async def test_replay_empty(client: AsyncClient) -> None:
    r = await client.post("/api/cli/replay", json={"correlation_id": "test-corr-001"})
    assert r.status_code == 200
    data = r.json()
    assert data["verdict"] == "MATCH"
    assert len(data["stages"]) == 5
    for s in data["stages"]:
        assert s["status"] == "absent"


# ============================================================================
# V1 / Telemetry + Approvals
# ============================================================================


@pytest.mark.anyio
async def test_telemetry_ingest_creates_approval(client: AsyncClient) -> None:
    r = await client.post("/v1/telemetry/ingest", json={
        "observation_type": "anomaly",
        "source_federate_id": "cell-test",
        "confidence": 0.95,
        "payload_type": "json",
        "payload_data": {"alert": "test"},
        "evidence_refs": ["ev-001"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ingested"
    assert data["approval_required"] is True
    assert data["approval_id"] is not None

    # Fetch approval
    approval_id = data["approval_id"]
    r = await client.get(f"/v1/approvals/{approval_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"

    # Approve
    r = await client.post(
        f"/v1/approvals/{approval_id}/approve",
        headers={"operator-id": "test-op"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    # Verify status updated
    r = await client.get(f"/v1/approvals/{approval_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"


@pytest.mark.anyio
async def test_telemetry_ingest_low_confidence_no_approval(client: AsyncClient) -> None:
    r = await client.post("/v1/telemetry/ingest", json={
        "observation_type": "metric",
        "source_federate_id": "cell-test",
        "confidence": 0.30,
        "payload_type": "json",
        "payload_data": {"value": 42},
        "evidence_refs": [],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["approval_required"] is False
    assert data["approval_id"] is None


@pytest.mark.anyio
async def test_deny_requires_reason(client: AsyncClient) -> None:
    r = await client.post("/v1/telemetry/ingest", json={
        "observation_type": "anomaly",
        "source_federate_id": "cell-test",
        "confidence": 0.95,
        "payload_type": "json",
        "payload_data": {},
        "evidence_refs": [],
    })
    approval_id = r.json()["approval_id"]

    # Deny without reason → 422
    r = await client.post(
        f"/v1/approvals/{approval_id}/deny",
        headers={"operator-id": "test-op"},
    )
    assert r.status_code == 422

    # Deny with reason → success
    r = await client.post(
        f"/v1/approvals/{approval_id}/deny",
        headers={"operator-id": "test-op", "reason": "suspicious pattern"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "DENIED"


@pytest.mark.anyio
async def test_approve_without_operator_id(client: AsyncClient) -> None:
    r = await client.post("/v1/telemetry/ingest", json={
        "observation_type": "anomaly",
        "source_federate_id": "cell-test",
        "confidence": 0.95,
        "payload_type": "json",
        "payload_data": {},
        "evidence_refs": [],
    })
    approval_id = r.json()["approval_id"]

    r = await client.post(f"/v1/approvals/{approval_id}/approve")
    assert r.status_code == 401


# ============================================================================
# V1 / Audit
# ============================================================================


@pytest.mark.anyio
async def test_audit_empty(client: AsyncClient) -> None:
    r = await client.get("/v1/audit/nonexistent-corr")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 0
    assert data["audit_records"] == []


# ============================================================================
# V2 / Visibility
# ============================================================================


@pytest.mark.anyio
async def test_visibility_statistics(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/statistics")
    assert r.status_code == 200
    data = r.json()
    assert "ingest_statistics" in data
    assert "belief_statistics" in data
    assert "timestamp" in data


@pytest.mark.anyio
async def test_visibility_observations(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/observations?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_visibility_beliefs(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/beliefs?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_visibility_federates(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/federates")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_visibility_arbitrations(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/arbitrations?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_visibility_timeline_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v2/visibility/timeline/test-corr")
    assert r.status_code == 200
    data = r.json()
    assert data["correlation_id"] == "test-corr"
    assert data["observations"] == []
    assert data["beliefs"] == []
