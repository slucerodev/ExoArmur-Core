"""
Tests for HandshakeController
Tests complete handshake flow with verification, retry logic, and audit events
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional

# Import fixtures from federation_fixtures
from tests.federation_fixtures import (
    fixed_clock,
    handshake_context,
    test_key_pair,
    test_federate_identity,
    mock_feature_flags_enabled
)

from spec.contracts.models_v1 import (
    HandshakeState,
    FederationRole,
    CellStatus
)
from src.federation.handshake_controller import HandshakeController, HandshakeResult
from src.federation.handshake_state_machine import HandshakeConfig, HandshakeTransitionReason
from src.federation.crypto import VerificationFailureReason
from src.federation.messages import (
    MessageType,
    create_identity_exchange_message,
    create_capability_negotiate_message,
    create_trust_establish_message
)
from src.federation.clock import FixedClock
from tests.federation_fixtures import (
    fixed_clock,
    handshake_context,
    test_key_pair,
    test_federate_identity
)


class TestHandshakeController:
    """Test handshake controller with complete flow scenarios"""
    
    @pytest.fixture
    def controller(self, handshake_context, fixed_clock):
        """Test handshake controller"""
        config = HandshakeConfig(
            max_retry_attempts=3,
            base_retry_delay=timedelta(seconds=1),
            max_retry_delay=timedelta(seconds=10),
            handshake_timeout=timedelta(minutes=10),
            correlation_id_ttl=timedelta(hours=24)
        )
        return HandshakeController(handshake_context, fixed_clock, config)
    
    def test_handshake_fails_without_signature(self, controller, test_key_pair, test_federate_identity):
        """Test that handshake fails without proper signature"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity first
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Create message without signing
        message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            key_id=test_federate_identity.key_id
        )
        
        # Start handshake
        result = controller.start_handshake(federate_id, correlation_id, message)
        
        assert result.success is False
        assert result.failure_reason == VerificationFailureReason.INVALID_SIGNATURE
        assert result.session_state == HandshakeState.FAILED_IDENTITY
        assert result.audit_event is not None
        assert result.audit_event["event_type"] == "handshake_failed"
        assert result.retry_after is None
    
    def test_handshake_fails_on_nonce_reuse(self, controller, test_key_pair, test_federate_identity):
        """Test that handshake fails on nonce reuse"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Create and sign message
        message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=controller.clock.now()
        )
        from src.federation.crypto import sign_message
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # Start handshake and process message
        controller.start_handshake(federate_id, correlation_id)
        result1 = controller.process_message(correlation_id, signed_message)
        
        assert result1.success is True
        assert result1.session_state == HandshakeState.IDENTITY_EXCHANGE
        
        # Try to reuse same nonce (create new message with same nonce)
        message2 = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",  # Same nonce
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=controller.clock.now()
        )
        signed_message2 = sign_message(message2, test_key_pair.private_key)
        
        # Should fail due to nonce reuse
        result2 = controller.process_message(correlation_id, signed_message2)
        
        assert result2.success is False
        assert result2.failure_reason == VerificationFailureReason.NONCE_REUSE
        assert result2.session_state == HandshakeState.IDENTITY_EXCHANGE
        assert result2.audit_event is not None
        assert result2.audit_event["event_type"] == "handshake_retry"
    
    def test_handshake_reaches_confirmed_on_valid_sequence(self, controller, test_key_pair, test_federate_identity):
        """Test that handshake reaches confirmed state with valid message sequence"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Start handshake
        result = controller.start_handshake(federate_id, correlation_id)
        assert result.success is True
        assert result.session_state == HandshakeState.UNINITIALIZED
        
        # Step 1: Identity Exchange
        identity_message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_key_pair.public_key_b64,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=controller.clock.now()
        )
        from src.federation.crypto import sign_message
        signed_identity = sign_message(identity_message, test_key_pair.private_key)
        
        result1 = controller.process_message(correlation_id, signed_identity)
        assert result1.success is True
        assert result1.session_state == HandshakeState.IDENTITY_EXCHANGE
        
        # Step 2: Capability Negotiation
        capability_message = create_capability_negotiate_message(
            federate_id=federate_id,
            nonce="test-nonce-456",
            correlation_id=correlation_id,
            supported_capabilities=["belief_aggregation", "policy_distribution"],
            required_capabilities=["belief_aggregation"],
            timestamp=controller.clock.now()
        )
        signed_capability = sign_message(capability_message, test_key_pair.private_key)
        
        result2 = controller.process_message(correlation_id, signed_capability)
        assert result2.success is True
        assert result2.session_state == HandshakeState.CAPABILITY_NEGOTIATION
        
        # Step 3: Trust Establishment
        trust_message = create_trust_establish_message(
            federate_id=federate_id,
            nonce="test-nonce-789",
            correlation_id=correlation_id,
            trust_score=0.85,
            trust_reasons=["verified_identity", "capability_match"],
            expiration=controller.clock.now() + timedelta(hours=24),
            timestamp=controller.clock.now()
        )
        signed_trust = sign_message(trust_message, test_key_pair.private_key)
        
        result3 = controller.process_message(correlation_id, signed_trust)
        assert result3.success is True
        assert result3.session_state == HandshakeState.CONFIRMED
        
        # Verify audit events were emitted
        status = controller.get_session_status(correlation_id)
        assert status is not None
        assert status["current_state"] == "confirmed"
        assert status["transition_count"] == 3  # Start + 2 message transitions + confirmation
        assert status["is_terminal"] is True
    
    def test_handshake_stops_after_failed_identity(self, controller, test_key_pair, test_federate_identity):
        """Test that handshake stops after identity failure"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Start handshake
        controller.start_handshake(federate_id, correlation_id)
        
        # Create message with wrong signature (simulating identity failure)
        message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=controller.clock.now()
        )
        
        # Sign with wrong key
        from src.federation.crypto import FederateKeyPair, sign_message
        wrong_key = FederateKeyPair()
        signed_message = sign_message(message, wrong_key.private_key)
        
        result = controller.process_message(correlation_id, signed_message)
        
        assert result.success is False
        assert result.session_state == HandshakeState.FAILED_IDENTITY
        assert result.failure_reason == VerificationFailureReason.KEY_MISMATCH
        
        # Try to continue with capability negotiation (should fail)
        capability_message = create_capability_negotiate_message(
            federate_id=federate_id,
            nonce="test-nonce-456",
            correlation_id=correlation_id,
            supported_capabilities=["belief_aggregation"],
            required_capabilities=["belief_aggregation"],
            timestamp=controller.clock.now()
        )
        signed_capability = sign_message(capability_message, test_key_pair.private_key)
        
        result2 = controller.process_message(correlation_id, signed_capability)
        assert result2.success is False
        assert result2.session_state == HandshakeState.FAILED_IDENTITY  # Should remain in failed state
        assert result2.audit_event is not None
        assert result2.audit_event["event_type"] == "handshake_failed"
    
    def test_handshake_retry_backoff_enforced(self, controller, test_key_pair, test_federate_identity, fixed_clock):
        """Test that retry backoff is enforced"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Start handshake
        controller.start_handshake(federate_id, correlation_id)
        
        # Create message with timestamp skew (retryable error)
        old_timestamp = fixed_clock.now() - timedelta(hours=1)
        message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=old_timestamp
        )
        from src.federation.crypto import sign_message
        signed_message = sign_message(message, test_key_pair.private_key)
        
        # First attempt should fail with retry
        result1 = controller.process_message(correlation_id, signed_message)
        assert result1.success is False
        assert result1.failure_reason == VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS
        assert result1.retry_after is not None
        assert result1.retry_after == timedelta(seconds=1)  # First retry delay
        
        # Second attempt should fail with longer retry
        result2 = controller.process_message(correlation_id, signed_message)
        assert result2.success is False
        assert result2.retry_after == timedelta(seconds=2)  # Second retry delay
        
        # Third attempt should fail with longer retry
        result3 = controller.process_message(correlation_id, signed_message)
        assert result3.success is False
        assert result3.retry_after == timedelta(seconds=4)  # Third retry delay
        
        # Fourth attempt should exceed max retries and fail permanently
        result4 = controller.process_message(correlation_id, signed_message)
        assert result4.success is False
        assert result4.session_state == HandshakeState.FAILED_IDENTITY
        assert result4.failure_reason == HandshakeTransitionReason.RETRY_EXHAUSTED
        assert result4.retry_after is None  # No retry after exhaustion
    
    def test_handshake_timeout_emits_audit_event(self, controller, test_key_pair, test_federate_identity, fixed_clock):
        """Test that handshake timeout emits audit event"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Start handshake
        controller.start_handshake(federate_id, correlation_id)
        
        # Advance clock beyond timeout
        fixed_clock.advance(timedelta(minutes=11))
        
        # Try to process any message (should trigger timeout handling)
        message = create_identity_exchange_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            cell_public_key=test_federate_identity.public_key,
            certificate_chain=["test-cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=fixed_clock.now()
        )
        from src.federation.crypto import sign_message
        signed_message = sign_message(message, test_key_pair.private_key)
        
        result = controller.process_message(correlation_id, signed_message)
        
        assert result.success is False
        assert result.session_state == HandshakeState.FAILED_TRUST
        
        # Check timeout audit event was emitted
        status = controller.get_session_status(correlation_id)
        assert status is not None
        assert status["current_state"] == "failed_trust"
        assert result.failure_reason == HandshakeTransitionReason.TIMEOUT
        
        # Check transitions include timeout
        transitions = status["transitions"]
        timeout_transition = next((t for t in transitions if t["reason_code"] == HandshakeTransitionReason.TIMEOUT), None)
        assert timeout_transition is not None
        assert timeout_transition["message_type"] == "timeout"
    
    def test_replay_reproduces_handshake_state_transitions(self, controller, test_key_pair, test_federate_identity):
        """Test that replay reproduces identical state transitions"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-replay-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Perform complete handshake
        controller.start_handshake(federate_id, correlation_id)
        
        # Process all messages
        messages = [
            create_identity_exchange_message(
                federate_id=federate_id,
                nonce="test-nonce-123",
                correlation_id=correlation_id,
                cell_public_key=test_federate_identity.public_key,
                certificate_chain=["test-cert"],
                federation_role="member",
                capabilities=["belief_aggregation"],
                trust_score=0.8,
                timestamp=controller.clock.now()
            ),
            create_capability_negotiate_message(
                federate_id=federate_id,
                nonce="test-nonce-456",
                correlation_id=correlation_id,
                supported_capabilities=["belief_aggregation", "policy_distribution"],
                required_capabilities=["belief_aggregation"],
                timestamp=controller.clock.now()
            ),
            create_trust_establish_message(
                federate_id=federate_id,
                nonce="test-nonce-789",
                correlation_id=correlation_id,
                trust_score=0.85,
                trust_reasons=["verified_identity", "capability_match"],
                expiration=controller.clock.now() + timedelta(hours=24),
                timestamp=controller.clock.now()
            )
        ]
        
        from src.federation.crypto import sign_message
        signed_messages = [
            sign_message(msg, test_key_pair.private_key)
            for msg in messages
        ]
        
        results = []
        for signed_msg in signed_messages:
            result = controller.process_message(correlation_id, signed_msg)
            results.append(result)
        
        # All should succeed
        assert all(r.success for r in results)
        assert results[-1].session_state == HandshakeState.CONFIRMED
        
        # Capture final state and transitions
        final_status = controller.get_session_status(correlation_id)
        final_transitions = final_status["transitions"]
        
        # Create new controller for replay
        replay_controller = HandshakeController(controller.context, controller.clock, controller.config)
        
        # Replay the same sequence with different correlation ID
        replay_correlation_id = "corr-replay-67890"
        replay_controller.start_handshake(federate_id, replay_correlation_id)
        
        # Create new messages for replay (same content, different correlation ID and nonces)
        replay_messages = [
            create_identity_exchange_message(
                federate_id=federate_id,
                nonce="test-nonce-replay-123",
                correlation_id=replay_correlation_id,
                cell_public_key=test_federate_identity.public_key,
                certificate_chain=["test-cert"],
                federation_role="member",
                capabilities=["belief_aggregation"],
                trust_score=0.8,
                timestamp=controller.clock.now()
            ),
            create_capability_negotiate_message(
                federate_id=federate_id,
                nonce="test-nonce-replay-456",
                correlation_id=replay_correlation_id,
                supported_capabilities=["belief_aggregation", "policy_distribution"],
                required_capabilities=["belief_aggregation"],
                timestamp=controller.clock.now()
            ),
            create_trust_establish_message(
                federate_id=federate_id,
                nonce="test-nonce-replay-789",
                correlation_id=replay_correlation_id,
                trust_score=0.85,
                trust_reasons=["verified_identity", "capability_match"],
                expiration=controller.clock.now() + timedelta(hours=24),
                timestamp=controller.clock.now()
            )
        ]
        
        replay_signed_messages = [
            sign_message(msg, test_key_pair.private_key)
            for msg in replay_messages
        ]
        
        replay_results = []
        for signed_msg in replay_signed_messages:
            result = replay_controller.process_message(replay_correlation_id, signed_msg)
            replay_results.append(result)
        
        # Verify replay produces identical results
        assert len(replay_results) == len(results)
        for i, (original, replay) in enumerate(zip(results, replay_results)):
            assert replay.success == original.success
            assert replay.session_state == original.session_state
        
        # Verify replay produces identical transitions
        replay_status = replay_controller.get_session_status(replay_correlation_id)
        replay_transitions = replay_status["transitions"]
        
        assert len(replay_transitions) == len(final_transitions)
        for i, (original, replay) in enumerate(zip(final_transitions, replay_transitions)):
            assert replay["from_state"] == original["from_state"]
            assert replay["to_state"] == original["to_state"]
            assert replay["message_type"] == original["message_type"]
            assert replay["reason_code"] == original["reason_code"]
    
    def test_correlation_id_reuse_prevention(self, controller, test_key_pair):
        """Test that correlation ID reuse is prevented"""
        federate_id = "cell-test-01"
        correlation_id = "corr-reuse-12345"
        
        # Start first handshake
        result1 = controller.start_handshake(federate_id, correlation_id)
        assert result1.success is True
        
        # Try to start second handshake with same correlation ID
        result2 = controller.start_handshake(federate_id, correlation_id)
        assert result2.success is False
        assert "not available" in result2.failure_reason.lower()
    
    def test_protocol_error_handling(self, controller, test_key_pair, test_federate_identity):
        """Test protocol error handling"""
        federate_id = test_federate_identity.federate_id
        correlation_id = "corr-protocol-12345"
        
        # Store identity
        controller.context.identity_store.store_identity(test_federate_identity)
        
        # Start handshake
        controller.start_handshake(federate_id, correlation_id)
        
        # Send wrong message type for current state
        # Should send identity_exchange but send capability_negotiate instead
        message = create_capability_negotiate_message(
            federate_id=federate_id,
            nonce="test-nonce-123",
            correlation_id=correlation_id,
            supported_capabilities=["belief_aggregation"],
            required_capabilities=["belief_aggregation"],
            timestamp=controller.clock.now()
        )
        from src.federation.crypto import sign_message
        signed_message = sign_message(message, test_key_pair.private_key)
        
        result = controller.process_message(correlation_id, signed_message)
        
        assert result.success is False
        assert result.session_state == HandshakeState.FAILED_TRUST
        assert result.failure_reason == "protocol_error"
        assert result.audit_event is not None
        assert result.audit_event["event_type"] == "handshake_failed"
    
    def test_cleanup_expired_resources(self, controller, fixed_clock):
        """Test cleanup of expired resources"""
        # Create sessions that will expire
        federate_id = "cell-test-01"
        
        # Expired session
        expired_correlation = "corr-expired"
        controller.start_handshake(federate_id, expired_correlation)
        
        # Advance clock to expire one session
        fixed_clock.advance(timedelta(minutes=11))
        
        # Active session (created after clock advance)
        active_correlation = "corr-active"
        controller.start_handshake(federate_id, active_correlation)
        
        # Clean up expired resources
        cleanup_stats = controller.cleanup_expired_resources()
        
        assert cleanup_stats["expired_sessions"] == 1
        assert cleanup_stats["expired_locks"] >= 0
        
        # Verify expired session is gone
        assert controller.get_session_status(expired_correlation) is None
        
        # Verify active session still exists
        assert controller.get_session_status(active_correlation) is not None
