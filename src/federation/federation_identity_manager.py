"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Identity Manager
Main coordinator for federation identity handshake with feature flag isolation
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .identity_handshake_state_machine import (
    IdentityHandshakeStateMachine,
    HandshakeConfig,
    HandshakeEvent,
    HandshakeResult,
)
from .identity_audit_emitter import IdentityAuditEmitter
from .models.federation_identity_v2 import HandshakeState
from .audit_interface import AuditInterface

logger = logging.getLogger(__name__)


class FederationIdentityManager:
    """Main federation identity manager with feature flag isolation"""
    
    def __init__(
        self,
        config: Optional[HandshakeConfig] = None,
        feature_flag_checker=None,
        audit_interface: Optional[AuditInterface] = None
    ):
        """
        Initialize federation identity manager
        
        Args:
            config: Handshake configuration
            feature_flag_checker: Function to check if V2 federation is enabled
            audit_interface: Boundary-safe audit interface
        """
        self.config = config or HandshakeConfig()
        self.feature_flag_checker = feature_flag_checker or (lambda: False)
        
        # Initialize components only if feature flag is enabled
        if self.feature_flag_checker():
            self._state_machine = IdentityHandshakeStateMachine(self.config)
            self._audit_emitter = IdentityAuditEmitter(
                audit_interface=audit_interface,
                feature_flag_checker=self.feature_flag_checker
            )
            
            # Wire audit emitter to state machine
            self._state_machine.add_event_handler(self._audit_emitter.create_event_handler())
            
            logger.info("FederationIdentityManager initialized - V2 federation enabled")
        else:
            self._state_machine = None
            self._audit_emitter = None
            logger.debug("FederationIdentityManager initialized - V2 federation disabled")
    
    def initiate_handshake(self, initiator_cell_id: str, responder_cell_id: str) -> HandshakeResult:
        """
        Initiate federation identity handshake
        
        Args:
            initiator_cell_id: ID of the initiating cell
            responder_cell_id: ID of the responding cell
            
        Returns:
            HandshakeResult indicating success/failure
        """
        if not self.feature_flag_checker():
            return HandshakeResult(
                False,
                HandshakeState.UNINITIALIZED,
                "V2 federation is disabled - feature flag off"
            )
        
        if not self._state_machine:
            return HandshakeResult(
                False,
                HandshakeState.UNINITIALIZED,
                "State machine not initialized"
            )
        
        return self._state_machine.initiate_handshake(initiator_cell_id, responder_cell_id)
    
    def process_message(self, message_type: str, message_data: Dict[str, Any], direction: str = "incoming") -> HandshakeResult:
        """
        Process federation identity message
        
        Args:
            message_type: Type of message (identity_exchange, capability_negotiate, etc.)
            message_data: Message payload
            direction: "incoming" or "outgoing"
            
        Returns:
            HandshakeResult indicating success/failure
        """
        if not self.feature_flag_checker():
            return HandshakeResult(
                False,
                HandshakeState.UNINITIALIZED,
                "V2 federation is disabled - feature flag off"
            )
        
        if not self._state_machine:
            return HandshakeResult(
                False,
                HandshakeState.UNINITIALIZED,
                "State machine not initialized"
            )
        
        return self._state_machine.process_message(message_type, message_data, direction)
    
    def get_handshake_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current handshake status
        
        Returns:
            Handshake status information or None if no active session
        """
        if not self.feature_flag_checker():
            return {
                "enabled": False,
                "status": "disabled",
                "reason": "V2 federation feature flag is off"
            }
        
        if not self._state_machine:
            return {
                "enabled": True,
                "status": "not_initialized",
                "reason": "State machine not available"
            }
        
        session_info = self._state_machine.get_session_info()
        if not session_info:
            return {
                "enabled": True,
                "status": "no_active_session",
                "reason": "No active handshake session"
            }
        
        return {
            "enabled": True,
            "status": "active",
            "session_info": session_info,
            "is_complete": self._state_machine.is_complete(),
            "is_failed": self._state_machine.is_failed(),
            "current_state": self._state_machine.get_current_state()
        }
    
    def get_audit_trail(self, session_id: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Get audit trail for a handshake session
        
        Args:
            session_id: Session ID to retrieve trail for
            limit: Maximum number of events to retrieve
            
        Returns:
            Audit trail data or None if not available
        """
        if not self.feature_flag_checker():
            return None
        
        if not self._audit_emitter:
            return None
        
        return self._audit_emitter.get_audit_trail(session_id, limit)
    
    def validate_audit_integrity(self, session_id: str, expected_step_count: int) -> Dict[str, Any]:
        """
        Validate audit trail integrity for a session
        
        Args:
            session_id: Session ID to validate
            expected_step_count: Expected number of steps in handshake
            
        Returns:
            Validation result with integrity status
        """
        if not self.feature_flag_checker():
            return {
                "session_id": session_id,
                "valid": False,
                "reason": "V2 federation is disabled",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        if not self._audit_emitter:
            return {
                "session_id": session_id,
                "valid": False,
                "reason": "Audit emitter not available",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return self._audit_emitter.validate_audit_integrity(session_id, expected_step_count)
    
    def is_federation_member(self, cell_id: str) -> bool:
        """
        Check if a cell is a federation member
        
        Args:
            cell_id: Cell ID to check
            
        Returns:
            True if cell is federation member, False otherwise
        """
        if not self.feature_flag_checker():
            return False
        
        if not self._state_machine:
            return False
        
        # Check if we have an active session and the cell is in the federation
        session_info = self._state_machine.get_session_info()
        if not session_info:
            return False
        
        # For now, check if the cell is part of the current handshake
        # In a full implementation, this would query a membership table
        current_state = self._state_machine.get_current_state()
        if current_state == HandshakeState.ACTIVE:
            # Active federation means both initiator and responder are members
            return (
                session_info.get("initiator_cell_id") == cell_id or
                session_info.get("responder_cell_id") == cell_id
            )
        
        return False
    
    def get_federation_members(self) -> List[str]:
        """
        Get list of federation members
        
        Returns:
            List of member cell IDs
        """
        if not self.feature_flag_checker():
            return []
        
        if not self._state_machine:
            return []
        
        session_info = self._state_machine.get_session_info()
        if not session_info:
            return []
        
        current_state = self._state_machine.get_current_state()
        if current_state == HandshakeState.ACTIVE:
            return [
                session_info.get("initiator_cell_id", ""),
                session_info.get("responder_cell_id", "")
            ]
        
        return []
    
    def shutdown(self) -> bool:
        """
        Shutdown federation identity manager
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            if self._state_machine:
                # Clean up any active sessions
                # In a full implementation, this would gracefully close connections
                logger.info("Shutting down federation identity manager")
                self._state_machine = None
            
            if self._audit_emitter:
                self._audit_emitter = None
            
            logger.info("FederationIdentityManager shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary
        
        Returns:
            Configuration summary
        """
        return {
            "v2_federation_enabled": self.feature_flag_checker(),
            "buffer_window_ms": self.config.buffer_window_ms,
            "step_timeout_ms": self.config.step_timeout_ms,
            "minimum_trust_score": self.config.minimum_trust_score,
            "max_retry_attempts": self.config.max_retry_attempts,
            "retry_backoff_base_ms": self.config.retry_backoff_base_ms
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on federation identity manager
        
        Returns:
            Health check status
        """
        if not self.feature_flag_checker():
            return {
                "status": "healthy",
                "v2_federation_enabled": False,
                "reason": "V2 federation is disabled - this is normal"
            }
        
        if not self._state_machine or not self._audit_emitter:
            return {
                "status": "unhealthy",
                "v2_federation_enabled": True,
                "reason": "Components not properly initialized"
            }
        
        # Check if there are any active sessions in failed state
        if self._state_machine.is_failed():
            return {
                "status": "degraded",
                "v2_federation_enabled": True,
                "reason": "Active handshake session in failed state",
                "current_state": str(self._state_machine.get_current_state())
            }
        
        return {
            "status": "healthy",
            "v2_federation_enabled": True,
            "current_state": str(self._state_machine.get_current_state()) if self._state_machine.get_current_state() else "no_session"
        }
