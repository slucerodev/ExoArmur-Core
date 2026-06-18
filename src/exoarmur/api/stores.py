"""
Dual-write stores for the ExoArmur API layer.

Each store maintains the original in-memory buffer AND writes to PostgreSQL
when a DB connection pool is available.  Reads prefer the database (source of
truth) and fall back to memory when the DB is unreachable or unconfigured.

This supports the Phase 6 cutover strategy:
  1. Deploy with EXOARMUR_DATABASE_URL set → dual-write begins
  2. Monitor /admin/consistency → memory vs DB counts match
  3. When counts are stable, flip reads to DB-first (already done here)
"""

import asyncio
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


class _LockedStore:
    """Base class providing asyncio.Lock for thread-safe stores."""

    def __init__(self):
        self._lock = asyncio.Lock()


class ObservationStore(_LockedStore):
    """Dual-write store for telemetry observations."""

    def __init__(self):
        super().__init__()
        self._observations: List[ObservationInfo] = []
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import ObservationRepository
            self._repo = ObservationRepository()
        return self._repo

    async def add(self, observation: ObservationInfo) -> None:
        async with self._lock:
            self._observations.append(observation)
        await self._repository().add(observation)

    async def list(self, limit: int = 100, offset: int = 0) -> List[ObservationInfo]:
        db = await self._repository().list(limit, offset)
        if db:
            return db
        async with self._lock:
            return self._observations[-(offset + limit) :][:limit]

    async def get_by_correlation(self, correlation_id: str) -> List[ObservationInfo]:
        db = await self._repository().get_by_correlation(correlation_id)
        if db:
            return db
        async with self._lock:
            return [
                o for o in self._observations if o.correlation_id == correlation_id
            ]

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._observations)


class BeliefStore(_LockedStore):
    """Dual-write store for derived beliefs."""

    def __init__(self):
        super().__init__()
        self._beliefs: List[BeliefInfo] = []
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import BeliefRepository
            self._repo = BeliefRepository()
        return self._repo

    async def add(self, belief: BeliefInfo) -> None:
        async with self._lock:
            self._beliefs.append(belief)
        await self._repository().add(belief)

    async def list(self, limit: int = 100, offset: int = 0) -> List[BeliefInfo]:
        db = await self._repository().list(limit, offset)
        if db:
            return db
        async with self._lock:
            return self._beliefs[-(offset + limit) :][:limit]

    async def get_by_correlation(self, correlation_id: str) -> List[BeliefInfo]:
        db = await self._repository().get_by_correlation(correlation_id)
        if db:
            return db
        async with self._lock:
            return [b for b in self._beliefs if b.correlation_id == correlation_id]

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._beliefs)


class AuditStore(_LockedStore):
    """Dual-write append-only store for audit records."""

    def __init__(self):
        super().__init__()
        self._records: List[AuditRecord] = []
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import AuditRepository
            self._repo = AuditRepository()
        return self._repo

    async def append(self, record: AuditRecord) -> None:
        async with self._lock:
            self._records.append(record)
        await self._repository().append(record)

    async def get_by_correlation(self, correlation_id: str) -> List[AuditRecord]:
        db = await self._repository().get_by_correlation(correlation_id)
        if db:
            return db
        async with self._lock:
            return [r for r in self._records if r.correlation_id == correlation_id]

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._records)

    async def count_by_correlation(self, correlation_id: str) -> int:
        db = await self._repository().count_by_correlation(correlation_id)
        if db > 0:
            return db
        async with self._lock:
            return sum(
                1 for r in self._records if r.correlation_id == correlation_id
            )


class ApprovalStore(_LockedStore):
    """Dual-write store for approval workflow state."""

    def __init__(self):
        super().__init__()
        self._approvals: Dict[str, ApprovalStatusResponse] = {}
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import ApprovalRepository
            self._repo = ApprovalRepository()
        return self._repo

    async def create(self, approval: ApprovalStatusResponse) -> None:
        async with self._lock:
            if approval.approval_id in self._approvals:
                raise ValueError(
                    f"Approval {approval.approval_id} already exists"
                )
            self._approvals[approval.approval_id] = approval
        await self._repository().create(approval)

    async def get(self, approval_id: str) -> Optional[ApprovalStatusResponse]:
        db = await self._repository().get(approval_id)
        if db is not None:
            return db
        async with self._lock:
            return self._approvals.get(approval_id)

    async def update_status(
        self,
        approval_id: str,
        new_status: str,
        operator_id: str,
        reason: Optional[str] = None,
    ) -> ApprovalStatusResponse:
        async with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise KeyError(f"Approval {approval_id} not found")
            if approval.status != "PENDING":
                raise ValueError(
                    f"Approval {approval_id} is already {approval.status}"
                )
            if new_status not in ("APPROVED", "DENIED"):
                raise ValueError(f"Invalid status transition to {new_status}")
            if new_status == "DENIED" and not reason:
                raise ValueError("Denial requires a reason")

            updated = ApprovalStatusResponse(
                approval_id=approval.approval_id,
                status=new_status,  # type: ignore[arg-type]
                created_at=approval.created_at,
                requested_action_class=approval.requested_action_class,
                correlation_id=approval.correlation_id,
            )
            self._approvals[approval_id] = updated

        # Write to DB after memory update (so memory is always consistent)
        await self._repository().update_status(
            approval_id, new_status, operator_id, reason
        )
        return updated

    async def list(self, status: Optional[str] = None) -> List[ApprovalStatusResponse]:
        db = await self._repository().list(status)
        if db:
            return db
        async with self._lock:
            approvals = list(self._approvals.values())
            if status:
                approvals = [a for a in approvals if a.status == status]
            return approvals

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._approvals)


class FederateStore(_LockedStore):
    """Dual-write store for federation cells."""

    def __init__(self):
        super().__init__()
        self._federates: Dict[str, FederateInfo] = {}
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import FederateRepository
            self._repo = FederateRepository()
        return self._repo

    async def register(self, federate: FederateInfo) -> None:
        async with self._lock:
            self._federates[federate.federate_id] = federate
        await self._repository().register(federate)

    async def get(self, federate_id: str) -> Optional[FederateInfo]:
        db = await self._repository().get(federate_id)
        if db is not None:
            return db
        async with self._lock:
            return self._federates.get(federate_id)

    async def list(self) -> List[FederateInfo]:
        db = await self._repository().list()
        if db:
            return db
        async with self._lock:
            return list(self._federates.values())

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._federates)


class ArbitrationStore(_LockedStore):
    """Dual-write store for arbitrations."""

    def __init__(self):
        super().__init__()
        self._arbitrations: List[ArbitrationInfo] = []
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import ArbitrationRepository
            self._repo = ArbitrationRepository()
        return self._repo

    async def add(self, arbitration: ArbitrationInfo) -> None:
        async with self._lock:
            self._arbitrations.append(arbitration)
        await self._repository().add(arbitration)

    async def list(self, limit: int = 100, offset: int = 0) -> List[ArbitrationInfo]:
        db = await self._repository().list(limit, offset)
        if db:
            return db
        async with self._lock:
            return self._arbitrations[-(offset + limit) :][:limit]

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._arbitrations)


class BenchmarkHistoryStore(_LockedStore):
    """Dual-write store for recent benchmark runs."""

    def __init__(self, max_size: int = 100):
        super().__init__()
        self._max_size = max_size
        self._runs: List[BenchmarkResult] = []
        self._repo: Optional[Any] = None

    def _repository(self):
        if self._repo is None:
            from exoarmur.api.repositories import BenchmarkHistoryRepository
            self._repo = BenchmarkHistoryRepository()
        return self._repo

    async def append(self, run: BenchmarkResult) -> None:
        async with self._lock:
            self._runs.append(run)
            if len(self._runs) > self._max_size:
                self._runs = self._runs[-self._max_size :]
        await self._repository().append(run)

    async def latest(self) -> Optional[BenchmarkResult]:
        db = await self._repository().latest()
        if db is not None:
            return db
        async with self._lock:
            return self._runs[-1] if self._runs else None

    async def list(self, limit: int = 10) -> List[BenchmarkResult]:
        db = await self._repository().list(limit)
        if db:
            return db
        async with self._lock:
            return self._runs[-limit:]

    async def count(self) -> int:
        db = await self._repository().count()
        if db > 0:
            return db
        async with self._lock:
            return len(self._runs)


# ============================================================================
# Global store instances (singletons)
# ============================================================================

observation_store = ObservationStore()
belief_store = BeliefStore()
audit_store = AuditStore()
approval_store = ApprovalStore()
federate_store = FederateStore()
arbitration_store = ArbitrationStore()
benchmark_history = BenchmarkHistoryStore()
