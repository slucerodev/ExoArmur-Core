"""
ExoArmur ADMO V2 Federation Handshake Controller
Orchestrates handshake state machine with verification and audit events
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from spec.contracts.models_v1 import (
    HandshakeState,
    FederationRole,
    CellStatus
)
from .handshake_state_machine import (
    HandshakeStateMachine,
    HandshakeConfig,
    HandshakeTransitionReason
)
from .handshake_context import HandshakeContext
from .messages import (
    FederationSignedMessage,
    MessageType,
    IdentityExchangeMessage,
    CapabilityNegotiateMessage,
    TrustEstablishMessage
)
from .crypto import VerificationFailureReason
from .clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class HandshakeResult:
    """Result of handshake processing"""
    success: bool
    session_state: HandshakeState
    failure_reason: Optional[str] = None
    audit_event: Optional[Dict[str, Any]] = None
    retry_after: Optional[timedelta] = None


class HandshakeController:
    """
    Controller for federation handshake protocol
    
    Orchestrates the handshake state machine with verification, audit events,
    retry logic, and timeout handling.
    """
    
    def __init__(
        self,
        handshake_context: HandshakeContext,
        clock: Clock,
        config: Optional[HandshakeConfig] = None
    ):
        """
        Initialize handshake controller
        
        Args:
            handshake_context: Context for verification operations
            clock: Clock interface for deterministic time
            config: Optional configuration override
        """
        self.context = handshake_context
        self.clock = clock
        self.config = config or HandshakeConfig()
        
        # Initialize state machine
        self.state_machine = HandshakeStateMachine(self.clock, self.config)
        
        logger.info("HandshakeController initialized")
    
    def start_handshake(
        self,
        federate_id: str,
        correlation_id: str,
        initial_message: Optional[FederationSignedMessage] = None
    ) -> HandshakeResult:
        """
        Start a new handshake session
        
        Args:
            federate_id: Federate identifier
            correlation_id: Unique correlation identifier
            initial_message: Optional initial message
            
        Returns:
            Handshake result
        """
        try:
            # Create session
            session = self.state_machine.create_session(
                federate_id=federate_id,
                correlation_id=correlation_id,
                initial_state=HandshakeState.UNINITIALIZED
            )
            
            # Emit audit event for session creation
            audit_event = self._emit_audit_event(
                correlation_id=correlation_id,
                federate_id=federate_id,
                event_type="handshake_started",
                message_type="session_creation",
                reason_code=HandshakeTransitionReason.VERIFICATION_SUCCESS,
                details={"initial_state": HandshakeState.UNINITIALIZED.value}
            )
            
            # Process initial message if provided
            if initial_message:
                return self.process_message(correlation_id, initial_message)
            
            return HandshakeResult(
                success=True,
                session_state=session.state,
                audit_event=audit_event
            )
            
        except Exception as e:
            logger.error(f"Failed to start handshake for {federate_id}: {e}")
            return HandshakeResult(
                success=False,
                session_state=HandshakeState.UNINITIALIZED,
                failure_reason=str(e)
            )
    
    def process_message(
        self,
        correlation_id: str,
        message: FederationSignedMessage
    ) -> HandshakeResult:
        """
        Process a handshake message
        
        Args:
            correlation_id: Correlation identifier
            message: Signed federation message
            
        Returns:
            Handshake result
        """
        session = self.state_machine.get_session(correlation_id)
        if not session:
            return HandshakeResult(
                success=False,
                session_state=HandshakeState.UNINITIALIZED,
                failure_reason="Session not found"
            )
        
        # Check if session is expired
        if self.state_machine.is_session_expired(correlation_id):
            return self._handle_timeout(correlation_id)
        
        # Verify message at protocol boundary
        verification_success, failure_reason, audit_event = self.context.verify_signed_message(message)
        
        if not verification_success:
            return self._handle_verification_failure(
                correlation_id, message, failure_reason, audit_event
            )
        
        # Process message based on type and current state
        return self._process_verified_message(correlation_id, message)
    
    def _process_verified_message(
        self,
        correlation_id: str,
        message: FederationSignedMessage
    ) -> HandshakeResult:
        """
        Process a verified message
        
        Args:
            correlation_id: Correlation identifier
            message: Verified federation message
            
        Returns:
            Handshake result
        """
        session = self.state_machine.get_session(correlation_id)
        current_state = session.state
        message_type = message.msg_type
        
        # Check if session is already in a terminal state
        if self.state_machine.is_terminal_state(current_state):
            return HandshakeResult(
                success=False,
                session_state=current_state,
                failure_reason=f"Session already in terminal state: {current_state.value}",
                audit_event=self._emit_audit_event(
                    correlation_id=correlation_id,
                    federate_id=session.federate_id,
                    event_type="handshake_failed",
                    message_type=message_type,
                    reason_code=HandshakeTransitionReason.PROTOCOL_ERROR,
                    details={"error": "Session in terminal state"}
                )
            )
        
        # Determine expected message type for current state
        expected_type = self._get_expected_message_type(current_state)
        if message_type != expected_type:
            return self._handle_protocol_error(
                correlation_id,
                message,
                f"Expected {expected_type}, got {message_type}"
            )
        
        # Transition to next state based on message type and current state
        next_state = self._get_next_state_for_message(message_type, current_state)
        
        # Emit transition audit event
        audit_event = self._emit_audit_event(
            correlation_id=correlation_id,
            federate_id=session.federate_id,
            event_type="handshake_transition",
            message_type=message_type,
            reason_code=HandshakeTransitionReason.VERIFICATION_SUCCESS,
            details={
                "from_state": current_state.value,
                "to_state": next_state.value,
                "message_validated": True
            }
        )
        
        # Perform state transition
        transition_success = self.state_machine.transition_state(
            correlation_id=correlation_id,
            to_state=next_state,
            message_type=message_type,
            reason_code=HandshakeTransitionReason.VERIFICATION_SUCCESS,
            audit_event=audit_event
        )
        
        if not transition_success:
            return HandshakeResult(
                success=False,
                session_state=current_state,
                failure_reason="State transition failed"
            )
        
        # Check if handshake is confirmed
        if next_state == HandshakeState.CONFIRMED:
            return self._handle_handshake_confirmed(correlation_id)
        
        return HandshakeResult(
            success=True,
            session_state=next_state,
            audit_event=audit_event
        )
    
    def _handle_verification_failure(
        self,
        correlation_id: str,
        message: FederationSignedMessage,
        failure_reason: str,
        audit_event: Dict[str, Any]
    ) -> HandshakeResult:
        """
        Handle verification failure
        
        Args:
            correlation_id: Correlation identifier
            message: Failed message
            failure_reason: Verification failure reason
            audit_event: Verification audit event
            
        Returns:
            Handshake result with retry logic
        """
        session = self.state_machine.get_session(correlation_id)
        current_state = session.state
        
        # Determine failure state based on current state
        failure_state = self._get_failure_state_for_verification(current_state, failure_reason)
        
        # Check if we should retry
        if self._should_retry_verification(failure_reason):
            retry_success, retry_count = self.state_machine.increment_retry(correlation_id)
            if not retry_success:
                # Max retries exceeded
                return self._fail_handshake(
                    correlation_id,
                    failure_state,
                    HandshakeTransitionReason.RETRY_EXHAUSTED
                )
            
            # Calculate retry delay
            retry_delay = self.state_machine.calculate_retry_delay(retry_count)
            
            # Record retry audit event
            retry_audit_event = self._emit_audit_event(
                    correlation_id=correlation_id,
                    federate_id=session.federate_id,
                    event_type="handshake_retry",
                    message_type=message.msg_type,
                    reason_code=HandshakeTransitionReason.VERIFICATION_FAILED,
                    details={
                        "failure_reason": failure_reason,
                        "retry_count": retry_count,
                        "retry_after_seconds": int(retry_delay.total_seconds())
                    }
                )
            
            return HandshakeResult(
                success=False,
                session_state=current_state,
                failure_reason=failure_reason,
                audit_event=retry_audit_event,
                retry_after=retry_delay
            )
        
        # Immediate failure (non-retryable errors)
        return self._fail_handshake(
            correlation_id,
            failure_state,
            failure_reason
        )
    
    def _handle_protocol_error(
        self,
        correlation_id: str,
        message: FederationSignedMessage,
        error_detail: str
    ) -> HandshakeResult:
        """
        Handle protocol error
        
        Args:
            correlation_id: Correlation identifier
            message: Error message
            error_detail: Error description
            
        Returns:
            Handshake result
        """
        session = self.state_machine.get_session(correlation_id)
        
        # Emit protocol error audit event
        audit_event = self._emit_audit_event(
            correlation_id=correlation_id,
            federate_id=session.federate_id,
            event_type="handshake_protocol_error",
            message_type=message.msg_type,
            reason_code=HandshakeTransitionReason.PROTOCOL_ERROR,
            details={"error_detail": error_detail}
        )
        
        # Fail handshake immediately
        return self._fail_handshake(
            correlation_id,
            HandshakeState.FAILED_TRUST,
            HandshakeTransitionReason.PROTOCOL_ERROR
        )
    
    def _handle_timeout(self, correlation_id: str):
        """
        Handle handshake timeout
        
        Args:
            correlation_id: Correlation identifier
        """
        session = self.state_machine.get_session(correlation_id)
        
        # Emit timeout audit event
        audit_event = self._emit_audit_event(
            correlation_id=correlation_id,
            federate_id=session.federate_id,
            event_type="handshake_timeout",
            message_type="timeout",
            reason_code=HandshakeTransitionReason.TIMEOUT,
            details={
                "timeout_duration": int(self.config.handshake_timeout.total_seconds()),
                "session_age": int((self.clock.now() - session.created_at).total_seconds())
            }
        )
        
        # Fail the handshake
        self.state_machine.fail_handshake(
            correlation_id=correlation_id,
            failure_state=HandshakeState.FAILED_TRUST,
            reason_code=HandshakeTransitionReason.TIMEOUT,
            audit_event=audit_event
        )
        
        return HandshakeResult(
            success=False,
            session_state=HandshakeState.FAILED_TRUST,
            failure_reason=HandshakeTransitionReason.TIMEOUT,
            audit_event=audit_event
        )
    
    def _handle_handshake_confirmed(self, correlation_id: str) -> HandshakeResult:
        """
        Handle successful handshake confirmation
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            Handshake result
        """
        session = self.state_machine.get_session(correlation_id)
        
        # Emit confirmation audit event
        audit_event = self._emit_audit_event(
            correlation_id=correlation_id,
            federate_id=session.federate_id,
            event_type="handshake_confirmed",
            message_type="confirmation",
            reason_code=HandshakeTransitionReason.VERIFICATION_SUCCESS,
            details={
                "handshake_duration": int((self.clock.now() - session.created_at).total_seconds()),
                "retry_count": 0  # Would be calculated from transitions
            }
        )
        
        return HandshakeResult(
            success=True,
            session_state=HandshakeState.CONFIRMED,
            audit_event=audit_event
        )
    
    def _fail_handshake(
        self,
        correlation_id: str,
        failure_state: HandshakeState,
        reason_code: str,
        message_type: str = "failure"
    ) -> HandshakeResult:
        """
        Fail handshake with terminal state
        
        Args:
            correlation_id: Correlation identifier
            failure_state: Terminal failure state
            reason_code: Failure reason
            
        Returns:
            Handshake result
        """
        session = self.state_machine.get_session(correlation_id)
        
        # Emit failure audit event
        audit_event = self._emit_audit_event(
            correlation_id=correlation_id,
            federate_id=session.federate_id,
            event_type="handshake_failed",
            message_type=message_type,
            reason_code=reason_code,
            details={
                "failure_state": failure_state.value,
                "final_retry_count": 0  # Would be calculated from transitions
            }
        )
        
        # Fail the handshake
        self.state_machine.fail_handshake(
            correlation_id=correlation_id,
            failure_state=failure_state,
            reason_code=reason_code,
            audit_event=audit_event
        )
        
        return HandshakeResult(
            success=False,
            session_state=failure_state,
            failure_reason=reason_code,
            audit_event=audit_event
        )
    
    def _get_expected_message_type(self, current_state: HandshakeState) -> str:
        """
        Get expected message type for current state
        
        Args:
            current_state: Current handshake state
            
        Returns:
            Expected message type
        """
        mapping = {
            HandshakeState.UNINITIALIZED: MessageType.IDENTITY_EXCHANGE,
            HandshakeState.IDENTITY_EXCHANGE: MessageType.CAPABILITY_NEGOTIATE,
            HandshakeState.CAPABILITY_NEGOTIATION: MessageType.TRUST_ESTABLISH,
            HandshakeState.TRUST_ESTABLISHMENT: None,  # No message expected, should confirm
        }
        return mapping.get(current_state)
    
    def _get_next_state_for_message(self, message_type: str, current_state: HandshakeState) -> HandshakeState:
        """
        Get next state for message type
        
        Args:
            message_type: Message type
            current_state: Current handshake state
            
        Returns:
            Next handshake state
        """
        # For TRUST_ESTABLISH messages from CAPABILITY_NEGOTIATION, go directly to CONFIRMED
        # This represents the successful completion of the handshake
        if message_type == MessageType.TRUST_ESTABLISH and current_state == HandshakeState.CAPABILITY_NEGOTIATION:
            return HandshakeState.CONFIRMED
        else:
            mapping = {
                MessageType.IDENTITY_EXCHANGE: HandshakeState.IDENTITY_EXCHANGE,
                MessageType.CAPABILITY_NEGOTIATE: HandshakeState.CAPABILITY_NEGOTIATION,
            }
            return mapping.get(message_type, HandshakeState.FAILED_TRUST)
    
    def _get_failure_state_for_verification(
        self,
        current_state: HandshakeState,
        failure_reason: str
    ) -> HandshakeState:
        """
        Get failure state for verification failure
        
        Args:
            current_state: Current handshake state
            failure_reason: Verification failure reason
            
        Returns:
            Terminal failure state
        """
        # Map verification failures to appropriate terminal states
        if current_state == HandshakeState.UNINITIALIZED:
            return HandshakeState.FAILED_IDENTITY
        elif current_state == HandshakeState.IDENTITY_EXCHANGE:
            return HandshakeState.FAILED_IDENTITY
        elif current_state == HandshakeState.CAPABILITY_NEGOTIATION:
            return HandshakeState.FAILED_CAPABILITIES
        elif current_state == HandshakeState.TRUST_ESTABLISHMENT:
            return HandshakeState.FAILED_TRUST
        else:
            return HandshakeState.FAILED_TRUST
    
    def _should_retry_verification(self, failure_reason: str) -> bool:
        """
        Determine if verification failure should trigger retry
        
        Args:
            failure_reason: Verification failure reason
            
        Returns:
            True if should retry, False otherwise
        """
        # Retry on transient failures, not on permanent ones
        retryable_reasons = [
            VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS,
            VerificationFailureReason.NONCE_REUSE,  # Might be timing issue
        ]
        
        return failure_reason in retryable_reasons
    
    def _emit_audit_event(
        self,
        correlation_id: str,
        federate_id: str,
        event_type: str,
        message_type: str,
        reason_code: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Emit audit event for handshake operation
        
        Args:
            correlation_id: Correlation identifier
            federate_id: Federate identifier
            event_type: Type of event
            message_type: Message type involved
            reason_code: Reason for event
            details: Additional event details
            
        Returns:
            Audit event dictionary
        """
        # Create audit event
        audit_event = {
            "event_type": event_type,
            "federate_id": federate_id,
            "correlation_id": correlation_id,
            "message_type": message_type,
            "reason_code": reason_code,
            "timestamp": self.clock.now().isoformat(),
            "details": details or {}
        }
        
        # Store in context's audit system (would integrate with actual audit logger)
        logger.info(f"Handshake audit event: {event_type} for {federate_id} ({correlation_id})")
        
        return audit_event
    
    def get_session_status(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a handshake session
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            Session status or None if not found
        """
        session = self.state_machine.get_session(correlation_id)
        if not session:
            return None
        
        transitions = self.state_machine.get_transitions_for_correlation(correlation_id)
        
        return {
            "correlation_id": session.correlation_id,
            "federate_id": session.federate_id,
            "current_state": session.state.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "retry_count": 0,  # Would be calculated from transitions
            "last_message_type": "",  # Would be tracked from transitions
            "failure_reason": "",  # Would be tracked from transitions
            "is_expired": self.state_machine.is_session_expired(correlation_id),
            "is_terminal": self.state_machine.is_terminal_state(session.state),
            "transition_count": len(transitions),
            "transitions": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "message_type": t.message_type,
                    "reason_code": t.reason_code
                }
                for t in transitions
            ]
        }
    
    def cleanup_expired_resources(self) -> Dict[str, int]:
        """
        Clean up expired resources
        
        Returns:
            Cleanup statistics
        """
        expired_sessions = self.state_machine.cleanup_expired_sessions()
        expired_locks = self.state_machine.cleanup_expired_locks()
        
        return {
            "expired_sessions": expired_sessions,
            "expired_locks": expired_locks
        }
