"""
Identity Containment Window (ICW) API - V2 Feature-Flagged Endpoints
Minimal endpoints for ICW operations with feature flag protection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Depends, Query
from pydantic import BaseModel

from federation.clock import Clock, FixedClock
from federation.audit import AuditService
from identity_containment.recommender import IdentityContainmentRecommender
from identity_containment.intent_service import IdentityContainmentIntentService
from identity_containment.execution import IdentityContainmentExecutor
from identity_containment.effector import SimulatedIdentityProviderEffector
from control_plane.approval_service import ApprovalService
from control_plane.intent_store import IntentStore

from spec.contracts.models_v1 import (
    IdentitySubjectV1,
    IdentityContainmentRecommendationV1,
    IdentityContainmentIntentV1,
    IdentityContainmentScopeV1
)

logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses
class ContainmentStatusResponse(BaseModel):
    """Response for containment status query"""
    subject_id: str
    provider: str
    scope: str
    status: str  # "not_contained", "contained", "expired"
    applied_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    approval_id: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Request for containment recommendation"""
    subject_id: str
    provider: str
    scope: IdentityContainmentScopeV1


class RecommendationResponse(BaseModel):
    """Response for containment recommendation"""
    recommendation_id: str
    subject_id: str
    provider: str
    scope: str
    suggested_ttl_seconds: int
    risk_level: str
    confidence: float
    evidence_refs: List[str]
    belief_refs: List[str]


class IntentFromRecommendationRequest(BaseModel):
    """Request to create intent from recommendation"""
    recommendation_id: str


class IntentFromRecommendationResponse(BaseModel):
    """Response for intent creation from recommendation"""
    intent_id: str
    intent_hash: str
    approval_id: str
    correlation_id: str
    ttl_seconds: int
    expires_at: datetime


class IntentResponse(BaseModel):
    """Response for intent query"""
    intent_id: str
    correlation_id: str
    subject_id: str
    provider: str
    scope: str
    ttl_seconds: int
    created_at: datetime
    expires_at: datetime
    intent_hash: str
    approval_id: str


class TickResponse(BaseModel):
    """Response for tick operation"""
    processed_count: int
    reverted_records: List[Dict[str, Any]]


class IdentityContainmentAPI:
    """ICW API endpoints with feature flag protection"""
    
    def __init__(self, 
                 feature_flag_enabled: bool = False,
                 clock: Optional[Clock] = None,
                 audit_service: Optional[AuditService] = None,
                 recommender: Optional[IdentityContainmentRecommender] = None,
                 intent_service: Optional[IdentityContainmentIntentService] = None,
                 executor: Optional[IdentityContainmentExecutor] = None,
                 effector: Optional[SimulatedIdentityProviderEffector] = None,
                 approval_service: Optional[ApprovalService] = None,
                 intent_store: Optional[IntentStore] = None):
        """
        Initialize ICW API
        
        Args:
            feature_flag_enabled: Whether ICW feature is enabled
            clock: Clock for deterministic operations
            audit_service: Audit service for event emission
            recommender: ICW recommendation engine
            intent_service: ICW intent service
            executor: ICW execution service
            effector: ICW effector for apply/revert
            approval_service: Approval service for intent approval
            intent_store: Intent store for frozen intents
        """
        self.feature_flag_enabled = feature_flag_enabled
        self.clock = clock or FixedClock()
        self.audit_service = audit_service
        self.recommender = recommender
        self.intent_service = intent_service
        self.executor = executor
        self.effector = effector
        self.approval_service = approval_service
        self.intent_store = intent_store
        
        logger.info(f"ICW API initialized with feature_flag_enabled={feature_flag_enabled}")
    
    def _check_feature_flag(self):
        """Check if ICW feature flag is enabled"""
        if not self.feature_flag_enabled:
            raise HTTPException(
                status_code=404,
                detail="Identity Containment Window feature is not enabled"
            )
    
    def _ensure_components(self):
        """Ensure required components are initialized"""
        if not all([self.recommender, self.intent_service, self.executor, 
                   self.effector, self.approval_service, self.intent_store]):
            raise HTTPException(
                status_code=503,
                detail="ICW services not properly initialized"
            )
    
    async def get_containment_status(self, 
                                   subject_id: str = Query(...),
                                   provider: str = Query(...)) -> ContainmentStatusResponse:
        """Get containment status for a subject"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Check effector for containment state
            state_key = self.effector._make_state_key(subject_id, provider, IdentityContainmentScopeV1.SESSIONS)
            state = self.effector.state_store.get_state(state_key)
            
            if state and state.status.value == "active":
                return ContainmentStatusResponse(
                    subject_id=subject_id,
                    provider=provider,
                    scope="sessions",
                    status="contained",
                    applied_at=state.applied_at_utc,
                    expires_at=state.expires_at_utc,
                    approval_id=state.approval_id
                )
            else:
                return ContainmentStatusResponse(
                    subject_id=subject_id,
                    provider=provider,
                    scope="sessions",
                    status="not_contained"
                )
                
        except Exception as e:
            logger.error(f"Failed to get containment status for {subject_id}@{provider}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_recommendation(self, request: RecommendationRequest) -> RecommendationResponse:
        """Generate containment recommendation"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Create subject
            subject = IdentitySubjectV1(
                subject_id=request.subject_id,
                subject_type="USER",
                provider=request.provider,
                metadata={}
            )
            
            # Generate recommendation
            recommendations = self.recommender.generate_recommendations([subject])
            
            if not recommendations:
                raise HTTPException(
                    status_code=404,
                    detail="No recommendation generated for subject"
                )
            
            recommendation = recommendations[0]
            
            return RecommendationResponse(
                recommendation_id=recommendation.recommendation_id,
                subject_id=recommendation.subject.subject_id,
                provider=recommendation.subject.provider,
                scope=recommendation.scope.value,
                suggested_ttl_seconds=recommendation.suggested_ttl_seconds,
                risk_level=recommendation.risk_level,
                confidence=recommendation.confidence,
                evidence_refs=recommendation.evidence_refs,
                belief_refs=recommendation.belief_refs
            )
            
        except Exception as e:
            logger.error(f"Failed to generate recommendation for {request.subject_id}@{request.provider}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_intent_from_recommendation(self, request: IntentFromRecommendationRequest) -> IntentFromRecommendationResponse:
        """Freeze intent from recommendation and create approval"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Get recommendation (in real implementation, would fetch from store)
            # For now, create a mock recommendation
            recommendation = IdentityContainmentRecommendationV1(
                recommendation_id=request.recommendation_id,
                correlation_id=f"rec-{request.recommendation_id}",
                subject=IdentitySubjectV1(
                    subject_id="mock_user",
                    subject_type="USER",
                    provider="okta",
                    metadata={}
                ),
                scope=IdentityContainmentScopeV1.SESSIONS,
                suggested_ttl_seconds=1800,
                confidence=0.9,
                risk_level="HIGH",
                summary="Mock recommendation",
                evidence_refs=[],
                belief_refs=[],
                recommended_authority="A3"
            )
            
            # Create intent and approval
            intent, approval_id = self.intent_service.create_intent_from_recommendation(recommendation)
            
            return IntentFromRecommendationResponse(
                intent_id=intent.intent_id,
                intent_hash=intent.intent_hash,
                approval_id=approval_id,
                correlation_id=intent.correlation_id,
                ttl_seconds=intent.ttl_seconds,
                expires_at=intent.expires_at_utc
            )
            
        except Exception as e:
            logger.error(f"Failed to create intent from recommendation {request.recommendation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_intent(self, intent_id: str) -> IntentResponse:
        """Get intent details"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            intent = self.intent_service.get_intent(intent_id)
            if not intent:
                raise HTTPException(status_code=404, detail="Intent not found")
            
            return IntentResponse(
                intent_id=intent.intent_id,
                correlation_id=intent.correlation_id,
                subject_id=intent.subject.subject_id,
                provider=intent.subject.provider,
                scope=intent.scope.value,
                ttl_seconds=intent.ttl_seconds,
                created_at=intent.created_at_utc,
                expires_at=intent.expires_at_utc,
                intent_hash=intent.intent_hash,
                approval_id=""  # Would need to look up from intent store
            )
            
        except Exception as e:
            logger.error(f"Failed to get intent {intent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def tick(self) -> TickResponse:
        """Process expirations (admin/test only)"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Process expirations
            reverted_records = self.effector.process_expirations()
            
            return TickResponse(
                processed_count=len(reverted_records),
                reverted_records=[
                    {
                        "intent_id": r.intent_id,
                        "subject_id": r.subject_id,
                        "provider": r.provider,
                        "reason": r.reason,
                        "reverted_at": r.reverted_at_utc.isoformat()
                    }
                    for r in reverted_records
                ]
            )
            
        except Exception as e:
            logger.error(f"Failed to process expirations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_approval(self, approval_id: str) -> Dict[str, Any]:
        """Execute containment with approval"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Execute containment apply
            result = self.executor.execute_containment_apply(approval_id)
            
            if result is None:
                raise HTTPException(
                    status_code=403,
                    detail="Execution blocked - approval not found or not approved"
                )
            
            return {
                "success": True,
                "intent_id": result.intent_id,
                "subject_id": result.subject_id,
                "provider": result.provider,
                "scope": result.scope.value,
                "applied_at": result.applied_at_utc.isoformat(),
                "expires_at": result.expires_at_utc.isoformat(),
                "approval_id": result.approval_id
            }
            
        except Exception as e:
            logger.error(f"Failed to execute containment with approval {approval_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# Global ICW API instance (will be initialized in main.py)
icw_api: Optional[IdentityContainmentAPI] = None


def get_icw_api() -> IdentityContainmentAPI:
    """Get ICW API instance"""
    # This function will be overridden in main.py to return the global instance
    raise HTTPException(status_code=503, detail="ICW API not initialized")
