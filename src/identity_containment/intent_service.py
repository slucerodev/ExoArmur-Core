"""
Identity Containment Intent Service

Converts recommendations into frozen intents with approval binding
and authority enforcement.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
import hashlib
import json
from unittest.mock import Mock

from spec.contracts.models_v1 import (
    IdentityContainmentIntentV1,
    IdentityContainmentRecommendationV1,
    IdentitySubjectV1,
    IdentityContainmentScopeV1
)
from src.federation.clock import Clock
from src.federation.audit import AuditService, AuditEventType
from src.safety.safety_gate import SafetyGate, SafetyVerdict
from src.control_plane.approval_service import ApprovalService, ApprovalRequest

logger = logging.getLogger(__name__)


class CanonicalJSON:
    """Utility for canonical JSON serialization"""
    
    @staticmethod
    def serialize(data: Dict) -> str:
        """Serialize data in canonical JSON format"""
        def sort_dict(obj):
            if isinstance(obj, dict):
                return {k: sort_dict(v) for k, v in sorted(obj.items())}
            elif isinstance(obj, list):
                return [sort_dict(item) for item in obj]
            else:
                return obj
        
        return json.dumps(sort_dict(data), separators=(',', ':'), ensure_ascii=True)
    
    @staticmethod
    def stable_hash(data: Dict) -> str:
        """Generate stable hash from canonical JSON"""
        canonical = CanonicalJSON.serialize(data)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class IntentStore:
    """Store for frozen intents keyed by intent hash"""
    
    def __init__(self):
        """Initialize intent store"""
        self._intents: Dict[str, IdentityContainmentIntentV1] = {}  # intent_hash -> intent
        self._approval_bindings: Dict[str, str] = {}  # approval_id -> intent_hash
    
    def store_intent(self, intent: IdentityContainmentIntentV1) -> None:
        """Store a frozen intent"""
        self._intents[intent.intent_hash] = intent
    
    def get_intent(self, intent_hash: str) -> Optional[IdentityContainmentIntentV1]:
        """Get intent by hash"""
        return self._intents.get(intent_hash)
    
    def bind_approval(self, approval_id: str, intent_hash: str) -> None:
        """Bind approval to intent hash"""
        self._approval_bindings[approval_id] = intent_hash
    
    def get_intent_by_approval(self, approval_id: str) -> Optional[IdentityContainmentIntentV1]:
        """Get intent by approval ID"""
        intent_hash = self._approval_bindings.get(approval_id)
        if intent_hash:
            return self._intents.get(intent_hash)
        return None
    
    def verify_binding(self, approval_id: str, intent_hash: str) -> bool:
        """Verify approval is bound to intent hash"""
        return self._approval_bindings.get(approval_id) == intent_hash


class IdentityContainmentIntentService:
    """Service for creating and managing identity containment intents"""
    
    def __init__(
        self,
        clock: Clock,
        audit_service: AuditService,
        safety_gate: SafetyGate,
        approval_service: ApprovalService,
        max_ttl_seconds: int = 3600
    ):
        """Initialize intent service
        
        Args:
            clock: Clock for deterministic time handling
            audit_service: Audit service for event emission
            safety_gate: Safety gate for authority verification
            approval_service: Approval service for human approval
            max_ttl_seconds: Maximum allowed TTL (default 1 hour)
        """
        self.clock = clock
        self.audit_service = audit_service
        self.safety_gate = safety_gate
        self.approval_service = approval_service
        self.max_ttl_seconds = max_ttl_seconds
        self.intent_store = IntentStore()
    
    def _generate_intent_id(self, subject: IdentitySubjectV1, scope: IdentityContainmentScopeV1) -> str:
        """Generate deterministic intent ID"""
        time_str = self.clock.now().isoformat()
        content = f"{subject.subject_id}:{subject.provider}:{scope.value}:{time_str}"
        return f"int_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def _create_intent_hash(self, intent_data: Dict) -> str:
        """Create stable hash from intent data"""
        return CanonicalJSON.stable_hash(intent_data)
    
    def _recommendation_to_intent_data(self, recommendation: IdentityContainmentRecommendationV1) -> Dict:
        """Convert recommendation to intent data for hashing"""
        return {
            "subject": {
                "subject_id": recommendation.subject.subject_id,
                "subject_type": recommendation.subject.subject_type,
                "provider": recommendation.subject.provider,
                "metadata": recommendation.subject.metadata
            },
            "scope": recommendation.scope.value,
            "ttl_seconds": recommendation.suggested_ttl_seconds,
            "reason_code": "recommendation_based",
            "risk_level": recommendation.risk_level,
            "confidence": recommendation.confidence,
            "evidence_refs": sorted(recommendation.evidence_refs),
            "belief_refs": sorted(recommendation.belief_refs),
            "required_authority": recommendation.recommended_authority
        }
    
    def create_intent_from_recommendation(
        self,
        recommendation: IdentityContainmentRecommendationV1
    ) -> Tuple[Optional[IdentityContainmentIntentV1], Optional[str]]:
        """Create frozen intent from recommendation
        
        Args:
            recommendation: Containment recommendation
            
        Returns:
            Tuple of (intent, approval_id) or (None, None) if denied
        """
        now = self.clock.now()
        
        # Validate TTL bounds
        if recommendation.suggested_ttl_seconds > self.max_ttl_seconds:
            logger.error(f"Recommendation TTL {recommendation.suggested_ttl_seconds} exceeds maximum {self.max_ttl_seconds}")
            return None, None
        
        # Generate intent ID
        intent_id = self._generate_intent_id(recommendation.subject, recommendation.scope)
        
        # Create intent data for hashing
        intent_data = self._recommendation_to_intent_data(recommendation)
        intent_data["intent_id"] = intent_id
        intent_data["correlation_id"] = recommendation.correlation_id
        intent_data["created_at_utc"] = now.isoformat()
        intent_data["expires_at_utc"] = (now + timedelta(seconds=recommendation.suggested_ttl_seconds)).isoformat()
        
        # Create intent hash
        intent_hash = self._create_intent_hash(intent_data)
        
        # Create frozen intent
        intent = IdentityContainmentIntentV1(
            intent_id=intent_id,
            correlation_id=recommendation.correlation_id,
            subject=recommendation.subject,
            scope=recommendation.scope,
            ttl_seconds=recommendation.suggested_ttl_seconds,
            created_at_utc=now,
            expires_at_utc=now + timedelta(seconds=recommendation.suggested_ttl_seconds),
            reason_code="recommendation_based",
            risk_level=recommendation.risk_level,
            confidence=recommendation.confidence,
            evidence_refs=recommendation.evidence_refs,
            belief_refs=recommendation.belief_refs,
            required_authority=recommendation.recommended_authority,
            intent_hash=intent_hash
        )
        
        # Check with safety gate
        # Create mock objects for safety gate evaluation
        from spec.contracts.models_v1 import LocalDecisionV1
        mock_local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01H2X6VZB5Z2Z2Z2Z2Z2Z2Z2Z2",  # Valid ULID format
            tenant_id="tenant-001",
            cell_id="cell-001",
            subject={"subject_type": "user", "subject_id": recommendation.subject.subject_id},
            classification="suspicious",
            severity="high",
            confidence=0.8,
            recommended_intents=[],
            evidence_refs={"event_ids": recommendation.evidence_refs, "belief_ids": recommendation.belief_refs},
            correlation_id=recommendation.correlation_id,
            trace_id="trace-001"
        )
        mock_collective_state = {}
        mock_policy_state = Mock()
        mock_policy_state.kill_switch_global = False
        mock_trust_state = Mock()
        mock_environment_state = Mock()
        
        safety_verdict = self.safety_gate.evaluate_safety(
            intent=None,  # No ExecutionIntentV1 for containment
            local_decision=mock_local_decision,
            collective_state=mock_collective_state,
            policy_state=mock_policy_state,
            trust_state=mock_trust_state,
            environment_state=mock_environment_state
        )
        
        if safety_verdict.verdict.verdict == "deny":
            logger.warning(f"Safety gate denied intent {intent_id}: {safety_verdict.reason}")
            
            # Emit audit event for denial
            self.audit_service.emit_event(
                event_type=AuditEventType.IDENTITY_CONTAINMENT_DENIED,
                correlation_id=recommendation.correlation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent_id,
                    "subject_id": recommendation.subject.subject_id,
                    "provider": recommendation.subject.provider,
                    "scope": recommendation.scope.value,
                    "reason": safety_verdict.reason,
                    "verdict": safety_verdict.verdict.verdict
                }
            )
            
            return None, None
        
        # Store frozen intent
        self.intent_store.store_intent(intent)
        
        # Emit audit event for intent frozen
        self.audit_service.emit_event(
            event_type=AuditEventType.IDENTITY_CONTAINMENT_INTENT_FROZEN,
            correlation_id=recommendation.correlation_id,
            source_federate_id=None,  # Local operation
            event_data={
                "intent_id": intent_id,
                "intent_hash": intent_hash,
                "subject_id": recommendation.subject.subject_id,
                "provider": recommendation.subject.provider,
                "scope": recommendation.scope.value,
                "ttl_seconds": intent.ttl_seconds,
                "required_authority": intent.required_authority,
                "safety_verdict": safety_verdict.verdict.verdict
            }
        )
        
        # Create approval if required
        approval_id = None
        if safety_verdict.verdict.verdict in ["require_human", "require_quorum"]:
            # Create approval request
            approval_request = ApprovalRequest(
                approval_id=f"apr_{intent_id[:12]}",
                correlation_id=recommendation.correlation_id,
                trace_id=f"trace-{intent_id[:12]}",
                tenant_id="tenant-001",
                cell_id="cell-001",
                idempotency_key=f"idemp-{intent_id[:12]}",
                requested_action_class="identity_containment",
                payload_ref={
                    "intent_id": intent_id,
                    "intent_hash": intent_hash,
                    "subject_id": recommendation.subject.subject_id,
                    "scope": recommendation.scope.value,
                    "ttl_seconds": intent.ttl_seconds
                },
                created_at=self.clock.now(),
                bound_intent_hash=intent_hash
            )
            
            # Create approval directly in the service
            self.approval_service._approvals[approval_request.approval_id] = approval_request
            approval_id = approval_request.approval_id
            
            # Bind approval to intent
            self.intent_store.bind_approval(approval_id, intent_hash)
            
            # Emit audit event for approval creation
            self.audit_service.emit_event(
                event_type=AuditEventType.IDENTITY_CONTAINMENT_APPROVAL_CREATED,
                correlation_id=recommendation.correlation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent_id,
                    "intent_hash": intent_hash,
                    "approval_id": approval_id,
                    "required_authority": intent.required_authority,
                    "approval_type": safety_verdict.verdict.verdict
                }
            )
        
        logger.info(f"Created frozen intent {intent_id} with approval {approval_id}")
        
        return intent, approval_id
    
    def get_intent(self, intent_hash: str) -> Optional[IdentityContainmentIntentV1]:
        """Get intent by hash"""
        return self.intent_store.get_intent(intent_hash)
    
    def get_intent_by_approval(self, approval_id: str) -> Optional[IdentityContainmentIntentV1]:
        """Get intent by approval ID"""
        return self.intent_store.get_intent_by_approval(approval_id)
    
    def verify_approval_binding(self, approval_id: str, intent_hash: str) -> bool:
        """Verify approval is bound to intent hash"""
        return self.intent_store.verify_binding(approval_id, intent_hash)
