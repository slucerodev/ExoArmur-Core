"""
Collective confidence aggregation from beliefs
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
from models_v1 import BeliefV1

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
        self.belief_cache: Dict[str, List[BeliefV1]] = {}
        logger.info("CollectiveConfidenceAggregator initialized")
    
    def add_belief(self, belief: BeliefV1) -> None:
        """Add belief to aggregation cache"""
        logger.info(f"Adding belief {belief.belief_id} to aggregation")
        
        # Group beliefs by type and correlation for aggregation
        # Using belief_type and correlation_id since subject field was removed
        subject_key = f"{belief.belief_type}:{belief.correlation_id or 'unknown'}"
        if subject_key not in self.belief_cache:
            self.belief_cache[subject_key] = []
        
        self.belief_cache[subject_key].append(belief)
    
    def compute_collective_state(self, belief: BeliefV1) -> CollectiveState:
        """Compute collective confidence state for a belief"""
        subject_key = f"{belief.belief_type}:{belief.correlation_id or 'unknown'}"
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
