"""Deterministic replay adapter for AuditRecordV1 inputs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from spec.contracts.models_v1 import AuditRecordV1

from ..canonical_utils import canonical_json
from ..event_envelope import EventTypePriority
from ..replay_envelope_builder import ReplayEnvelope

logger = logging.getLogger(__name__)


class ReplayAdapter:
    """Convert AuditRecordV1 values into deterministic replay envelopes."""

    def adapt(
        self,
        audit_record: AuditRecordV1,
        sequence_number: Optional[int] = None,
        preserve_ordering: bool = True,
    ) -> ReplayEnvelope:
        if not isinstance(audit_record, AuditRecordV1):
            raise TypeError(f"ReplayAdapter accepts AuditRecordV1 only, got {type(audit_record).__name__}")

        recorded_at = self._normalize_datetime(audit_record.recorded_at)
        payload_ref = self._normalize_payload(audit_record.payload_ref)
        event_timestamp = self._extract_event_timestamp(payload_ref) or recorded_at
        priority = EventTypePriority.get_priority(audit_record.event_kind)
        ordering_key = self._generate_ordering_key(
            priority=priority,
            recorded_at=recorded_at,
            audit_id=audit_record.audit_id,
            sequence_number=sequence_number,
            preserve_ordering=preserve_ordering,
        )

        return ReplayEnvelope(
            audit_id=audit_record.audit_id,
            event_kind=audit_record.event_kind,
            correlation_id=audit_record.correlation_id,
            trace_id=audit_record.trace_id,
            tenant_id=audit_record.tenant_id,
            cell_id=audit_record.cell_id,
            recorded_at=recorded_at,
            event_timestamp=event_timestamp,
            payload_ref=payload_ref,
            source_format="audit_record_v1",
            event_category=self._derive_event_category(audit_record.event_kind),
            event_severity=self._derive_event_severity(audit_record.event_kind, payload_ref),
            ordering_key=ordering_key,
            priority=priority,
            sequence_number=sequence_number,
            parent_event_id=None,
        )

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _normalize_payload(self, payload_ref: Any) -> Any:
        if isinstance(payload_ref, (dict, list)):
            return json.loads(canonical_json(payload_ref))
        return payload_ref

    def _extract_event_timestamp(self, payload_ref: Any) -> Optional[datetime]:
        if not isinstance(payload_ref, dict):
            return None

        for field in ("observed_at", "timestamp", "event_time", "created_at"):
            if field not in payload_ref:
                continue

            raw_value = payload_ref[field]
            if isinstance(raw_value, datetime):
                return self._normalize_datetime(raw_value)
            if isinstance(raw_value, str):
                try:
                    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
                except ValueError:
                    continue
                return self._normalize_datetime(parsed)

        return None

    def _generate_ordering_key(
        self,
        *,
        priority: int,
        recorded_at: datetime,
        audit_id: str,
        sequence_number: Optional[int],
        preserve_ordering: bool,
    ) -> str:
        if not preserve_ordering:
            return ""

        timestamp_text = recorded_at.isoformat().replace("+00:00", "Z")
        sequence_text = f"{sequence_number or 0:010d}"
        return f"{priority:03d}|{timestamp_text}|{audit_id}|{sequence_text}"

    def _derive_event_category(self, event_kind: str) -> str:
        category_mapping = {
            "telemetry_ingested": "ingestion",
            "local_decision_generated": "decision",
            "belief_generated": "reasoning",
            "collective_state_computed": "aggregation",
            "safety_gate_evaluated": "safety",
            "execution_intent_created": "execution",
            "action_executed": "execution",
            "approval_requested": "approval",
            "approval_granted": "approval",
            "approval_denied": "approval",
        }
        return category_mapping.get(event_kind, "other")

    def _derive_event_severity(self, event_kind: str, payload_ref: Any) -> str:
        if isinstance(payload_ref, dict):
            severity = str(payload_ref.get("severity", "")).lower()
            if severity in {"low", "medium", "high", "critical"}:
                return severity

        high_severity_events = {
            "safety_gate_denied",
            "action_executed",
            "approval_denied",
        }
        medium_severity_events = {
            "safety_gate_evaluated",
            "execution_intent_created",
            "approval_requested",
        }

        if event_kind in high_severity_events:
            return "high"
        if event_kind in medium_severity_events:
            return "medium"
        return "low"
