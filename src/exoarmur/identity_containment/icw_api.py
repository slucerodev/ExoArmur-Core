"""
Identity Containment Window (ICW) API - V2 Feature-Flagged Endpoints
Minimal endpoints for ICW operations with feature flag protection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Depends, Query
from pydantic import BaseModel

from exoarmur.federation.clock import Clock, FixedClock
from exoarmur.federation.audit import AuditService
from exoarmur.identity_containment.recommender import IdentityContainmentRecommender
from exoarmur.identity_containment.intent_service import IdentityContainmentIntentService
from exoarmur.feature_flags.resolver import load_v2_core_types, load_v2_entry_gate
from exoarmur.identity_containment.execution import IdentityContainmentExecutor
from exoarmur.identity_containment.effector import SimulatedIdentityProviderEffector
from exoarmur.control_plane.approval_service import ApprovalService
from exoarmur.control_plane.intent_store import IntentStore

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
        """Process expirations through V2 Entry Gate - ONLY ALLOWED PATH"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Create V2 ExecutionRequest for tick-based expiration processing
            v2_entry_gate = load_v2_entry_gate()
            v2_core_types = load_v2_core_types()
            
            execution_request = v2_entry_gate.ExecutionRequest(
                module_id=v2_core_types.ModuleID("icw_tick_expiration"),
                execution_context=v2_core_types.ModuleExecutionContext(
                    execution_id=v2_core_types.ExecutionID("tick_processing" + "0" * 8),
                    module_id=v2_core_types.ModuleID("icw_tick_expiration"),
                    module_version=v2_core_types.ModuleVersion(1, 0, 0),
                    deterministic_seed=v2_core_types.DeterministicSeed(hash("tick_expiration") % (2**63)),
                    logical_timestamp=int(datetime.now(timezone.utc).timestamp()),
                    dependency_hash="icw_tick"
                ),
                action_data={
                    'action_class': 'identity_containment',
                    'action_type': 'tick_expiration',
                    'subject': 'system',
                    'parameters': {'tick_based': True}
                },
                correlation_id="tick_system"
            )

            # Execute through V2 Entry Gate - ONLY ALLOWED PATH
            result = v2_entry_gate.execute_module(execution_request)
            
            if not result.success:
                logger.error(f"V2 Entry Gate blocked tick expiration: {result.error}")
                return TickResponse(
                    processed_count=0,
                    reverted_records=[],
                    v2_enforced=True,
                    v2_execution_id=result.execution_id,
                    v2_error=result.error
                )
            
            # Process expirations through effector (only after V2 validation)
            reverted_records = self.effector.process_expirations()
            
            return TickResponse(
                processed_count=len(reverted_records),
                reverted_records=[
                    {
                        "reverted_record": {
                            "intent_id": r.intent_id,
                            "subject_id": r.subject_id,
                            "provider": r.provider,
                            "scope": r.scope.value,
                            "reverted_at": r.reverted_at_utc.isoformat(),
                            "reversion_reason": r.reversion_reason
                        },
                        "reason": "expired"
                    }
                    for r in reverted_records
                ],
                v2_enforced=True,
                v2_execution_id=result.execution_id,
                v2_audit_trail=result.audit_trail_id
            )
            
        except Exception as e:
            logger.error(f"Failed to process expirations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_approval(self, approval_id: str) -> Dict[str, Any]:
        """Execute containment with approval through V2 Entry Gate - SINGLE MANDATORY PATH"""
        self._check_feature_flag()
        self._ensure_components()
        
        try:
            # Create V2 ExecutionRequest for containment execution
            v2_entry_gate = load_v2_entry_gate()
            v2_core_types = load_v2_core_types()
            
            execution_request = v2_entry_gate.ExecutionRequest(
                module_id=v2_core_types.ModuleID("icw_containment_executor"),
                execution_context=v2_core_types.ModuleExecutionContext(
                    execution_id=v2_core_types.ExecutionID(approval_id[:26] + "0" * (26 - len(approval_id[:26]))),
                    module_id=v2_core_types.ModuleID("icw_containment_executor"),
                    module_version=v2_core_types.ModuleVersion(1, 0, 0),
                    deterministic_seed=v2_core_types.DeterministicSeed(hash(approval_id) % (2**63)),
                    logical_timestamp=int(datetime.now().timestamp()),
                    dependency_hash="icw_execution"
                ),
                action_data={
                    'action_class': 'identity_containment',
                    'action_type': 'execute_approval',
                    'subject': 'containment_approval',
                    'parameters': {'approval_id': approval_id}
                },
                correlation_id=approval_id
            )

            # Execute through V2 Entry Gate - ONLY ALLOWED PATH
            result = v2_entry_gate.execute_module(execution_request)
            
            if not result.success:
                raise HTTPException(
                    status_code=403,
                    detail=f"V2 Entry Gate execution blocked: {result.error}"
                )
            
            # Return result from V2 execution only
            return {
                "success": True,
                "intent_id": result.result_data.get('intent_id', 'unknown'),
                "subject_id": result.result_data.get('subject_id', 'unknown'),
                "provider": result.result_data.get('provider', 'unknown'),
                "scope": result.result_data.get('scope', 'unknown'),
                "applied_at": result.result_data.get('applied_at', datetime.now(timezone.utc).isoformat()),
                "expires_at": result.result_data.get('expires_at', ''),
                "approval_id": approval_id,
                "v2_enforced": True,
                "v2_execution_id": result.execution_id,
                "v2_audit_trail": result.audit_trail_id
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
