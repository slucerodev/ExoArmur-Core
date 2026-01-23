"""
Tests for HandshakeStateMachine
Tests state machine logic, transition enforcement, and terminal failure behavior
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional

from spec.contracts.models_v1 import (
    HandshakeState,
    FederateIdentityV1,
    FederationRole,
    CellStatus
)
from src.federation.handshake_state_machine import (
    HandshakeStateMachine,
    HandshakeConfig,
    HandshakeTransitionReason
)
from src.federation.clock import FixedClock, SystemClock
from tests.federation_fixtures import (
    fixed_clock,
    test_key_pair,
    test_federate_identity
)


class TestHandshakeStateMachine:
    """Test handshake state machine logic and enforcement"""
    
    @pytest.fixture
    def state_machine(self, fixed_clock):
        """Test state machine with fixed clock"""
        config = HandshakeConfig(
            max_retry_attempts=3,
            base_retry_delay=timedelta(seconds=1),
            max_retry_delay=timedelta(seconds=10),
            handshake_timeout=timedelta(minutes=10),
            correlation_id_ttl=timedelta(hours=24)
        )
        return HandshakeStateMachine(fixed_clock, config)
    
    def test_valid_transitions(self, state_machine):
        """Test that valid transitions are allowed"""
        # UNINITIALIZED -> IDENTITY_EXCHANGE
        assert state_machine.can_transition(
            HandshakeState.UNINITIALIZED,
            HandshakeState.IDENTITY_EXCHANGE
        )
        
        # IDENTITY_EXCHANGE -> CAPABILITY_NEGOTIATION
        assert state_machine.can_transition(
            HandshakeState.IDENTITY_EXCHANGE,
            HandshakeState.CAPABILITY_NEGOTIATION
        )
        
        # CAPABILITY_NEGOTIATION -> TRUST_ESTABLISHMENT
        assert state_machine.can_transition(
            HandshakeState.CAPABILITY_NEGOTIATION,
            HandshakeState.TRUST_ESTABLISHMENT
        )
        
        # TRUST_ESTABLISHMENT -> CONFIRMED
        assert state_machine.can_transition(
            HandshakeState.TRUST_ESTABLISHMENT,
            HandshakeState.CONFIRMED
        )
    
    def test_invalid_transitions(self, state_machine):
        """Test that invalid transitions are rejected"""
        # Cannot skip states
        assert not state_machine.can_transition(
            HandshakeState.UNINITIALIZED,
            HandshakeState.CAPABILITY_NEGOTIATION
        )
        
        # Cannot go backwards
        assert not state_machine.can_transition(
            HandshakeState.CAPABILITY_NEGOTIATION,
            HandshakeState.IDENTITY_EXCHANGE
        )
        
        # Cannot transition from terminal states
        assert not state_machine.can_transition(
            HandshakeState.CONFIRMED,
            HandshakeState.IDENTITY_EXCHANGE
        )
        
        assert not state_machine.can_transition(
            HandshakeState.FAILED_IDENTITY,
            HandshakeState.CAPABILITY_NEGOTIATION
        )
    
    def test_terminal_states(self, state_machine):
        """Test terminal state detection"""
        terminal_states = [
            HandshakeState.CONFIRMED,
            HandshakeState.FAILED_IDENTITY,
            HandshakeState.FAILED_CAPABILITIES,
            HandshakeState.FAILED_TRUST
        ]
        
        for state in terminal_states:
            assert state_machine.is_terminal_state(state)
        
        non_terminal_states = [
            HandshakeState.UNINITIALIZED,
            HandshakeState.IDENTITY_EXCHANGE,
            HandshakeState.CAPABILITY_NEGOTIATION,
            HandshakeState.TRUST_ESTABLISHMENT
        ]
        
        for state in non_terminal_states:
            assert not state_machine.is_terminal_state(state)
    
    def test_create_session(self, state_machine, fixed_clock):
        """Test session creation"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        session = state_machine.create_session(
            federate_id=federate_id,
            correlation_id=correlation_id
        )
        
        assert session.correlation_id == correlation_id
        assert session.federate_id == federate_id
        assert session.state == HandshakeState.UNINITIALIZED
        assert session.created_at == fixed_clock.now()
        assert session.updated_at == fixed_clock.now()
    
    def test_correlation_id_uniqueness(self, state_machine):
        """Test correlation ID uniqueness enforcement"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create first session
        state_machine.create_session(federate_id, correlation_id)
        
        # Attempt to create second session with same correlation ID
        with pytest.raises(ValueError, match="Correlation ID corr-12345 is not available"):
            state_machine.create_session("cell-test-02", correlation_id)
    
    def test_correlation_id_locking(self, state_machine, fixed_clock):
        """Test correlation ID locking after session completion"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create and complete session through proper state transitions
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Follow proper state transitions to reach CONFIRMED
        state_machine.transition_state(
            correlation_id,
            HandshakeState.IDENTITY_EXCHANGE,
            "test_message",
            "test_reason",
            {}
        )
        
        state_machine.transition_state(
            correlation_id,
            HandshakeState.CAPABILITY_NEGOTIATION,
            "test_message",
            "test_reason",
            {}
        )
        
        state_machine.transition_state(
            correlation_id,
            HandshakeState.CONFIRMED,
            "test_message",
            "test_reason",
            {}
        )
        
        # Correlation ID should be locked
        assert not state_machine.is_correlation_id_available(correlation_id)
        
        # Advance clock beyond TTL
        fixed_clock.advance(timedelta(hours=25))
        
        # Clean up expired locks
        cleaned = state_machine.cleanup_expired_locks()
        assert cleaned == 1
        
        # Correlation ID should now be available
        assert state_machine.is_correlation_id_available(correlation_id)
    
    def test_state_transition(self, state_machine):
        """Test successful state transition"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Transition to IDENTITY_EXCHANGE
        success = state_machine.transition_state(
            correlation_id,
            HandshakeState.IDENTITY_EXCHANGE,
            "identity_exchange",
            "verification_success",
            {"test": "data"}
        )
        
        assert success
        updated_session = state_machine.get_session(correlation_id)
        assert updated_session.state == HandshakeState.IDENTITY_EXCHANGE
        
        # Check transition was recorded
        transitions = state_machine.get_transitions_for_correlation(correlation_id)
        assert len(transitions) == 1
        assert transitions[0].from_state == HandshakeState.UNINITIALIZED
        assert transitions[0].to_state == HandshakeState.IDENTITY_EXCHANGE
        assert transitions[0].message_type == "identity_exchange"
        assert transitions[0].reason_code == "verification_success"
    
    def test_invalid_state_transition(self, state_machine):
        """Test that invalid transitions are rejected"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Attempt invalid transition
        success = state_machine.transition_state(
            correlation_id,
            HandshakeState.TRUST_ESTABLISHMENT,  # Skip intermediate states
            "trust_establish",
            "verification_success",
            {}
        )
        
        assert not success
        updated_session = state_machine.get_session(correlation_id)
        assert updated_session.state == HandshakeState.UNINITIALIZED
    
    def test_terminal_state_transition_rejection(self, state_machine):
        """Test that transitions from terminal states are rejected"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session and transition to terminal state
        session = state_machine.create_session(federate_id, correlation_id)
        state_machine.transition_state(
            correlation_id,
            HandshakeState.CONFIRMED,
            "confirmation",
            "verification_success",
            {}
        )
        
        # Attempt transition from terminal state
        success = state_machine.transition_state(
            correlation_id,
            HandshakeState.IDENTITY_EXCHANGE,
            "invalid_transition",
            "test_reason",
            {}
        )
        
        assert not success
        updated_session = state_machine.get_session(correlation_id)
        assert updated_session.state == HandshakeState.CONFIRMED
    
    def test_failure_handshake(self, state_machine):
        """Test handshake failure with terminal state"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Fail handshake
        success = state_machine.fail_handshake(
            correlation_id,
            HandshakeState.FAILED_IDENTITY,
            "verification_failed"
        )
        
        assert success
        updated_session = state_machine.get_session(correlation_id)
        assert updated_session.state == HandshakeState.FAILED_IDENTITY
    
    def test_retry_count_increment(self, state_machine):
        """Test retry count increment and limits"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Note: retry_count is tracked in transitions, not in session model
        # First retry should succeed
        assert state_machine.increment_retry(correlation_id)
        
        # Add failure transition to track retry
        state_machine.fail_handshake(
            correlation_id, 
            HandshakeState.FAILED_IDENTITY, 
            "verification_failed",
            {}
        )
        
        # Second retry should succeed
        assert state_machine.increment_retry(correlation_id)
        
        # Add another failure transition
        state_machine.fail_handshake(correlation_id, HandshakeState.FAILED_IDENTITY, "verification_failed")
        
        # Third retry should succeed
        assert state_machine.increment_retry(correlation_id)
        
        # Add another failure transition
        state_machine.fail_handshake(correlation_id, HandshakeState.FAILED_IDENTITY, "verification_failed", {})
        
        # Fourth retry should exceed max retries
        assert not state_machine.increment_retry(correlation_id)
    
    def test_retry_delay_calculation(self, state_machine):
        """Test exponential backoff delay calculation"""
        # Base delay
        delay = state_machine.calculate_retry_delay(0)
        assert delay == timedelta(seconds=1)
        
        # Exponential growth
        delay = state_machine.calculate_retry_delay(1)
        assert delay == timedelta(seconds=2)
        
        delay = state_machine.calculate_retry_delay(2)
        assert delay == timedelta(seconds=4)
        
        # Capped at max delay
        delay = state_machine.calculate_retry_delay(10)
        assert delay == timedelta(seconds=10)  # Max delay
    
    def test_session_expiration(self, state_machine, fixed_clock):
        """Test session expiration handling"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Session should not be expired initially
        assert not state_machine.is_session_expired(correlation_id)
        
        # Advance clock beyond timeout
        fixed_clock.advance(timedelta(minutes=11))
        
        # Session should now be expired
        assert state_machine.is_session_expired(correlation_id)
    
    def test_cleanup_expired_sessions(self, state_machine, fixed_clock):
        """Test cleanup of expired sessions"""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            federate_id = f"cell-test-{i:02d}"
            correlation_id = f"corr-{i:05d}"
            session = state_machine.create_session(federate_id, correlation_id)
            sessions.append(session)
        
        # Advance clock and expire one session
        fixed_clock.advance(timedelta(minutes=11))
        
        # Clean up expired sessions
        cleaned = state_machine.cleanup_expired_sessions()
        assert cleaned == 1
        
        # Check expired session was removed
        assert state_machine.get_session(sessions[0].correlation_id) is None
        
        # Check other sessions still exist
        for session in sessions[1:]:
            assert state_machine.get_session(session.correlation_id) is not None
    
    def test_get_active_sessions(self, state_machine):
        """Test retrieval of active sessions"""
        federate_id = "cell-test-01"
        
        # Create active session
        active_correlation = "corr-active"
        state_machine.create_session(federate_id, active_correlation)
        
        # Create failed session
        failed_correlation = "corr-failed"
        state_machine.create_session(federate_id, failed_correlation)
        state_machine.fail_handshake(
            failed_correlation,
            HandshakeState.FAILED_IDENTITY,
            "test_failure"
        )
        
        # Get active sessions
        active_sessions = state_machine.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].correlation_id == active_correlation
    
    def test_get_session_statistics(self, state_machine):
        """Test session statistics"""
        # Create sessions in different states
        federate_id = "cell-test-01"
        
        # Active session
        state_machine.create_session(federate_id, "corr-active")
        
        # Failed session
        state_machine.create_session(federate_id, "corr-failed")
        state_machine.fail_handshake(
            "corr-failed",
            HandshakeState.FAILED_IDENTITY,
            "test_failure"
        )
        
        # Get statistics
        stats = state_machine.get_session_statistics()
        
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["state_distribution"]["uninitialized"] == 1
        assert stats["state_distribution"]["failed_identity"] == 1
        assert stats["total_transitions"] == 1  # One failure transition
        assert stats["locked_correlation_ids"] == 2  # Both correlation IDs locked
    
    def test_federate_to_correlation_mapping(self, state_machine):
        """Test federate to correlation ID mapping"""
        federate_id = "cell-test-01"
        correlation_id = "corr-12345"
        
        # Create session
        session = state_machine.create_session(federate_id, correlation_id)
        
        # Check mapping
        active_correlation = state_machine.get_active_correlation_id(federate_id)
        assert active_correlation == correlation_id
        
        # Fail session
        state_machine.fail_handshake(
            correlation_id,
            HandshakeState.FAILED_IDENTITY,
            "test_failure",
            {}
        )
        
        # Mapping should be removed for failed session
        active_correlation = state_machine.get_active_correlation_id(federate_id)
        assert active_correlation is None
