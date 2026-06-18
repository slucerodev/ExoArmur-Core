"""
Asyncpg-backed repository implementations.

Each repository mirrors the interface of its in-memory store counterpart
so that `stores.py` can delegate to either (or both in dual-write mode).

All methods return the same types as the in-memory stores and raise the
same exceptions on invalid state transitions.
"""

from typing import Any, Dict, List, Optional

from exoarmur.api.models import (
    ApprovalStatusResponse,
    ArbitrationInfo,
    AuditRecord,
    BeliefInfo,
    BenchmarkResult,
    FederateInfo,
    ObservationInfo,
)


async def _get_pool():
    try:
        from exoarmur.api.db import get_pool
        return await get_pool()
    except ImportError:
        return None


class ObservationRepository:
    async def add(self, observation: ObservationInfo) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO observations (
                    observation_id, source_federate_id, timestamp_utc,
                    correlation_id, observation_type, confidence,
                    evidence_refs, payload_type, payload_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (observation_id) DO NOTHING
                """,
                observation.observation_id,
                observation.source_federate_id,
                observation.timestamp_utc,
                observation.correlation_id,
                observation.observation_type,
                observation.confidence,
                observation.evidence_refs,
                observation.payload_type,
                observation.payload_data,
            )

    async def list(self, limit: int = 100, offset: int = 0) -> List[ObservationInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT observation_id, source_federate_id, timestamp_utc,
                       correlation_id, observation_type, confidence,
                       evidence_refs, payload_type, payload_data
                FROM observations
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [_row_to_observation(r) for r in rows]

    async def get_by_correlation(self, correlation_id: str) -> List[ObservationInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT observation_id, source_federate_id, timestamp_utc,
                       correlation_id, observation_type, confidence,
                       evidence_refs, payload_type, payload_data
                FROM observations
                WHERE correlation_id = $1
                ORDER BY created_at DESC
                """,
                correlation_id,
            )
        return [_row_to_observation(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM observations") or 0


class BeliefRepository:
    async def add(self, belief: BeliefInfo) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO beliefs (
                    belief_id, belief_type, confidence,
                    source_observations, derived_at, correlation_id,
                    evidence_summary, conflicts, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (belief_id) DO NOTHING
                """,
                belief.belief_id,
                belief.belief_type,
                belief.confidence,
                belief.source_observations,
                belief.derived_at,
                belief.correlation_id,
                belief.evidence_summary,
                belief.conflicts,
                belief.metadata,
            )

    async def list(self, limit: int = 100, offset: int = 0) -> List[BeliefInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT belief_id, belief_type, confidence,
                       source_observations, derived_at, correlation_id,
                       evidence_summary, conflicts, metadata
                FROM beliefs
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [_row_to_belief(r) for r in rows]

    async def get_by_correlation(self, correlation_id: str) -> List[BeliefInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT belief_id, belief_type, confidence,
                       source_observations, derived_at, correlation_id,
                       evidence_summary, conflicts, metadata
                FROM beliefs
                WHERE correlation_id = $1
                ORDER BY created_at DESC
                """,
                correlation_id,
            )
        return [_row_to_belief(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM beliefs") or 0


class AuditRepository:
    async def append(self, record: AuditRecord) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_records (
                    audit_id, event_kind, payload_ref, correlation_id,
                    trace_id, tenant_id, cell_id, idempotency_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                record.audit_id,
                record.event_kind,
                record.payload_ref,
                record.correlation_id,
                record.trace_id,
                record.tenant_id,
                record.cell_id,
                record.idempotency_key,
            )

    async def get_by_correlation(self, correlation_id: str) -> List[AuditRecord]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT audit_id, event_kind, payload_ref, correlation_id,
                       trace_id, tenant_id, cell_id, idempotency_key, created_at
                FROM audit_records
                WHERE correlation_id = $1
                ORDER BY created_at DESC
                """,
                correlation_id,
            )
        return [_row_to_audit(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM audit_records") or 0

    async def count_by_correlation(self, correlation_id: str) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM audit_records WHERE correlation_id = $1",
                correlation_id,
            ) or 0


class ApprovalRepository:
    async def create(self, approval: ApprovalStatusResponse) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO approvals (
                    approval_id, status, created_at,
                    requested_action_class, correlation_id
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (approval_id) DO NOTHING
                """,
                approval.approval_id,
                approval.status,
                approval.created_at,
                approval.requested_action_class,
                approval.correlation_id,
            )

    async def get(self, approval_id: str) -> Optional[ApprovalStatusResponse]:
        pool = await _get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT approval_id, status, created_at,
                       requested_action_class, correlation_id
                FROM approvals
                WHERE approval_id = $1
                """,
                approval_id,
            )
        if row is None:
            return None
        return _row_to_approval(row)

    async def update_status(
        self,
        approval_id: str,
        new_status: str,
        operator_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ApprovalStatusResponse]:
        pool = await _get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    "SELECT status FROM approvals WHERE approval_id = $1 FOR UPDATE",
                    approval_id,
                )
                if current is None:
                    raise KeyError(f"Approval {approval_id} not found")
                if current["status"] != "PENDING":
                    raise ValueError(
                        f"Approval {approval_id} is already {current['status']}"
                    )
                if new_status not in ("APPROVED", "DENIED"):
                    raise ValueError(f"Invalid status transition to {new_status}")
                if new_status == "DENIED" and not reason:
                    raise ValueError("Denial requires a reason")

                await conn.execute(
                    """
                    UPDATE approvals
                    SET status = $1, operator_id = $2, reason = $3, resolved_at = NOW()
                    WHERE approval_id = $4
                    """,
                    new_status,
                    operator_id,
                    reason,
                    approval_id,
                )
                updated = await conn.fetchrow(
                    """
                    SELECT approval_id, status, created_at,
                           requested_action_class, correlation_id
                    FROM approvals WHERE approval_id = $1
                    """,
                    approval_id,
                )
        return _row_to_approval(updated)

    async def list(self, status: Optional[str] = None) -> List[ApprovalStatusResponse]:
        pool = await _get_pool()
        if pool is None:
            return []
        query = """
            SELECT approval_id, status, created_at,
                   requested_action_class, correlation_id
            FROM approvals
        """
        params: tuple = ()
        if status:
            query += " WHERE status = $1"
            params = (status,)
        query += " ORDER BY created_at DESC"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [_row_to_approval(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM approvals") or 0


class FederateRepository:
    async def register(self, federate: FederateInfo) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO federates (
                    federate_id, federation_role, cell_status,
                    created_at, updated_at, public_key
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (federate_id) DO UPDATE SET
                    federation_role = EXCLUDED.federation_role,
                    cell_status = EXCLUDED.cell_status,
                    updated_at = EXCLUDED.updated_at,
                    public_key = EXCLUDED.public_key
                """,
                federate.federate_id,
                federate.federation_role,
                federate.cell_status,
                federate.created_at,
                federate.updated_at,
                federate.public_key,
            )

    async def get(self, federate_id: str) -> Optional[FederateInfo]:
        pool = await _get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT federate_id, federation_role, cell_status,
                       created_at, updated_at, public_key
                FROM federates WHERE federate_id = $1
                """,
                federate_id,
            )
        if row is None:
            return None
        return _row_to_federate(row)

    async def list(self) -> List[FederateInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT federate_id, federation_role, cell_status,
                       created_at, updated_at, public_key
                FROM federates ORDER BY created_at DESC
                """
            )
        return [_row_to_federate(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM federates") or 0


class ArbitrationRepository:
    async def add(self, arbitration: ArbitrationInfo) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO arbitrations (
                    arbitration_id, created_at_utc, status, conflict_type,
                    subject_key, conflict_key, claims, evidence_refs,
                    correlation_id, proposed_resolution, decision, approval_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (arbitration_id) DO NOTHING
                """,
                arbitration.arbitration_id,
                arbitration.created_at_utc,
                arbitration.status,
                arbitration.conflict_type,
                arbitration.subject_key,
                arbitration.conflict_key,
                arbitration.claims,
                arbitration.evidence_refs,
                arbitration.correlation_id,
                arbitration.proposed_resolution,
                arbitration.decision,
                arbitration.approval_id,
            )

    async def list(self, limit: int = 100, offset: int = 0) -> List[ArbitrationInfo]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT arbitration_id, created_at_utc, status, conflict_type,
                       subject_key, conflict_key, claims, evidence_refs,
                       correlation_id, proposed_resolution, decision, approval_id
                FROM arbitrations
                ORDER BY created_at_utc DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [_row_to_arbitration(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM arbitrations") or 0


class BenchmarkHistoryRepository:
    async def append(self, run: BenchmarkResult) -> None:
        pool = await _get_pool()
        if pool is None:
            return
        data = run.model_dump()
        mode = data.get("mode", "unknown")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO benchmark_runs (
                    run_id, core_version, started_at, finished_at, mode, data
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (run_id) DO NOTHING
                """,
                run.run_id,
                run.core_version,
                run.started_at,
                run.finished_at,
                mode,
                data,
            )

    async def latest(self) -> Optional[BenchmarkResult]:
        pool = await _get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT data FROM benchmark_runs
                ORDER BY started_at DESC LIMIT 1
                """
            )
        if row is None:
            return None
        return _row_to_benchmark(row)

    async def list(self, limit: int = 10) -> List[BenchmarkResult]:
        pool = await _get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT data FROM benchmark_runs
                ORDER BY started_at DESC LIMIT $1
                """,
                limit,
            )
        return [_row_to_benchmark(r) for r in rows]

    async def count(self) -> int:
        pool = await _get_pool()
        if pool is None:
            return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM benchmark_runs") or 0


# ============================================================================
# Row → Model helpers
# ============================================================================


def _row_to_observation(row: Any) -> ObservationInfo:
    return ObservationInfo(
        observation_id=row["observation_id"],
        source_federate_id=row["source_federate_id"],
        timestamp_utc=str(row["timestamp_utc"]),
        correlation_id=row["correlation_id"],
        observation_type=row["observation_type"],
        confidence=float(row["confidence"]),
        evidence_refs=list(row["evidence_refs"]) if row["evidence_refs"] else [],
        payload_type=row["payload_type"],
        payload_data=dict(row["payload_data"]) if row["payload_data"] else {},
    )


def _row_to_belief(row: Any) -> BeliefInfo:
    return BeliefInfo(
        belief_id=row["belief_id"],
        belief_type=row["belief_type"],
        confidence=float(row["confidence"]),
        source_observations=list(row["source_observations"]) if row["source_observations"] else [],
        derived_at=str(row["derived_at"]),
        correlation_id=row["correlation_id"],
        evidence_summary=row["evidence_summary"],
        conflicts=list(row["conflicts"]) if row["conflicts"] else [],
        metadata=dict(row["metadata"]) if row["metadata"] else {},
    )


def _row_to_audit(row: Any) -> AuditRecord:
    return AuditRecord(
        audit_id=row["audit_id"],
        event_kind=row["event_kind"],
        payload_ref=dict(row["payload_ref"]) if row["payload_ref"] else {},
        correlation_id=row["correlation_id"],
        trace_id=row["trace_id"],
        tenant_id=row["tenant_id"],
        cell_id=row["cell_id"],
        idempotency_key=row["idempotency_key"],
        created_at=str(row["created_at"]),
    )


def _row_to_approval(row: Any) -> ApprovalStatusResponse:
    return ApprovalStatusResponse(
        approval_id=row["approval_id"],
        status=row["status"],
        created_at=str(row["created_at"]),
        requested_action_class=row["requested_action_class"],
        correlation_id=row["correlation_id"],
    )


def _row_to_federate(row: Any) -> FederateInfo:
    return FederateInfo(
        federate_id=row["federate_id"],
        federation_role=row["federation_role"],
        cell_status=row["cell_status"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        public_key=row["public_key"],
    )


def _row_to_arbitration(row: Any) -> ArbitrationInfo:
    return ArbitrationInfo(
        arbitration_id=row["arbitration_id"],
        created_at_utc=str(row["created_at_utc"]),
        status=row["status"],
        conflict_type=row["conflict_type"],
        subject_key=row["subject_key"],
        conflict_key=row["conflict_key"],
        claims=list(row["claims"]) if row["claims"] else [],
        evidence_refs=list(row["evidence_refs"]) if row["evidence_refs"] else [],
        correlation_id=row["correlation_id"],
        proposed_resolution=dict(row["proposed_resolution"]) if row["proposed_resolution"] else None,
        decision=dict(row["decision"]) if row["decision"] else None,
        approval_id=row["approval_id"],
    )


def _row_to_benchmark(row: Any) -> BenchmarkResult:
    import json
    from exoarmur.api.models import (
        BenchmarkDeterminism,
        BenchmarkNoise,
        BenchmarkReplay,
        BenchmarkThroughput,
    )
    data = row["data"]
    mode = data.get("mode", "determinism")
    if mode == "determinism":
        return BenchmarkDeterminism(**data)
    if mode == "throughput":
        return BenchmarkThroughput(**data)
    if mode == "replay":
        return BenchmarkReplay(**data)
    return BenchmarkNoise(**data)
