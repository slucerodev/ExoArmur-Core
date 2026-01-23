"""
Tests for Federation Protocol Boundary Enforcement
Tests V2 federation protocol enforcement and state transitions
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.federation.protocol_enforcer import ProtocolEnforcer
from src.federation.crypto import (
    FederateKeyPair,
    sign_message,
    VerificationFailureReason
)
from src.federation.messages import create_identity_exchange_message
from src.federation.federate_identity_store import FederateIdentityStore
from spec.contracts.models_v1 import (
    FederateIdentityV1,
    FederationRole,
    CellStatus,
    HandshakeState
)


class TestProtocolEnforcer:
    """Test protocol boundary enforcement"""
    
    @pytest.fixture
    def identity_store(self):
        """Test identity store"""
        return FederateIdentityStore()
    
    @pytest.fixture
    def protocol_enforcer(self, identity_store):
        """Test protocol enforcer"""
        return ProtocolEnforcer(identity_store)
    
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
    
    def test_valid_message_passes_enforcement(self, protocol_enforcer, key_pair, federate_identity):
        """Test that valid messages pass protocol enforcement"""
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
        
        signed_message = sign_message(message, key_pair.private_key)
        
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success is True
        assert failure_reason is None
        assert audit_event['success'] is True
        assert audit_event['event_type'] == "signature_verification_success"
    
    def test_unknown_federate_is_rejected(self, protocol_enforcer, key_pair):
        """Test that unknown federates are rejected"""
        message = create_identity_exchange_message(
            federate_id="cell-unknown-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.UNKNOWN_KEY_ID
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.UNKNOWN_KEY_ID
    
    def test_invalid_signature_is_rejected(self, protocol_enforcer, key_pair, federate_identity):
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
        
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.INVALID_SIGNATURE
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.INVALID_SIGNATURE
    
    def test_nonce_reuse_is_rejected(self, protocol_enforcer, key_pair, federate_identity):
        """Test that nonce reuse is rejected"""
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
        
        signed_message = sign_message(message, key_pair.private_key)
        
        # First message should succeed
        success1, failure_reason1, audit_event1 = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success1 is True
        assert failure_reason1 is None
        assert audit_event1['success'] is True
        
        # Second message with same nonce should fail
        success2, failure_reason2, audit_event2 = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success2 is False
        assert failure_reason2 == VerificationFailureReason.NONCE_REUSE
        assert audit_event2['success'] is False
        assert audit_event2['failure_reason'] == VerificationFailureReason.NONCE_REUSE
    
    def test_timestamp_skew_is_rejected(self, protocol_enforcer, key_pair, federate_identity):
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
        
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success is False
        assert failure_reason == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
    
    def test_audit_events_emitted_on_verification_failure(self, protocol_enforcer, key_pair):
        """Test that audit events are emitted on verification failures"""
        message = create_identity_exchange_message(
            federate_id="cell-unknown-01",
            nonce="test-nonce-123",
            correlation_id="test-correlation-456",
            cell_public_key=key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        signed_message = sign_message(message, key_pair.private_key)
        
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        # Verify audit event structure
        assert audit_event is not None
        assert audit_event['event_type'] == "signature_verification_failure"
        assert audit_event['federate_id'] == "cell-unknown-01"
        assert audit_event['key_id'] == key_pair.key_id
        assert audit_event['message_type'] == "identity_exchange"
        assert audit_event['correlation_id'] == "test-correlation-456"
        assert audit_event['success'] is False
        assert audit_event['failure_reason'] == VerificationFailureReason.UNKNOWN_KEY_ID
        assert 'timestamp' in audit_event
    
    def test_handshake_state_transitions(self, protocol_enforcer, key_pair, federate_identity):
        """Test handshake state transitions"""
        # Create identity exchange message
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
        
        signed_message = sign_message(message, key_pair.private_key)
        
        # Process message
        success, failure_reason, audit_event = protocol_enforcer.process_handshake_message(signed_message)
        
        assert success is True
        
        # Check that session was created
        session = protocol_enforcer.identity_store.get_handshake_session(
            "cell-test-01",
            "test-correlation-456"
        )
        
        assert session is not None
        assert session.state == HandshakeState.IDENTITY_EXCHANGE
    
    def test_max_timestamp_skew_configuration(self, protocol_enforcer):
        """Test configurable timestamp skew"""
        # Set custom skew
        protocol_enforcer.set_max_timestamp_skew(60)  # 1 minute
        
        assert protocol_enforcer.max_timestamp_skew_seconds == 60
        
        # Reset to default
        protocol_enforcer.set_max_timestamp_skew(300)  # 5 minutes
        
        assert protocol_enforcer.max_timestamp_skew_seconds == 300
