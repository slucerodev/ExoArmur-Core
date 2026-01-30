"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Identity Audit Emitter
Integration with V1 audit system for federation identity events via boundary interface
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .identity_handshake_state_machine import HandshakeEvent
from .audit_interface import AuditInterface

logger = logging.getLogger(__name__)


class IdentityAuditEmitter:
    """Audit event emitter for federation identity handshake"""
    
    def __init__(self, audit_interface: Optional[AuditInterface] = None, feature_flag_checker=None):
        """
        Initialize audit emitter
        
        Args:
            audit_interface: Boundary-safe audit interface (optional for testing)
            feature_flag_checker: Function to check if V2 federation is enabled
        """
        self.audit_interface = audit_interface
        self.feature_flag_checker = feature_flag_checker or (lambda: False)
    
    def emit_handshake_event(self, event: HandshakeEvent) -> bool:
        """
        Emit handshake event to audit log
        
        Args:
            event: Handshake event to emit
            
        Returns:
            True if event was emitted, False if disabled or failed
        """
        # Check if V2 federation is enabled
        if not self.feature_flag_checker():
            # Emit single diagnostic event when disabled
            return self._emit_diagnostic_event(event)
        
        # Emit the actual handshake event
        return self._emit_audit_event(event)
    
    def _emit_audit_event(self, event: HandshakeEvent) -> bool:
        """Emit audit event via boundary interface"""
        try:
            # Create audit event data
            audit_data = {
                "event_name": event.event_name,
                "session_id": event.session_id,
                "step_index": event.step_index,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
            
            # Add federation-specific context
            audit_data.update({
                "federation_version": "2.0",
                "component": "federation_identity",
                "audit_category": "federation_handshake"
            })
            
            # Emit via boundary interface
            if self.audit_interface:
                return self.audit_interface.log_event(
                    event_type=f"federation.identity.{event.event_name}",
                    correlation_id=event.session_id,
                    data=audit_data,
                    recorded_at=event.timestamp
                )
            else:
                # Fallback logging for testing
                logger.info(f"Audit event: {event.event_name} for session {event.session_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to emit audit event {event.event_name}: {e}")
            return False
    
    def _emit_diagnostic_event(self, event: HandshakeEvent) -> bool:
        """Emit single diagnostic event when V2 federation is disabled"""
        try:
            # Only emit one diagnostic event per session when disabled
            if event.event_name != "handshake_initiated":
                return False  # Skip non-initiation events when disabled
            
            diagnostic_data = {
                "event_name": "federation_identity_disabled",
                "cell_id": event.data.get("initiator_cell_id", "unknown"),
                "timestamp": event.timestamp.isoformat(),
                "reason": "feature_flag_disabled",
                "component": "federation_identity",
                "federation_version": "2.0",
                "audit_category": "diagnostic"
            }
            
            # Emit via boundary interface
            if self.audit_interface:
                return self.audit_interface.log_event(
                    event_type="federation.identity.disabled",
                    correlation_id="diagnostic",
                    data=diagnostic_data,
                    recorded_at=event.timestamp
                )
            else:
                # Fallback logging for testing
                logger.info("Federation identity disabled - feature flag off")
                return True
            
        except Exception as e:
            logger.error(f"Failed to emit diagnostic event: {e}")
            return False
    
    def create_event_handler(self) -> callable:
        """
        Create event handler function for state machine
        
        Returns:
            Event handler function that can be added to state machine
        """
        def handle_event(event: HandshakeEvent):
            """Handle handshake event"""
            success = self.emit_handshake_event(event)
            if not success:
                logger.warning(f"Failed to emit audit event: {event.event_name}")
        
        return handle_event
    
    def get_audit_trail(self, session_id: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Retrieve audit trail for a session
        
        Args:
            session_id: Session ID to retrieve trail for
            limit: Maximum number of events to retrieve
            
        Returns:
            Audit trail data or None if not available
        """
        if not self.feature_flag_checker():
            return None
        
        try:
            # Query via boundary interface
            if self.audit_interface:
                events = self.audit_interface.get_events(
                    event_type_prefix="federation.identity.",
                    correlation_id=session_id,
                    limit=limit
                )
                
                if events is not None:
                    return {
                        "session_id": session_id,
                        "events": events,
                        "event_count": len(events),
                        "retrieved_at": datetime.now(timezone.utc).isoformat()
                    }
            
            # Fallback for testing
            return {
                    "session_id": session_id,
                    "events": [],
                    "event_count": 0,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Audit logger not available"
                }
                
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail for session {session_id}: {e}")
            return None
    
    def validate_audit_integrity(self, session_id: str, expected_step_count: int) -> Dict[str, Any]:
        """
        Validate audit trail integrity for a session
        
        Args:
            session_id: Session ID to validate
            expected_step_count: Expected number of steps in handshake
            
        Returns:
            Validation result with integrity status
        """
        audit_trail = self.get_audit_trail(session_id)
        
        if not audit_trail:
            return {
                "session_id": session_id,
                "valid": False,
                "reason": "Audit trail not available",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        events = audit_trail.get("events", [])
        actual_step_count = len(events)
        
        # Check step count
        step_count_valid = actual_step_count == expected_step_count
        
        # Check idempotency key uniqueness
        idempotency_keys = [event.get("data", {}).get("idempotency_key") for event in events]
        unique_keys = set(idempotency_keys)
        idempotency_valid = len(idempotency_keys) == len(unique_keys)
        
        # Check chronological order
        timestamps = [event.get("timestamp") for event in events]
        timestamps_sorted = sorted(timestamps)
        chronological_valid = timestamps == timestamps_sorted
        
        # Check step index progression
        step_indices = [event.get("data", {}).get("step_index") for event in events]
        step_indices_sorted = sorted(step_indices)
        step_order_valid = step_indices == step_indices_sorted
        
        overall_valid = step_count_valid and idempotency_valid and chronological_valid and step_order_valid
        
        return {
            "session_id": session_id,
            "valid": overall_valid,
            "step_count_valid": step_count_valid,
            "idempotency_valid": idempotency_valid,
            "chronological_valid": chronological_valid,
            "step_order_valid": step_order_valid,
            "expected_steps": expected_step_count,
            "actual_steps": actual_step_count,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "issues": [
                "Step count mismatch" if not step_count_valid else None,
                "Duplicate idempotency keys" if not idempotency_valid else None,
                "Timestamp order violation" if not chronological_valid else None,
                "Step index order violation" if not step_order_valid else None
            ] if not overall_valid else []
        }
