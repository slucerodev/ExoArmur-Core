"""
ExoArmur ADMO V2 Federation Protocol Boundary Enforcement
Enforces cryptographic verification and replay protection for handshake messages
"""

import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from .crypto import (
    verify_message_integrity,
    emit_verification_audit_event,
    VerificationFailureReason,
    deserialize_public_key_from_identity
)
from .clock import Clock, SystemClock
from .messages import FederationSignedMessage
from .federate_identity_store import FederateIdentityStore

import sys
import os
from spec.contracts.models_v1 import HandshakeState

logger = logging.getLogger(__name__)


class ProtocolEnforcer:
    """Enforces federation protocol boundaries"""
    
    def __init__(self, identity_store: FederateIdentityStore, clock: Optional[Clock] = None):
        """
        Initialize protocol enforcer
        
        Args:
            identity_store: Federate identity store for key lookup
            clock: Clock interface for time operations (defaults to SystemClock)
        """
        self.identity_store = identity_store
        self.clock = clock or SystemClock()
        self.max_timestamp_skew_seconds = 300  # 5 minutes
    
    def verify_handshake_message(self, message: FederationSignedMessage) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Verify a handshake message according to protocol rules
        
        Args:
            message: Handshake message to verify
            
        Returns:
            Tuple of (is_valid, failure_reason, audit_event)
        """
        # 1. Basic schema validation (handled by Pydantic)
        
        # 2. Check if federate identity exists
        identity = self.identity_store.get_identity(message.federate_id)
        if identity is None:
            audit_event = emit_verification_audit_event(
                event_type="signature_verification_failure",
                message=message,
                success=False,
                failure_reason=VerificationFailureReason.UNKNOWN_KEY_ID
            )
            return False, VerificationFailureReason.UNKNOWN_KEY_ID, audit_event.to_dict()
        
        # 3. Deserialize public key
        try:
            public_key = deserialize_public_key_from_identity(identity.public_key)
        except Exception as e:
            logger.error(f"Failed to deserialize public key for {message.federate_id}: {e}")
            audit_event = emit_verification_audit_event(
                event_type="signature_verification_failure",
                message=message,
                success=False,
                failure_reason=VerificationFailureReason.KEY_MISMATCH
            )
            return False, VerificationFailureReason.KEY_MISMATCH, audit_event.to_dict()
        
        # 4. Verify message integrity
        is_valid, error = verify_message_integrity(
            message=message,
            expected_key_id=identity.key_id,
            public_key=public_key,
            nonce_store=self.identity_store,
            clock=self.clock
        )
        
        if not is_valid:
            audit_event = emit_verification_audit_event(
                event_type="signature_verification_failure",
                message=message,
                success=False,
                failure_reason=error
            )
            return False, error, audit_event.to_dict()
        
        # Success
        audit_event = emit_verification_audit_event(
            event_type="signature_verification_success",
            message=message,
            success=True
        )
        return True, None, audit_event.to_dict()
    
    def can_advance_handshake_state(
        self,
        federate_id: str,
        current_state: HandshakeState,
        message_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if handshake state can be advanced based on message type
        
        Args:
            federate_id: Federate identifier
            current_state: Current handshake state
            message_type: Incoming message type
            
        Returns:
            Tuple of (can_advance, reason)
        """
        # State transition rules
        allowed_transitions = {
            HandshakeState.UNINITIALIZED: ["identity_exchange"],
            HandshakeState.IDENTITY_EXCHANGE: ["capability_negotiate"],
            HandshakeState.CAPABILITY_NEGOTIATION: ["trust_establish"],
            HandshakeState.TRUST_ESTABLISHMENT: ["federation_confirm"],
            HandshakeState.CONFIRMED: [],  # No transitions allowed
            # Failed states
            HandshakeState.FAILED_IDENTITY_VERIFICATION: [],
            HandshakeState.FAILED_CAPABILITY_NEGOTIATION: [],
            HandshakeState.FAILED_TRUST_ESTABLISHMENT: [],
            HandshakeState.FAILED_TIMEOUT: [],
            HandshakeState.FAILED_PROTOCOL_VIOLATION: []
        }
        
        allowed_messages = allowed_transitions.get(current_state, [])
        
        if message_type not in allowed_messages:
            return False, f"Message type '{message_type}' not allowed in state '{current_state}'"
        
        return True, None
    
    def handle_verification_failure(
        self,
        federate_id: str,
        failure_reason: str,
        correlation_id: str
    ) -> HandshakeState:
        """
        Handle verification failure by transitioning to appropriate failed state
        
        Args:
            federate_id: Federate identifier
            failure_reason: Reason for verification failure
            correlation_id: Handshake correlation ID
            
        Returns:
            New handshake state
        """
        # Map failure reasons to failed states
        failure_state_map = {
            VerificationFailureReason.INVALID_SIGNATURE: HandshakeState.FAILED_IDENTITY_VERIFICATION,
            VerificationFailureReason.KEY_MISMATCH: HandshakeState.FAILED_IDENTITY_VERIFICATION,
            VerificationFailureReason.NONCE_REUSE: HandshakeState.FAILED_PROTOCOL_VIOLATION,
            VerificationFailureReason.TIMESTAMP_OUT_OF_BOUNDS: HandshakeState.FAILED_TIMEOUT,
            VerificationFailureReason.UNKNOWN_KEY_ID: HandshakeState.FAILED_IDENTITY_VERIFICATION,
            VerificationFailureReason.SCHEMA_VALIDATION_FAILED: HandshakeState.FAILED_PROTOCOL_VIOLATION
        }
        
        failed_state = failure_state_map.get(failure_reason, HandshakeState.FAILED_PROTOCOL_VIOLATION)
        
        # Update handshake session state
        session_id = correlation_id  # Use correlation_id as session_id
        success = self.identity_store.update_handshake_session(
            session_id=session_id,
            new_state=failed_state
        )
        
        if not success:
            logger.warning(f"Failed to update session {session_id} - session not found")
        
        logger.warning(f"Handshake failed for {federate_id}: {failure_reason} -> {failed_state}")
        
        return failed_state
    
    def process_handshake_message(self, message: FederationSignedMessage) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Process a handshake message with full protocol enforcement
        
        Args:
            message: Handshake message to process
            
        Returns:
            Tuple of (success, failure_reason, audit_event)
        """
        # 1. Verify message integrity
        is_valid, failure_reason, audit_event = self.verify_handshake_message(message)
        
        if not is_valid:
            # Handle verification failure
            self.handle_verification_failure(
                federate_id=message.federate_id,
                failure_reason=failure_reason,
                correlation_id=message.correlation_id
            )
            return False, failure_reason, audit_event
        
        # 2. Check if state transition is allowed
        session_id = message.correlation_id  # Use correlation_id as session_id
        current_session = self.identity_store.get_handshake_session(session_id)
        
        if current_session is None:
            # Create new session for identity exchange
            if message.msg_type != "identity_exchange":
                failure_reason = "Handshake session not found"
                audit_event = emit_verification_audit_event(
                    event_type="signature_verification_failure",
                    message=message,
                    success=False,
                    failure_reason=failure_reason
                )
                return False, failure_reason, audit_event.to_dict()
            
            # Create new session - need initiator and responder
            # For identity exchange, we only have the initiator
            initiator_id = message.federate_id
            responder_id = initiator_id  # Use same ID for now (self-handshake)
            
            session = self.identity_store.create_handshake_session(
                session_id=session_id,
                initiator_cell_id=initiator_id,
                responder_cell_id=responder_id
            )
            
            if session is None:
                failure_reason = "Failed to create handshake session"
                audit_event = emit_verification_audit_event(
                    event_type="session_creation_failure",
                    message=message,
                    success=False,
                    failure_reason=failure_reason
                )
                return False, failure_reason, audit_event.to_dict()
            
            # Advance state for newly created session
            new_state = self._get_next_state(session.state, message.msg_type)
            logger.info(f"Advancing new session {session_id} from {session.state} to {new_state}")
            success = self.identity_store.update_handshake_session(
                session_id=session_id,
                new_state=new_state
            )
            
            if not success:
                logger.warning(f"Failed to advance new session {session_id} to {new_state}")
                return False, "State transition failed", audit_event.to_dict()
            else:
                logger.info(f"Successfully advanced new session {session_id} to {new_state}")
        else:
            # Check state transition
            can_advance, reason = self.can_advance_handshake_state(
                federate_id=message.federate_id,
                current_state=current_session.state,
                message_type=message.msg_type
            )
            
            if not can_advance:
                self.handle_verification_failure(
                    federate_id=message.federate_id,
                    failure_reason=VerificationFailureReason.SCHEMA_VALIDATION_FAILED,
                    correlation_id=message.correlation_id
                )
                audit_event = emit_verification_audit_event(
                    event_type="signature_verification_failure",
                    message=message,
                    success=False,
                    failure_reason=reason
                )
                return False, reason, audit_event.to_dict()
            
            # Advance state
            new_state = self._get_next_state(current_session.state, message.msg_type)
            logger.info(f"Advancing session {session_id} from {current_session.state} to {new_state}")
            success = self.identity_store.update_handshake_session(
                session_id=session_id,
                new_state=new_state
            )
            
            if not success:
                logger.warning(f"Failed to advance session {session_id} to {new_state}")
                return False, "State transition failed", audit_event.to_dict()
            else:
                logger.info(f"Successfully advanced session {session_id} to {new_state}")
        
        return True, None, audit_event
    
    def _get_next_state(self, current_state: HandshakeState, message_type: str) -> HandshakeState:
        """Get next state based on current state and message type"""
        state_transitions = {
            (HandshakeState.UNINITIALIZED, "identity_exchange"): HandshakeState.IDENTITY_EXCHANGE,
            (HandshakeState.IDENTITY_EXCHANGE, "capability_negotiate"): HandshakeState.CAPABILITY_NEGOTIATION,
            (HandshakeState.CAPABILITY_NEGOTIATION, "trust_establish"): HandshakeState.TRUST_ESTABLISHMENT,
            (HandshakeState.TRUST_ESTABLISHMENT, "federation_confirm"): HandshakeState.CONFIRMED,
        }
        
        return state_transitions.get((current_state, message_type), HandshakeState.FAILED_PROTOCOL_VIOLATION)
    
    def set_max_timestamp_skew(self, seconds: int):
        """Set maximum allowed timestamp skew"""
        self.max_timestamp_skew_seconds = seconds
