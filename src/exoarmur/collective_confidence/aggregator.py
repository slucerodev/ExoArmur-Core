"""
Collective confidence aggregation from beliefs
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Union
from dataclasses import dataclass

import sys
import os
from spec.contracts.models_v1 import BeliefV1, BeliefTelemetryV1

logger = logging.getLogger(__name__)


@dataclass
class CollectiveState:
    """Collective confidence state"""
    aggregate_score: float
    quorum_count: int
    conflict_detected: bool


class CollectiveConfidenceAggregator:
    """Aggregates beliefs to compute collective confidence"""
    
    def __init__(self, nats_client=None):
        self.nats_client = nats_client
        self.belief_cache: Dict[str, List[Union[BeliefV1, BeliefTelemetryV1]]] = {}
        logger.info("CollectiveConfidenceAggregator initialized")
    
    def add_belief(self, belief: Union[BeliefV1, BeliefTelemetryV1]) -> None:
        """Add belief to aggregation cache"""
        logger.info(f"Adding belief {belief.belief_id} to aggregation")
        
        # Group beliefs by type and correlation for aggregation
        # Handle both belief_type (BeliefV1) and claim_type (BeliefTelemetryV1)
        if hasattr(belief, 'claim_type'):
            belief_type = belief.claim_type
        else:
            belief_type = belief.belief_type
        
        subject_key = f"{belief_type}:{belief.correlation_id or 'unknown'}"
        if subject_key not in self.belief_cache:
            self.belief_cache[subject_key] = []
        
        self.belief_cache[subject_key].append(belief)
    
    def compute_collective_state(self, belief: Union[BeliefV1, BeliefTelemetryV1]) -> CollectiveState:
        """Compute collective confidence state for a belief"""
        # Handle both belief_type (BeliefV1) and claim_type (BeliefTelemetryV1)
        if hasattr(belief, 'claim_type'):
            belief_type = belief.claim_type
        else:
            belief_type = belief.belief_type
        
        subject_key = f"{belief_type}:{belief.correlation_id or 'unknown'}"
        related_beliefs = self.belief_cache.get(subject_key, [])
        
        # Simple aggregation logic
        if not related_beliefs:
            return CollectiveState(
                aggregate_score=belief.confidence,
                quorum_count=1,
                conflict_detected=False
            )
        
        # Compute aggregate score as average confidence
        aggregate_score = sum(b.confidence for b in related_beliefs) / len(related_beliefs)
        quorum_count = len(related_beliefs)
        
        # Simple conflict detection: varying confidence levels
        # Using confidence instead of severity since severity field was removed
        confidence_variance = max(b.confidence for b in related_beliefs) - min(b.confidence for b in related_beliefs)
        conflict_detected = confidence_variance > 0.3  # Threshold for conflict detection
        
        return CollectiveState(
            aggregate_score=aggregate_score,
            quorum_count=quorum_count,
            conflict_detected=conflict_detected
        )
    
    async def start_consumer(self) -> None:
        """Start consuming beliefs from JetStream"""
        logger.info("Starting belief consumer")
        # TODO: implement actual JetStream consumer
