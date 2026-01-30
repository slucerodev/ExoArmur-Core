"""
ExoArmur ADMO V2 Federation Cryptographic Operations
Ed25519 signing and verification for federation identity handshake
"""

import logging
import base64
import secrets
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

# Import canonical utilities from Workflow 1
import sys
import os
from exoarmur.replay.canonical_utils import canonical_json, stable_hash

# Import federation models
from .messages import (
    FederationSignedMessage,
    SignatureInfo,
    SignatureAlgorithm
)

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of message verification"""
    
    success: bool
    failure_reason: Optional[str] = None
    audit_event: Optional[dict] = None
    
    @classmethod
    def success_result(cls, audit_event: dict) -> 'VerificationResult':
        """Create successful verification result"""
        return cls(success=True, audit_event=audit_event)
    
    @classmethod
    def failure_result(cls, failure_reason: str, audit_event: dict) -> 'VerificationResult':
        """Create failed verification result"""
        return cls(success=False, failure_reason=failure_reason, audit_event=audit_event)


class VerificationFailureReason(str):
    """Reasons for verification failure"""
    INVALID_SIGNATURE = "invalid_signature"
    KEY_MISMATCH = "key_mismatch"
    NONCE_REUSE = "nonce_reuse"
    TIMESTAMP_OUT_OF_BOUNDS = "timestamp_out_of_bounds"
    UNKNOWN_KEY_ID = "unknown_key_id"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    MISSING_SIGNATURE = "missing_signature"


class FederateKeyPair:
    """Federate key pair for Ed25519 signing"""
    
    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        """
        Initialize key pair
        Args:
            private_key: Optional existing private key, generates new one if None
        """
        if private_key is None:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            self._private_key = private_key
        
        self._public_key = self._private_key.public_key()
        self._key_id = self._compute_key_id()
    
    def _compute_key_id(self) -> str:
        """Compute stable key_id as hash of public key"""
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return stable_hash(base64.b64encode(public_bytes).decode('utf-8'))
    
    @property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        """Get private key (never logged or audited)"""
        return self._private_key
    
    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Get public key"""
        return self._public_key
    
    @property
    def key_id(self) -> str:
        """Get key identifier"""
        return self._key_id
    
    @property
    def public_key_b64(self) -> str:
        """Get public key as base64 string"""
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_bytes).decode('utf-8')
    
    @classmethod
    def from_private_key_bytes(cls, private_key_bytes: bytes) -> 'FederateKeyPair':
        """Create key pair from private key bytes"""
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        return cls(private_key)
    
    @classmethod
    def from_public_key_b64(cls, public_key_b64: str) -> 'FederateKeyPair':
        """Create key pair from public key (private key will be None)"""
        public_bytes = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        
        # Create a key pair with only public key (private key will be None)
        key_pair = cls.__new__(cls)
        key_pair._private_key = None
        key_pair._public_key = public_key
        key_pair._key_id = key_pair._compute_key_id()
        return key_pair
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary (only public key)"""
        return {
            'key_id': self.key_id,
            'public_key': self.public_key_b64
        }


def sign_message(message: FederationSignedMessage, private_key: ed25519.Ed25519PrivateKey) -> FederationSignedMessage:
    """
    Sign a federation message with Ed25519
    
    Args:
        message: Message to sign
        private_key: Private key for signing
        
    Returns:
        Message with signature attached
    """
    # Get canonical bytes for signing
    canonical_bytes = message.canonical_bytes()
    
    # Sign the canonical bytes
    signature = private_key.sign(canonical_bytes)
    
    # Create signature info
    signature_info = SignatureInfo(
        alg=SignatureAlgorithm.ED25519,
        key_id=FederateKeyPair(private_key).key_id,
        cert_fingerprint=None,
        sig_b64=base64.b64encode(signature).decode('utf-8')
    )
    
    # Update message with signature
    message.signature = signature_info
    
    return message


def verify_message_signature(
    message: FederationSignedMessage,
    public_key: ed25519.Ed25519PublicKey
) -> Tuple[bool, Optional[str]]:
    """
    Verify message signature
    
    Args:
        message: Message to verify
        public_key: Public key for verification
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    try:
        # Get canonical bytes
        canonical_bytes = message.canonical_bytes()
        
        # Decode signature
        signature = base64.b64decode(message.signature.sig_b64)
        
        # Verify signature
        public_key.verify(signature, canonical_bytes)
        
        return True, None
        
    except InvalidSignature:
        return False, VerificationFailureReason.INVALID_SIGNATURE
    except Exception as e:
        logger.error(f"Unexpected error during signature verification: {e}")
        return False, VerificationFailureReason.INVALID_SIGNATURE


def verify_message_integrity(
    message: FederationSignedMessage,
    expected_key_id: str,
    public_key: ed25519.Ed25519PublicKey,
    nonce_store,
    clock=None,
    max_timestamp_skew_seconds: int = 300  # 5 minutes
) -> Tuple[bool, Optional[str]]:
    """
    Complete message integrity verification
    
    Args:
        message: Message to verify
        expected_key_id: Expected key identifier
        public_key: Public key for verification
        nonce_store: Nonce store for replay protection
        max_timestamp_skew_seconds: Maximum allowed timestamp skew
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    # 1. Verify key_id matches
    if message.signature.key_id != expected_key_id:
        return False, VerificationFailureReason.KEY_MISMATCH
    
    # 2. Verify signature
    signature_valid, signature_error = verify_message_signature(message, public_key)
    if not signature_valid:
        return False, signature_error
    
    # 3. Check timestamp freshness
    if clock is None:
        from .clock import SystemClock
        clock = SystemClock()
    
    now = clock.now()
    message_time = message.timestamp_utc
    
    # Allow both future and past timestamps within bounds
    time_diff = abs((now - message_time).total_seconds())
    if time_diff > max_timestamp_skew_seconds:
        return False, VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
    
    # 4. Check nonce uniqueness
    if not nonce_store.is_nonce_available(message.federate_id, message.nonce):
        return False, VerificationFailureReason.NONCE_REUSE
    
    # 5. Mark nonce as used to prevent replay
    nonce_store.mark_nonce_used(message.federate_id, message.nonce)
    
    return True, None


def generate_nonce() -> str:
    """Generate a cryptographically secure nonce"""
    return secrets.token_urlsafe(32)


def create_test_key_pair() -> FederateKeyPair:
    """Create a test key pair for unit tests"""
    return FederateKeyPair()


def serialize_public_key_for_identity(public_key: ed25519.Ed25519PublicKey) -> str:
    """Serialize public key for storage in federate identity"""
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return base64.b64encode(public_bytes).decode('utf-8')


def deserialize_public_key_from_identity(public_key_str: str) -> ed25519.Ed25519PublicKey:
    """Deserialize public key from federate identity storage"""
    public_bytes = base64.b64decode(public_key_str)
    return ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)


class VerificationAuditEvent:
    """Audit event for verification operations"""
    
    def __init__(
        self,
        event_type: str,
        federate_id: str,
        key_id: str,
        message_type: str,
        correlation_id: str,
        success: bool,
        failure_reason: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.federate_id = federate_id
        self.key_id = key_id
        self.message_type = message_type
        self.correlation_id = correlation_id
        self.success = success
        self.failure_reason = failure_reason
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging"""
        result = {
            'event_type': self.event_type,
            'federate_id': self.federate_id,
            'key_id': self.key_id,
            'message_type': self.message_type,
            'correlation_id': self.correlation_id,
            'success': self.success,
            'timestamp': self.timestamp.isoformat().replace('+00:00', 'Z')
        }
        
        if self.failure_reason:
            result['failure_reason'] = self.failure_reason
            
        return result


def emit_verification_audit_event(
    event_type: str,
    message: FederationSignedMessage,
    success: bool,
    failure_reason: Optional[str] = None
) -> VerificationAuditEvent:
    """
    Create verification audit event
    
    Args:
        event_type: Type of audit event
        message: Message being verified
        success: Whether verification succeeded
        failure_reason: Reason for failure (if any)
        
    Returns:
        Audit event for logging
    """
    return VerificationAuditEvent(
        event_type=event_type,
        federate_id=message.federate_id,
        key_id=message.signature.key_id,
        message_type=message.msg_type,
        correlation_id=message.correlation_id,
        success=success,
        failure_reason=failure_reason
    )
