"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Identity Models
Pydantic v2 models for federation identity handshake matching federation_identity_v2.yaml contract
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from enum import Enum
import uuid


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


class CapabilityType(str, Enum):
    """Federation capability types"""
    BELIEF_AGGREGATION = "belief_aggregation"
    POLICY_DISTRIBUTION = "policy_distribution"
    AUDIT_CONSOLIDATION = "audit_consolidation"
    OPERATOR_APPROVAL = "operator_approval"


class HandshakeState(str, Enum):
    """Handshake state enumeration"""
    UNINITIALIZED = "uninitialized"
    IDENTITY_EXCHANGE = "identity_exchange"
    CAPABILITY_NEGOTIATION = "capability_negotiation"
    TRUST_ESTABLISHMENT = "trust_establishment"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    FAILED_IDENTITY = "failed_identity"
    FAILED_CAPABILITIES = "failed_capabilities"
    FAILED_TRUST = "failed_trust"
    SUSPENDED = "suspended"


class CellIdentity(BaseModel):
    """Cell identity information matching federation_identity_v2.yaml contract"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    cell_id: str = Field(..., description="Unique cell identifier")
    cell_public_key: str = Field(..., description="Base64 encoded Ed25519 public key")
    cell_certificate_chain: List[str] = Field(..., description="PE encoded X.509 certificate chain")
    federation_role: FederationRole = Field(default=FederationRole.MEMBER, description="Federation role")
    capabilities: List[CapabilityType] = Field(..., description="Supported capabilities")
    trust_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Trust score")
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last heartbeat timestamp")
    status: CellStatus = Field(default=CellStatus.ACTIVE, description="Cell status")
    
    @field_validator('cell_id')
    @classmethod
    def validate_cell_id_format(cls, v):
        """Validate cell_id format: cell-[region]-[cluster]-[node]"""
        if not v.startswith('cell-'):
            raise ValueError('cell_id must start with "cell-"')
        parts = v.split('-')
        if len(parts) < 4:
            raise ValueError('cell_id must have format: cell-[region]-[cluster]-[node]')
        return v


class IdentityExchangeMessage(BaseModel):
    """Identity exchange message matching contract"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    cell_identity: CellIdentity = Field(..., description="Cell identity information")
    signature: str = Field(..., description="Ed25519 signature of message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")
    nonce: str = Field(..., description="Cryptographic nonce for replay protection")


class CapabilityNegotiateMessage(BaseModel):
    """Capability negotiation message matching contract"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    supported_capabilities: List[CapabilityType] = Field(..., description="Supported capabilities")
    required_capabilities: List[CapabilityType] = Field(..., description="Required capabilities from peer")
    priority: int = Field(default=1, ge=1, le=10, description="Negotiation priority")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")
    signature: str = Field(..., description="Ed25519 signature of message")
    nonce: str = Field(..., description="Cryptographic nonce for replay protection")


class TrustEstablishMessage(BaseModel):
    """Trust establishment message matching contract"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Proposed trust score")
    trust_reasons: List[str] = Field(..., description="Reasons for trust score")
    expiration: datetime = Field(..., description="Trust score expiration")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")
    signature: str = Field(..., description="Ed25519 signature of message")
    nonce: str = Field(..., description="Cryptographic nonce for replay protection")


class FederationConfirmMessage(BaseModel):
    """Federation confirmation message matching contract"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    federation_id: str = Field(..., description="Federation identifier")
    member_cells: List[str] = Field(..., description="Member cell IDs")
    coordinator_cell: str = Field(..., description="Coordinator cell ID")
    terms: Dict[str, Any] = Field(..., description="Federation terms")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")
    signature: str = Field(..., description="Ed25519 signature of message")
    nonce: str = Field(..., description="Cryptographic nonce for replay protection")


class HandshakeSession(BaseModel):
    """Handshake session tracking"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    session_id: str = Field(..., description="Session identifier")
    session_nonce: str = Field(..., description="Session nonce for replay protection")
    initiator_cell_id: str = Field(..., description="Initiator cell ID")
    responder_cell_id: str = Field(..., description="Responder cell ID")
    current_state: HandshakeState = Field(default=HandshakeState.UNINITIALIZED, description="Current handshake state")
    step_index: int = Field(default=0, description="Current step index")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Session creation time")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update time")


class FederationIdentityMessage(BaseModel):
    """Union type for all federation identity messages"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    message_type: str = Field(..., description="Message type identifier")
    message_data: Union[IdentityExchangeMessage, CapabilityNegotiateMessage, TrustEstablishMessage, FederationConfirmMessage] = Field(..., description="Message payload")
