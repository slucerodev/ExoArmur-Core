"""
ExoArmur ADMO V2 Federation Handshake State Machine
Deterministic state machine for federation identity handshake protocol
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from spec.contracts.models_v1 import (
    HandshakeState,
    HandshakeSessionV1,
    FederationRole,
    CellStatus
)
from .clock import Clock
from .crypto import VerificationFailureReason

logger = logging.getLogger(__name__)


class HandshakeTransitionReason(str):
    """Reasons for handshake state transitions"""
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"
    PROTOCOL_ERROR = "protocol_error"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    FEDERATION_DISABLED = "federation_disabled"
    CORRELATION_ID_REUSE = "correlation_id_reuse"
    INVALID_STATE_TRANSITION = "invalid_state_transition"


@dataclass
class HandshakeTransition:
    """Record of a handshake state transition"""
    from_state: HandshakeState
    to_state: HandshakeState
    timestamp: datetime
    federate_id: str
    correlation_id: str
    message_type: str
    reason_code: str
    audit_event: Dict[str, Any]
    retry_count: int = 0


@dataclass
class HandshakeConfig:
    """Configuration for handshake behavior"""
    max_retry_attempts: int = 3
    base_retry_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    max_retry_delay: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    handshake_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    correlation_id_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))


class HandshakeStateMachine:
    """
    Deterministic state machine for federation identity handshake protocol
    
    Enforces strict transition rules and terminal failure behavior with complete audit trail.
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        HandshakeState.UNINITIALIZED: [
            HandshakeState.IDENTITY_EXCHANGE,
            HandshakeState.FAILED_IDENTITY,  # Can fail immediately during identity verification
            HandshakeState.FAILED_TRUST  # Can fail due to timeout
        ],
        HandshakeState.IDENTITY_EXCHANGE: [
            HandshakeState.CAPABILITY_NEGOTIATION,
            HandshakeState.FAILED_IDENTITY
        ],
        HandshakeState.CAPABILITY_NEGOTIATION: [
            HandshakeState.TRUST_ESTABLISHMENT,
            HandshakeState.CONFIRMED,  # Direct transition to confirmed on successful trust establishment
            HandshakeState.FAILED_CAPABILITIES
        ],
        HandshakeState.TRUST_ESTABLISHMENT: [
            HandshakeState.CONFIRMED,
            HandshakeState.FAILED_TRUST
        ],
        # Terminal states - no transitions allowed
        HandshakeState.CONFIRMED: [],
        HandshakeState.FAILED_IDENTITY: [],
        HandshakeState.FAILED_CAPABILITIES: [],
        HandshakeState.FAILED_TRUST: [],
    }
    
    def __init__(self, clock: Clock, config: Optional[HandshakeConfig] = None):
        """
        Initialize handshake state machine
        
        Args:
            clock: Clock interface for deterministic time
            config: Optional configuration override
        """
        self.clock = clock
        self.config = config or HandshakeConfig()
        
        # State tracking
        self._sessions: Dict[str, HandshakeSessionV1] = {}  # correlation_id -> session
        self._correlation_ids: Dict[str, str] = {}  # federate_id -> correlation_id
        self._transitions: List[HandshakeTransition] = []
        self._locked_correlation_ids: Dict[str, datetime] = {}  # correlation_id -> lock expiry
        
        logger.info("HandshakeStateMachine initialized")
    
    def can_transition(self, from_state: HandshakeState, to_state: HandshakeState) -> bool:
        """
        Check if a state transition is valid
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_targets = self.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets
    
    def is_terminal_state(self, state: HandshakeState) -> bool:
        """
        Check if a state is terminal (no further transitions allowed)
        
        Args:
            state: State to check
            
        Returns:
            True if terminal, False otherwise
        """
        return len(self.VALID_TRANSITIONS.get(state, [])) == 0
    
    def get_session(self, correlation_id: str) -> Optional[HandshakeSessionV1]:
        """
        Get handshake session by correlation ID
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            Handshake session or None if not found
        """
        return self._sessions.get(correlation_id)
    
    def get_active_correlation_id(self, federate_id: str) -> Optional[str]:
        """
        Get active correlation ID for a federate
        
        Args:
            federate_id: Federate identifier
            
        Returns:
            Active correlation ID or None if no active session
        """
        return self._correlation_ids.get(federate_id)
    
    def is_correlation_id_available(self, correlation_id: str) -> bool:
        """
        Check if correlation ID is available for use
        
        Args:
            correlation_id: Correlation identifier to check
            
        Returns:
            True if available, False if in use or locked
        """
        # Check if correlation ID is in use
        if correlation_id in self._sessions:
            return False
        
        # Check if correlation ID is locked (recently used)
        lock_expiry = self._locked_correlation_ids.get(correlation_id)
        if lock_expiry and self.clock.now() < lock_expiry:
            return False
        
        return True
    
    def lock_correlation_id(self, correlation_id: str):
        """
        Lock a correlation ID to prevent reuse
        
        Args:
            correlation_id: Correlation ID to lock
        """
        lock_expiry = self.clock.now() + self.config.correlation_id_ttl
        self._locked_correlation_ids[correlation_id] = lock_expiry
    
    def cleanup_expired_locks(self) -> int:
        """
        Clean up expired correlation ID locks
        
        Returns:
            Number of locks cleaned up
        """
        now = self.clock.now()
        expired = [
            cid for cid, expiry in self._locked_correlation_ids.items()
            if now >= expiry
        ]
        
        for cid in expired:
            del self._locked_correlation_ids[cid]
        
        return len(expired)
    
    def create_session(
        self,
        federate_id: str,
        correlation_id: str,
        initial_state: HandshakeState = HandshakeState.UNINITIALIZED
    ) -> HandshakeSessionV1:
        """
        Create a new handshake session
        
        Args:
            federate_id: Federate identifier
            correlation_id: Unique correlation identifier
            initial_state: Initial state (default UNINITIALIZED)
            
        Returns:
            Created handshake session
            
        Raises:
            ValueError: If correlation ID is not available
        """
        if not self.is_correlation_id_available(correlation_id):
            raise ValueError(f"Correlation ID {correlation_id} is not available")
        
        now = self.clock.now()
        session = HandshakeSessionV1(
            correlation_id=correlation_id,
            federate_id=federate_id,
            state=initial_state,
            created_at=now,
            updated_at=now,
            expires_at=now + self.config.handshake_timeout
        )
        
        # Store session and mappings
        self._sessions[correlation_id] = session
        self._correlation_ids[federate_id] = correlation_id
        self.lock_correlation_id(correlation_id)
        
        logger.info(f"Created handshake session: {correlation_id} for {federate_id}")
        return session
    
    def transition_state(
        self,
        correlation_id: str,
        to_state: HandshakeState,
        message_type: str,
        reason_code: str,
        audit_event: Dict[str, Any]
    ) -> bool:
        """
        Transition a handshake session to a new state
        
        Args:
            correlation_id: Correlation identifier
            to_state: Target state
            message_type: Type of message causing transition
            reason_code: Reason for transition
            audit_event: Audit event data
            
        Returns:
            True if transition succeeded, False otherwise
        """
        session = self.get_session(correlation_id)
        if not session:
            logger.error(f"Session not found for correlation_id: {correlation_id}")
            return False
        
        from_state = session.state
        
        # Check if transition is valid
        if not self.can_transition(from_state, to_state):
            logger.error(f"Invalid transition: {from_state} -> {to_state}")
            return False
        
        # Check if current state is terminal
        if self.is_terminal_state(from_state):
            logger.error(f"Cannot transition from terminal state: {from_state}")
            return False
        
        # Perform transition
        now = self.clock.now()
        session.state = to_state
        session.updated_at = now
        
        # Record transition
        transition = HandshakeTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=now,
            federate_id=session.federate_id,
            correlation_id=correlation_id,
            message_type=message_type,
            reason_code=reason_code,
            audit_event=audit_event,
            retry_count=0
        )
        self._transitions.append(transition)
        
        logger.info(f"Transitioned {correlation_id}: {from_state} -> {to_state} ({reason_code})")
        return True
    
    def fail_handshake(
        self,
        correlation_id: str,
        failure_state: HandshakeState,
        reason_code: str,
        audit_event: Dict[str, Any]
    ) -> bool:
        """
        Fail a handshake session with terminal failure state
        
        Args:
            correlation_id: Correlation identifier
            failure_state: Terminal failure state
            reason_code: Reason for failure
            audit_event: Audit event data
            
        Returns:
            True if failure succeeded, False otherwise
        """
        return self.transition_state(
            correlation_id=correlation_id,
            to_state=failure_state,
            message_type=audit_event.get("message_type", "failure"),
            reason_code=reason_code,
            audit_event=audit_event
        )
    
    def increment_retry(self, correlation_id: str) -> Tuple[bool, int]:
        """
        Increment retry count for a session
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            Tuple of (success, new_retry_count)
        """
        session = self.get_session(correlation_id)
        if not session:
            return False, 0
        
        # Track retry count in session metadata
        if not hasattr(session, '_retry_count'):
            session._retry_count = 0
        
        current_retry_count = session._retry_count
        
        if current_retry_count >= self.config.max_retry_attempts:
            logger.warning(f"Max retries exceeded for {correlation_id}")
            return False, current_retry_count
        
        session._retry_count = current_retry_count + 1
        return True, session._retry_count
    
    def calculate_retry_delay(self, retry_count: int) -> timedelta:
        """
        Calculate exponential backoff delay
        
        Args:
            retry_count: Current retry attempt number (0-based)
            
        Returns:
            Delay duration
        """
        delay = self.config.base_retry_delay * (2 ** (retry_count - 1)) if retry_count > 0 else self.config.base_retry_delay
        return min(delay, self.config.max_retry_delay)
    
    def is_session_expired(self, correlation_id: str) -> bool:
        """
        Check if a session has expired
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            True if expired, False otherwise
        """
        session = self.get_session(correlation_id)
        if not session:
            return True
        
        return self.clock.now() >= session.expires_at
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        now = self.clock.now()
        expired = [
            cid for cid, session in self._sessions.items()
            if now >= session.expires_at
        ]
        
        for cid in expired:
            session = self._sessions[cid]
            del self._sessions[cid]
            # Remove federate mapping if this was the active session
            if self._correlation_ids.get(session.federate_id) == cid:
                del self._correlation_ids[session.federate_id]
        
        return len(expired)
    
    def get_transitions_for_correlation(self, correlation_id: str) -> List[HandshakeTransition]:
        """
        Get all transitions for a specific correlation ID
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            List of transitions in chronological order
        """
        return [
            t for t in self._transitions
            if t.correlation_id == correlation_id
        ]
    
    def get_active_sessions(self) -> List[HandshakeSessionV1]:
        """
        Get all active (non-terminal, non-expired) sessions
        
        Returns:
            List of active sessions
        """
        now = self.clock.now()
        return [
            session for session in self._sessions.values()
            if not self.is_terminal_state(session.state)
            and now < session.expires_at
        ]
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about handshake sessions
        
        Returns:
            Statistics dictionary
        """
        total_sessions = len(self._sessions)
        active_sessions = len(self.get_active_sessions())
        
        # Count by state
        state_counts = {}
        for session in self._sessions.values():
            state = session.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "state_distribution": state_counts,
            "total_transitions": len(self._transitions),
            "locked_correlation_ids": len(self._locked_correlation_ids)
        }
