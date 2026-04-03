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
from exoarmur.execution_boundary_v2.detection import check_domain_logic_access, ViolationSeverity

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
        # DETECTION ONLY: Check if this domain logic access is outside V2EntryGate
        check_domain_logic_access("CollectiveConfidenceAggregator", "add_belief", ViolationSeverity.MEDIUM)
        
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
        """Start consuming beliefs from JetStream through V2EntryGate"""
        logger.info("Starting belief consumer through V2EntryGate")
        
        try:
            # Import V2EntryGate components
            from exoarmur.execution_boundary_v2.entry.v2_entry_gate import execute_module, ExecutionRequest
            from exoarmur.execution_boundary_v2.core.core_types import ModuleID, ExecutionID, DeterministicSeed, ModuleExecutionContext, ModuleVersion
            from datetime import datetime, timezone
            import hashlib
            import ulid
            
            # TODO: Implement actual JetStream consumer
            # For now, simulate receiving messages and route through V2EntryGate
            
            # Simulate receiving a belief message
            simulated_belief = {
                'belief_id': str(ulid.ULID()),
                'content': 'Simulated belief for V2 routing',
                'confidence': 0.8,
                'source': 'test_consumer',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Received belief: {simulated_belief['belief_id']}")
            
            # Route belief processing through V2EntryGate
            belief_ulid = str(ulid.ULID())
            execution_ulid = str(ulid.ULID())
            
            belief_request = ExecutionRequest(
                module_id=ModuleID(belief_ulid),
                execution_context=ModuleExecutionContext(
                    execution_id=ExecutionID(execution_ulid),
                    module_id=ModuleID(belief_ulid),
                    module_version=ModuleVersion(1, 0, 0),
                    deterministic_seed=DeterministicSeed(hash("belief_processing") % (2**63)),
                    logical_timestamp=int(datetime.now(timezone.utc).timestamp()),
                    dependency_hash="belief_processing"
                ),
                action_data={
                    'intent_type': 'BELIEF_PROCESSING',
                    'action_class': 'message_processing',
                    'action_type': 'process_belief',
                    'subject': 'belief',
                    'parameters': {
                        'belief_data': simulated_belief
                    }
                },
                correlation_id=simulated_belief['belief_id']
            )
            
            # Execute belief processing through V2EntryGate
            result = execute_module(belief_request)
            
            if result.success:
                logger.info(f"Belief processed successfully through V2EntryGate: {result.result_data.get('belief_id')}")
            else:
                logger.error(f"Belief processing failed through V2EntryGate: {result.error}")
                
        except Exception as e:
            logger.error(f"Belief consumer error: {e}")
            
        logger.info("Belief consumer started (V2-compliant)")
