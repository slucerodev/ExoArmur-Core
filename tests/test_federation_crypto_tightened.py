"""
Tightened tests for Federation Cryptographic Operations
Tests V2 federation crypto verification with deterministic time and isolated state
"""

import pytest
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.sensitive

from exoarmur.federation.crypto import (
    FederateKeyPair,
    sign_message,
    verify_message_signature,
    verify_message_integrity,
    VerificationFailureReason,
    VerificationAuditEvent,
    emit_verification_audit_event,
    serialize_public_key_for_identity,
    deserialize_public_key_from_identity
)
from exoarmur.federation.messages import (
    IdentityExchangeMessage,
    SignatureAlgorithm,
    SignatureInfo,
    IdentityExchangePayload,
    create_identity_exchange_message
)
from tests.federation_fixtures import (
    fixed_clock,
    mock_feature_flags_enabled,
    mock_feature_flags_disabled,
    fresh_identity_store,
    fresh_protocol_enforcer,
    handshake_context,
    test_key_pair,
    test_federate_identity,
    old_timestamp,
    future_timestamp,
    MockFeatureFlags
)
from exoarmur.federation.federate_identity_store import FederateIdentityStore


class TestFederateKeyPair:
    """Test federate key pair operations"""
    
    def test_key_pair_generation(self, test_key_pair):
        """Test key pair generation"""
        assert test_key_pair.private_key is not None
        assert test_key_pair.public_key is not None
        assert test_key_pair.key_id is not None
        assert len(test_key_pair.key_id) == 64  # SHA-256 hash
        assert test_key_pair.public_key_b64 is not None
        assert len(test_key_pair.public_key_b64) > 0
    
    def test_key_pair_from_private_key_bytes(self, test_key_pair):
        """Test creating key pair from private key bytes"""
        from cryptography.hazmat.primitives import serialization
        
        private_bytes = test_key_pair.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        restored_key_pair = FederateKeyPair.from_private_key_bytes(private_bytes)
        
        assert restored_key_pair.key_id == test_key_pair.key_id
        assert restored_key_pair.public_key_b64 == test_key_pair.public_key_b64
    
    def test_key_pair_to_dict(self, test_key_pair):
        """Test converting key pair to dictionary"""
        key_dict = test_key_pair.to_dict()
        
        assert 'key_id' in key_dict
        assert 'public_key' in key_dict
        assert key_dict['key_id'] == test_key_pair.key_id
        assert key_dict['public_key'] == test_key_pair.public_key_b64
        assert 'private_key' not in key_dict  # Never expose private key


class TestMessageSigning:
    """Test message signing operations"""
    
    def test_sign_message(self, test_key_pair, fixed_clock):
        """Test signing a message"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        assert signed_message.signature.alg == SignatureAlgorithm.ED25519
        assert signed_message.signature.key_id == test_key_pair.key_id
        assert signed_message.signature.sig_b64 is not None
        assert len(signed_message.signature.sig_b64) > 0
    
    def test_verify_valid_signature(self, test_key_pair, fixed_clock):
        """Test verifying a valid signature"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        is_valid, error = verify_message_signature(signed_message, test_key_pair.public_key)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_invalid_signature(self, test_key_pair, fixed_clock):
        """Test verifying an invalid signature"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        
        # Sign with one key
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # Try to verify with different key
        wrong_key_pair = FederateKeyPair()
        
        is_valid, error = verify_message_signature(signed_message, wrong_key_pair.public_key)
        
        assert is_valid is False
        assert error == VerificationFailureReason.INVALID_SIGNATURE
    
    def test_signature_over_mutated_payload_fails(self, test_key_pair, fixed_clock):
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
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        signed_message = sign_message(original_message, test_key_pair.private_key)
        
        # Create a new message with mutated payload (since payloads are frozen)
        mutated_message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.9,  # Mutated trust score
            timestamp=fixed_clock.now()
        )
        
        # Copy the signature from the original message
        mutated_message.signature = signed_message.signature
        
        # Verification should fail
        is_valid, error = verify_message_signature(mutated_message, test_key_pair.public_key)
        
        assert is_valid is False
        assert error == VerificationFailureReason.INVALID_SIGNATURE


class TestProtocolEnforcement:
    """Test protocol enforcement with deterministic time"""
    
    def test_valid_message_passes_enforcement(self, handshake_context, test_key_pair, test_federate_identity):
        """Test that valid messages pass protocol enforcement"""
        # Store identity
        handshake_context.identity_store.store_identity(test_federate_identity)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=handshake_context.clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        success, failure_reason, audit_event = handshake_context.verify_signed_message(signed_message)
        
        assert success is True
        assert failure_reason is None
        assert audit_event['success'] is True
        assert audit_event['event_type'] == "signature_verification_success"
    
    def test_unknown_federate_is_rejected(self, handshake_context, test_key_pair):
        """Test that unknown federates are rejected"""
        message = create_identity_exchange_message(
            federate_id="cell-unknown-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=handshake_context.clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        success, failure_reason, audit_event = handshake_context.verify_signed_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.UNKNOWN_KEY_ID
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.UNKNOWN_KEY_ID
    
    def test_invalid_signature_is_rejected(self, handshake_context, test_key_pair, test_federate_identity):
        """Test that invalid signatures are rejected"""
        # Store identity
        handshake_context.identity_store.store_identity(test_federate_identity)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=handshake_context.clock.now()
        )
        
        # Sign with wrong key
        wrong_key_pair = FederateKeyPair()
        signed_message = sign_message(message, wrong_key_pair.private_key)
        
        success, failure_reason, audit_event = handshake_context.verify_signed_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.KEY_MISMATCH
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.KEY_MISMATCH
    
    def test_nonce_reuse_is_rejected(self, handshake_context, test_key_pair, test_federate_identity):
        """Test that nonce reuse is rejected"""
        # Store identity
        handshake_context.identity_store.store_identity(test_federate_identity)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=handshake_context.clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # First verification should succeed
        success1, failure_reason1, audit_event1 = handshake_context.verify_signed_message(signed_message)
        
        assert success1 is True
        assert failure_reason1 is None
        assert audit_event1['success'] is True
        
        # Second verification with same nonce should fail
        success2, failure_reason2, audit_event2 = handshake_context.verify_signed_message(signed_message)
        
        assert success2 is False
        assert failure_reason2 == VerificationFailureReason.NONCE_REUSE
        assert audit_event2['success'] is False
        assert audit_event2['failure_reason'] == VerificationFailureReason.NONCE_REUSE
    
    def test_timestamp_skew_is_rejected(self, handshake_context, test_key_pair, test_federate_identity, old_timestamp):
        """Test that timestamp skew is rejected"""
        # Store identity
        handshake_context.identity_store.store_identity(test_federate_identity)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=old_timestamp
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        success, failure_reason, audit_event = handshake_context.verify_signed_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
    
    def test_future_timestamp_skew_is_rejected(self, handshake_context, test_key_pair, test_federate_identity, future_timestamp):
        """Test that future timestamp skew is rejected"""
        # Store identity
        handshake_context.identity_store.store_identity(test_federate_identity)
        
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=future_timestamp
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        success, failure_reason, audit_event = handshake_context.verify_signed_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS


class TestFeatureFlagIsolation:
    """Test feature flag isolation and import-order independence"""
    
    def test_feature_flag_off_blocks_entrypoints_cleanly(self, mock_feature_flags_disabled):
        """Test that disabled feature flag blocks entrypoints cleanly"""
        # Create store with disabled flags
        store = FederateIdentityStore(feature_flags=mock_feature_flags_disabled)
        
        assert store.is_enabled() is False
        
        # All operations should return early without errors
        assert store.get_identity("any-id") is None
        assert store.list_identities() == []
        assert store.store_identity(None) is False  # Will fail validation but not crash
    
    def test_no_import_time_flag_evaluation(self):
        """Test that handlers don't change behavior based on import order"""
        # Create stores with different flag configurations
        enabled_flags = MockFeatureFlags(v2_federation_enabled=True)
        disabled_flags = MockFeatureFlags(v2_federation_enabled=False)
        
        store_enabled = FederateIdentityStore(feature_flags=enabled_flags)
        store_disabled = FederateIdentityStore(feature_flags=disabled_flags)
        
        # Behavior should be determined by injected flags, not import order
        assert store_enabled.is_enabled() is True
        assert store_disabled.is_enabled() is False
    
    def test_nonce_store_isolated_between_tests(self, fresh_identity_store, test_key_pair, fixed_clock, test_federate_identity):
        """Test that nonce store is isolated between tests"""
        # Create and store identity
        identity = test_federate_identity
        fresh_identity_store.store_identity(identity)
        
        # Create message and verify
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-isolation",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # First verification should succeed
        is_valid1, error1 = verify_message_integrity(
            message=signed_message,
            expected_key_id=test_key_pair.key_id,
            public_key=test_key_pair.public_key,
            nonce_store=fresh_identity_store,
            clock=fixed_clock
        )
        
        assert is_valid1 is True
        assert error1 is None
        
        # Second verification should fail due to nonce reuse
        is_valid2, error2 = verify_message_integrity(
            message=signed_message,
            expected_key_id=test_key_pair.key_id,
            public_key=test_key_pair.public_key,
            nonce_store=fresh_identity_store,
            clock=fixed_clock
        )
        
        assert is_valid2 is False
        assert error2 == VerificationFailureReason.NONCE_REUSE


class TestDeterministicTime:
    """Test deterministic time handling"""
    
    def test_fixed_clock_is_deterministic(self, fixed_clock):
        """Test that fixed clock returns deterministic time"""
        initial_time = fixed_clock.now()
        
        # Multiple calls should return same time
        assert fixed_clock.now() == initial_time
        assert fixed_clock.now() == initial_time
        assert fixed_clock.now() == initial_time
    
    def test_fixed_clock_advance(self, fixed_clock):
        """Test that fixed clock can be advanced"""
        initial_time = fixed_clock.now()
        
        # Advance by 1 hour
        fixed_clock.advance(timedelta(hours=1))
        
        # Time should be advanced
        advanced_time = fixed_clock.now()
        assert advanced_time == initial_time + timedelta(hours=1)
        
        # Further advance
        fixed_clock.advance(timedelta(minutes=30))
        final_time = fixed_clock.now()
        assert final_time == initial_time + timedelta(hours=1, minutes=30)
    
    def test_timestamp_validation_uses_injected_clock(self, fresh_identity_store, test_key_pair, fixed_clock, test_federate_identity):
        """Test that timestamp validation uses injected clock"""
        # Store identity
        identity = test_federate_identity
        fresh_identity_store.store_identity(identity)
        
        # Create message with current time
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-timestamp",
            correlation_id="test-correlation-456",
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # Should succeed with current time
        is_valid1, error1 = verify_message_integrity(
            message=signed_message,
            expected_key_id=test_key_pair.key_id,
            public_key=test_key_pair.public_key,
            nonce_store=fresh_identity_store,
            clock=fixed_clock
        )
        
        assert is_valid1 is True
        assert error1 is None
        
        # Advance clock beyond skew limit
        fixed_clock.advance(timedelta(hours=1))
        
        # Should now fail due to timestamp skew
        is_valid2, error2 = verify_message_integrity(
            message=signed_message,
            expected_key_id=test_key_pair.key_id,
            public_key=test_key_pair.public_key,
            nonce_store=fresh_identity_store,
            clock=fixed_clock
        )
        
        assert is_valid2 is False
        assert error2 == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS


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
    
    def test_emit_verification_audit_event(self, fixed_clock):
        """Test emitting verification audit events"""
        message = create_identity_exchange_message(
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key="test-public-key",
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
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
        from exoarmur.federation.crypto import generate_nonce
        
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        
        assert nonce1 != nonce2
        assert len(nonce1) > 0
        assert len(nonce2) > 0
    
    def test_serialize_deserialize_public_key(self, test_key_pair):
        """Test public key serialization/deserialization"""
        # Serialize
        serialized = serialize_public_key_for_identity(test_key_pair.public_key)
        
        # Deserialize
        deserialized = deserialize_public_key_from_identity(serialized)
        
        # Verify they're the same
        from cryptography.hazmat.primitives import serialization
        
        assert test_key_pair.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ) == deserialized.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
