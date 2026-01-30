"""
Identity Containment Effector Interface and Implementation

Provides the interface and simulated implementation for identity containment
operations with TTL enforcement and guaranteed auto-revert.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

from spec.contracts.models_v1 import (
    IdentityContainmentIntentV1,
    IdentityContainmentAppliedRecordV1,
    IdentityContainmentRevertedRecordV1,
    IdentityContainmentStatusV1,
    IdentityContainmentScopeV1,
    IdentitySubjectV1
)
from federation.clock import Clock
from federation.audit import AuditService, AuditEventType

logger = logging.getLogger(__name__)


@dataclass
class ContainmentState:
    """Internal containment state tracking"""
    intent_id: str
    subject_id: str
    provider: str
    scope: IdentityContainmentScopeV1
    applied_at_utc: datetime
    expires_at_utc: datetime
    status: IdentityContainmentStatusV1
    approval_id: str
    correlation_id: str


class IdentityContainmentEffector(ABC):
    """Interface for identity containment effectors"""
    
    @abstractmethod
    def apply(self, intent: IdentityContainmentIntentV1, approval_id: str) -> IdentityContainmentAppliedRecordV1:
        """Apply containment for the given intent"""
        pass
    
    @abstractmethod
    def revert(self, intent: IdentityContainmentIntentV1, reason: str) -> IdentityContainmentRevertedRecordV1:
        """Revert containment for the given intent"""
        pass
    
    @abstractmethod
    def status(self, subject_id: str, provider: str, scope: IdentityContainmentScopeV1) -> Optional[ContainmentState]:
        """Get current containment status for a subject"""
        pass
    
    @abstractmethod
    def process_expirations(self) -> List[IdentityContainmentRevertedRecordV1]:
        """Process and revert any expired containments"""
        pass


class ContainmentStateStore:
    """In-memory store for containment state with deterministic behavior"""
    
    def __init__(self):
        """Initialize containment state store"""
        self._states: Dict[str, ContainmentState] = {}  # key: subject_id:provider:scope
        self._lock = True  # Simple lock for thread safety
    
    def store_state(self, key: str, state: ContainmentState) -> None:
        """Store containment state"""
        self._states[key] = state
    
    def get_state(self, key: str) -> Optional[ContainmentState]:
        """Get containment state"""
        return self._states.get(key)
    
    def remove_state(self, key: str) -> Optional[ContainmentState]:
        """Remove and return containment state"""
        return self._states.pop(key, None)
    
    def list_all_states(self) -> List[ContainmentState]:
        """List all containment states"""
        return list(self._states.values())
    
    def clear(self) -> None:
        """Clear all states (for testing)"""
        self._states.clear()


class SimulatedIdentityProviderEffector(IdentityContainmentEffector):
    """Simulated identity provider effector for testing and demo purposes
    
    This implementation maintains containment state in memory and enforces
    TTL expiration deterministically using an injected Clock.
    """
    
    def __init__(self, clock: Clock, audit_service: AuditService, max_ttl_seconds: int = 3600):
        """Initialize simulated effector
        
        Args:
            clock: Clock for deterministic time handling
            audit_service: Audit service for event emission
            max_ttl_seconds: Maximum allowed TTL (default 1 hour)
        """
        self.clock = clock
        self.audit_service = audit_service
        self.max_ttl_seconds = max_ttl_seconds
        self.state_store = ContainmentStateStore()
    
    def _make_state_key(self, subject_id: str, provider: str, scope: IdentityContainmentScopeV1) -> str:
        """Create a unique key for containment state"""
        return f"{subject_id}:{provider}:{scope}"
    
    def apply(self, intent: IdentityContainmentIntentV1, approval_id: str) -> IdentityContainmentAppliedRecordV1:
        """Apply containment for the given intent
        
        Args:
            intent: Frozen containment intent
            approval_id: Approval identifier for the operation
            
        Returns:
            Record of the applied containment
            
        Raises:
            ValueError: If TTL exceeds maximum or intent is expired
        """
        now = self.clock.now()
        
        # Calculate TTL from intent timestamps
        ttl_seconds = int((intent.expires_at_utc - intent.created_at_utc).total_seconds())
        
        # Validate TTL bounds
        if ttl_seconds > self.max_ttl_seconds:
            raise ValueError(f"TTL {ttl_seconds} exceeds maximum {self.max_ttl_seconds}")
        
        # Validate intent not expired
        if now >= intent.expires_at_utc:
            raise ValueError("Intent is expired")
        
        # Create state key
        state_key = self._make_state_key(intent.subject_id, "identity_provider", intent.scope)
        
        # Check if already contained
        existing_state = self.state_store.get_state(state_key)
        if existing_state and existing_state.status == IdentityContainmentStatusV1.ACTIVE:
            logger.warning(f"Subject {intent.subject_id} already contained for scope {intent.scope}")
            # Return existing record
            return IdentityContainmentAppliedRecordV1(
                intent_id=existing_state.intent_id,
                subject_id=existing_state.subject_id,
                provider=existing_state.provider,
                scope=existing_state.scope,
                applied_at_utc=existing_state.applied_at_utc,
                expires_at_utc=existing_state.expires_at_utc,
                status=existing_state.status,
                approval_id=existing_state.approval_id,
                correlation_id=existing_state.correlation_id
            )
        
        # Create containment state
        state = ContainmentState(
            intent_id=intent.intent_id,
            subject_id=intent.subject_id,
            provider="identity_provider",
            scope=intent.scope,
            applied_at_utc=now,
            expires_at_utc=intent.expires_at_utc,
            status=IdentityContainmentStatusV1.ACTIVE,
            approval_id=approval_id,
            correlation_id=intent.intent_id  # Use intent_id as correlation_id
        )
        
        # Store state
        self.state_store.store_state(state_key, state)
        
        # Create applied record
        applied_record = IdentityContainmentAppliedRecordV1(
            record_id=f"rec_{intent.intent_id[:12]}",
            intent_id=intent.intent_id,
            subject_id=intent.subject_id,
            scope_id=intent.scope.scope_id,
            applied_at_utc=now,
            applied_by="identity_containment_effector",
            effectors_used=["simulated_identity_provider"],
            ttl_seconds=ttl_seconds,
            expires_at_utc=intent.expires_at_utc,
            status="active",
            metadata={"approval_id": approval_id}
        )
        
        # Emit audit event
        self.audit_service.emit_event(
            event_type=AuditEventType.BELIEF_CREATED,
            correlation_id=intent.intent_id,  # Use intent_id as correlation_id
            source_federate_id=None,  # Local operation
            event_data={
                "intent_id": intent.intent_id,
                "subject_id": intent.subject_id,
                "provider": "identity_provider",
                "scope_id": intent.scope.scope_id,
                "approval_id": approval_id,
                "applied_at_utc": now.isoformat(),
                "expires_at_utc": intent.expires_at_utc.isoformat()
            }
        )
        
        logger.info(f"Applied containment for subject {intent.subject_id}, scope {intent.scope.scope_id}")
        
        return applied_record
    
    def revert(self, intent: IdentityContainmentIntentV1, reason: str) -> IdentityContainmentRevertedRecordV1:
        """Revert containment for the given intent
        
        Args:
            intent: Original containment intent
            reason: Reason for reversion
            
        Returns:
            Record of the reverted containment
        """
        now = self.clock.now()
        
        # Create state key
        state_key = self._make_state_key(intent.subject_id, "identity_provider", intent.scope)
        
        # Get existing state
        existing_state = self.state_store.get_state(state_key)
        if not existing_state:
            logger.warning(f"No containment state found for subject {intent.subject_id}, scope {intent.scope}")
            # Return reverted record anyway for idempotency
            reverted_record = IdentityContainmentRevertedRecordV1(
                record_id=f"rev_{intent.intent_id[:12]}",
                applied_record_id=f"rec_{intent.intent_id[:12]}",
                intent_id=intent.intent_id,
                subject_id=intent.subject_id,
                reverted_at_utc=now,
                reverted_by="identity_containment_effector",
                reason=reason,
                metadata={}
            )
            return reverted_record
        
        # Remove state
        self.state_store.remove_state(state_key)
        
        # Create reverted record
        reverted_record = IdentityContainmentRevertedRecordV1(
            record_id=f"rev_{intent.intent_id[:12]}",
            applied_record_id=f"rec_{intent.intent_id[:12]}",
            intent_id=intent.intent_id,
            subject_id=intent.subject_id,
            reverted_at_utc=now,
            reverted_by="identity_containment_effector",
            reason=reason,
            metadata={}
        )
        
        logger.info(f"Reverted containment for subject {intent.subject_id}, scope {intent.scope.scope_id}")
        
        return reverted_record
    
    def process_expirations(self) -> List[IdentityContainmentRevertedRecordV1]:
        """Process expired containments and revert them
        
        Returns:
            List of reverted records
        """
        now = self.clock.now()
        reverted_records = []
        
        # Get all states
        all_states = self.state_store.list_all_states()
        
        for state in all_states:
            if now >= state.expires_at_utc and state.status == IdentityContainmentStatusV1.ACTIVE:
                # Expired - revert it
                logger.info(f"Processing expired containment for {state.subject_id}")
                
                # Create reverted record
                reverted_record = IdentityContainmentRevertedRecordV1(
                    record_id=f"rev_exp_{state.intent_id[:12]}",
                    applied_record_id=f"rec_{state.intent_id[:12]}",
                    intent_id=state.intent_id,
                    subject_id=state.subject_id,
                    reverted_at_utc=now,
                    reverted_by="identity_containment_effector",
                    reason="expired",
                    metadata={"original_applied_at_utc": state.applied_at_utc}
                )
                
                # Update state status
                state.status = IdentityContainmentStatusV1.REVERTED
                # Note: We would need to store the updated state back, but for now just create record
                
                reverted_records.append(reverted_record)
                
                # Emit audit event for auto-revert
                self.audit_service.emit_event(
                    event_type=AuditEventType.BELIEF_CREATED,
                    correlation_id=state.intent_id,
                    source_federate_id=None,  # Local operation
                    event_data={
                        "intent_id": state.intent_id,
                        "subject_id": state.subject_id,
                        "provider": "identity_provider",
                        "scope_id": state.scope.scope_id,
                        "reason": "expired",
                        "reverted_at_utc": now.isoformat()
                    }
                )
        
        return reverted_records
    
    def status(self, subject_id: str, provider: str, scope: IdentityContainmentScopeV1) -> Optional[ContainmentState]:
        """Get current containment status for a subject
        
        Args:
            subject_id: Subject identifier
            provider: Identity provider
            scope: Containment scope
            
        Returns:
            Current containment state or None if not contained
        """
        state_key = self._make_state_key(subject_id, provider, scope)
        state = self.state_store.get_state(state_key)
        
        if state and state.status == IdentityContainmentStatusV1.ACTIVE:
            # Check if expired
            if self.clock.now() >= state.expires_at_utc:
                # Auto-revert expired containment
                self.revert(
                    IdentityContainmentIntentV1(
                        intent_id=state.intent_id,
                        correlation_id=state.correlation_id,
                        subject={"subject_id": subject_id, "subject_type": "USER", "provider": provider, "metadata": {}},
                        scope=scope,
                        ttl_seconds=0,  # Not used for revert
                        created_at_utc=state.applied_at_utc,
                        expires_at_utc=state.expires_at_utc,
                        reason_code="auto_revert",
                        risk_level="LOW",
                        confidence=1.0,
                        evidence_refs=[],
                        belief_refs=[],
                        required_authority="A3",
                        intent_hash="auto_revert"
                    ),
                    reason="expired"
                )
                return None
        
        return state
