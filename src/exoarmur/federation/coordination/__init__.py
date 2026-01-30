"""
# PHASE 2B — LOCKED
# Coordination logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Coordination Module
"""

from .coordination_models_v2 import (
    CoordinationType,
    CoordinationState,
    CoordinationRole,
    CoordinationScope,
    CoordinationAnnouncement,
    CoordinationClaim,
    CoordinationRelease,
    CoordinationObservation,
    CoordinationIntentBroadcast,
    CoordinationEvent,
    CoordinationSession
)

from .coordination_state_machine import (
    CoordinationStateMachine,
    CoordinationConfig,
    CoordinationResult
)

from .coordination_audit_emitter import CoordinationAuditEmitter

from .federation_coordination_manager import FederationCoordinationManager

__all__ = [
    # Models
    "CoordinationType",
    "CoordinationState", 
    "CoordinationRole",
    "CoordinationScope",
    "CoordinationAnnouncement",
    "CoordinationClaim",
    "CoordinationRelease",
    "CoordinationObservation",
    "CoordinationIntentBroadcast",
    "CoordinationEvent",
    "CoordinationSession",
    
    # State Machine
    "CoordinationStateMachine",
    "CoordinationConfig",
    "CoordinationResult",
    
    # Audit
    "CoordinationAuditEmitter",
    
    # Manager
    "FederationCoordinationManager"
]
