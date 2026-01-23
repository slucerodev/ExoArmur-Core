"""
# PHASE 2B — LOCKED
# Coordination logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Coordination Manager
Main coordinator for federation coordination with feature flag isolation
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

from .coordination_state_machine import (
    CoordinationStateMachine,
    CoordinationConfig,
    CoordinationResult
)
from .coordination_audit_emitter import CoordinationAuditEmitter
from .coordination_models_v2 import (
    CoordinationType, CoordinationState, CoordinationRole,
    CoordinationAnnouncement, CoordinationClaim, CoordinationRelease,
    CoordinationObservation, CoordinationIntentBroadcast
)
from ..audit_interface import AuditInterface

logger = logging.getLogger(__name__)


class FederationCoordinationManager:
    """Main federation coordination manager with feature flag isolation"""
    
    def __init__(
        self,
        config: Optional[CoordinationConfig] = None,
        feature_flag_checker=None,
        audit_interface: Optional[AuditInterface] = None
    ):
        """
        Initialize federation coordination manager
        
        Args:
            config: Coordination configuration
            feature_flag_checker: Function to check if V2 federation is enabled
            audit_interface: Boundary-safe audit interface
        """
        self.config = config or CoordinationConfig()
        self.feature_flag_checker = feature_flag_checker or (lambda: False)
        
        # Initialize components only if feature flag is enabled
        if self.feature_flag_checker():
            self._state_machine = CoordinationStateMachine(self.config)
            self._audit_emitter = CoordinationAuditEmitter(
                audit_interface=audit_interface,
                feature_flag_checker=self.feature_flag_checker
            )
            
            # Wire audit emitter to state machine
            self._state_machine.add_event_handler(self._audit_emitter.create_event_handler())
            
            logger.info("FederationCoordinationManager initialized - V2 coordination enabled")
        else:
            self._state_machine = None
            self._audit_emitter = None
            logger.debug("FederationCoordinationManager initialized - V2 coordination disabled")
    
    def announce_coordination(self, owner_cell_id: str, coordination_type: CoordinationType,
                            scope_data: Dict[str, Any], capabilities: List[str] = None,
                            requirements: List[str] = None, 
                            expiration_hours: int = 24) -> CoordinationResult:
        """
        Announce availability for coordination
        
        Args:
            owner_cell_id: ID of the announcing cell
            coordination_type: Type of coordination
            scope_data: Scope definition data
            capabilities: List of capabilities
            requirements: List of requirements
            expiration_hours: Hours until expiration
            
        Returns:
            CoordinationResult with outcome
        """
        if not self.feature_flag_checker():
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="V2 coordination disabled"
            )
        
        if not self._state_machine:
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="Coordination not available"
            )
        
        try:
            # Create scope from data
            from .coordination_models_v2 import CoordinationScope
            scope = CoordinationScope(
                coordination_type=coordination_type,
                affected_cells=scope_data.get("affected_cells", []),
                resource_types=scope_data.get("resource_types", []),
                geographic_scope=scope_data.get("geographic_scope"),
                temporal_scope=scope_data.get("temporal_scope")
            )
            
            # Create announcement
            expiration_timestamp = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
            
            announcement = CoordinationAnnouncement(
                owner_cell_id=owner_cell_id,
                coordination_type=coordination_type,
                scope=scope,
                capabilities=capabilities or [],
                requirements=requirements or [],
                expiration_timestamp=expiration_timestamp
            )
            
            return self._state_machine.create_announcement(announcement)
            
        except Exception as e:
            logger.error(f"Failed to announce coordination: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to announce coordination: {e}"
            )
    
    def claim_coordination_role(self, owner_cell_id: str, coordination_id: str,
                               coordination_role: CoordinationRole, claimed_resources: List[str] = None,
                               expiration_hours: int = 1) -> CoordinationResult:
        """
        Claim coordination role
        
        Args:
            owner_cell_id: ID of the claiming cell
            coordination_id: ID of the coordination to claim
            coordination_role: Role to claim
            claimed_resources: Resources being claimed
            expiration_hours: Hours until claim expiration
            
        Returns:
            CoordinationResult with outcome
        """
        if not self.feature_flag_checker():
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="V2 coordination disabled"
            )
        
        if not self._state_machine:
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="Coordination not available"
            )
        
        try:
            # Get coordination session to determine type
            status = self._state_machine.get_coordination_status(coordination_id)
            if not status:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Coordination not found"
                )
            
            expiration_timestamp = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
            
            # Create scope from session
            from .coordination_models_v2 import CoordinationScope
            scope = CoordinationScope(
                coordination_type=status["coordination_type"],
                affected_cells=status.get("participants", []),
                resource_types=claimed_resources or []
            )
            
            claim = CoordinationClaim(
                owner_cell_id=owner_cell_id,
                coordination_id=coordination_id,
                coordination_type=status["coordination_type"],
                scope=scope,
                expiration_timestamp=expiration_timestamp,
                coordination_role=coordination_role,
                claimed_resources=claimed_resources or []
            )
            
            return self._state_machine.claim_coordination(claim)
            
        except Exception as e:
            logger.error(f"Failed to claim coordination role: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to claim coordination role: {e}"
            )
    
    def release_coordination_role(self, owner_cell_id: str, coordination_id: str,
                                 release_reason: str = "Manual release") -> CoordinationResult:
        """
        Release coordination role
        
        Args:
            owner_cell_id: ID of the releasing cell
            coordination_id: ID of the coordination to release
            release_reason: Reason for release
            
        Returns:
            CoordinationResult with outcome
        """
        if not self.feature_flag_checker():
            return CoordinationResult(
                success=False,
                state=CoordinationState.CLAIMED,
                message="V2 coordination disabled"
            )
        
        if not self._state_machine:
            return CoordinationResult(
                success=False,
                state=CoordinationState.CLAIMED,
                message="Coordination not available"
            )
        
        try:
            status = self._state_machine.get_coordination_status(coordination_id)
            if not status:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.CLAIMED,
                    message="Coordination not found"
                )
            
            release = CoordinationRelease(
                coordination_id=coordination_id,
                owner_cell_id=owner_cell_id,
                coordination_type=status["coordination_type"],
                release_reason=release_reason,
                final_state=CoordinationState.RELEASED
            )
            
            return self._state_machine.release_coordination(release)
            
        except Exception as e:
            logger.error(f"Failed to release coordination role: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.CLAIMED,
                message=f"Failed to release coordination role: {e}"
            )
    
    def share_observation(self, observer_cell_id: str, coordination_id: str,
                         observation_type: str, observed_data: Dict[str, Any],
                         confidence_score: float = 0.8, scope_data: Dict[str, Any] = None) -> CoordinationResult:
        """
        Share observation (non-authoritative)
        
        Args:
            observer_cell_id: ID of the observing cell
            coordination_id: ID of the coordination (optional)
            observation_type: Type of observation
            observed_data: Observation data
            confidence_score: Confidence in observation (0.0-1.0)
            scope_data: Scope definition data
            
        Returns:
            CoordinationResult with outcome
        """
        if not self.feature_flag_checker():
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="V2 coordination disabled"
            )
        
        if not self._state_machine:
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="Coordination not available"
            )
        
        try:
            # Create scope from data
            from .coordination_models_v2 import CoordinationScope
            scope = CoordinationScope(
                coordination_type=CoordinationType.OBSERVATION_SHARING,
                affected_cells=scope_data.get("affected_cells", []) if scope_data else [],
                resource_types=scope_data.get("resource_types", []) if scope_data else [],
                geographic_scope=scope_data.get("geographic_scope") if scope_data else None,
                temporal_scope=scope_data.get("temporal_scope") if scope_data else None
            )
            
            observation = CoordinationObservation(
                observer_cell_id=observer_cell_id,
                coordination_id=coordination_id,
                observation_type=observation_type,
                observed_data=observed_data,
                confidence_score=confidence_score,
                observation_scope=scope
            )
            
            return self._state_machine.add_observation(observation)
            
        except Exception as e:
            logger.error(f"Failed to share observation: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to share observation: {e}"
            )
    
    def broadcast_intent(self, broadcaster_cell_id: str, intent_type: str,
                        intent_data: Dict[str, Any], target_cells: List[str] = None,
                        priority: int = 5, valid_hours: int = 4) -> CoordinationResult:
        """
        Broadcast intent (non-binding)
        
        Args:
            broadcaster_cell_id: ID of the broadcasting cell
            intent_type: Type of intent
            intent_data: Intent data
            target_cells: Target cells (empty = broadcast to all)
            priority: Priority level (1-10)
            valid_hours: Hours until intent expires
            
        Returns:
            CoordinationResult with outcome
        """
        if not self.feature_flag_checker():
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="V2 coordination disabled"
            )
        
        if not self._state_machine:
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message="Coordination not available"
            )
        
        try:
            valid_until = datetime.now(timezone.utc) + timedelta(hours=valid_hours)
            
            intent = CoordinationIntentBroadcast(
                broadcaster_cell_id=broadcaster_cell_id,
                coordination_type=CoordinationType.INTENT_BROADCAST,
                intent_type=intent_type,
                intent_data=intent_data,
                valid_until=valid_until,
                target_cells=target_cells or [],
                priority=priority
            )
            
            return self._state_machine.broadcast_intent(intent)
            
        except Exception as e:
            logger.error(f"Failed to broadcast intent: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to broadcast intent: {e}"
            )
    
    def get_coordination_status(self, coordination_id: str) -> Optional[Dict[str, Any]]:
        """
        Get coordination status
        
        Args:
            coordination_id: ID of the coordination
            
        Returns:
            Coordination status or None if not found
        """
        if not self._state_machine:
            return None
        
        return self._state_machine.get_coordination_status(coordination_id)
    
    def get_active_coordinations(self, cell_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active coordinations
        
        Args:
            cell_id: Optional cell ID to filter by
            
        Returns:
            List of active coordination statuses
        """
        if not self._state_machine:
            return []
        
        return self._state_machine.get_active_coordinations(cell_id)
    
    def get_coordination_audit_trail(self, coordination_id: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Get coordination audit trail
        
        Args:
            coordination_id: ID of the coordination
            limit: Maximum number of events to retrieve
            
        Returns:
            Audit trail data or None if not available
        """
        if not self._audit_emitter:
            return None
        
        return self._audit_emitter.get_coordination_audit_trail(coordination_id, limit)
    
    def validate_coordination_integrity(self, coordination_id: str, expected_event_count: int) -> Dict[str, Any]:
        """
        Validate coordination audit integrity
        
        Args:
            coordination_id: ID of the coordination
            expected_event_count: Expected number of events
            
        Returns:
            Validation result
        """
        if not self._audit_emitter:
            return {
                "coordination_id": coordination_id,
                "valid": False,
                "reason": "Audit emitter not available",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return self._audit_emitter.validate_coordination_audit_integrity(coordination_id, expected_event_count)
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """
        Get coordination summary
        
        Returns:
            Summary of coordination state
        """
        if not self._state_machine:
            return {
                "v2_coordination_enabled": False,
                "active_coordinations": 0,
                "total_sessions": 0,
                "expired_sessions": 0
            }
        
        active_coordinations = self.get_active_coordinations()
        total_sessions = len(self._state_machine._sessions)
        expired_sessions = sum(1 for s in self._state_machine._sessions.values() if s.is_expired())
        
        return {
            "v2_coordination_enabled": True,
            "active_coordinations": len(active_coordinations),
            "total_sessions": total_sessions,
            "expired_sessions": expired_sessions,
            "announcements": len(self._state_machine._announcements),
            "claims": len(self._state_machine._claims),
            "feature_flag_enabled": self.feature_flag_checker()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for coordination manager
        
        Returns:
            Health status
        """
        if not self.feature_flag_checker():
            return {
                "status": "disabled",
                "v2_coordination_enabled": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if not self._state_machine:
            return {
                "status": "unhealthy",
                "v2_coordination_enabled": True,
                "reason": "State machine not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        summary = self.get_coordination_summary()
        
        # Determine health based on active coordinations
        if summary["active_coordinations"] > 100:
            status = "degraded"
            reason = "High number of active coordinations"
        elif summary["expired_sessions"] > summary["total_sessions"] * 0.5:
            status = "degraded"
            reason = "High number of expired sessions"
        else:
            status = "healthy"
            reason = "Coordination operating normally"
        
        return {
            "status": status,
            "v2_coordination_enabled": True,
            "reason": reason,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def start_background_tasks(self):
        """Start background tasks"""
        if self._state_machine:
            await self._state_machine.start_cleanup_task()
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        if self._state_machine:
            await self._state_machine.stop_cleanup_task()
    
    def shutdown(self) -> bool:
        """
        Shutdown coordination manager
        
        Returns:
            True if shutdown successful
        """
        try:
            if self._state_machine:
                self._state_machine.shutdown()
            
            logger.info("FederationCoordinationManager shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to shutdown coordination manager: {e}")
            return False
