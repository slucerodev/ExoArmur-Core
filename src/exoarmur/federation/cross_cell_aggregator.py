"""
ExoArmur ADMO V2 Cross-Cell Belief Aggregator
Aggregates beliefs across federation cells with deterministic ordering and audit trail.

Phase 2B additive component — does not touch V1 paths.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from exoarmur.core.phase_gate import PhaseGate

logger = logging.getLogger(__name__)


@dataclass
class AggregationConfig:
    """Configuration for cross-cell belief aggregation"""
    enabled: bool = False
    strategy: str = "weighted_mean"  # weighted_mean | majority_vote | max_confidence
    min_cell_quorum: int = 2
    confidence_floor: float = 0.1


class CrossCellAggregator:
    """Aggregates beliefs received from multiple federation cells.

    When ``enabled=False`` every public method is a silent no-op so that
    importing or instantiating the class never affects V1 behaviour.
    When ``enabled=True`` the Phase Gate enforces ``EXOARMUR_PHASE=2``.
    """

    def __init__(self, config: Optional[AggregationConfig] = None):
        self.config = config or AggregationConfig()
        self._initialized = False
        # cell_id -> list of belief dicts received from that cell
        self._cell_beliefs: Dict[str, List[Dict[str, Any]]] = {}
        self._audit_log: List[Dict[str, Any]] = []

        if self.config.enabled:
            logger.warning("CrossCellAggregator: enabled=True")
        else:
            logger.debug("CrossCellAggregator: scaffolding mode (enabled=False)")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize the aggregator."""
        if not self.config.enabled:
            logger.debug("CrossCellAggregator.initialize() — no-op (scaffolding)")
            return

        PhaseGate.check_phase_2_eligibility("CrossCellAggregator")

        self._cell_beliefs = {}
        self._audit_log = []
        self._initialized = True
        self._emit_audit("aggregator_initialized", {
            "strategy": self.config.strategy,
            "min_cell_quorum": self.config.min_cell_quorum,
        })
        logger.info("CrossCellAggregator initialized")

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        if not self.config.enabled:
            logger.debug("CrossCellAggregator.shutdown() — no-op (scaffolding)")
            return

        self._emit_audit("aggregator_shutdown", {
            "cells_tracked": len(self._cell_beliefs),
            "audit_events": len(self._audit_log),
        })
        self._cell_beliefs = {}
        self._initialized = False
        logger.info("CrossCellAggregator shutdown complete")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit_beliefs(
        self, cell_id: str, beliefs: List[Dict[str, Any]]
    ) -> None:
        """Accept a batch of beliefs from a remote cell."""
        if not self.config.enabled:
            return

        if cell_id not in self._cell_beliefs:
            self._cell_beliefs[cell_id] = []
        self._cell_beliefs[cell_id].extend(beliefs)

        self._emit_audit("beliefs_received", {
            "cell_id": cell_id,
            "count": len(beliefs),
        })

    async def aggregate(self) -> Dict[str, Any]:
        """Run aggregation across all submitted cell beliefs.

        Returns a dict with ``aggregated_beliefs``, ``cell_count``, and
        ``quorum_met``.
        """
        if not self.config.enabled:
            return {
                "aggregated_beliefs": [],
                "cell_count": 0,
                "quorum_met": False,
            }

        cell_count = len(self._cell_beliefs)
        quorum_met = cell_count >= self.config.min_cell_quorum

        # Flatten all beliefs and group by belief_type for aggregation
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for cell_id, beliefs in sorted(self._cell_beliefs.items()):
            for b in beliefs:
                btype = b.get("belief_type", "unknown")
                grouped.setdefault(btype, []).append(b)

        aggregated: List[Dict[str, Any]] = []
        for btype, items in sorted(grouped.items()):
            agg = self._aggregate_group(btype, items)
            if agg:
                aggregated.append(agg)

        self._emit_audit("aggregation_complete", {
            "cell_count": cell_count,
            "quorum_met": quorum_met,
            "belief_types": len(aggregated),
        })

        return {
            "aggregated_beliefs": aggregated,
            "cell_count": cell_count,
            "quorum_met": quorum_met,
        }

    async def get_aggregation_status(self) -> Dict[str, Any]:
        """Return current aggregation status."""
        if not self.config.enabled:
            return {
                "status": "scaffolding",
                "cells_tracked": 0,
                "total_beliefs": 0,
                "initialized": False,
            }

        total_beliefs = sum(len(v) for v in self._cell_beliefs.values())
        return {
            "status": "active" if self._initialized else "not_initialized",
            "cells_tracked": len(self._cell_beliefs),
            "total_beliefs": total_beliefs,
            "initialized": self._initialized,
            "strategy": self.config.strategy,
        }

    async def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the audit trail for this aggregator instance."""
        if not self.config.enabled:
            return []
        return list(self._audit_log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _aggregate_group(
        self, belief_type: str, items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Aggregate a single belief-type group using the configured strategy."""
        if not items:
            return None

        confidences = [
            float(b.get("confidence", 0.0)) for b in items
        ]

        if self.config.strategy == "max_confidence":
            agg_confidence = max(confidences)
        elif self.config.strategy == "majority_vote":
            agg_confidence = sum(
                1.0 for c in confidences if c >= 0.5
            ) / len(confidences)
        else:  # weighted_mean (default)
            agg_confidence = sum(confidences) / len(confidences)

        agg_confidence = max(agg_confidence, self.config.confidence_floor)

        return {
            "belief_type": belief_type,
            "aggregated_confidence": round(agg_confidence, 6),
            "source_count": len(items),
            "strategy": self.config.strategy,
        }

    def _emit_audit(self, event_type: str, details: Dict[str, Any]) -> None:
        """Append a deterministic audit entry."""
        self._audit_log.append({
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })
