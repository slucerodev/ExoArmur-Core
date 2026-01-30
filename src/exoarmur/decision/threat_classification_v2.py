"""
Phase 2A Threat Classification Decision Models (Additive, V2)
Constitutionally compliant decision-only autonomous capability
"""

from datetime import datetime
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
import re
import hashlib
import json


class ThreatEventV2(BaseModel):
    """Synthetic threat event for Phase 2A decision testing"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    event_id: str = Field(description="ULID event identifier")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    observed_at: datetime = Field(description="When the event occurred")
    threat_type: Literal["malware", "phishing", "command_control", "data_exfiltration", "anomaly"] = Field(
        description="Type of threat detected"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(description="Severity level")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Initial confidence from detection system")
    source_ip: Optional[str] = Field(default=None, description="Source IP address")
    target_asset: str = Field(description="Target asset identifier")
    indicators: List[str] = Field(default_factory=list, description="IOCs or indicators")
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('event_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('event_id must be a valid ULID')
        return v
    
    @field_serializer('observed_at')
    def serialize_observed_at(self, value: datetime) -> str:
        return value.isoformat()


class ThreatFactsV2(BaseModel):
    """Observable facts derived from threat event"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    facts_id: str = Field(description="ULID facts identifier")
    derived_from_event_id: str = Field(description="Source event ID")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    
    # Observable facts (deterministic, verifiable)
    is_internal_ip: bool = Field(description="Source IP is internal network")
    is_known_bad_ip: bool = Field(description="Source IP in threat intelligence")
    is_unusual_time: bool = Field(description="Event outside normal business hours")
    is_high_risk_asset: bool = Field(description="Target asset is high value")
    is_repeated_pattern: bool = Field(description="Pattern seen multiple times")
    
    # Quantitative features
    threat_score: float = Field(ge=0.0, le=10.0, description="Calculated threat score")
    risk_score: float = Field(ge=0.0, le=1.0, description="Calculated risk score")
    
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('facts_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('facts_id must be a valid ULID')
        return v


class ThreatDecisionV2(BaseModel):
    """Autonomous threat classification decision"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    decision_id: str = Field(description="ULID decision identifier")
    facts_id: str = Field(description="Source facts identifier")
    tenant_id: str = Field(description="Tenant identifier")
    cell_id: str = Field(description="Cell identifier")
    
    # Decision outcome (the only autonomous action)
    classification: Literal["IGNORE", "SIMULATE", "ESCALATE"] = Field(
        description="Threat classification decision"
    )
    
    # Decision metadata
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence")
    reasoning: str = Field(description="Decision reasoning")
    governance_rules_fired: List[str] = Field(default_factory=list, description="Governance rules applied")
    
    # Authority envelope compliance
    authority_tier: Literal["T0_OBSERVE", "T1_SOFT_CONTAINMENT"] = Field(
        description="Authority tier used for decision"
    )
    
    # Deterministic inputs hash
    inputs_hash: Optional[str] = Field(default="", description="SHA256 hash of normalized inputs")
    
    # Timing
    decided_at: datetime = Field(description="When decision was made")
    
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('decision_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('decision_id must be a valid ULID')
        return v
    
    @field_validator('inputs_hash')
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA256 hash format."""
        if v and not re.match(r'^[a-f0-9]{64}$', v):
            raise ValueError('inputs_hash must be a valid SHA256 hash')
        return v
    
    @field_serializer('decided_at')
    def serialize_decided_at(self, value: datetime) -> str:
        return value.isoformat()
    
    def compute_inputs_hash(self) -> str:
        """Compute deterministic hash of decision inputs"""
        # Create canonical representation of inputs
        canonical_data = {
            "facts_id": self.facts_id,
            "tenant_id": self.tenant_id,
            "cell_id": self.cell_id,
            "classification": self.classification,
            "authority_tier": self.authority_tier
        }
        canonical_json = json.dumps(canonical_data, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


class DecisionTranscriptV2(BaseModel):
    """Complete deterministic decision transcript for replay and audit"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    schema_version: str = Field(default="2.0.0", description="Schema version")
    transcript_id: str = Field(description="ULID transcript identifier")
    
    # Decision identification
    decision_id: str = Field(description="Decision identifier")
    correlation_id: str = Field(description="Correlation identifier")
    
    # Input tracking
    normalized_inputs_hash: str = Field(description="Hash of normalized inputs")
    
    # Governance context
    policy_version: str = Field(default="2.0.0", description="Policy version used")
    feature_flags_snapshot: Dict[str, bool] = Field(description="Feature flags state")
    
    # Decision process
    belief_summary: str = Field(description="Summary of beliefs/facts considered")
    proposed_action: str = Field(description="Proposed autonomous action")
    authority_tier: Literal["T0_OBSERVE", "T1_SOFT_CONTAINMENT"] = Field(
        description="Authority tier exercised"
    )
    
    # Governance evaluation
    governance_rules_fired: List[str] = Field(default_factory=list, description="Rules that fired")
    evidence_score: float = Field(ge=0.0, le=1.0, description="Evidence confidence score")
    risk_score: float = Field(ge=0.0, le=1.0, description="Risk assessment score")
    
    # Authorization result
    authorization_result: Literal["ALLOW_AUTO", "REQUIRE_APPROVAL", "DENY"] = Field(
        description="Authorization outcome"
    )
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Decision constraints")
    
    # Audit trail
    explanation: str = Field(description="Decision explanation")
    rollback_plan: Optional[str] = Field(default=None, description="Rollback plan if applicable")
    
    # Timing and provenance
    decision_timestamp: datetime = Field(description="When decision was made")
    operator_approval_reference: Optional[str] = Field(default=None, description="Approval reference if needed")
    audit_chain_link: Optional[str] = Field(default=None, description="Link to audit chain")
    
    @field_validator('transcript_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('transcript_id must be a valid ULID')
        return v
    
    @field_validator('normalized_inputs_hash')
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA256 hash format."""
        if not re.match(r'^[a-f0-9]{64}$', v):
            raise ValueError('normalized_inputs_hash must be a valid SHA256 hash')
        return v
    
    @field_serializer('decision_timestamp')
    def serialize_decision_timestamp(self, value: datetime) -> str:
        return value.isoformat()


class GovernanceRuleV2(BaseModel):
    """Governance rule definition for threat classification"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    rule_id: str = Field(description="Rule identifier")
    rule_name: str = Field(description="Human-readable rule name")
    rule_version: str = Field(description="Rule version")
    description: str = Field(description="Rule description")
    
    # Rule conditions
    conditions: Dict[str, Any] = Field(description="Rule conditions")
    
    # Rule actions
    action: Literal["ALLOW", "DENY", "ESCALATE"] = Field(description="Rule action")
    
    # Authority constraints
    max_authority_tier: Literal["T0_OBSERVE", "T1_SOFT_CONTAINMENT"] = Field(
        description="Maximum authority tier this rule can authorize"
    )
    
    # Rule metadata
    priority: int = Field(ge=1, le=10, description="Rule priority (1=highest)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    
    @field_validator('rule_id')
    @classmethod
    def validate_rule_id(cls, v: str) -> str:
        """Validate rule ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('rule_id must contain only alphanumeric characters, underscores, and hyphens')
        return v