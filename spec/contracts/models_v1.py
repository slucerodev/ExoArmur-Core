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


# V2 Federation Identity Models (additive, behind feature flags)
from enum import Enum
from typing import Union


class FederationRole(str, Enum):
    """Federation role enumeration"""
    MEMBER = "member"
    COORDINATOR = "coordinator"
    OBSERVER = "observer"


class CellStatus(str, Enum):
    """Cell status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DECOMMISSIONED = "decommissioned"


class HandshakeState(str, Enum):
    """Handshake state enumeration"""
    UNINITIALIZED = "uninitialized"
    IDENTITY_EXCHANGE = "identity_exchange"
    CAPABILITY_NEGOTIATION = "capability_negotiation"
    TRUST_ESTABLISHMENT = "trust_establishment"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    FAILED_IDENTITY = "failed_identity"
    FAILED_IDENTITY_VERIFICATION = "failed_identity_verification"
    FAILED_CAPABILITIES = "failed_capabilities"
    FAILED_TRUST = "failed_trust"
    FAILED_PROTOCOL_VIOLATION = "failed_protocol_violation"
    FAILED_TIMEOUT = "failed_timeout"
    FAILED_NONCE_REUSE = "failed_nonce_reuse"
    FAILED_TIMESTAMP_SKEW = "failed_timestamp_skew"
    FAILED_SIGNATURE = "failed_signature"
    SUSPENDED = "suspended"


class FederateIdentityV1(BaseModel):
    """Federate identity data model for V2 federation (additive to V1)"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    federate_id: str = Field(description="Unique federate identifier (cell_id)")
    public_key: str = Field(description="Base64 encoded Ed25519 public key")
    key_id: str = Field(description="Key identifier (hash of public key)")
    certificate_chain: List[str] = Field(description="PE encoded X.509 certificate chain")
    federation_role: FederationRole = Field(default=FederationRole.MEMBER, description="Federation role")
    capabilities: List[str] = Field(description="Supported capabilities")
    trust_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Trust score")
    last_seen: datetime = Field(description="Last activity timestamp")
    status: CellStatus = Field(default=CellStatus.ACTIVE, description="Current status")
    created_at: datetime = Field(description="Identity creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    
    @field_validator('federate_id')
    @classmethod
    def validate_federate_id_format(cls, v):
        """Validate federate_id format: cell-[region]-[cluster]-[node]"""
        if not v.startswith('cell-'):
            raise ValueError('federate_id must start with "cell-"')
        parts = v.split('-')
        if len(parts) < 4:
            raise ValueError('federate_id must have format: cell-[region]-[cluster]-[node]')
        return v
    
    @field_serializer('last_seen')
    def serialize_last_seen(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, value: datetime) -> str:
        return value.isoformat()


class FederateNonceV1(BaseModel):
    """Nonce tracking for replay protection"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    nonce: str = Field(description="Cryptographic nonce")
    federate_id: str = Field(description="Federate identifier")
    created_at: datetime = Field(description="Nonce creation timestamp")
    expires_at: datetime = Field(description="Nonce expiration timestamp")
    used: bool = Field(default=False, description="Whether nonce has been used")
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('expires_at')
    def serialize_expires_at(self, value: datetime) -> str:
        return value.isoformat().replace('+00:00', 'Z')  # Modified to include 'Z' at the end



# V2 Federation Message Models (additive, behind feature flags)
class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms"""
    ED25519 = "ed25519"
    RSA_PSS_SHA256 = "rsa-pss-sha256"


class MessageType(str, Enum):
    """Federation message types"""
    IDENTITY_EXCHANGE = "identity_exchange"
    CAPABILITY_NEGOTIATE = "capability_negotiate"
    TRUST_ESTABLISH = "trust_establish"


class VerificationFailureReason(str, Enum):
    """Reasons for verification failure"""
    INVALID_SIGNATURE = "invalid_signature"
    KEY_MISMATCH = "key_mismatch"
    NONCE_REUSE = "nonce_reuse"
    TIMESTAMP_OUT_OF_BOUNDS = "timestamp_out_of_bounds"
    UNKNOWN_KEY_ID = "unknown_key_id"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    MISSING_SIGNATURE = "missing_signature"


class SignatureInfoV1(BaseModel):
    """Signature information for signed messages"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    alg: SignatureAlgorithm = Field(description="Signature algorithm")
    key_id: Optional[str] = Field(description="Key identifier")
    cert_fingerprint: Optional[str] = Field(description="Certificate fingerprint")
    sig_b64: str = Field(description="Base64 encoded signature")


class IdentityExchangePayloadV1(BaseModel):
    """Identity exchange message payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    cell_public_key: str = Field(description="Base64 encoded Ed25519 public key")
    certificate_chain: List[str] = Field(description="PE encoded X.509 certificate chain")
    federation_role: str = Field(description="Federation role")
    capabilities: List[str] = Field(description="Supported capabilities")
    trust_score: float = Field(ge=0.0, le=1.0, description="Trust score")
    cell_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional cell metadata")


class CapabilityNegotiatePayloadV1(BaseModel):
    """Capability negotiation message payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    supported_capabilities: List[str] = Field(description="Supported capabilities")
    required_capabilities: List[str] = Field(description="Required capabilities from peer")
    priority: int = Field(ge=1, le=10, description="Negotiation priority")
    capability_constraints: Dict[str, Any] = Field(default_factory=dict, description="Capability constraints")
    negotiation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Negotiation metadata")


class TrustEstablishPayloadV1(BaseModel):
    """Trust establishment message payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    trust_score: float = Field(ge=0.0, le=1.0, description="Proposed trust score")
    trust_reasons: List[str] = Field(description="Reasons for trust score")
    expiration: datetime = Field(description="Trust score expiration")
    trust_policies: List[str] = Field(default_factory=list, description="Applicable trust policies")
    trust_metadata: Dict[str, Any] = Field(default_factory=dict, description="Trust metadata")
    
    @field_serializer('expiration')
    def serialize_expiration(self, value: datetime) -> str:
        return value.isoformat().replace('+00:00', 'Z')


# Additional V2 Federation Models for Store
class FederateNonceV1(BaseModel):
    """Nonce tracking for replay protection"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    nonce: str = Field(description="Cryptographic nonce")
    federate_id: str = Field(description="Federate identifier")
    created_at: datetime = Field(description="Creation timestamp")
    expires_at: datetime = Field(description="Expiration timestamp")


class HandshakeSessionV1(BaseModel):
    """Handshake session tracking"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    federate_id: str = Field(description="Federate identifier")
    correlation_id: str = Field(description="Handshake correlation ID")
    state: HandshakeState = Field(description="Current handshake state")
    created_at: datetime = Field(description="Session creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Session expiration")


# V2 Coordination Visibility Models (additive)
from enum import Enum

class ObservationType(str, Enum):
    """Enumeration of observation types"""
    TELEMETRY_SUMMARY = "telemetry_summary"
    THREAT_INTEL = "threat_intel"
    ANOMALY_DETECTION = "anomaly_detection"
    SYSTEM_HEALTH = "system_health"
    NETWORK_ACTIVITY = "network_activity"
    CUSTOM = "custom"


class ObservationPayloadV1(BaseModel):
    """Base class for observation payloads"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(description="Payload type identifier")
    data: Dict[str, Any] = Field(description="Payload data")


class TelemetrySummaryPayloadV1(ObservationPayloadV1):
    """Telemetry summary observation payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(default="telemetry_summary", description="Payload type")
    event_count: int = Field(description="Number of events summarized")
    time_window_seconds: int = Field(description="Time window in seconds")
    event_types: List[str] = Field(description="Event types included")
    severity_distribution: Dict[str, int] = Field(description="Distribution of severities")


class ThreatIntelPayloadV1(ObservationPayloadV1):
    """Threat intelligence observation payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(default="threat_intel", description="Payload type")
    ioc_count: int = Field(description="Number of indicators of compromise")
    threat_types: List[str] = Field(description="Types of threats observed")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in threat assessment")
    sources: List[str] = Field(description="Threat intelligence sources")


class AnomalyDetectionPayloadV1(ObservationPayloadV1):
    """Anomaly detection observation payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(default="anomaly_detection", description="Payload type")
    anomaly_score: float = Field(ge=0.0, le=1.0, description="Anomaly confidence score")
    affected_entities: List[str] = Field(description="Entities affected by anomaly")
    anomaly_type: str = Field(description="Type of anomaly detected")
    baseline_deviation: float = Field(description="Deviation from baseline")


class SystemHealthPayloadV1(ObservationPayloadV1):
    """System health observation payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(default="system_health", description="Payload type")
    cpu_utilization: float = Field(ge=0.0, le=100.0, description="CPU utilization percentage")
    memory_utilization: float = Field(ge=0.0, le=100.0, description="Memory utilization percentage")
    disk_utilization: float = Field(ge=0.0, le=100.0, description="Disk utilization percentage")
    network_latency_ms: float = Field(description="Network latency in milliseconds")
    service_status: Dict[str, str] = Field(description="Service status mapping")


class NetworkActivityPayloadV1(ObservationPayloadV1):
    """Network activity observation payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    payload_type: str = Field(default="network_activity", description="Payload type")
    connection_count: int = Field(description="Number of connections observed")
    bytes_transferred: int = Field(description="Bytes transferred")
    top_protocols: List[str] = Field(description="Top protocols by volume")
    suspicious_ips: List[str] = Field(description="Suspicious IP addresses detected")


class ObservationV1(BaseModel):
    """Canonical observation message from a federate"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    observation_id: str = Field(example="obs_01J...", description="Observation identifier")
    source_federate_id: str = Field(description="Federate identifier that created this observation")
    timestamp_utc: datetime = Field(description="Observation timestamp in UTC")
    
    @field_serializer('timestamp_utc')
    def serialize_timestamp_utc(self, value: datetime) -> str:
        """Serialize timestamp as ISO 8601 UTC"""
        return value.isoformat().replace('+00:00', 'Z')
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for linking to other events")
    nonce: Optional[str] = Field(default=None, description="Cryptographic nonce for replay protection")
    observation_type: ObservationType = Field(description="Type of observation")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in observation accuracy")
    evidence_refs: List[str] = Field(default_factory=list, description="References to evidence sources")
    payload: ObservationPayloadV1 = Field(description="Typed observation payload")
    signature: Optional[SignatureInfoV1] = Field(default=None, description="Signature block")
    
    def canonical_bytes(self) -> bytes:
        """Return canonical byte representation for signing"""
        # Create dict without signature for canonical representation
        data = self.signed_payload_dict()
        import json
        return json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')
    
    def signed_payload_dict(self) -> Dict[str, Any]:
        """Return dictionary representation for signing (excluding signature)"""
        data = self.model_dump(exclude={'signature'})
        # Convert datetime to ISO format for serialization
        data['timestamp_utc'] = self.timestamp_utc.isoformat()
        # Handle nested payload serialization
        if 'payload' in data:
            data['payload'] = self.payload.model_dump()
        return data
    
    @property
    def federate_id(self) -> str:
        """Alias for source_federate_id for compatibility with verification functions"""
        return self.source_federate_id


class BeliefV1(BaseModel):
    """Canonical belief derived from observations"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    belief_id: str = Field(example="belief_01J...", description="Belief identifier")
    belief_type: str = Field(description="Type of belief")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in belief")
    source_observations: List[str] = Field(description="List of observation IDs that contributed to this belief")
    derived_at: datetime = Field(description="When belief was derived")
    
    @field_serializer('derived_at')
    def serialize_derived_at(self, value: datetime) -> str:
        """Serialize timestamp as ISO 8601 UTC"""
        return value.isoformat().replace('+00:00', 'Z')
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for linking")
    evidence_summary: str = Field(description="Summary of evidence supporting this belief")
    conflicts: List[str] = Field(default_factory=list, description="List of conflicting belief IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Arbitration Models
class ArbitrationStatus(str, Enum):
    """Arbitration status"""
    OPEN = "open"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ArbitrationConflictType(str, Enum):
    """Types of conflicts that can be arbitrated"""
    THREAT_CLASSIFICATION = "threat_classification"
    SYSTEM_HEALTH = "system_health"
    CONFIDENCE_DISPUTE = "confidence_dispute"
    EVIDENCE_CONFLICT = "evidence_conflict"
    POLICY_VIOLATION = "policy_violation"
    TRUST_DISPUTE = "trust_dispute"


class ArbitrationV1(BaseModel):
    """Arbitration object for conflict resolution"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    arbitration_id: str = Field(example="arb_01J...", description="Arbitration identifier")
    created_at_utc: datetime = Field(description="When arbitration was created")
    
    @field_serializer('created_at_utc')
    def serialize_created_at_utc(self, value: datetime) -> str:
        """Serialize timestamp as ISO 8601 UTC"""
        return value.isoformat().replace('+00:00', 'Z')
    
    status: ArbitrationStatus = Field(description="Current arbitration status")
    conflict_type: ArbitrationConflictType = Field(description="Type of conflict")
    subject_key: str = Field(description="Subject of the conflict")
    conflict_key: str = Field(description="Deterministic conflict key")
    
    claims: List[Dict[str, Any]] = Field(description="Conflicting claims/beliefs")
    evidence_refs: List[str] = Field(default_factory=list, description="Evidence references")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID")
    
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list, description="Detected conflicts")
    
    # Resolution fields
    proposed_resolution: Optional[Dict[str, Any]] = Field(default=None, description="Proposed resolution")
    decision: Optional[Dict[str, Any]] = Field(default=None, description="Final decision after approval")
    approval_id: Optional[str] = Field(default=None, description="Approval request ID")
    resolved_at_utc: Optional[datetime] = Field(default=None, description="When arbitration was resolved")
    
    @field_serializer('resolved_at_utc')
    def serialize_resolved_at_utc(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize timestamp as ISO 8601 UTC"""
        if value:
            return value.isoformat().replace('+00:00', 'Z')
        return None
    
    resolver_federate_id: Optional[str] = Field(default=None, description="Federate that resolved the conflict")
    resolution_applied_at_utc: Optional[datetime] = Field(default=None, description="When resolution was applied")
    
    @field_serializer('resolution_applied_at_utc')
    def serialize_resolution_applied_at_utc(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize timestamp as ISO 8601 UTC"""
        if value:
            return value.isoformat().replace('+00:00', 'Z')
        return None
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Identity Containment Models (V3 additive)
class IdentitySubjectV1(BaseModel):
    """Identity subject for containment operations"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    subject_id: str = Field(description="Unique identifier for the identity subject")
    subject_type: str = Field(description="Type of subject (user, host, service, etc.)")
    tenant_id: str = Field(description="Tenant identifier")
    containment_scope: str = Field(default="none", description="Current containment scope")
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Risk assessment score")
    last_activity_utc: datetime = Field(description="Last activity timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional subject metadata")


class IdentityContainmentScopeV1(BaseModel):
    """Identity containment scope definition"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    scope_id: str = Field(description="Unique scope identifier")
    scope_type: str = Field(description="Type of containment (quarantine, monitoring, etc.)")
    severity_level: str = Field(description="Severity level (low, medium, high, critical)")
    ttl_seconds: int = Field(gt=0, description="Time-to-live in seconds")
    auto_expire: bool = Field(default=True, description="Whether scope auto-expires")
    requires_approval: bool = Field(default=True, description="Whether approval is required")
    approval_level: str = Field(default="A2", description="Required approval level")
    effectors: List[str] = Field(default_factory=list, description="List of effectors to apply")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Scope conditions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional scope metadata")


class IdentityContainmentRecommendationV1(BaseModel):
    """Identity containment recommendation"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    recommendation_id: str = Field(description="Unique recommendation identifier")
    subject_id: str = Field(description="Subject this recommendation applies to")
    scope: IdentityContainmentScopeV1 = Field(description="Recommended containment scope")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in recommendation")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk assessment details")
    evidence_refs: List[str] = Field(default_factory=list, description="References to supporting evidence")
    recommended_by: str = Field(description="What generated the recommendation")
    generated_at_utc: datetime = Field(description="When recommendation was generated")
    expires_at_utc: datetime = Field(description="When recommendation expires")
    status: str = Field(default="pending", description="Recommendation status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional recommendation metadata")


class IdentityContainmentIntentV1(BaseModel):
    """Identity containment intent for execution"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    intent_id: str = Field(description="Unique intent identifier")
    recommendation_id: str = Field(description="Source recommendation ID")
    subject_id: str = Field(description="Subject this intent applies to")
    scope: IdentityContainmentScopeV1 = Field(description="Containment scope to apply")
    intent_type: str = Field(description="Type of intent (apply, revert, modify)")
    approval_status: str = Field(default="pending", description="Approval status")
    approval_id: Optional[str] = Field(default=None, description="Approval ID if approved")
    approval_level: str = Field(default="A2", description="Required approval level")
    requested_by: str = Field(description="Who requested the intent")
    created_at_utc: datetime = Field(description="When intent was created")
    expires_at_utc: datetime = Field(description="When intent expires")
    execution_status: str = Field(default="pending", description="Execution status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional intent metadata")


class IdentityContainmentAppliedRecordV1(BaseModel):
    """Record of containment scope being applied"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    record_id: str = Field(description="Unique record identifier")
    intent_id: str = Field(description="Intent that was applied")
    subject_id: str = Field(description="Subject containment was applied to")
    scope_id: str = Field(description="Scope that was applied")
    applied_at_utc: datetime = Field(description="When containment was applied")
    applied_by: str = Field(description="What applied the containment")
    effectors_used: List[str] = Field(default_factory=list, description="Effectors that were used")
    ttl_seconds: int = Field(description="TTL for the containment")
    expires_at_utc: datetime = Field(description="When containment expires")
    status: str = Field(default="active", description="Current status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional record metadata")


class IdentityContainmentRevertedRecordV1(BaseModel):
    """Record of containment scope being reverted"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    record_id: str = Field(description="Unique record identifier")
    applied_record_id: str = Field(description="Applied record being reverted")
    intent_id: str = Field(description="Intent that triggered reversion")
    subject_id: str = Field(description="Subject containment was reverted for")
    reverted_at_utc: datetime = Field(description="When containment was reverted")
    reverted_by: str = Field(description="What reverted the containment")
    reason: str = Field(description="Reason for reversion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional record metadata")


class IdentityContainmentStatusV1(str, Enum):
    """Identity containment status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVERTED = "reverted"
    FAILED = "failed"
    SUSPENDED = "suspended"


# Export all models
__all__ = [
    # Core ADMO Models (V1)
    'TelemetryEventV1',
    'SignalFactsV1',
    'BeliefV1',
    'LocalDecisionV1',
    'ExecutionIntentV1',
    'AuditRecordV1',
    
    # V2 Federation Models (additive)
    'FederateIdentityV1',
    'FederateNonceV1',
    'SignatureInfoV1',
    'IdentityExchangePayloadV1',
    'CapabilityNegotiatePayloadV1',
    'TrustEstablishPayloadV1',
    'HandshakeSessionV1',
    'FederationRole',
    'CellStatus',
    'HandshakeState',
    'HandshakeResult',
    'ObservationType',
    'ObservationPayloadV1',
    'TelemetrySummaryPayloadV1',
    'ThreatIntelPayloadV1',
    'AnomalyDetectionPayloadV1',
    'SystemHealthPayloadV1',
    'NetworkActivityPayloadV1',
    'ObservationV1',
    # V2 Arbitration Models (additive)
    'ArbitrationStatus',
    'ArbitrationConflictType',
    'ArbitrationV1',
    # V3 Identity Containment Models (additive)
    'IdentitySubjectV1',
    'IdentityContainmentScopeV1', 
    'IdentityContainmentRecommendationV1',
    'IdentityContainmentIntentV1',
    'IdentityContainmentAppliedRecordV1',
    'IdentityContainmentRevertedRecordV1',
    'IdentityContainmentStatusV1'
]