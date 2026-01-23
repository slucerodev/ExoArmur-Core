"""
# PHASE 2B — LOCKED
# Coordination logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Coordination Audit Emitter
Integration with V1 audit system for federation coordination events via boundary interface
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..audit_interface import AuditInterface
from .coordination_models_v2 import CoordinationEvent


logger = logging.getLogger(__name__)


class CoordinationAuditEmitter:
    """Audit event emitter for federation coordination"""
    
    def __init__(self, audit_interface: Optional[AuditInterface] = None, feature_flag_checker=None):
        """
        Initialize audit emitter
        
        Args:
            audit_interface: Boundary-safe audit interface (optional for testing)
            feature_flag_checker: Function to check if V2 federation is enabled
        """
        self.audit_interface = audit_interface
        self.feature_flag_checker = feature_flag_checker or (lambda: False)
    
    def emit_coordination_event(self, event: CoordinationEvent) -> bool:
        """
        Emit coordination event to audit log
        
        Args:
            event: Coordination event to emit
            
        Returns:
            True if event was emitted, False if disabled or failed
        """
        # Check if V2 federation is enabled
        if not self.feature_flag_checker():
            # Emit single diagnostic event when disabled
            return self._emit_diagnostic_event(event)
        
        # Emit the actual coordination event
        return self._emit_audit_event(event)
    
    def _emit_audit_event(self, event: CoordinationEvent) -> bool:
        """Emit audit event via boundary interface"""
        try:
            # Create audit event data
            audit_data = {
                "event_name": event.event_name,
                "coordination_id": event.coordination_id,
                "owner_cell_id": event.owner_cell_id,
                "coordination_type": event.coordination_type,
                "timestamp": event.event_timestamp.isoformat(),
                "event_data": event.event_data
            }
            
            # Add federation-specific context
            audit_data.update({
                "federation_version": "2.0",
                "component": "federation_coordination",
                "audit_category": "coordination_lifecycle"
            })
            
            # Emit via boundary interface
            if self.audit_interface:
                return self.audit_interface.log_event(
                    event_type=f"federation.coordination.{event.event_name}",
                    correlation_id=event.coordination_id,
                    data=audit_data,
                    recorded_at=event.event_timestamp
                )
            else:
                # Fallback logging for testing
                logger.info(f"Coordination audit event: {event.event_name} for {event.coordination_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to emit coordination audit event {event.event_name}: {e}")
            return False
    
    def _emit_diagnostic_event(self, event: CoordinationEvent) -> bool:
        """Emit single diagnostic event when V2 federation is disabled"""
        try:
            # Only emit one diagnostic event per session when disabled
            if event.event_name != "announcement_created":
                return False  # Skip non-initiation events when disabled
            
            diagnostic_data = {
                "event_name": "federation_coordination_disabled",
                "coordination_id": event.coordination_id,
                "cell_id": event.owner_cell_id,
                "timestamp": event.event_timestamp.isoformat(),
                "reason": "feature_flag_disabled",
                "component": "federation_coordination",
                "federation_version": "2.0",
                "audit_category": "diagnostic"
            }
            
            # Emit via boundary interface
            if self.audit_interface:
                return self.audit_interface.log_event(
                    event_type="federation.coordination.disabled",
                    correlation_id="diagnostic",
                    data=diagnostic_data,
                    recorded_at=event.event_timestamp
                )
            else:
                # Fallback logging for testing
                logger.info("Federation coordination disabled - feature flag off")
                return True
            
        except Exception as e:
            logger.error(f"Failed to emit diagnostic coordination event: {e}")
            return False
    
    def create_event_handler(self) -> callable:
        """
        Create event handler function for state machine
        
        Returns:
            Event handler function
        """
        def handle_event(event: CoordinationEvent):
            """Handle coordination event"""
            success = self.emit_coordination_event(event)
            if not success:
                logger.warning(f"Failed to emit coordination audit event: {event.event_name}")
        
        return handle_event
    
    def get_coordination_audit_trail(self, coordination_id: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Retrieve coordination audit trail for a coordination
        
        Args:
            coordination_id: Coordination ID to retrieve trail for
            limit: Maximum number of events to retrieve
            
        Returns:
            Coordination audit trail data or None if not available
        """
        if not self.feature_flag_checker():
            return None
        
        try:
            # Query via boundary interface
            if self.audit_interface:
                events = self.audit_interface.get_events(
                    event_type_prefix="federation.coordination.",
                    correlation_id=coordination_id,
                    limit=limit
                )
                
                if events is not None:
                    return {
                        "coordination_id": coordination_id,
                        "events": events,
                        "event_count": len(events),
                        "retrieved_at": datetime.now(timezone.utc).isoformat()
                    }
            
            # Fallback for testing
            return {
                "coordination_id": coordination_id,
                "events": [],
                "event_count": 0,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "note": "Audit interface not available"
            }
                
        except Exception as e:
            logger.error(f"Failed to retrieve coordination audit trail for {coordination_id}: {e}")
            return None
    
    def validate_coordination_audit_integrity(self, coordination_id: str, expected_event_count: int) -> Dict[str, Any]:
        """
        Validate coordination audit trail integrity for a coordination
        
        Args:
            coordination_id: Coordination ID to validate
            expected_event_count: Expected number of events in coordination
            
        Returns:
            Validation result with integrity status
        """
        audit_trail = self.get_coordination_audit_trail(coordination_id)
        
        if not audit_trail:
            return {
                "coordination_id": coordination_id,
                "valid": False,
                "reason": "Coordination audit trail not available",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        events = audit_trail.get("events", [])
        actual_event_count = len(events)
        
        # Check event count
        if actual_event_count != expected_event_count:
            return {
                "coordination_id": coordination_id,
                "valid": False,
                "reason": f"Event count mismatch: expected {expected_event_count}, got {actual_event_count}",
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "expected_count": expected_event_count,
                "actual_count": actual_event_count
            }
        
        # Check for duplicate idempotency keys
        idempotency_keys = [event.get("data", {}).get("idempotency_key") for event in events]
        unique_keys = set(idempotency_keys)
        if len(idempotency_keys) != len(unique_keys):
            return {
                "coordination_id": coordination_id,
                "valid": False,
                "reason": "Duplicate idempotency keys found in audit trail",
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "duplicate_keys": len(idempotency_keys) - len(unique_keys)
            }
        
        # Check chronological order
        timestamps = [event.get("recorded_at") for event in events]
        if timestamps != sorted(timestamps):
            return {
                "coordination_id": coordination_id,
                "valid": False,
                "reason": "Audit events not in chronological order",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return {
            "coordination_id": coordination_id,
            "valid": True,
            "reason": "Coordination audit trail integrity validated",
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "event_count": actual_event_count,
            "idempotency_keys_unique": True,
            "chronological_order": True
        }
