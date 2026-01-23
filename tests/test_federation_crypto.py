"""
Tests for Federation Cryptographic Operations
Tests V2 federation crypto verification and replay protection
"""

import pytest
import base64
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519

from src.federation.crypto import (
    FederateKeyPair,
    sign_message,
    verify_message_signature,
    verify_message_integrity,
    generate_nonce,
    VerificationFailureReason,
    VerificationAuditEvent,
    emit_verification_audit_event,
    serialize_public_key_for_identity,
    deserialize_public_key_from_identity
)
from src.federation.messages import (
    IdentityExchangeMessage,
    CapabilityNegotiateMessage,
    TrustEstablishMessage,
    SignatureAlgorithm,
    SignatureInfo,
    IdentityExchangePayload,
    CapabilityNegotiatePayload,
    TrustEstablishPayload,
    create_identity_exchange_message,
    create_capability_negotiate_message,
    create_trust_establish_message
)
from src.federation.federate_identity_store import FederateIdentityStore
from spec.contracts.models_v1 import FederateIdentityV1, FederationRole, CellStatus


class TestFederateKeyPair:
    """Test federate key pair operations"""
    
    def test_key_pair_generation(self):
        """Test key pair generation"""
        key_pair = FederateKeyPair()
        
        assert key_pair.private_key is not None
        assert key_pair.public_key is not None
        assert key_pair.key_id is not None
        assert len(key_pair.key_id) == 64  # SHA-256 hash
        assert key_pair.public_key_b64 is not None
        assert len(key_pair.public_key_b64) > 0
    
    def test_key_pair_from_private_key_bytes(self):
        """Test creating key pair from private key bytes"""
        original_key_pair = FederateKeyPair()
        private_bytes = original_key_pair.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        restored_key_pair = FederateKeyPair.from_private_key_bytes(private_bytes)
        
        assert restored_key_pair.key_id == original_key_pair.key_id
        assert restored_key_pair.public_key_b64 == original_key_pair.public_key_b64
    
    def test_key_pair_from_public_key_b64(self):
        """Test creating key pair from public key only"""
        original_key_pair = FederateKeyPair()
        
        public_only_key_pair = FederateKeyPair.from_public_key_b64(original_key_pair.public_key_b64)
        
        assert public_only_key_pair.key_id == original_key_pair.key_id
        assert public_only_key_pair.public_key_b64 == original_key_pair.public_key_b64
        assert public_only_key_pair.private_key is None
    
    def test_key_pair_to_dict(self):
        """Test converting key pair to dictionary"""
        key_pair = FederateKeyPair()
        key_dict = key_pair.to_dict()
        
        assert 'key_id' in key_dict
        assert 'public_key' in key_dict
        assert key_dict['key_id'] == key_pair.key_id
        assert key_dict['public_key'] == key_pair.public_key_b64
        assert 'private_key' not in key_dict  # Never expose private key


class TestMessageSigning:
    """Test message signing operations"""
    
    @pytest.fixture
    def key_pair(self):
        """Test key pair"""
        return FederateKeyPair()
    
    @pytest.fixture
    def sample_message(self):
        """Sample identity exchange message"""
        return create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
    
    def test_sign_message(self, key_pair, sample_message):
        """Test signing a message"""
        signed_message = sign_message(sample_message, key_pair.private_key)
        
        assert signed_message.signature.alg == SignatureAlgorithm.ED25519
        assert signed_message.signature.key_id == key_pair.key_id
        assert signed_message.signature.sig_b64 is not None
        assert len(signed_message.signature.sig_b64) > 0
    
    def test_verify_valid_signature(self, key_pair, sample_message):
        """Test verifying a valid signature"""
        signed_message = sign_message(sample_message, key_pair.private_key)
        
        is_valid, error = verify_message_signature(signed_message, key_pair.public_key)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_invalid_signature(self, key_pair, sample_message):
        """Test verifying an invalid signature"""
        # Sign with one key
        signed_message = sign_message(sample_message, key_pair.private_key)
        
        # Try to verify with different key
        wrong_key_pair = FederateKeyPair()
        
        is_valid, error = verify_message_signature(signed_message, wrong_key_pair.public_key)
        
        assert is_valid is False
        assert error == VerificationFailureReason.INVALID_SIGNATURE
    
    def test_signature_over_mutated_payload_fails(self, key_pair):
        """Test that signature verification fails if payload is mutated"""
        # Create and sign message
        original_message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        signed_message = sign_message(original_message, key_pair.private_key)
        
        # Create a new message with mutated payload (since payloads are frozen)
        mutated_message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.9  # Mutated trust score
        )
        
        # Copy the signature from the original message
        mutated_message.signature = signed_message.signature
        
        # Verification should fail
        is_valid, error = verify_message_signature(mutated_message, key_pair.public_key)
        
        assert is_valid is False
        assert error == VerificationFailureReason.INVALID_SIGNATURE


class TestProtocolEnforcement:
    """Test protocol enforcement and replay protection"""
    
    @pytest.fixture
    def identity_store(self):
        """Test identity store"""
        # Enable V2 federation identity for tests
        import os
        os.environ['EXOARMUR_FLAG_V2_FEDERATION_IDENTITY_ENABLED'] = 'true'
        return FederateIdentityStore()
    
    @pytest.fixture
    def key_pair(self):
        """Test key pair"""
        return FederateKeyPair()
    
    @pytest.fixture
    def federate_identity(self, identity_store, key_pair):
        """Test federate identity"""
        identity = FederateIdentityV1(
            federate_id="cell-us-east-1-cluster-01-node-01",
            public_key=key_pair.public_key_b64,
            key_id=key_pair.key_id,
            certificate_chain=["test-cert"],
            federation_role=FederationRole.MEMBER,
            status=CellStatus.ACTIVE,
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            last_seen=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        identity_store.store_identity(identity)
        return identity
    
    def test_valid_signed_message_is_accepted(self, identity_store, key_pair, federate_identity):
        """Test that valid signed messages are accepted"""
        import secrets
        
        # Clear any existing nonces to ensure clean state
        identity_store._nonces.clear()
        
        # Generate unique nonce for this test
        unique_nonce = f"test-nonce-{secrets.token_urlsafe(8)}"
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce=unique_nonce,
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        is_valid, error = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store
        )
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_signature_is_rejected(self, identity_store, key_pair, federate_identity):
        """Test that invalid signatures are rejected"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        # Sign with wrong key
        wrong_key_pair = FederateKeyPair()
        signed_message = sign_message(message, wrong_key_pair.private_key)
        
        is_valid, error = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store
        )
        
        assert is_valid is False
        assert error == VerificationFailureReason.KEY_MISMATCH
    
    def test_unknown_key_id_is_rejected(self, identity_store, key_pair):
        """Test that unknown key IDs are rejected"""
        message = create_identity_exchange_message(
            federate_id="cell-unknown-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        is_valid, error = verify_message_integrity(
            message=signed_message,
            expected_key_id="unknown-key-id",
            public_key=key_pair.public_key,
            nonce_store=identity_store
        )
        
        assert is_valid is False
        assert error == VerificationFailureReason.KEY_MISMATCH
    
    def test_nonce_reuse_is_rejected(self, identity_store, key_pair, federate_identity):
        """Test that nonce reuse is rejected"""
        import secrets
        
        # Clear any existing nonces to ensure clean state
        identity_store._nonces.clear()
        
        # Generate unique nonce for this test
        unique_nonce = f"test-nonce-reuse-{secrets.token_urlsafe(8)}"
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce=unique_nonce,
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        # First verification should succeed
        is_valid1, error1 = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store
        )
        
        assert is_valid1 is True
        assert error1 is None
        
        # Second verification with same nonce should fail
        is_valid2, error2 = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store
        )
        
        assert is_valid2 is False
        assert error2 == VerificationFailureReason.NONCE_REUSE
    
    def test_timestamp_skew_is_rejected(self, identity_store, key_pair, federate_identity):
        """Test that timestamp skew is rejected"""
        # Create message with old timestamp
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=old_timestamp
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        is_valid, error = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store,
            max_timestamp_skew_seconds=300  # 5 minutes
        )
        
        assert is_valid is False
        assert error == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
    
    def test_future_timestamp_skew_is_rejected(self, identity_store, key_pair, federate_identity):
        """Test that future timestamp skew is rejected"""
        # Create message with future timestamp
        future_timestamp = datetime.now(timezone.utc) + timedelta(hours=1)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=future_timestamp
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        is_valid, error = verify_message_integrity(
            message=signed_message,
            expected_key_id=key_pair.key_id,
            public_key=key_pair.public_key,
            nonce_store=identity_store,
            max_timestamp_skew_seconds=300  # 5 minutes
        )
        
        assert is_valid is False
        assert error == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS


class TestAuditEvents:
    """Test verification audit events"""
    
    def test_audit_event_creation(self):
        """Test audit event creation"""
        event = VerificationAuditEvent(
            event_type="signature_verification_success",
            federate_id="cell-us-east-1-cluster-01-node-01",
            key_id="key-123",
            message_type="identity_exchange",
            correlation_id="corr-456",
            success=True
        )
        
        assert event.event_type == "signature_verification_success"
        assert event.federate_id == "cell-us-east-1-cluster-01-node-01"
        assert event.key_id == "key-123"
        assert event.message_type == "identity_exchange"
        assert event.correlation_id == "corr-456"
        assert event.success is True
        assert event.failure_reason is None
        assert event.timestamp is not None
    
    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary"""
        event = VerificationAuditEvent(
            event_type="signature_verification_failure",
            federate_id="cell-us-east-1-cluster-01-node-01",
            key_id="key-123",
            message_type="identity_exchange",
            correlation_id="corr-456",
            success=False,
            failure_reason=VerificationFailureReason.INVALID_SIGNATURE
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['event_type'] == "signature_verification_failure"
        assert event_dict['federate_id'] == "cell-us-east-1-cluster-01-node-01"
        assert event_dict['key_id'] == "key-123"
        assert event_dict['message_type'] == "identity_exchange"
        assert event_dict['correlation_id'] == "corr-456"
        assert event_dict['success'] is False
        assert event_dict['failure_reason'] == VerificationFailureReason.INVALID_SIGNATURE
        assert 'timestamp' in event_dict
    
    def test_emit_verification_audit_event(self):
        """Test emitting verification audit events"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        # Success event
        success_event = emit_verification_audit_event(
            event_type="signature_verification_success",
            message=message,
            success=True
        )
        
        assert success_event.success is True
        assert success_event.failure_reason is None
        
        # Failure event
        failure_event = emit_verification_audit_event(
            event_type="signature_verification_failure",
            message=message,
            success=False,
            failure_reason=VerificationFailureReason.INVALID_SIGNATURE
        )
        
        assert failure_event.success is False
        assert failure_event.failure_reason == VerificationFailureReason.INVALID_SIGNATURE


class TestUtilityFunctions:
    """Test cryptographic utility functions"""
    
    def test_generate_nonce(self):
        """Test nonce generation"""
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        
        assert nonce1 != nonce2
        assert len(nonce1) > 0
        assert len(nonce2) > 0
    
    def test_serialize_deserialize_public_key(self):
        """Test public key serialization/deserialization"""
        key_pair = FederateKeyPair()
        
        # Serialize
        serialized = serialize_public_key_for_identity(key_pair.public_key)
        
        # Deserialize
        deserialized = deserialize_public_key_from_identity(serialized)
        
        # Verify they're the same
        assert key_pair.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ) == deserialized.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )


# Import serialization for tests
from cryptography.hazmat.primitives import serialization
