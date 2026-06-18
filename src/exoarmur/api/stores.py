"""
Thread-safe in-memory stores for the ExoArmur API layer.

These stores back the HTTP endpoints during Phases 0–5.  In Phase 6 they are
replaced by PostgreSQL repositories behind the same interface.
"""

import asyncio
from datetime import datetime, timezone
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
    """In-memory store for telemetry observations."""

    def __init__(self):
        super().__init__()
        self._observations: List[ObservationInfo] = []

    async def add(self, observation: ObservationInfo) -> None:
        async with self._lock:
            self._observations.append(observation)

    async def list(self, limit: int = 100, offset: int = 0) -> List[ObservationInfo]:
        async with self._lock:
            return self._observations[-(offset + limit) :][:limit]

    async def get_by_correlation(self, correlation_id: str) -> List[ObservationInfo]:
        async with self._lock:
            return [
                o for o in self._observations if o.correlation_id == correlation_id
            ]

    async def count(self) -> int:
        async with self._lock:
            return len(self._observations)


class BeliefStore(_LockedStore):
    """In-memory store for derived beliefs."""

    def __init__(self):
        super().__init__()
        self._beliefs: List[BeliefInfo] = []

    async def add(self, belief: BeliefInfo) -> None:
        async with self._lock:
            self._beliefs.append(belief)

    async def list(self, limit: int = 100, offset: int = 0) -> List[BeliefInfo]:
        async with self._lock:
            return self._beliefs[-(offset + limit) :][:limit]

    async def get_by_correlation(self, correlation_id: str) -> List[BeliefInfo]:
        async with self._lock:
            return [b for b in self._beliefs if b.correlation_id == correlation_id]

    async def count(self) -> int:
        async with self._lock:
            return len(self._beliefs)


class AuditStore(_LockedStore):
    """
    Append-only in-memory store for audit records.
    Records are never updated or deleted — this preserves the evidence chain.
    """

    def __init__(self):
        super().__init__()
        self._records: List[AuditRecord] = []

    async def append(self, record: AuditRecord) -> None:
        async with self._lock:
            self._records.append(record)

    async def get_by_correlation(self, correlation_id: str) -> List[AuditRecord]:
        async with self._lock:
            return [r for r in self._records if r.correlation_id == correlation_id]

    async def count(self) -> int:
        async with self._lock:
            return len(self._records)

    async def count_by_correlation(self, correlation_id: str) -> int:
        async with self._lock:
            return sum(
                1 for r in self._records if r.correlation_id == correlation_id
            )


class ApprovalStore(_LockedStore):
    """
    In-memory store for approval workflow state.
    Enforces state-machine transitions.
    """

    def __init__(self):
        super().__init__()
        self._approvals: Dict[str, ApprovalStatusResponse] = {}

    async def create(self, approval: ApprovalStatusResponse) -> None:
        async with self._lock:
            if approval.approval_id in self._approvals:
                raise ValueError(
                    f"Approval {approval.approval_id} already exists"
                )
            self._approvals[approval.approval_id] = approval

    async def get(self, approval_id: str) -> Optional[ApprovalStatusResponse]:
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
            return updated

    async def list(self, status: Optional[str] = None) -> List[ApprovalStatusResponse]:
        async with self._lock:
            approvals = list(self._approvals.values())
            if status:
                approvals = [a for a in approvals if a.status == status]
            return approvals

    async def count(self) -> int:
        async with self._lock:
            return len(self._approvals)


class FederateStore(_LockedStore):
    """In-memory store for federation cells."""

    def __init__(self):
        super().__init__()
        self._federates: Dict[str, FederateInfo] = {}

    async def register(self, federate: FederateInfo) -> None:
        async with self._lock:
            self._federates[federate.federate_id] = federate

    async def get(self, federate_id: str) -> Optional[FederateInfo]:
        async with self._lock:
            return self._federates.get(federate_id)

    async def list(self) -> List[FederateInfo]:
        async with self._lock:
            return list(self._federates.values())

    async def count(self) -> int:
        async with self._lock:
            return len(self._federates)


class ArbitrationStore(_LockedStore):
    """In-memory store for arbitrations."""

    def __init__(self):
        super().__init__()
        self._arbitrations: List[ArbitrationInfo] = []

    async def add(self, arbitration: ArbitrationInfo) -> None:
        async with self._lock:
            self._arbitrations.append(arbitration)

    async def list(self, limit: int = 100, offset: int = 0) -> List[ArbitrationInfo]:
        async with self._lock:
            return self._arbitrations[-(offset + limit) :][:limit]

    async def count(self) -> int:
        async with self._lock:
            return len(self._arbitrations)


class BenchmarkHistoryStore(_LockedStore):
    """In-memory store for recent benchmark runs."""

    def __init__(self, max_size: int = 100):
        super().__init__()
        self._max_size = max_size
        self._runs: List[BenchmarkResult] = []

    async def append(self, run: BenchmarkResult) -> None:
        async with self._lock:
            self._runs.append(run)
            if len(self._runs) > self._max_size:
                self._runs = self._runs[-self._max_size :]

    async def latest(self) -> Optional[BenchmarkResult]:
        async with self._lock:
            return self._runs[-1] if self._runs else None

    async def list(self, limit: int = 10) -> List[BenchmarkResult]:
        async with self._lock:
            return self._runs[-limit:]

    async def count(self) -> int:
        async with self._lock:
            return len(self._runs)


# ============================================================================
# Global store instances (singletons for the in-memory phase)
# ============================================================================

observation_store = ObservationStore()
belief_store = BeliefStore()
audit_store = AuditStore()
approval_store = ApprovalStore()
federate_store = FederateStore()
arbitration_store = ArbitrationStore()
benchmark_history = BenchmarkHistoryStore()
