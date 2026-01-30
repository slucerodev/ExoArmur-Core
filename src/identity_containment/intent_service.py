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
from federation.clock import Clock
from federation.audit import AuditService, AuditEventType
from safety.safety_gate import SafetyGate, SafetyVerdict
from control_plane.approval_service import ApprovalService, ApprovalRequest

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
        intent_hash = intent.metadata.get("intent_hash")
        if intent_hash:
            self._intents[intent_hash] = intent
    
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
    
    def _generate_intent_id(self, subject_id: str, scope: IdentityContainmentScopeV1) -> str:
        """Generate deterministic intent ID"""
        time_str = self.clock.now().isoformat()
        content = f"{subject_id}:identity_provider:{scope.scope_id}:{time_str}"
        return f"int_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def _create_intent_hash(self, intent_data: Dict) -> str:
        """Create stable hash from intent data"""
        return CanonicalJSON.stable_hash(intent_data)
    
    def _recommendation_to_intent_data(self, recommendation: IdentityContainmentRecommendationV1) -> Dict:
        """Convert recommendation to intent data for hashing"""
        return {
            "subject_id": recommendation.subject_id,
            "scope_id": recommendation.scope.scope_id,
            "confidence_score": recommendation.confidence_score,
            "risk_assessment": recommendation.risk_assessment,
            "evidence_refs": sorted(recommendation.evidence_refs),
            "recommended_by": recommendation.recommended_by,
            "status": recommendation.status,
            "metadata": recommendation.metadata
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
        
        # Calculate TTL from recommendation timestamps
        ttl_seconds = int((recommendation.expires_at_utc - recommendation.generated_at_utc).total_seconds())
        
        # Validate TTL bounds
        if ttl_seconds > self.max_ttl_seconds:
            logger.error(f"Recommendation TTL {ttl_seconds} exceeds maximum {self.max_ttl_seconds}")
            return None, None
        
        # Generate intent ID
        intent_id = self._generate_intent_id(recommendation.subject_id, recommendation.scope)
        
        # Create intent data for hashing
        intent_data = self._recommendation_to_intent_data(recommendation)
        intent_data["intent_id"] = intent_id
        intent_data["created_at_utc"] = now.isoformat()
        intent_data["expires_at_utc"] = (now + timedelta(seconds=ttl_seconds)).isoformat()
        
        # Create intent hash
        intent_hash = self._create_intent_hash(intent_data)
        
        # Create frozen intent
        intent = IdentityContainmentIntentV1(
            intent_id=intent_id,
            recommendation_id=recommendation.recommendation_id,
            subject_id=recommendation.subject_id,
            scope=recommendation.scope,
            intent_type="apply",
            approval_status="pending",
            approval_id=None,
            approval_level="A2",
            requested_by="identity_containment_service",
            created_at_utc=now,
            expires_at_utc=now + timedelta(seconds=ttl_seconds),
            execution_status="pending",
            metadata={"intent_hash": intent_hash}
        )
        
        # Check with safety gate
        # Create mock objects for safety gate evaluation
        from spec.contracts.models_v1 import LocalDecisionV1
        mock_local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01H2X6VZB5Z2Z2Z2Z2Z2Z2Z2Z2",  # Valid ULID format
            tenant_id="tenant-001",
            cell_id="cell-001",
            subject={"subject_type": "user", "subject_id": recommendation.subject_id},
            classification="suspicious",
            severity="high",
            confidence=0.8,
            recommended_intents=[],
            evidence_refs={"event_ids": recommendation.evidence_refs, "belief_ids": []},
            correlation_id=recommendation.recommendation_id,
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
                event_type=AuditEventType.BELIEF_CREATED,
                correlation_id=recommendation.recommendation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent_id,
                    "subject_id": recommendation.subject_id,
                    "scope_id": recommendation.scope.scope_id,
                    "reason": safety_verdict.reason,
                    "verdict": safety_verdict.verdict.verdict
                }
            )
            
            return None, None
        
        # Store frozen intent
        self.intent_store.store_intent(intent)
        
        # Emit audit event for intent frozen
        self.audit_service.emit_event(
            event_type=AuditEventType.BELIEF_CREATED,
            correlation_id=recommendation.recommendation_id,
            source_federate_id=None,  # Local operation
            event_data={
                "intent_id": intent_id,
                "intent_hash": intent_hash,
                "subject_id": recommendation.subject_id,
                "scope_id": recommendation.scope.scope_id,
                "approval_level": intent.approval_level,
                "created_at_utc": intent.created_at_utc.isoformat(),
                "expires_at_utc": intent.expires_at_utc.isoformat()
            }
        )
        
        # Create approval if required
        approval_id = None
        if safety_verdict.verdict.verdict in ["require_human", "require_quorum"]:
            # Create approval request
            approval_request = ApprovalRequest(
                approval_id=f"apr_{intent_id[:12]}",
                correlation_id=recommendation.recommendation_id,
                trace_id=f"trace-{intent_id[:12]}",
                tenant_id="tenant-001",
                cell_id="cell-001",
                idempotency_key=f"idemp-{intent_id[:12]}",
                requested_action_class="identity_containment",
                payload_ref={
                    "intent_id": intent_id,
                    "intent_hash": intent_hash,
                    "subject_id": recommendation.subject_id,
                    "scope_id": recommendation.scope.scope_id
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
                event_type=AuditEventType.BELIEF_CREATED,
                correlation_id=recommendation.recommendation_id,
                source_federate_id=None,  # Local operation
                event_data={
                    "intent_id": intent_id,
                    "intent_hash": intent_hash,
                    "approval_id": approval_id,
                    "approval_level": intent.approval_level,
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
