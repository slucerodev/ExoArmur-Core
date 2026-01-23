"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Identity Handshake State Machine
Deterministic state machine for federation identity handshake
"""

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .models.federation_identity_v2 import (
    HandshakeState,
    CellIdentity,
    IdentityExchangeMessage,
    CapabilityNegotiateMessage,
    TrustEstablishMessage,
    FederationConfirmMessage,
    HandshakeSession,
    CapabilityType,
)
from .identity_transcript_builder import TranscriptBuilder

logger = logging.getLogger(__name__)


@dataclass
class HandshakeConfig:
    """Configuration for handshake behavior"""
    buffer_window_ms: int = 5000  # 5 seconds
    step_timeout_ms: int = 10000  # 10 seconds
    minimum_trust_score: float = 0.7
    max_retry_attempts: int = 3
    retry_backoff_base_ms: int = 1000  # 1 second base


@dataclass
class HandshakeEvent:
    """Event emitted during handshake"""
    event_name: str
    session_id: str
    step_index: int
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = field(init=False)
    
    def __post_init__(self):
        """Generate idempotency key after initialization"""
        self.idempotency_key = hashlib.sha256(
            f"{self.session_id}:{self.event_name}:{self.step_index}".encode('utf-8')
        ).hexdigest()


class HandshakeResult:
    """Result of handshake operation"""
    
    def __init__(self, success: bool, state: HandshakeState, message: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.state = state
        self.message = message
        self.data = data or {}
    
    def __bool__(self):
        return self.success


class IdentityHandshakeStateMachine:
    """Deterministic state machine for federation identity handshake"""
    
    def __init__(self, config: Optional[HandshakeConfig] = None):
        """Initialize state machine with configuration"""
        self.config = config or HandshakeConfig()
        self.session: Optional[HandshakeSession] = None
        self.transcript_builder: Optional[TranscriptBuilder] = None
        self.event_handlers: List[Callable[[HandshakeEvent], None]] = []
        self._message_buffer: Dict[str, Tuple[datetime, Any]] = {}
        self._retry_attempts: Dict[str, int] = {}
    
    def add_event_handler(self, handler: Callable[[HandshakeEvent], None]):
        """Add event handler for handshake events"""
        self.event_handlers.append(handler)
    
    def _emit_event(self, event_name: str, data: Dict[str, Any] = None) -> HandshakeEvent:
        """Emit handshake event to all handlers"""
        if not self.session:
            raise RuntimeError("No active session")
        
        event = HandshakeEvent(
            event_name=event_name,
            session_id=self.session.session_id,
            step_index=self.session.step_index,
            timestamp=datetime.now(timezone.utc),
            data=data or {}
        )
        
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        return event
    
    def initiate_handshake(self, initiator_cell_id: str, responder_cell_id: str) -> HandshakeResult:
        """
        Initiate a new handshake session
        
        Args:
            initiator_cell_id: ID of the initiating cell
            responder_cell_id: ID of the responding cell
            
        Returns:
            HandshakeResult indicating success/failure
        """
        try:
            # Generate session nonce and ID
            session_nonce = secrets.token_hex(16)  # 128-bit random nonce
            session_id = hashlib.sha256(
                f"{initiator_cell_id}:{responder_cell_id}:{session_nonce}".encode('utf-8')
            ).hexdigest()
            
            # Create session
            self.session = HandshakeSession(
                session_id=session_id,
                session_nonce=session_nonce,
                initiator_cell_id=initiator_cell_id,
                responder_cell_id=responder_cell_id,
                current_state=HandshakeState.UNINITIALIZED,
                step_index=0
            )
            
            # Create transcript builder
            self.transcript_builder = TranscriptBuilder(session_id)
            
            # Add session nonce to transcript for replay
            self.transcript_builder.add_message_with_timestamp(
                "session_initiation",
                {
                    "session_nonce": session_nonce,
                    "initiator_cell_id": initiator_cell_id,
                    "responder_cell_id": responder_cell_id
                },
                "outgoing",
                self.session.created_at
            )
            
            # Transition to IDENTITY_EXCHANGE
            result = self._transition_to_state(
                HandshakeState.IDENTITY_EXCHANGE,
                "Handshake initiated"
            )
            
            if result.success:
                # Emit handshake initiated event
                self._emit_event("handshake_initiated", {
                    "session_nonce": session_nonce,
                    "initiator_cell_id": initiator_cell_id,
                    "responder_cell_id": responder_cell_id
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to initiate handshake: {e}")
            return HandshakeResult(False, HandshakeState.UNINITIALIZED, str(e))
    
    def process_message(self, message_type: str, message_data: Dict[str, Any], direction: str = "incoming") -> HandshakeResult:
        """
        Process an incoming message
        
        Args:
            message_type: Type of message
            message_data: Message payload
            direction: "incoming" or "outgoing"
            
        Returns:
            HandshakeResult indicating success/failure
        """
        if not self.session or not self.transcript_builder:
            return HandshakeResult(False, HandshakeState.UNINITIALIZED, "No active session")
        
        try:
            # Add to transcript
            step_index = self.transcript_builder.add_message(message_type, message_data, direction)
            
            # Check if this message is for current step
            if not self._is_message_for_current_step(message_type, direction):
                # Buffer for potential out-of-order handling
                self._buffer_message(message_type, message_data, direction)
                return HandshakeResult(True, self.session.current_state, "Message buffered")
            
            # Process based on current state
            return self._process_message_for_state(message_type, message_data, direction)
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return HandshakeResult(False, self.session.current_state, str(e))
    
    def _is_message_for_current_step(self, message_type: str, direction: str) -> bool:
        """Check if message is appropriate for current state and step"""
        if not self.session:
            return False
        
        current_state = self.session.current_state
        
        # Define expected messages for each state
        state_messages = {
            HandshakeState.IDENTITY_EXCHANGE: ["identity_exchange"],
            HandshakeState.CAPABILITY_NEGOTIATION: ["capability_negotiate"],
            HandshakeState.TRUST_ESTABLISHMENT: ["trust_establish"],
            HandshakeState.CONFIRMED: ["federation_confirm"],
        }
        
        expected_messages = state_messages.get(current_state, [])
        return message_type in expected_messages
    
    def _process_message_for_state(self, message_type: str, message_data: Dict[str, Any], direction: str) -> HandshakeResult:
        """Process message based on current state"""
        current_state = self.session.current_state
        
        if current_state == HandshakeState.IDENTITY_EXCHANGE:
            result = self._process_identity_exchange(message_data, direction)
        elif current_state == HandshakeState.CAPABILITY_NEGOTIATION:
            result = self._process_capability_negotiation(message_data, direction)
        elif current_state == HandshakeState.TRUST_ESTABLISHMENT:
            result = self._process_trust_establish(message_data, direction)
        elif current_state == HandshakeState.CONFIRMED:
            result = self._process_federation_confirm(message_data, direction)
        else:
            return HandshakeResult(False, current_state, f"Unexpected message in state {current_state}")
        
        # Increment step index on successful state transition
        if result.success and result.state != current_state:
            self.session.step_index += 1
        
        return result
    
    def _process_identity_exchange(self, message_data: Dict[str, Any], direction: str) -> HandshakeResult:
        """Process identity exchange message"""
        try:
            # Validate required fields
            required_fields = ["cell_identity", "signature", "timestamp", "nonce"]
            for field in required_fields:
                if field not in message_data:
                    return HandshakeResult(False, HandshakeState.IDENTITY_EXCHANGE, f"Missing required field: {field}")
            
            # Validate cell identity
            cell_identity_data = message_data["cell_identity"]
            cell_identity = CellIdentity(**cell_identity_data)
            
            # TODO: Validate signature and certificate
            # For now, assume validation passes
            
            # Emit success event
            self._emit_event("identity_verification_success", {
                "cell_id": cell_identity.cell_id,
                "direction": direction,
                "step_index": self.session.step_index
            })
            
            # Transition to next state
            return self._transition_to_state(
                HandshakeState.CAPABILITY_NEGOTIATION,
                "Identity verification completed"
            )
            
        except Exception as e:
            self._emit_event("identity_verification_failure", {
                "error": str(e),
                "step_index": self.session.step_index
            })
            return self._transition_to_state(
                HandshakeState.FAILED_IDENTITY,
                f"Identity verification failed: {e}"
            )
    
    def _process_capability_negotiation(self, message_data: Dict[str, Any], direction: str) -> HandshakeResult:
        """Process capability negotiation message"""
        try:
            # Validate required fields
            required_fields = ["supported_capabilities", "required_capabilities", "priority"]
            for field in required_fields:
                if field not in message_data:
                    return HandshakeResult(False, HandshakeState.CAPABILITY_NEGOTIATION, f"Missing required field: {field}")
            
            # TODO: Validate capability matching
            # For now, assume negotiation succeeds
            
            # Emit success event
            self._emit_event("capability_negotiation_completed", {
                "supported_capabilities": message_data["supported_capabilities"],
                "required_capabilities": message_data["required_capabilities"],
                "step_index": self.session.step_index
            })
            
            # Transition to next state
            return self._transition_to_state(
                HandshakeState.TRUST_ESTABLISHMENT,
                "Capability negotiation completed"
            )
            
        except Exception as e:
            self._emit_event("capability_negotiation_failure", {
                "error": str(e),
                "step_index": self.session.step_index
            })
            return self._transition_to_state(
                HandshakeState.FAILED_CAPABILITIES,
                f"Capability negotiation failed: {e}"
            )
    
    def _process_trust_establish(self, message_data: Dict[str, Any], direction: str) -> HandshakeResult:
        """Process trust establishment message"""
        try:
            # Validate required fields
            required_fields = ["trust_score", "trust_reasons", "expiration"]
            for field in required_fields:
                if field not in message_data:
                    return HandshakeResult(False, HandshakeState.TRUST_ESTABLISHMENT, f"Missing required field: {field}")
            
            trust_score = message_data["trust_score"]
            
            # Check minimum trust score
            if trust_score < self.config.minimum_trust_score:
                self._emit_event("trust_establishment_failure", {
                    "trust_score": trust_score,
                    "minimum_required": self.config.minimum_trust_score,
                    "reason": "Trust score below minimum threshold",
                    "step_index": self.session.step_index
                })
                return self._transition_to_state(
                    HandshakeState.FAILED_TRUST,
                    f"Trust score {trust_score} below minimum {self.config.minimum_trust_score}"
                )
            
            # Emit success event
            self._emit_event("trust_establishment_completed", {
                "trust_score": trust_score,
                "trust_reasons": message_data["trust_reasons"],
                "step_index": self.session.step_index
            })
            
            # Transition to next state
            return self._transition_to_state(
                HandshakeState.CONFIRMED,
                "Trust establishment completed"
            )
            
        except Exception as e:
            self._emit_event("trust_establishment_failure", {
                "error": str(e),
                "step_index": self.session.step_index
            })
            return self._transition_to_state(
                HandshakeState.FAILED_TRUST,
                f"Trust establishment failed: {e}"
            )
    
    def _process_federation_confirm(self, message_data: Dict[str, Any], direction: str) -> HandshakeResult:
        """Process federation confirmation message"""
        try:
            # Validate required fields
            required_fields = ["federation_id", "member_cells", "coordinator_cell", "terms"]
            for field in required_fields:
                if field not in message_data:
                    return HandshakeResult(False, HandshakeState.CONFIRMED, f"Missing required field: {field}")
            
            # Emit federation join event
            self._emit_event("federation_join", {
                "federation_id": message_data["federation_id"],
                "member_cells": message_data["member_cells"],
                "coordinator_cell": message_data["coordinator_cell"],
                "step_index": self.session.step_index
            })
            
            # Transition to active state
            return self._transition_to_state(
                HandshakeState.ACTIVE,
                "Federation confirmed and active"
            )
            
        except Exception as e:
            return HandshakeResult(False, HandshakeState.CONFIRMED, f"Federation confirmation failed: {e}")
    
    def _transition_to_state(self, new_state: HandshakeState, message: str = "") -> HandshakeResult:
        """Transition to a new state"""
        if not self.session:
            return HandshakeResult(False, HandshakeState.UNINITIALIZED, "No active session")
        
        old_state = self.session.current_state
        self.session.current_state = new_state
        self.session.updated_at = datetime.now(timezone.utc)
        
        # Determine if this is a success or failure transition
        is_success = new_state not in [
            HandshakeState.FAILED_IDENTITY,
            HandshakeState.FAILED_CAPABILITIES,
            HandshakeState.FAILED_TRUST,
            HandshakeState.SUSPENDED
        ]
        
        logger.info(f"State transition: {old_state} -> {new_state} ({message})")
        
        return HandshakeResult(is_success, new_state, message)
    
    def _buffer_message(self, message_type: str, message_data: Dict[str, Any], direction: str):
        """Buffer message for potential out-of-order handling"""
        buffer_key = f"{message_type}:{direction}"
        self._message_buffer[buffer_key] = (datetime.now(timezone.utc), (message_type, message_data, direction))
        
        # Clean old messages outside buffer window
        cutoff_time = datetime.now(timezone.utc) - timedelta(milliseconds=self.config.buffer_window_ms)
        self._message_buffer = {
            k: v for k, v in self._message_buffer.items() 
            if v[0] > cutoff_time
        }
    
    def get_current_state(self) -> Optional[HandshakeState]:
        """Get current handshake state"""
        return self.session.current_state if self.session else None
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if not self.session:
            return None
        
        return {
            "session_id": self.session.session_id,
            "session_nonce": self.session.session_nonce,
            "initiator_cell_id": self.session.initiator_cell_id,
            "responder_cell_id": self.session.responder_cell_id,
            "current_state": self.session.current_state,
            "step_index": self.session.step_index,
            "created_at": self.session.created_at.isoformat(),
            "updated_at": self.session.updated_at.isoformat(),
            "transcript_hash": self.transcript_builder.get_transcript_hash() if self.transcript_builder else None
        }
    
    def is_complete(self) -> bool:
        """Check if handshake is complete"""
        return bool(self.session and self.session.current_state == HandshakeState.ACTIVE)
    
    def is_failed(self) -> bool:
        """Check if handshake has failed"""
        return bool(self.session and self.session.current_state in [
            HandshakeState.FAILED_IDENTITY,
            HandshakeState.FAILED_CAPABILITIES,
            HandshakeState.FAILED_TRUST,
            HandshakeState.SUSPENDED
        ])
