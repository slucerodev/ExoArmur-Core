"""
Round-trip tests: verify every Pydantic model serialises to JSON that
matches the structure expected by the dashboard's Zod schemas.

These tests do not run Zod (no JS runtime here).  Instead they enforce
the same structural constraints (required fields, discriminant values,
field types) that the Zod schemas enforce on the frontend.
"""

import json
from datetime import datetime, timezone

import pytest

from exoarmur.api.models import (
    ApprovalResponse,
    ApprovalStatusResponse,
    ArbitrationInfo,
    AuditRecord,
    AuditResponse,
    BeliefInfo,
    BenchmarkDeterminism,
    BenchmarkNoise,
    BenchmarkReplay,
    BenchmarkThroughput,
    ContainmentStatus,
    DeterminismStatus,
    ErrorEnvelope,
    FederateInfo,
    HashVerification,
    HealthResponse,
    LiveProofResponse,
    ObservationInfo,
    ReplayMismatch,
    ReplayResult,
    ReplayStage,
    ReplayTargetCorrelationId,
    TimelineInfo,
    VisibilityStats,
)


# ============================================================================
# Health
# ============================================================================

def test_health_response_serialises() -> None:
    obj = HealthResponse(status="healthy", service="exoarmur-api", version="2.2.0")
    raw = obj.model_dump_json()
    data = json.loads(raw)
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "exoarmur-api"
    assert data["version"] == "2.2.0"


# ============================================================================
# Determinism
# ============================================================================

def test_determinism_status_serialises() -> None:
    obj = DeterminismStatus(
        run_id="run-001",
        core_version="2.2.0",
        status="PASS",
        unique_hashes=1,
        concurrency=500,
        executions=100,
        failures=0,
        runtime_ms=1234,
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["status"] in ("PASS", "FAIL")
    assert data["unique_hashes"] >= 0
    assert data["runtime_ms"] >= 0


# ============================================================================
# Hash verification
# ============================================================================

def test_hash_verification_serialises() -> None:
    obj = HashVerification(
        run_id="run-001",
        core_version="2.2.0",
        verdict="MATCH",
        input_hash="abc123",
        execution_hash="abc123",
        replay_hash="abc123",
        all_equal=True,
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["verdict"] in ("MATCH", "MISMATCH", "STALE_CORE_VERSION")
    assert data["input_hash"]
    assert data["execution_hash"]


# ============================================================================
# Benchmark (discriminated union)
# ============================================================================

def test_benchmark_determinism_serialises() -> None:
    obj = BenchmarkDeterminism(
        run_id="run-001",
        core_version="2.2.0",
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
        mode="determinism",
        concurrency=500,
        runs=100,
        unique_hashes=1,
        status="PASS",
        failures=0,
    )
    data = json.loads(obj.model_dump_json())
    assert data["mode"] == "determinism"
    assert data["status"] in ("PASS", "FAIL")


def test_benchmark_throughput_serialises() -> None:
    obj = BenchmarkThroughput(
        run_id="run-001",
        core_version="2.2.0",
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
        mode="throughput",
        concurrency=100,
        runs=1000,
        executions_per_second=500.0,
        latency_p50_ms=10.0,
        latency_p95_ms=25.0,
        latency_p99_ms=50.0,
    )
    data = json.loads(obj.model_dump_json())
    assert data["mode"] == "throughput"
    assert data["latency_p99_ms"] >= data["latency_p50_ms"]


def test_benchmark_replay_serialises() -> None:
    obj = BenchmarkReplay(
        run_id="run-001",
        core_version="2.2.0",
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
        mode="replay",
        runs=50,
        replay_time_avg_ms=15.0,
        replay_time_p95_ms=25.0,
        replay_time_p99_ms=35.0,
    )
    data = json.loads(obj.model_dump_json())
    assert data["mode"] == "replay"


def test_benchmark_noise_serialises() -> None:
    obj = BenchmarkNoise(
        run_id="run-001",
        core_version="2.2.0",
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
        mode="noise",
        runs=10,
        noise_level=0.05,
        hash_stable=True,
        latency_impact_ms=2.0,
    )
    data = json.loads(obj.model_dump_json())
    assert data["mode"] == "noise"
    assert isinstance(data["hash_stable"], bool)


# ============================================================================
# Replay
# ============================================================================

def test_replay_result_serialises() -> None:
    obj = ReplayResult(
        run_id="run-001",
        target=ReplayTargetCorrelationId(correlation_id="corr-001"),
        core_version="2.2.0",
        audit_bundle_digest="digest-001",
        input_hash="abc",
        execution_hash="abc",
        replay_hash="abc",
        verdict="MATCH",
        stages=[
            ReplayStage(stage="intent", status="match", hash="h1"),
            ReplayStage(stage="policy", status="match", hash="h2"),
            ReplayStage(stage="gate", status="match", hash="h3"),
            ReplayStage(stage="executor", status="match", hash="h4"),
            ReplayStage(stage="evidence", status="match", hash="h5"),
        ],
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["verdict"] in ("MATCH", "MISMATCH", "STALE_CORE_VERSION")
    assert len(data["stages"]) == 5
    for s in data["stages"]:
        assert s["stage"] in ("intent", "policy", "gate", "executor", "evidence")
        assert s["status"] in ("match", "mismatch", "absent")


def test_replay_mismatch_serialises() -> None:
    obj = ReplayResult(
        run_id="run-001",
        target=ReplayTargetCorrelationId(correlation_id="corr-001"),
        core_version="2.2.0",
        audit_bundle_digest="digest-001",
        input_hash="abc",
        execution_hash="abc",
        replay_hash="def",
        verdict="MISMATCH",
        mismatch=ReplayMismatch(
            first_divergence_stage="executor",
            expected_hash="abc",
            actual_hash="def",
        ),
        stages=[
            ReplayStage(stage="intent", status="match", hash="h1"),
            ReplayStage(stage="executor", status="mismatch", hash="h4"),
        ],
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:00:01Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["mismatch"]["first_divergence_stage"] == "executor"
    assert data["mismatch"]["expected_hash"] == "abc"
    assert data["mismatch"]["actual_hash"] == "def"


# ============================================================================
# Visibility
# ============================================================================

def test_federate_info_serialises() -> None:
    obj = FederateInfo(
        federate_id="cell-001",
        federation_role="observer",
        cell_status="active",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        public_key="pk-001",
    )
    data = json.loads(obj.model_dump_json())
    assert data["federate_id"]
    assert data["cell_status"]


def test_observation_info_serialises() -> None:
    obj = ObservationInfo(
        observation_id="obs-001",
        source_federate_id="cell-001",
        timestamp_utc="2024-01-01T00:00:00Z",
        correlation_id="corr-001",
        observation_type="anomaly",
        confidence=0.95,
        evidence_refs=["ev-001"],
        payload_type="json",
        payload_data={"key": "value"},
    )
    data = json.loads(obj.model_dump_json())
    assert 0.0 <= data["confidence"] <= 1.0
    assert isinstance(data["evidence_refs"], list)


def test_belief_info_serialises() -> None:
    obj = BeliefInfo(
        belief_id="belief-001",
        belief_type="threat_detected",
        confidence=0.88,
        source_observations=["obs-001"],
        derived_at="2024-01-01T00:00:00Z",
        correlation_id="corr-001",
        evidence_summary="High-confidence anomaly",
        conflicts=[],
        metadata={},
    )
    data = json.loads(obj.model_dump_json())
    assert data["belief_type"]
    assert isinstance(data["source_observations"], list)


def test_timeline_info_serialises() -> None:
    obj = TimelineInfo(
        correlation_id="corr-001",
        observations=[
            ObservationInfo(
                observation_id="obs-001",
                source_federate_id="cell-001",
                timestamp_utc="2024-01-01T00:00:00Z",
                correlation_id="corr-001",
                observation_type="anomaly",
                confidence=0.95,
                evidence_refs=["ev-001"],
                payload_type="json",
                payload_data={},
            )
        ],
        beliefs=[
            BeliefInfo(
                belief_id="belief-001",
                belief_type="threat_detected",
                confidence=0.88,
                source_observations=["obs-001"],
                derived_at="2024-01-01T00:00:00Z",
                correlation_id="corr-001",
                evidence_summary="Anomaly",
                conflicts=[],
                metadata={},
            )
        ],
    )
    data = json.loads(obj.model_dump_json())
    assert len(data["observations"]) == 1
    assert len(data["beliefs"]) == 1


def test_visibility_stats_serialises() -> None:
    obj = VisibilityStats()
    data = json.loads(obj.model_dump_json())
    assert "ingest_statistics" in data
    assert "belief_statistics" in data
    assert "timestamp" in data


def test_arbitration_info_serialises() -> None:
    obj = ArbitrationInfo(
        arbitration_id="arb-001",
        created_at_utc="2024-01-01T00:00:00Z",
        status="PENDING",
        conflict_type="belief_conflict",
        subject_key="subject-001",
        conflict_key="conflict-001",
        claims=[{"key": "value"}],
        evidence_refs=["ev-001"],
        correlation_id="corr-001",
        proposed_resolution=None,
        decision=None,
        approval_id=None,
    )
    data = json.loads(obj.model_dump_json())
    assert data["status"]
    assert isinstance(data["claims"], list)


def test_containment_status_serialises() -> None:
    obj = ContainmentStatus(
        subject_id="sub-001",
        provider="local",
        scope="tenant",
        status="active",
        applied_at="2024-01-01T00:00:00Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["subject_id"]
    assert data["status"]


def test_audit_record_serialises() -> None:
    obj = AuditRecord(
        audit_id="audit-001",
        event_kind="executor_dispatch",
        payload_ref={"success": True},
        correlation_id="corr-001",
        trace_id="trace-001",
        tenant_id="tenant-001",
        cell_id="cell-001",
        idempotency_key="key-001",
        created_at="2024-01-01T00:00:00Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["audit_id"]
    assert data["event_kind"]
    assert data["correlation_id"]


def test_audit_response_serialises() -> None:
    obj = AuditResponse(
        correlation_id="corr-001",
        audit_records=[
            AuditRecord(
                audit_id="audit-001",
                event_kind="test",
                payload_ref={},
                correlation_id="corr-001",
                trace_id="trace-001",
                tenant_id="tenant-001",
                cell_id="cell-001",
                idempotency_key="key-001",
                created_at="2024-01-01T00:00:00Z",
            )
        ],
        total_count=1,
        retrieved_at="2024-01-01T00:00:00Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["total_count"] == 1
    assert len(data["audit_records"]) == 1


# ============================================================================
# Approvals
# ============================================================================

def test_approval_status_response_serialises() -> None:
    obj = ApprovalStatusResponse(
        approval_id="app-001",
        status="PENDING",
        created_at="2024-01-01T00:00:00Z",
        requested_action_class="A2_HARD_CONTAINMENT",
        correlation_id="corr-001",
    )
    data = json.loads(obj.model_dump_json())
    assert data["status"] in ("PENDING", "APPROVED", "DENIED")
    assert data["approval_id"]


def test_approval_response_serialises() -> None:
    obj = ApprovalResponse(
        approval_id="app-001",
        status="APPROVED",
        created_at="2024-01-01T00:00:00Z",
    )
    data = json.loads(obj.model_dump_json())
    assert data["status"] in ("APPROVED", "DENIED")


# ============================================================================
# Error envelope
# ============================================================================

def test_error_envelope_serialises() -> None:
    obj = ErrorEnvelope(
        code="NOT_FOUND",
        http_status=404,
        message="Resource not found",
        severity="error",
        endpoint="/v1/approvals/app-001",
        request_id="req-001",
        at="2024-01-01T00:00:00Z",
        field="approval_id",
        details={"hint": "Check the ID and try again"},
    )
    data = json.loads(obj.model_dump_json())
    assert data["code"]
    assert data["http_status"] == 404
    assert data["severity"]
    assert data["request_id"]


# ============================================================================
# Live proof
# ============================================================================

def test_live_proof_response_serialises() -> None:
    obj = LiveProofResponse(
        status="PASS",
        run_id="run-001",
        concurrency=500,
        runs=100,
        unique_hashes=1,
        failures=0,
        runtime_ms=1234,
    )
    data = json.loads(obj.model_dump_json())
    assert data["status"] in ("PASS", "FAIL")
    assert data["unique_hashes"] >= 0
    assert data["failures"] >= 0


# ============================================================================
# Server creation (smoke test)
# ============================================================================

def test_server_creates_without_error() -> None:
    from fastapi.routing import APIRoute
    from exoarmur.api.server import create_app

    app = create_app()
    assert app is not None
    routes = [r.path for r in app.routes if isinstance(r, APIRoute)]
    assert "/health" in routes
