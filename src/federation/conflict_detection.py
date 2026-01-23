"""
Conflict Detection Service

Detects deterministic conflicts between beliefs and observations.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

from spec.contracts.models_v1 import (
    BeliefV1,
    ObservationV1,
    ObservationType,
    ArbitrationV1,
    ArbitrationStatus,
    ArbitrationConflictType
)
from src.federation.audit import AuditEventEnvelope, AuditEventType
from src.federation.clock import Clock
from src.federation.arbitration_store import ArbitrationStore
from src.federation.audit import AuditService

logger = logging.getLogger(__name__)


class ConflictDetectionService:
    """Detects conflicts between beliefs and observations"""
    
    def __init__(
        self,
        arbitration_store: ArbitrationStore,
        audit_service: AuditService,
        clock: Clock,
        feature_flag_enabled: bool = False
    ):
        self.arbitration_store = arbitration_store
        self.audit_service = audit_service
        self.clock = clock
        self.feature_flag_enabled = feature_flag_enabled
    
    def detect_belief_conflicts(self, beliefs: List[BeliefV1]) -> List[ArbitrationV1]:
        """
        Detect conflicts between beliefs and create arbitration objects
        
        Args:
            beliefs: List of beliefs to check for conflicts
            
        Returns:
            List of created arbitration objects
        """
        if not self.feature_flag_enabled:
            return []
        
        arbitrations = []
        
        # Group beliefs by conflict key
        conflict_groups = self._group_beliefs_by_conflict(beliefs)
        
        for conflict_key, belief_group in conflict_groups.items():
            if len(belief_group) < 2:
                continue  # No conflict with single belief
            
            # Check for incompatible claims
            conflicts = self._detect_incompatible_claims(belief_group)
            
            if conflicts:
                arbitration = self._create_arbitration_from_conflict(
                    conflict_key, belief_group, conflicts
                )
                arbitrations.append(arbitration)
                
                # Store arbitration
                self.arbitration_store.store_arbitration(arbitration)
                
                # Emit audit event
                self._emit_conflict_detected_event(arbitration)
        
        return arbitrations
    
    def _group_beliefs_by_conflict(self, beliefs: List[BeliefV1]) -> Dict[str, List[BeliefV1]]:
        """Group beliefs by conflict key for conflict detection"""
        groups = {}
        
        for belief in beliefs:
            conflict_key = self._generate_conflict_key(belief)
            if conflict_key not in groups:
                groups[conflict_key] = []
            groups[conflict_key].append(belief)
        
        return groups
    
    def _generate_conflict_key(self, belief: BeliefV1) -> str:
        """
        Generate deterministic conflict key for a belief
        
        Format: belief_type:subject_key:time_window
        """
        # Extract subject key from belief metadata or evidence
        subject_key = self._extract_subject_key(belief)
        
        # Generate time window (hourly)
        time_window = self._get_time_window(belief.derived_at)
        
        # Create deterministic conflict key
        key_parts = [
            belief.belief_type,
            subject_key,
            time_window
        ]
        
        conflict_key = ":".join(key_parts)
        
        # Create hash for consistent length
        return hashlib.sha256(conflict_key.encode()).hexdigest()[:16]
    
    def _extract_subject_key(self, belief: BeliefV1) -> str:
        """Extract subject key from belief"""
        # Try to get subject from metadata
        if "subject" in belief.metadata:
            return str(belief.metadata["subject"])
        
        # Try to get from evidence summary
        if belief.evidence_summary:
            # Extract first few words as subject
            words = belief.evidence_summary.split()[:3]
            return "_".join(words)
        
        # Default to belief type
        return belief.belief_type
    
    def _get_time_window(self, timestamp: datetime) -> str:
        """Get hourly time window for conflict grouping"""
        return timestamp.strftime("%Y-%m-%d-%H")
    
    def _detect_incompatible_claims(self, beliefs: List[BeliefV1]) -> List[Dict[str, Any]]:
        """
        Detect incompatible claims between beliefs
        
        Args:
            beliefs: List of beliefs with same conflict key
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check for contradictory confidence levels
        if self._has_conflicting_confidence(beliefs):
            conflicts.append({
                "type": "confidence_conflict",
                "description": "Beliefs have conflicting confidence levels",
                "beliefs": [b.belief_id for b in beliefs]
            })
        
        # Check for contradictory evidence
        if self._has_conflicting_evidence(beliefs):
            conflicts.append({
                "type": "evidence_conflict", 
                "description": "Beliefs have conflicting evidence",
                "beliefs": [b.belief_id for b in beliefs]
            })
        
        # Check for specific belief type conflicts
        belief_type = beliefs[0].belief_type
        if belief_type.startswith("derived_from_THREAT_INTEL"):
            threats_conflicts = self._detect_threat_intel_conflicts(beliefs)
            conflicts.extend(threats_conflicts)
        elif belief_type.startswith("derived_from_SYSTEM_HEALTH"):
            health_conflicts = self._detect_system_health_conflicts(beliefs)
            conflicts.extend(health_conflicts)
        
        return conflicts
    
    def _has_conflicting_confidence(self, beliefs: List[BeliefV1]) -> bool:
        """Check if beliefs have conflicting confidence levels"""
        confidences = [b.confidence for b in beliefs]
        max_conf = max(confidences)
        min_conf = min(confidences)
        
        # Consider it conflicting if confidence differs by more than 0.3
        return (max_conf - min_conf) > 0.3
    
    def _has_conflicting_evidence(self, beliefs: List[BeliefV1]) -> bool:
        """Check if beliefs have conflicting evidence"""
        # Check for conflicting source observations
        source_sets = [set(b.source_observations) for b in beliefs]
        
        # If beliefs have completely different sources, might indicate conflict
        all_sources = set()
        for sources in source_sets:
            all_sources.update(sources)
        
        # If no overlap in sources and multiple beliefs, potential conflict
        return len(all_sources) > len(source_sets[0]) and len(source_sets) > 1
    
    def _detect_threat_intel_conflicts(self, beliefs: List[BeliefV1]) -> List[Dict[str, Any]]:
        """Detect conflicts in threat intelligence beliefs"""
        conflicts = []
        
        # Check for conflicting threat classifications
        threat_classifications = {}
        for belief in beliefs:
            if "threat_type" in belief.metadata:
                threat_type = belief.metadata["threat_type"]
                if threat_type not in threat_classifications:
                    threat_classifications[threat_type] = []
                threat_classifications[threat_type].append(belief)
        
        # Multiple threat types for same subject is a conflict
        if len(threat_classifications) > 1:
            conflicts.append({
                "type": "threat_classification_conflict",
                "description": f"Multiple threat types: {list(threat_classifications.keys())}",
                "beliefs": [b.belief_id for b in beliefs]
            })
        
        return conflicts
    
    def _detect_system_health_conflicts(self, beliefs: List[BeliefV1]) -> List[Dict[str, Any]]:
        """Detect conflicts in system health beliefs"""
        conflicts = []
        
        # Check for conflicting health scores
        health_scores = []
        for belief in beliefs:
            if "health_score" in belief.metadata:
                health_scores.append(belief.metadata["health_score"])
        
        if len(health_scores) > 1:
            max_score = max(health_scores)
            min_score = min(health_scores)
            
            # Conflicting if health scores differ significantly
            if abs(max_score - min_score) > 0.4:
                conflicts.append({
                    "type": "health_score_conflict",
                    "description": f"Conflicting health scores: {health_scores}",
                    "beliefs": [b.belief_id for b in beliefs]
                })
        
        return conflicts
    
    def _create_arbitration_from_conflict(
        self,
        conflict_key: str,
        beliefs: List[BeliefV1],
        conflicts: List[Dict[str, Any]]
    ) -> ArbitrationV1:
        """Create arbitration object from detected conflict"""
        
        # Determine conflict type
        conflict_type = self._determine_conflict_type(conflicts)
        
        # Extract subject key
        subject_key = self._extract_subject_key(beliefs[0])
        
        # Collect evidence references
        evidence_refs = []
        for belief in beliefs:
            evidence_refs.extend(belief.source_observations)
        
        # Get correlation ID if present
        correlation_id = beliefs[0].correlation_id
        
        arbitration = ArbitrationV1(
            arbitration_id=f"arb_{self.clock.now().strftime('%Y%m%d%H%M%S')}_{hash(conflict_key) % 10000:04d}",
            created_at_utc=self.clock.now(),
            status=ArbitrationStatus.OPEN,
            conflict_type=conflict_type,
            subject_key=subject_key,
            conflict_key=conflict_key,
            claims=[
                {
                    "belief_id": belief.belief_id,
                    "belief_type": belief.belief_type,
                    "confidence": belief.confidence,
                    "evidence_summary": belief.evidence_summary,
                    "metadata": belief.metadata
                }
                for belief in beliefs
            ],
            evidence_refs=list(set(evidence_refs)),
            correlation_id=correlation_id,
            conflicts_detected=conflicts
        )
        
        return arbitration
    
    def _determine_conflict_type(self, conflicts: List[Dict[str, Any]]) -> ArbitrationConflictType:
        """Determine primary conflict type from detected conflicts"""
        conflict_types = [c["type"] for c in conflicts]
        
        if "threat_classification_conflict" in conflict_types:
            return ArbitrationConflictType.THREAT_CLASSIFICATION
        elif "health_score_conflict" in conflict_types:
            return ArbitrationConflictType.SYSTEM_HEALTH
        elif "confidence_conflict" in conflict_types:
            return ArbitrationConflictType.CONFIDENCE_DISPUTE
        else:
            return ArbitrationConflictType.EVIDENCE_CONFLICT
    
    def _emit_conflict_detected_event(self, arbitration: ArbitrationV1):
        """Emit audit event for conflict detection"""
        try:
            audit_event = AuditEventEnvelope(
                event_type=AuditEventType.CONFLICT_DETECTED,
                timestamp_utc=self.clock.now(),
                correlation_id=arbitration.correlation_id,
                source_federate_id="conflict_detection_service",
                event_data={
                    "arbitration_id": arbitration.arbitration_id,
                    "conflict_type": arbitration.conflict_type.value,
                    "subject_key": arbitration.subject_key,
                    "conflict_key": arbitration.conflict_key,
                    "num_claims": len(arbitration.claims),
                    "evidence_refs": arbitration.evidence_refs
                }
            )
            
            self.audit_service.emit_audit_event(audit_event)
            
        except Exception as e:
            logger.error(f"Failed to emit conflict detected audit event: {e}")
