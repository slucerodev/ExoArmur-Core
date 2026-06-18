"""
Pydantic v2 response models that round-trip with the dashboard's Zod contracts.

Every model in this file is the backend-side mirror of a Zod schema defined in
`dashboard/src/lib/contracts/`.  Changes here must be paired with Zod updates
and vice-versa.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ============================================================================
# §3.7 Health
# ============================================================================

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: Optional[str] = None
    version: Optional[str] = None


# ============================================================================
# §3.14 Determinism status
# ============================================================================

class DeterminismStatus(BaseModel):
    run_id: str
    core_version: str
    status: Literal["PASS", "FAIL"]
    unique_hashes: int
    concurrency: int
    executions: int
    failures: int
    runtime_ms: int
    started_at: str
    finished_at: str


# ============================================================================
# §3.15 Hash verification
# ============================================================================

HashVerdict = Literal["MATCH", "MISMATCH", "STALE_CORE_VERSION"]


class HashVerification(BaseModel):
    run_id: str
    core_version: str
    verdict: HashVerdict
    reason: Optional[str] = None
    reason_detail: Optional[str] = None
    input_hash: str
    execution_hash: str
    replay_hash: Optional[str] = None
    all_equal: Optional[bool] = None
    started_at: str
    finished_at: str


# ============================================================================
# §3.3 Benchmark Result — discriminated union by `mode`
# ============================================================================

class BenchmarkBase(BaseModel):
    run_id: str = Field(..., min_length=1)
    core_version: str = Field(..., min_length=1)
    started_at: str
    finished_at: str


class BenchmarkDeterminism(BenchmarkBase):
    mode: Literal["determinism"]
    concurrency: int = Field(..., ge=0)
    runs: int = Field(..., ge=0)
    unique_hashes: int = Field(..., ge=0)
    status: Literal["PASS", "FAIL"]
    failures: int = Field(..., ge=0)


class BenchmarkThroughput(BenchmarkBase):
    mode: Literal["throughput"]
    concurrency: int = Field(..., ge=0)
    runs: int = Field(..., ge=0)
    executions_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float


class BenchmarkReplay(BenchmarkBase):
    mode: Literal["replay"]
    runs: int = Field(..., ge=0)
    replay_time_avg_ms: float
    replay_time_p95_ms: float
    replay_time_p99_ms: float


class BenchmarkNoise(BenchmarkBase):
    mode: Literal["noise"]
    runs: int = Field(..., ge=0)
    noise_level: float
    hash_stable: bool
    latency_impact_ms: float


BenchmarkResult = Union[
    BenchmarkDeterminism,
    BenchmarkThroughput,
    BenchmarkReplay,
    BenchmarkNoise,
]


# ============================================================================
# §3.2 Replay
# ============================================================================

ReplayVerdict = Literal["MATCH", "MISMATCH", "STALE_CORE_VERSION"]


class ReplayTargetCorrelationId(BaseModel):
    correlation_id: str = Field(..., min_length=1)


class ReplayTargetIntentId(BaseModel):
    intent_id: str = Field(..., min_length=1)


ReplayTarget = Union[ReplayTargetCorrelationId, ReplayTargetIntentId]


class ReplayStage(BaseModel):
    stage: Literal["intent", "policy", "gate", "executor", "evidence"]
    status: Literal["match", "mismatch", "absent"]
    hash: Optional[str] = None


class ReplayMismatch(BaseModel):
    first_divergence_stage: Literal[
        "intent", "policy", "gate", "executor", "evidence"
    ]
    expected_hash: str
    actual_hash: str


class ReplayResult(BaseModel):
    run_id: str = Field(..., min_length=1)
    target: ReplayTarget
    core_version: str = Field(..., min_length=1)
    audit_bundle_digest: str = Field(..., min_length=1)
    input_hash: str
    execution_hash: str
    replay_hash: Optional[str] = None
    verdict: ReplayVerdict
    mismatch: Optional[ReplayMismatch] = None
    stages: List[ReplayStage]
    started_at: str
    finished_at: str


class ReplayRequest(BaseModel):
    correlation_id: Optional[str] = Field(None, min_length=1)
    intent_id: Optional[str] = Field(None, min_length=1)


# ============================================================================
# §3.12 Visibility API
# ============================================================================

class FederateInfo(BaseModel):
    federate_id: str
    federation_role: str
    cell_status: str
    created_at: str
    updated_at: str
    public_key: Optional[str] = None


class ObservationInfo(BaseModel):
    observation_id: str
    source_federate_id: str
    timestamp_utc: str
    correlation_id: Optional[str] = None
    observation_type: str
    confidence: float
    evidence_refs: List[str]
    payload_type: str
    payload_data: Dict[str, Any]


class BeliefInfo(BaseModel):
    belief_id: str
    belief_type: str
    confidence: float
    source_observations: List[str]
    derived_at: str
    correlation_id: Optional[str] = None
    evidence_summary: str
    conflicts: List[str]
    metadata: Dict[str, Any]


class TimelineInfo(BaseModel):
    correlation_id: str
    observations: List[ObservationInfo]
    beliefs: List[BeliefInfo]


class VisibilityStats(BaseModel):
    ingest_statistics: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_ingested": 0,
            "total_signals": 0,
            "safety_evaluations": 0,
            "total_executed": 0,
        }
    )
    belief_statistics: Dict[str, Any] = Field(
        default_factory=lambda: {"total_beliefs": 0, "collective_count": 0}
    )
    store_statistics: Dict[str, Any] = Field(
        default_factory=lambda: {"total_records": 0}
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    arbitration_statistics: Optional[Dict[str, Any]] = None


class ArbitrationInfo(BaseModel):
    arbitration_id: str
    created_at_utc: str
    status: str
    conflict_type: str
    subject_key: str
    conflict_key: str
    claims: List[Dict[str, Any]]
    evidence_refs: List[str]
    correlation_id: Optional[str] = None
    proposed_resolution: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None


class ContainmentStatus(BaseModel):
    subject_id: str
    provider: str
    scope: str
    status: str
    applied_at: Optional[str] = None
    expires_at: Optional[str] = None
    approval_id: Optional[str] = None


class AuditRecord(BaseModel):
    audit_id: str
    event_kind: str
    payload_ref: Dict[str, Any]
    correlation_id: str
    trace_id: str
    tenant_id: str
    cell_id: str
    idempotency_key: str
    created_at: str


class AuditResponse(BaseModel):
    correlation_id: str
    audit_records: List[AuditRecord]
    total_count: int
    retrieved_at: str


# ============================================================================
# §3.10 / §3.11 Approvals
# ============================================================================

class ApprovalStatusResponse(BaseModel):
    approval_id: str
    status: Literal["PENDING", "APPROVED", "DENIED"]
    created_at: str
    requested_action_class: str
    correlation_id: str


class ApprovalResponse(BaseModel):
    approval_id: str
    status: Literal["APPROVED", "DENIED"]
    created_at: str


# ============================================================================
# §3.1 Error Envelope
# ============================================================================

class ErrorEnvelope(BaseModel):
    code: str
    http_status: int
    message: str
    severity: str
    endpoint: str
    request_id: str
    at: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Telemetry / Ingest
# ============================================================================

class TelemetryIngestRequest(BaseModel):
    observation_type: str
    source_federate_id: str
    correlation_id: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    payload_type: str = "json"
    payload_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)


class TelemetryIngestResponse(BaseModel):
    observation_id: str
    status: str
    approval_required: bool
    approval_id: Optional[str] = None


# ============================================================================
# Live Proof
# ============================================================================

class LiveProofRequest(BaseModel):
    concurrency: int = Field(default=500, ge=1, le=10000)
    runs: int = Field(default=100, ge=1, le=100000)


class LiveProofResponse(BaseModel):
    status: Literal["PASS", "FAIL"]
    run_id: str
    concurrency: int
    runs: int
    unique_hashes: int
    failures: int
    runtime_ms: int


# ============================================================================
# Admin / Consistency (Phase 6 dual-write verification)
# ============================================================================

class ConsistencyCheckResponse(BaseModel):
    store_name: str
    memory_count: int
    db_count: int
    consistent: bool
    checked_at: str
