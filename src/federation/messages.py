"""
ExoArmur ADMO V2 Federation Signed Message Schemas
Canonical signed message models for federation identity handshake
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from enum import Enum

# Import canonical utilities from Workflow 1
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from replay.canonical_utils import canonical_json, stable_hash

logger = logging.getLogger(__name__)


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms"""
    ED25519 = "ed25519"
    RSA_PSS_SHA256 = "rsa-pss-sha256"


class MessageType(str, Enum):
    """Federation message types"""
    IDENTITY_EXCHANGE = "identity_exchange"
    CAPABILITY_NEGOTIATE = "capability_negotiate"
    TRUST_ESTABLISH = "trust_establish"


class MessageVersion:
    """Message version constants"""
    CURRENT = 1
    IDENTITY_EXCHANGE = 1
    CAPABILITY_NEGOTIATE = 1
    TRUST_ESTABLISH = 1


class SignatureInfo(BaseModel):
    """Signature information for signed messages"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    alg: SignatureAlgorithm = Field(description="Signature algorithm")
    key_id: Optional[str] = Field(description="Key identifier")
    cert_fingerprint: Optional[str] = Field(description="Certificate fingerprint")
    sig_b64: str = Field(description="Base64 encoded signature")
    
    @field_validator('cert_fingerprint')
    @classmethod
    def validate_cert_fingerprint_or_key_id(cls, v, info):
        """Ensure either key_id or cert_fingerprint is provided"""
        if v is None and info.data.get('key_id') is None:
            raise ValueError("Either key_id or cert_fingerprint must be provided")
        return v


# Payload sub-models
class IdentityExchangePayload(BaseModel):
    """Identity exchange message payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    cell_public_key: str = Field(description="Base64 encoded Ed25519 public key")
    certificate_chain: List[str] = Field(description="PE encoded X.509 certificate chain")
    federation_role: str = Field(description="Federation role")
    capabilities: List[str] = Field(description="Supported capabilities")
    trust_score: float = Field(ge=0.0, le=1.0, description="Trust score")
    cell_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional cell metadata")


class CapabilityNegotiatePayload(BaseModel):
    """Capability negotiation message payload"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)
    
    supported_capabilities: List[str] = Field(description="Supported capabilities")
    required_capabilities: List[str] = Field(description="Required capabilities from peer")
    priority: int = Field(ge=1, le=10, description="Negotiation priority")
    capability_constraints: Dict[str, Any] = Field(default_factory=dict, description="Capability constraints")
    negotiation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Negotiation metadata")


class TrustEstablishPayload(BaseModel):
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




class IdentityExchangeMessage(BaseModel):
    """Complete identity exchange message"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)
    
    # Core message fields
    msg_type: Literal[MessageType.IDENTITY_EXCHANGE] = Field(default=MessageType.IDENTITY_EXCHANGE, description="Message type")
    msg_version: int = Field(default=MessageVersion.IDENTITY_EXCHANGE, description="Message version")
    federate_id: str = Field(min_length=1, description="Federate identifier")
    nonce: str = Field(min_length=1, description="Cryptographic nonce for replay protection")
    timestamp_utc: datetime = Field(description="Message timestamp in UTC")
    correlation_id: str = Field(min_length=1, description="Correlation ID for handshake timeline")
    
    # Payload
    payload: IdentityExchangePayload = Field(description="Identity exchange payload")
    
    # Signature
    signature: SignatureInfo = Field(description="Message signature")
    
    @field_validator('timestamp_utc')
    @classmethod
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is in UTC"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        elif v.tzinfo != timezone.utc:
            v = v.astimezone(timezone.utc)
        return v
    
    @field_serializer('timestamp_utc')
    def serialize_timestamp_utc(self, value: datetime) -> str:
        return value.isoformat().replace('+00:00', 'Z')
    
    def signed_payload_dict(self) -> Dict[str, Any]:
        """Return the exact structure to be canonicalized and signed"""
        return {
            'msg_type': self.msg_type,
            'msg_version': self.msg_version,
            'federate_id': self.federate_id,
            'nonce': self.nonce,
            'timestamp_utc': self.timestamp_utc.isoformat().replace('+00:00', 'Z'),
            'correlation_id': self.correlation_id,
            'payload': {
                'cell_public_key': self.payload.cell_public_key,
                'certificate_chain': self.payload.certificate_chain,
                'federation_role': self.payload.federation_role,
                'capabilities': self.payload.capabilities,
                'trust_score': self.payload.trust_score,
                'cell_metadata': self.payload.cell_metadata
            }
        }
    
    def canonical_bytes(self) -> bytes:
        """Produce deterministic bytes for signing"""
        payload_dict = self.signed_payload_dict()
        canonical_json_str = canonical_json(payload_dict)
        return canonical_json_str.encode('utf-8')
    
    def payload_hash(self) -> str:
        """Compute hash of the signed payload"""
        return stable_hash(self.canonical_bytes().decode('utf-8'))


class CapabilityNegotiateMessage(BaseModel):
    """Complete capability negotiation message"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)
    
    # Core message fields
    msg_type: Literal[MessageType.CAPABILITY_NEGOTIATE] = Field(default=MessageType.CAPABILITY_NEGOTIATE, description="Message type")
    msg_version: int = Field(default=MessageVersion.CAPABILITY_NEGOTIATE, description="Message version")
    federate_id: str = Field(min_length=1, description="Federate identifier")
    nonce: str = Field(min_length=1, description="Cryptographic nonce for replay protection")
    timestamp_utc: datetime = Field(description="Message timestamp in UTC")
    correlation_id: str = Field(min_length=1, description="Correlation ID for handshake timeline")
    
    # Payload
    payload: CapabilityNegotiatePayload = Field(description="Capability negotiation payload")
    
    # Signature
    signature: SignatureInfo = Field(description="Message signature")
    
    @field_validator('timestamp_utc')
    @classmethod
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is in UTC"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        elif v.tzinfo != timezone.utc:
            v = v.astimezone(timezone.utc)
        return v
    
    @field_serializer('timestamp_utc')
    def serialize_timestamp_utc(self, value: datetime) -> str:
        """Serialize timestamp as ISO 8601 UTC"""
        return value.isoformat().replace('+00:00', 'Z')
    
    def signed_payload_dict(self) -> Dict[str, Any]:
        """Return the exact structure to be canonicalized and signed"""
        return {
            'msg_type': self.msg_type,
            'msg_version': self.msg_version,
            'federate_id': self.federate_id,
            'nonce': self.nonce,
            'timestamp_utc': self.timestamp_utc.isoformat().replace('+00:00', 'Z'),
            'correlation_id': self.correlation_id,
            'payload': {
                'supported_capabilities': self.payload.supported_capabilities,
                'required_capabilities': self.payload.required_capabilities,
                'priority': self.payload.priority,
                'capability_constraints': self.payload.capability_constraints,
                'negotiation_metadata': self.payload.negotiation_metadata
            }
        }
    
    def canonical_bytes(self) -> bytes:
        """Produce deterministic bytes for signing"""
        payload_dict = self.signed_payload_dict()
        canonical_json_str = canonical_json(payload_dict)
        return canonical_json_str.encode('utf-8')
    
    def payload_hash(self) -> str:
        """Compute hash of the signed payload"""
        return stable_hash(self.canonical_bytes().decode('utf-8'))


class TrustEstablishMessage(BaseModel):
    """Complete trust establishment message"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True)
    
    # Core message fields
    msg_type: Literal[MessageType.TRUST_ESTABLISH] = Field(default=MessageType.TRUST_ESTABLISH, description="Message type")
    msg_version: int = Field(default=MessageVersion.TRUST_ESTABLISH, description="Message version")
    federate_id: str = Field(min_length=1, description="Federate identifier")
    nonce: str = Field(min_length=1, description="Cryptographic nonce for replay protection")
    timestamp_utc: datetime = Field(description="Message timestamp in UTC")
    correlation_id: str = Field(min_length=1, description="Correlation ID for handshake timeline")
    
    # Payload
    payload: TrustEstablishPayload = Field(description="Trust establishment payload")
    
    # Signature
    signature: SignatureInfo = Field(description="Message signature")
    
    @field_validator('timestamp_utc')
    @classmethod
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is in UTC"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        elif v.tzinfo != timezone.utc:
            v = v.astimezone(timezone.utc)
        return v
    
    @field_serializer('timestamp_utc')
    def serialize_timestamp_utc(self, value: datetime) -> str:
        """Serialize timestamp as ISO 8601 UTC"""
        return value.isoformat().replace('+00:00', 'Z')
    
    def signed_payload_dict(self) -> Dict[str, Any]:
        """Return the exact structure to be canonicalized and signed"""
        return {
            'msg_type': self.msg_type,
            'msg_version': self.msg_version,
            'federate_id': self.federate_id,
            'nonce': self.nonce,
            'timestamp_utc': self.timestamp_utc.isoformat().replace('+00:00', 'Z'),
            'correlation_id': self.correlation_id,
            'payload': {
                'trust_score': self.payload.trust_score,
                'trust_reasons': self.payload.trust_reasons,
                'expiration': self.payload.expiration.isoformat().replace('+00:00', 'Z'),
                'trust_policies': self.payload.trust_policies,
                'trust_metadata': self.payload.trust_metadata
            }
        }
    
    def canonical_bytes(self) -> bytes:
        """Produce deterministic bytes for signing"""
        payload_dict = self.signed_payload_dict()
        canonical_json_str = canonical_json(payload_dict)
        return canonical_json_str.encode('utf-8')
    
    def payload_hash(self) -> str:
        """Compute hash of the signed payload"""
        return stable_hash(self.canonical_bytes().decode('utf-8'))


# Union type for all signed messages
FederationSignedMessage = IdentityExchangeMessage | CapabilityNegotiateMessage | TrustEstablishMessage


def create_identity_exchange_message(
    federate_id: str,
    nonce: str,
    correlation_id: str,
    cell_public_key: str,
    certificate_chain: List[str],
    federation_role: str,
    capabilities: List[str],
    trust_score: float,
    signature_alg: SignatureAlgorithm = SignatureAlgorithm.ED25519,
    key_id: Optional[str] = "default-key-id",
    cert_fingerprint: Optional[str] = None,
    signature_b64: str = "",
    cell_metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> IdentityExchangeMessage:
    """Factory function to create identity exchange message"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    payload = IdentityExchangePayload(
        cell_public_key=cell_public_key,
        certificate_chain=certificate_chain,
        federation_role=federation_role,
        capabilities=capabilities,
        trust_score=trust_score,
        cell_metadata=cell_metadata or {}
    )
    
    signature_info = SignatureInfo(
        alg=signature_alg,
        key_id=key_id,
        cert_fingerprint=cert_fingerprint,
        sig_b64=signature_b64
    )
    
    return IdentityExchangeMessage(
        msg_type=MessageType.IDENTITY_EXCHANGE,
        msg_version=MessageVersion.IDENTITY_EXCHANGE,
        federate_id=federate_id,
        nonce=nonce,
        timestamp_utc=timestamp,
        correlation_id=correlation_id,
        payload=payload,
        signature=signature_info
    )


def create_capability_negotiate_message(
    federate_id: str,
    nonce: str,
    correlation_id: str,
    supported_capabilities: List[str],
    required_capabilities: List[str],
    priority: int = 1,
    signature_alg: SignatureAlgorithm = SignatureAlgorithm.ED25519,
    key_id: Optional[str] = "default-key-id",
    cert_fingerprint: Optional[str] = None,
    signature_b64: str = "",
    capability_constraints: Optional[Dict[str, Any]] = None,
    negotiation_metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> CapabilityNegotiateMessage:
    """Factory function to create capability negotiation message"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    payload = CapabilityNegotiatePayload(
        supported_capabilities=supported_capabilities,
        required_capabilities=required_capabilities,
        priority=priority,
        capability_constraints=capability_constraints or {},
        negotiation_metadata=negotiation_metadata or {}
    )
    
    signature_info = SignatureInfo(
        alg=signature_alg,
        key_id=key_id,
        cert_fingerprint=cert_fingerprint,
        sig_b64=signature_b64
    )
    
    return CapabilityNegotiateMessage(
        msg_type=MessageType.CAPABILITY_NEGOTIATE,
        msg_version=MessageVersion.CAPABILITY_NEGOTIATE,
        federate_id=federate_id,
        nonce=nonce,
        timestamp_utc=timestamp,
        correlation_id=correlation_id,
        payload=payload,
        signature=signature_info
    )


def create_trust_establish_message(
    federate_id: str,
    nonce: str,
    correlation_id: str,
    trust_score: float,
    trust_reasons: List[str],
    expiration: datetime,
    signature_alg: SignatureAlgorithm = SignatureAlgorithm.ED25519,
    key_id: Optional[str] = "default-key-id",
    cert_fingerprint: Optional[str] = None,
    signature_b64: str = "",
    trust_policies: Optional[List[str]] = None,
    trust_metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> TrustEstablishMessage:
    """Factory function to create trust establishment message"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    payload = TrustEstablishPayload(
        trust_score=trust_score,
        trust_reasons=trust_reasons,
        expiration=expiration,
        trust_policies=trust_policies or [],
        trust_metadata=trust_metadata or {}
    )
    
    signature_info = SignatureInfo(
        alg=signature_alg,
        key_id=key_id,
        cert_fingerprint=cert_fingerprint,
        sig_b64=signature_b64
    )
    
    return TrustEstablishMessage(
        msg_type=MessageType.TRUST_ESTABLISH,
        msg_version=MessageVersion.TRUST_ESTABLISH,
        federate_id=federate_id,
        nonce=nonce,
        timestamp_utc=timestamp,
        correlation_id=correlation_id,
        payload=payload,
        signature=signature_info
    )
