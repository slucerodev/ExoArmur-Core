"""
ADMO v1 Pydantic Models

Canonical contract models for ExoArmur Autonomous Defense Mesh Organism v1.
All models use strict validation and enforce field constraints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
import re


class TelemetryEventV1(BaseModel):
    """Canonical input event received by a cell. Validated at ingest."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    event_id: str = Field(example="01J...", description="ULID event identifier")
    tenant_id: str = Field(example="tenant_acme", description="Tenant identifier")
    cell_id: str = Field(example="cell-okc-01", description="Cell identifier")
    observed_at: datetime = Field(description="When the event occurred")
    received_at: datetime = Field(description="When the event was received")
    source: Dict[str, Any] = Field(
        description="Event source information",
        examples=[{
            "kind": "edr",
            "name": "crowdstrike",
            "host": "sensor-01",
            "sensor_id": "sensor-123"
        }]
    )
    event_type: str = Field(example="process_start", description="Event type")
    severity: Literal["low", "medium", "high", "critical"] = Field(description="Severity level")
    attributes: Dict[str, Any] = Field(
        description="Unstructured vendor fields. Must be JSON-serializable and bounded by max_event_bytes."
    )
    entity_refs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional normalized references if available at source"
    )
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_serializer('observed_at')
    def serialize_observed_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('received_at')
    def serialize_received_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_validator('event_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('event_id must be a valid ULID')
        return v


class SignalFactsV1(BaseModel):
    """Normalized facts/features derived from telemetry used for policy and decisioning."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    facts_id: str = Field(description="ULID facts identifier")
    derived_from_event_ids: List[str] = Field(min_items=1, description="Source event IDs")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    subject: Dict[str, Any] = Field(
        description="Subject information",
        examples=[{
            "subject_type": "host",
            "subject_id": "host-123"
        }]
    )
    claim_hints: List[str] = Field(description="Candidate claim types suggested by features")
    features: Dict[str, Any] = Field(
        description="Canonical feature map (stable keys). Avoid vendor-specific keys here."
    )
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate subject structure."""
        if 'subject_type' not in v or 'subject_id' not in v:
            raise ValueError('subject must contain subject_type and subject_id')
        valid_types = ["host", "user", "process", "ip", "service"]
        if v['subject_type'] not in valid_types:
            raise ValueError(f'subject_type must be one of {valid_types}')
        return v


class BeliefV1(BaseModel):
    """Evidence-backed claim emitted by a cell and propagated through the mesh."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    belief_id: str = Field(description="ULID belief identifier")
    tenant_id: str = Field(description="Tenant identifier")
    emitter_node_id: str = Field(description="Node ID of the emitter")
    subject: Dict[str, Any] = Field(
        description="Subject information",
        examples=[{
            "subject_type": "host",
            "subject_id": "host-123"
        }]
    )
    claim_type: str = Field(example="c2_beaconing", description="Type of claim")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    severity: Literal["low", "medium", "high", "critical"] = Field(description="Severity level")
    evidence_refs: Dict[str, Any] = Field(
        description="Evidence references",
        examples=[{
            "event_ids": ["event-1", "event-2"],
            "feature_hashes": ["hash-1", "hash-2"],
            "artifact_refs": ["artifact-1"]
        }]
    )
    policy_context: Dict[str, Any] = Field(
        description="Policy context",
        examples=[{
            "bundle_hash_sha256": "abc123...",
            "rule_ids": ["rule-1", "rule-2"],
            "trust_score_at_emit": 0.85
        }]
    )
    ttl_seconds: int = Field(ge=30, le=86400, description="Time to live in seconds")
    first_seen: datetime = Field(description="First time seen")
    last_seen: datetime = Field(description="Last time seen")
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_serializer('first_seen')
    def serialize_first_seen(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('last_seen')
    def serialize_last_seen(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_validator('belief_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('belief_id must be a valid ULID')
        return v


class LocalDecisionV1(BaseModel):
    """A cell-local decision derived from facts and beliefs, before safety gating."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    decision_id: str = Field(description="ULID decision identifier")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    subject: Dict[str, Any] = Field(
        description="Subject information",
        examples=[{
            "subject_type": "host",
            "subject_id": "host-123"
        }]
    )
    classification: Literal["benign", "suspicious", "malicious"] = Field(description="Classification")
    severity: Literal["low", "medium", "high", "critical"] = Field(description="Severity level")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    recommended_intents: List[Dict[str, Any]] = Field(
        default=[],
        description="Recommended execution intents",
        examples=[[
            {
                "intent_type": "isolate_host",
                "action_class": "A2_hard_containment",
                "ttl_seconds": 3600,
                "parameters": {"isolation_type": "network"}
            }
        ]]
    )
    evidence_refs: Dict[str, Any] = Field(
        description="Evidence references",
        examples=[{
            "event_ids": ["event-1", "event-2"],
            "belief_ids": ["belief-1", "belief-2"],
            "feature_hashes": ["hash-1", "hash-2"]
        }]
    )
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('decision_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('decision_id must be a valid ULID')
        return v


class ExecutionIntentV1(BaseModel):
    """Idempotent execution request produced after policy + safety gating."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    intent_id: str = Field(description="ULID intent identifier")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    idempotency_key: str = Field(description="Idempotency key for safe retries")
    subject: Dict[str, Any] = Field(
        description="Subject information",
        examples=[{
            "subject_type": "host",
            "subject_id": "host-123"
        }]
    )
    intent_type: str = Field(example="isolate_host", description="Type of intent")
    action_class: Literal["A0_observe", "A1_soft_containment", "A2_hard_containment", "A3_irreversible"] = Field(
        description="Action class"
    )
    requested_at: datetime = Field(description="When the intent was requested")
    ttl_seconds: Optional[int] = Field(default=None, description="Optional TTL")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Intent parameters")
    policy_context: Dict[str, Any] = Field(
        description="Policy context",
        examples=[{
            "bundle_hash_sha256": "abc123...",
            "rule_ids": ["rule-1", "rule-2"]
        }]
    )
    safety_context: Dict[str, Any] = Field(
        description="Safety context",
        examples=[{
            "safety_verdict": "allow",
            "rationale": "Low risk, policy authorized",
            "quorum_status": "satisfied",
            "human_approval_id": "approval-123"
        }]
    )
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_serializer('requested_at')
    def serialize_requested_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_validator('intent_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('intent_id must be a valid ULID')
        return v


class AuditRecordV1(BaseModel):
    """Append-only audit evidence record for replay and compliance."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(example="1.0.0", description="Schema version")
    audit_id: str = Field(description="ULID audit identifier")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    idempotency_key: str = Field(description="Idempotency key")
    recorded_at: datetime = Field(description="When the record was recorded")
    event_kind: str = Field(
        example="telemetry_ingested",
        description="Type of event being audited"
    )
    payload_ref: Dict[str, Any] = Field(
        description="Payload reference",
        examples=[{
            "kind": "inline",
            "ref": "payload-data"
        }]
    )
    hashes: Dict[str, Any] = Field(
        description="Hash information",
        examples=[{
            "sha256": "abc123...",
            "upstream_hashes": ["hash-1", "hash-2"]
        }]
    )
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_serializer('recorded_at')
    def serialize_recorded_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_validator('audit_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('audit_id must be a valid ULID')
        return v


# Export all models
__all__ = [
    'TelemetryEventV1',
    'SignalFactsV1', 
    'BeliefV1',
    'LocalDecisionV1',
    'ExecutionIntentV1',
    'AuditRecordV1'
]