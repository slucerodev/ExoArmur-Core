"""
# PHASE 2B — LOCKED
# Coordination logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Coordination State Machine
Deterministic state machine for federation coordination (no intelligence, no decisions)
"""

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .coordination_models_v2 import (
    CoordinationType, CoordinationState, CoordinationRole,
    CoordinationAnnouncement, CoordinationClaim, CoordinationRelease,
    CoordinationObservation, CoordinationIntentBroadcast, CoordinationEvent,
    CoordinationSession
)

logger = logging.getLogger(__name__)


@dataclass
class CoordinationConfig:
    """Configuration for coordination behavior"""
    max_session_duration_hours: int = 24
    max_claim_duration_hours: int = 1
    max_participants_per_coordination: int = 20
    max_observations_per_session: int = 100
    max_intents_per_session: int = 50
    cleanup_interval_seconds: int = 300  # 5 minutes


@dataclass
class CoordinationResult:
    """Result of coordination operation"""
    success: bool
    state: CoordinationState
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __bool__(self):
        return self.success


class CoordinationStateMachine:
    """Deterministic state machine for federation coordination"""
    
    def __init__(self, config: Optional[CoordinationConfig] = None):
        """Initialize state machine with configuration"""
        self.config = config or CoordinationConfig()
        self._sessions: Dict[str, CoordinationSession] = {}
        self._announcements: Dict[str, CoordinationAnnouncement] = {}
        self._claims: Dict[str, CoordinationClaim] = {}
        self._event_handlers: List[Callable] = []
        
        # Start cleanup task
        self._cleanup_task = None
        self._shutdown_event = asyncio.Event()
    
    def add_event_handler(self, handler: Callable):
        """Add event handler for coordination events"""
        self._event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable):
        """Remove event handler"""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)
    
    def _emit_event(self, event_name: str, coordination_id: str, owner_cell_id: str,
                   coordination_type: CoordinationType, event_data: Dict[str, Any]) -> None:
        """Emit coordination event to handlers"""
        event = CoordinationEvent(
            event_name=event_name,
            coordination_id=coordination_id,
            owner_cell_id=owner_cell_id,
            coordination_type=coordination_type,
            event_data=event_data
        )
        
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")
    
    def create_announcement(self, announcement: CoordinationAnnouncement) -> CoordinationResult:
        """Create coordination announcement"""
        try:
            # Validate announcement
            if self._validate_announcement(announcement):
                self._announcements[announcement.coordination_id] = announcement
                
                # Create session for the announcement
                session = CoordinationSession(
                    coordination_id=announcement.coordination_id,
                    coordinator_cell_id=announcement.owner_cell_id,
                    coordination_type=announcement.coordination_type,
                    scope=announcement.scope,
                    expiration_timestamp=announcement.expiration_timestamp
                )
                self._sessions[announcement.coordination_id] = session
                
                self._emit_event(
                    "announcement_created",
                    announcement.coordination_id,
                    announcement.owner_cell_id,
                    announcement.coordination_type,
                    {"scope": announcement.scope.model_dump(), "capabilities": announcement.capabilities}
                )
                
                return CoordinationResult(
                    success=True,
                    state=CoordinationState.UNCLAIMED,
                    message="Announcement created successfully",
                    data={"coordination_id": announcement.coordination_id}
                )
            else:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Invalid announcement"
                )
        except Exception as e:
            logger.error(f"Failed to create announcement: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to create announcement: {e}"
            )
    
    def claim_coordination(self, claim: CoordinationClaim) -> CoordinationResult:
        """Claim coordination role"""
        try:
            session = self._sessions.get(claim.coordination_id)
            if not session:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Coordination session not found"
                )
            
            # Validate claim
            if not self._validate_claim(claim, session):
                return CoordinationResult(
                    success=False,
                    state=session.state,
                    message="Invalid claim"
                )
            
            # Check if already claimed
            if session.state == CoordinationState.CLAIMED and session.current_claim:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.CLAIMED,
                    message="Coordination already claimed"
                )
            
            # Apply claim
            session.current_claim = claim
            session.state = CoordinationState.CLAIMED
            session.updated_at = datetime.now(timezone.utc)
            session.coordinator_cell_id = claim.owner_cell_id
            
            if claim.owner_cell_id not in session.participants:
                session.participants.append(claim.owner_cell_id)
            
            self._claims[claim.coordination_id] = claim
            
            self._emit_event(
                "coordination_claimed",
                claim.coordination_id,
                claim.owner_cell_id,
                claim.coordination_type,
                {"role": claim.coordination_role, "resources": claim.claimed_resources}
            )
            
            return CoordinationResult(
                success=True,
                state=CoordinationState.CLAIMED,
                message="Coordination claimed successfully",
                data={"coordination_id": claim.coordination_id, "role": claim.coordination_role}
            )
            
        except Exception as e:
            logger.error(f"Failed to claim coordination: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to claim coordination: {e}"
            )
    
    def release_coordination(self, release: CoordinationRelease) -> CoordinationResult:
        """Release coordination role"""
        try:
            session = self._sessions.get(release.coordination_id)
            if not session:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Coordination session not found"
                )
            
            # Validate release
            if session.current_claim and session.current_claim.owner_cell_id != release.owner_cell_id:
                return CoordinationResult(
                    success=False,
                    state=session.state,
                    message="Not authorized to release this coordination"
                )
            
            # Apply release
            session.state = CoordinationState.RELEASED
            session.updated_at = datetime.now(timezone.utc)
            session.final_state = release.final_state
            
            # Remove claim
            if release.coordination_id in self._claims:
                del self._claims[release.coordination_id]
            
            session.current_claim = None
            
            self._emit_event(
                "coordination_released",
                release.coordination_id,
                release.owner_cell_id,
                release.coordination_type,
                {"reason": release.release_reason, "final_state": release.final_state}
            )
            
            return CoordinationResult(
                success=True,
                state=CoordinationState.RELEASED,
                message="Coordination released successfully",
                data={"coordination_id": release.coordination_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to release coordination: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.CLAIMED,
                message=f"Failed to release coordination: {e}"
            )
    
    def add_observation(self, observation: CoordinationObservation) -> CoordinationResult:
        """Add observation to coordination session"""
        try:
            session = self._sessions.get(observation.coordination_id) if observation.coordination_id else None
            
            # If no specific session, add to general observations
            if not session:
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Coordination session not found"
                )
            
            # Validate observation
            if not self._validate_observation(observation, session):
                return CoordinationResult(
                    success=False,
                    state=session.state,
                    message="Invalid observation"
                )
            
            # Add observation
            if len(session.observations) >= self.config.max_observations_per_session:
                return CoordinationResult(
                    success=False,
                    state=session.state,
                    message="Maximum observations reached"
                )
            
            session.observations.append(observation)
            session.updated_at = datetime.now(timezone.utc)
            
            self._emit_event(
                "observation_added",
                observation.coordination_id or "general",
                observation.observer_cell_id,
                CoordinationType.OBSERVATION_SHARING,
                {
                    "observation_type": observation.observation_type,
                    "confidence": observation.confidence_score,
                    "data_keys": list(observation.observed_data.keys())
                }
            )
            
            return CoordinationResult(
                success=True,
                state=session.state,
                message="Observation added successfully",
                data={"observation_id": observation.observation_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to add observation: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to add observation: {e}"
            )
    
    def broadcast_intent(self, intent: CoordinationIntentBroadcast) -> CoordinationResult:
        """Broadcast intent (non-binding)"""
        try:
            # Find relevant sessions or create general broadcast
            relevant_sessions = []
            if intent.target_cells:
                relevant_sessions = [s for s in self._sessions.values() 
                                  if any(cell in intent.target_cells for cell in s.participants)]
            
            # Validate intent
            if not self._validate_intent(intent):
                return CoordinationResult(
                    success=False,
                    state=CoordinationState.UNCLAIMED,
                    message="Invalid intent"
                )
            
            # Add to relevant sessions
            for session in relevant_sessions:
                if len(session.intents) >= self.config.max_intents_per_session:
                    continue
                
                session.intents.append(intent)
                session.updated_at = datetime.now(timezone.utc)
            
            self._emit_event(
                "intent_broadcast",
                "general",
                intent.broadcaster_cell_id,
                intent.coordination_type,
                {
                    "intent_type": intent.intent_type,
                    "target_cells": intent.target_cells,
                    "priority": intent.priority,
                    "valid_until": intent.valid_until.isoformat()
                }
            )
            
            return CoordinationResult(
                success=True,
                state=CoordinationState.UNCLAIMED,
                message="Intent broadcast successfully",
                data={"intent_id": intent.intent_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to broadcast intent: {e}")
            return CoordinationResult(
                success=False,
                state=CoordinationState.UNCLAIMED,
                message=f"Failed to broadcast intent: {e}"
            )
    
    def get_coordination_status(self, coordination_id: str) -> Optional[Dict[str, Any]]:
        """Get coordination status"""
        session = self._sessions.get(coordination_id)
        if not session:
            return None
        
        return {
            "coordination_id": session.coordination_id,
            "state": session.state,
            "coordinator_cell_id": session.coordinator_cell_id,
            "coordination_type": session.coordination_type,
            "participants": session.participants,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "expiration_timestamp": session.expiration_timestamp.isoformat(),
            "is_expired": session.is_expired(),
            "observation_count": len(session.observations),
            "intent_count": len(session.intents),
            "current_claim": session.current_claim.dict() if session.current_claim else None
        }
    
    def get_active_coordinations(self, cell_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active coordinations"""
        active_coordinations = []
        
        for session in self._sessions.values():
            if not session.is_expired() and session.state in [CoordinationState.UNCLAIMED, CoordinationState.CLAIMED]:
                if cell_id is None or cell_id in session.participants:
                    status = self.get_coordination_status(session.coordination_id)
                    if status:
                        active_coordinations.append(status)
        
        return active_coordinations
    
    def _validate_announcement(self, announcement: CoordinationAnnouncement) -> bool:
        """Validate announcement"""
        # Check expiration
        if announcement.expiration_timestamp <= datetime.now(timezone.utc):
            return False
        
        # Check duration limit
        max_duration = timedelta(hours=self.config.max_session_duration_hours)
        if announcement.expiration_timestamp - announcement.announced_at > max_duration:
            return False
        
        return True
    
    def _validate_claim(self, claim: CoordinationClaim, session: CoordinationSession) -> bool:
        """Validate claim"""
        # Check expiration
        if claim.expiration_timestamp <= datetime.now(timezone.utc):
            return False
        
        # Check session not expired
        if session.is_expired():
            return False
        
        # Check duration limit
        max_duration = timedelta(hours=self.config.max_claim_duration_hours)
        if claim.expiration_timestamp - claim.claimed_at > max_duration:
            return False
        
        # Check scope compatibility
        if session.scope.coordination_type != claim.coordination_type:
            return False
        
        return True
    
    def _validate_observation(self, observation: CoordinationObservation, session: CoordinationSession) -> bool:
        """Validate observation"""
        # Check session not expired
        if session.is_expired():
            return False
        
        # Check confidence bounds
        if not (0.0 <= observation.confidence_score <= 1.0):
            return False
        
        return True
    
    def _validate_intent(self, intent: CoordinationIntentBroadcast) -> bool:
        """Validate intent"""
        # Check validity period
        if intent.valid_until <= datetime.now(timezone.utc):
            return False
        
        # Check priority bounds
        if not (1 <= intent.priority <= 10):
            return False
        
        return True
    
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop cleanup task"""
        self._shutdown_event.set()
        if self._cleanup_task:
            await self._cleanup_task
        self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while not self._shutdown_event.is_set():
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now(timezone.utc)
        expired_sessions = []
        
        for coordination_id, session in self._sessions.items():
            if session.expiration_timestamp <= now:
                expired_sessions.append(coordination_id)
        
        for coordination_id in expired_sessions:
            session = self._sessions[coordination_id]
            session.state = CoordinationState.EXPIRED
            session.updated_at = now
            
            # Remove claim if exists
            if coordination_id in self._claims:
                del self._claims[coordination_id]
            
            session.current_claim = None
            
            self._emit_event(
                "coordination_expired",
                coordination_id,
                session.coordinator_cell_id,
                session.coordination_type,
                {"expired_at": now.isoformat()}
            )
            
            logger.info(f"Coordination {coordination_id} expired")
    
    def shutdown(self):
        """Shutdown state machine"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        self._sessions.clear()
        self._announcements.clear()
        self._claims.clear()
        self._event_handlers.clear()
