"""
Identity Containment Recommendation Engine

Generates deterministic recommendations for identity containment
based on observations and beliefs.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import hashlib
import json


def create_sessions_scope():
    """Create a sessions scope for containment"""
    return IdentityContainmentScopeV1(
        scope_id="scope-sessions-001",
        scope_type="sessions",
        severity_level="medium",
        ttl_seconds=1800,
        auto_expire=True,
        requires_approval=True,
        approval_level="A2",
        effectors=["identity_provider"],
        conditions={"min_risk_score": 0.7}
    )


def create_login_scope():
    """Create a login scope for containment"""
    return IdentityContainmentScopeV1(
        scope_id="scope-login-001",
        scope_type="login",
        severity_level="high",
        ttl_seconds=900,
        auto_expire=True,
        requires_approval=True,
        approval_level="A2",
        effectors=["identity_provider"],
        conditions={"min_risk_score": 0.8}
    )


def create_api_access_scope():
    """Create an API access scope for containment"""
    return IdentityContainmentScopeV1(
        scope_id="scope-api-access-001",
        scope_type="api_access",
        severity_level="high",
        ttl_seconds=1200,
        auto_expire=True,
        requires_approval=True,
        approval_level="A2",
        effectors=["api_gateway"],
        conditions={"min_risk_score": 0.8}
    )


def create_token_issuance_scope():
    """Create a token issuance scope for containment"""
    return IdentityContainmentScopeV1(
        scope_id="scope-token-issuance-001",
        scope_type="token_issuance",
        severity_level="high",
        ttl_seconds=900,
        auto_expire=True,
        requires_approval=True,
        approval_level="A2",
        effectors=["token_service"],
        conditions={"min_risk_score": 0.85}
    )

from spec.contracts.models_v1 import (
    IdentitySubjectV1,
    IdentityContainmentScopeV1,
    IdentityContainmentRecommendationV1,
    ObservationV1,
    BeliefV1,
    ObservationType,
    ThreatIntelPayloadV1,
    AnomalyDetectionPayloadV1,
    SystemHealthPayloadV1
)
from federation.observation_store import ObservationStore
from federation.clock import Clock
from federation.audit import AuditService, AuditEventType

logger = logging.getLogger(__name__)


@dataclass
class ContainmentRule:
    """Rule for containment recommendation"""
    name: str
    condition: str
    scope: IdentityContainmentScopeV1
    ttl_seconds: int
    risk_level: str
    confidence: float
    authority: str = "A3"


class IdentityContainmentRecommender:
    """Generates identity containment recommendations from observations and beliefs"""
    
    def __init__(
        self,
        observation_store: ObservationStore,
        clock: Clock,
        audit_service: AuditService,
        max_ttl_seconds: int = 3600
    ):
        """Initialize recommender
        
        Args:
            observation_store: Store for observations and beliefs
            clock: Clock for deterministic time handling
            audit_service: Audit service for event emission
            max_ttl_seconds: Maximum TTL for recommendations (default 1 hour)
        """
        self.observation_store = observation_store
        self.clock = clock
        self.audit_service = audit_service
        self.max_ttl_seconds = max_ttl_seconds
        
        # Define deterministic containment rules
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[ContainmentRule]:
        """Initialize deterministic containment rules"""
        return [
            # High confidence threat intelligence
            ContainmentRule(
                name="threat_intel_high_confidence",
                condition="threat_intel_confidence >= 0.9",
                scope=create_sessions_scope(),
                ttl_seconds=1800,  # 30 minutes
                risk_level="CRITICAL",
                confidence=0.95
            ),
            
            # Impossible travel anomaly
            ContainmentRule(
                name="impossible_travel",
                condition="impossible_travel_score >= 0.8",
                scope=create_login_scope(),
                ttl_seconds=900,  # 15 minutes
                risk_level="HIGH",
                confidence=0.85
            ),
            
            # Repeated authentication failures
            ContainmentRule(
                name="repeated_auth_failures",
                condition="auth_failure_count >= 5 AND time_window_minutes <= 15",
                scope=create_login_scope(),
                ttl_seconds=600,  # 10 minutes
                risk_level="MEDIUM",
                confidence=0.75
            ),
            
            # System health compromise indicators
            ContainmentRule(
                name="system_compromise_indicators",
                condition="compromise_indicators_count >= 3",
                scope=create_api_access_scope(),
                ttl_seconds=1200,  # 20 minutes
                risk_level="HIGH",
                confidence=0.8
            ),
            
            # Anomaly detection high risk
            ContainmentRule(
                name="anomaly_high_risk",
                condition="anomaly_risk_score >= 0.85",
                scope=create_token_issuance_scope(),
                ttl_seconds=900,  # 15 minutes
                risk_level="HIGH",
                confidence=0.8
            )
        ]
    
    def _evaluate_rule_condition(self, rule: ContainmentRule, observations: List[ObservationV1], beliefs: List[BeliefV1]) -> bool:
        """Evaluate if a rule condition is met"""
        if rule.condition == "threat_intel_confidence >= 0.9":
            # Check for high confidence threat intelligence
            for obs in observations:
                if obs.observation_type == ObservationType.THREAT_INTEL:
                    payload = obs.payload
                    if isinstance(payload, ThreatIntelPayloadV1):
                        # Extract confidence from evidence (simplified)
                        if obs.confidence >= 0.9:
                            return True
            
        elif rule.condition == "impossible_travel_score >= 0.8":
            # Check for impossible travel anomalies
            for obs in observations:
                if obs.observation_type == ObservationType.ANOMALY_DETECTION:
                    payload = obs.payload
                    if isinstance(payload, AnomalyDetectionPayloadV1):
                        # Check for impossible travel in anomaly data
                        if payload.data.get("anomaly_type") == "impossible_travel":
                            if payload.baseline_deviation >= 0.8:
                                return True
            
        elif rule.condition == "auth_failure_count >= 5 AND time_window_minutes <= 15":
            # Count authentication failures in time window
            now = self.clock.now()
            window_start = now - timedelta(minutes=15)
            failure_count = 0
            
            for obs in observations:
                if obs.timestamp_utc >= window_start and obs.timestamp_utc <= now:
                    if obs.observation_type == ObservationType.TELEMETRY_SUMMARY:
                        payload = obs.payload
                        if isinstance(payload, dict) and payload.get("event_types"):
                            if "auth_failure" in payload.get("event_types", []):
                                failure_count += payload.get("event_count", 0)
            
            return failure_count >= 5
        
        elif rule.condition == "compromise_indicators_count >= 3":
            # Count system health compromise indicators
            indicator_count = 0
            
            for obs in observations:
                if obs.observation_type == ObservationType.SYSTEM_HEALTH:
                    payload = obs.payload
                    if isinstance(payload, SystemHealthPayloadV1):
                        # Count compromise indicators in service status
                        for service, status in payload.service_status.items():
                            if status in ["compromised", "suspicious", "breached"]:
                                indicator_count += 1
            
            return indicator_count >= 3
        
        elif rule.condition == "anomaly_risk_score >= 0.85":
            # Check for high risk anomalies
            for obs in observations:
                if obs.observation_type == ObservationType.ANOMALY_DETECTION:
                    payload = obs.payload
                    if isinstance(payload, AnomalyDetectionPayloadV1):
                        # Extract risk score from baseline deviation
                        if payload.baseline_deviation >= 0.85:
                            return True
        
        return False
    
    def _generate_recommendation_id(self, subject: IdentitySubjectV1, scope: IdentityContainmentScopeV1) -> str:
        """Generate deterministic recommendation ID"""
        # Use subject, scope, and current time for deterministic ID
        time_str = self.clock.now().isoformat()
        provider = subject.metadata.get("provider", "unknown")
        content = f"{subject.subject_id}:{provider}:{scope.scope_type}:{time_str}"
        return f"rec_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def _extract_subject_from_observations(self, observations: List[ObservationV1]) -> Optional[IdentitySubjectV1]:
        """Extract subject information from observations"""
        # Look for subject information in observation evidence
        for obs in observations:
            if hasattr(obs, 'evidence_refs') and obs.evidence_refs:
                # Try to extract subject from evidence (simplified)
                for ref in obs.evidence_refs:
                    if "user:" in ref or "service:" in ref:
                        parts = ref.split(":")
                        if len(parts) >= 3:
                            return IdentitySubjectV1(
                                subject_id=parts[1],
                                subject_type=parts[0].upper(),
                                tenant_id="tenant_default",
                                containment_scope="none",
                                risk_score=0.0,
                                last_activity_utc=self.clock.now(),
                                metadata={"provider": parts[2]}
                            )
        
        # Default subject if none found
        return IdentitySubjectV1(
            subject_id="unknown",
            subject_type="USER",
            tenant_id="tenant_default",
            containment_scope="none",
            risk_score=0.0,
            last_activity_utc=self.clock.now(),
            metadata={"provider": "LOCAL"}
        )
    
    def generate_recommendations(self, correlation_id: Optional[str] = None) -> List[IdentityContainmentRecommendationV1]:
        """Generate containment recommendations based on current observations and beliefs
        
        Args:
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            List of containment recommendations
        """
        recommendations = []
        
        # Get recent observations and beliefs
        now = self.clock.now()
        lookback_window = timedelta(hours=1)  # Look at last hour of data
        
        observations = self.observation_store.list_observations(
            since=now - lookback_window,
            limit=1000
        )
        
        beliefs = self.observation_store.list_beliefs(
            since=now - lookback_window,
            limit=1000
        )
        
        # Group observations by subject (simplified - using correlation_id)
        subject_groups: Dict[str, List[ObservationV1]] = {}
        for obs in observations:
            key = obs.correlation_id or "default"
            if key not in subject_groups:
                subject_groups[key] = []
            subject_groups[key].append(obs)
        
        # Generate recommendations for each subject group
        for subject_key, subject_observations in subject_groups.items():
            subject = self._extract_subject_from_observations(subject_observations)
            
            # Evaluate each rule
            for rule in self.rules:
                if self._evaluate_rule_condition(rule, subject_observations, beliefs):
                    # Generate recommendation
                    recommendation_id = self._generate_recommendation_id(subject, rule.scope)
                    
                    recommendation = IdentityContainmentRecommendationV1(
                        recommendation_id=recommendation_id,
                        subject_id=subject.subject_id,
                        scope=rule.scope,
                        confidence_score=rule.confidence,
                        risk_assessment={"risk_level": rule.risk_level},
                        evidence_refs=[obs.observation_id for obs in subject_observations],
                        recommended_by="recommender",
                        generated_at_utc=self.clock.now(),
                        expires_at_utc=self.clock.now() + timedelta(seconds=min(rule.ttl_seconds, self.max_ttl_seconds)),
                        status="pending",
                        metadata={
                        "summary": f"Containment recommended due to {rule.name}",
                        "provider": subject.metadata.get("provider", "unknown")
                    }
                    )
                    
                    recommendations.append(recommendation)
                    
                    # Emit audit event
                    self.audit_service.emit_event(
                        event_type=AuditEventType.BELIEF_CREATED,
                        correlation_id=correlation_id or subject_key,
                        source_federate_id=None,  # Local operation
                        event_data={
                            "recommendation_id": recommendation_id,
                            "subject_id": subject.subject_id,
                            "provider": subject.metadata.get("provider", "unknown"),
                            "scope": rule.scope.scope_type,
                            "rule_name": rule.name,
                            "risk_level": rule.risk_level,
                            "confidence": rule.confidence,
                            "ttl_seconds": rule.scope.ttl_seconds
                        }
                    )
                    
                    logger.info(f"Generated containment recommendation {recommendation_id} for subject {subject.subject_id}")
        
        return recommendations
    
    def get_recommendations_for_subject(
        self,
        subject_id: str,
        provider: str,
        correlation_id: Optional[str] = None
    ) -> List[IdentityContainmentRecommendationV1]:
        """Get recommendations for a specific subject
        
        Args:
            subject_id: Subject identifier
            provider: Identity provider
            correlation_id: Optional correlation ID
            
        Returns:
            List of recommendations for the subject
        """
        all_recommendations = self.generate_recommendations(correlation_id)
        
        # Filter by subject
        filtered_recommendations = [
            rec for rec in all_recommendations
            if rec.subject_id == subject_id and rec.metadata.get("provider", "unknown") == provider
        ]
        
        return filtered_recommendations
