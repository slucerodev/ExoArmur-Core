"""
ExoArmur ADMO V2 Observation Store
Deterministic storage and retrieval of federate observations
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import uuid

from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    FederateIdentityV1,
    HandshakeState
)
from .clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class ObservationStoreConfig:
    """Configuration for observation store behavior"""
    max_observations_per_federate: int = 10000
    max_beliefs: int = 5000
    observation_ttl_hours: int = 72
    belief_ttl_hours: int = 168


class ObservationStore:
    """
    Deterministic storage for federate observations
    
    Provides ordered storage and retrieval with provenance tracking.
    """
    
    def __init__(self, clock: Clock, config: Optional[ObservationStoreConfig] = None):
        self.clock = clock
        self.config = config or ObservationStoreConfig()
        
        # Use OrderedDict for deterministic ordering by timestamp
        self._observations: OrderedDict[str, ObservationV1] = OrderedDict()
        self._beliefs: OrderedDict[str, BeliefV1] = OrderedDict()
        
        # Indexes for efficient lookup
        self._observations_by_federate: Dict[str, List[str]] = {}
        self._observations_by_correlation: Dict[str, List[str]] = {}
        self._beliefs_by_correlation: Dict[str, List[str]] = {}
        
        # Nonce tracking for replay protection
        self._used_nonces: Dict[str, datetime] = {}
        
        logger.info("ObservationStore initialized")
    
    def store_observation(self, observation: ObservationV1) -> bool:
        """
        Store an observation with deterministic ordering
        
        Args:
            observation: Observation to store
            
        Returns:
            True if stored successfully, False if duplicate
        """
        # Check for duplicate
        if observation.observation_id in self._observations:
            logger.warning(f"Duplicate observation ID: {observation.observation_id}")
            return False
        
        # Store with timestamp ordering
        self._observations[observation.observation_id] = observation
        
        # Update indexes
        federate_id = observation.source_federate_id
        if federate_id not in self._observations_by_federate:
            self._observations_by_federate[federate_id] = []
        self._observations_by_federate[federate_id].append(observation.observation_id)
        
        if observation.correlation_id:
            corr_id = observation.correlation_id
            if corr_id not in self._observations_by_correlation:
                self._observations_by_correlation[corr_id] = []
            self._observations_by_correlation[corr_id].append(observation.observation_id)
        
        # Track nonce for replay protection
        if observation.nonce:
            self._used_nonces[observation.nonce] = observation.timestamp_utc
        
        logger.info(f"Stored observation {observation.observation_id} from {federate_id}")
        return True
    
    def get_observation(self, observation_id: str) -> Optional[ObservationV1]:
        """Get a specific observation by ID"""
        return self._observations.get(observation_id)
    
    def list_observations(
        self,
        federate_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        observation_type: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[ObservationV1]:
        """
        List observations with optional filters
        
        Args:
            federate_id: Filter by federate ID
            correlation_id: Filter by correlation ID
            observation_type: Filter by observation type
            limit: Maximum number to return
            since: Filter by timestamp (inclusive)
            
        Returns:
            List of observations in timestamp order
        """
        observations = []
        
        # Start with all observations or filtered subset
        if federate_id:
            obs_ids = self._observations_by_federate.get(federate_id, [])
            candidates = [self._observations[oid] for oid in obs_ids]
        elif correlation_id:
            obs_ids = self._observations_by_correlation.get(correlation_id, [])
            candidates = [self._observations[oid] for oid in obs_ids]
        else:
            candidates = list(self._observations.values())
        
        # Apply filters
        for obs in candidates:
            if observation_type and obs.observation_type != observation_type:
                continue
            if since and obs.timestamp_utc < since:
                continue
            observations.append(obs)
        
        # Sort by timestamp (deterministic)
        observations.sort(key=lambda x: x.timestamp_utc)
        
        # Apply limit
        if limit:
            observations = observations[:limit]
        
        return observations
    
    def store_belief(self, belief: BeliefV1) -> bool:
        """
        Store a belief with deterministic ordering
        
        Args:
            belief: Belief to store
            
        Returns:
            True if stored successfully, False if duplicate
        """
        # Check for duplicate
        if belief.belief_id in self._beliefs:
            logger.warning(f"Duplicate belief ID: {belief.belief_id}")
            return False
        
        # Store with timestamp ordering
        self._beliefs[belief.belief_id] = belief
        
        # Update correlation index
        if belief.correlation_id:
            corr_id = belief.correlation_id
            if corr_id not in self._beliefs_by_correlation:
                self._beliefs_by_correlation[corr_id] = []
            self._beliefs_by_correlation[corr_id].append(belief.belief_id)
        
        logger.info(f"Stored belief {belief.belief_id}")
        return True
    
    def get_belief(self, belief_id: str) -> Optional[BeliefV1]:
        """Get a specific belief by ID"""
        return self._beliefs.get(belief_id)
    
    def list_beliefs(
        self,
        correlation_id: Optional[str] = None,
        belief_type: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[BeliefV1]:
        """
        List beliefs with optional filters
        
        Args:
            correlation_id: Filter by correlation ID
            belief_type: Filter by belief type
            limit: Maximum number to return
            since: Filter by timestamp (inclusive)
            
        Returns:
            List of beliefs in timestamp order
        """
        beliefs = []
        
        # Start with all beliefs or filtered subset
        if correlation_id:
            belief_ids = self._beliefs_by_correlation.get(correlation_id, [])
            candidates = [self._beliefs[bid] for bid in belief_ids]
        else:
            candidates = list(self._beliefs.values())
        
        # Apply filters
        for belief in candidates:
            if belief_type and belief.belief_type != belief_type:
                continue
            if since and belief.derived_at < since:
                continue
            beliefs.append(belief)
        
        # Sort by timestamp (deterministic)
        beliefs.sort(key=lambda x: x.derived_at)
        
        # Apply limit
        if limit:
            beliefs = beliefs[:limit]
        
        return beliefs
    
    def is_nonce_used(self, nonce: str) -> bool:
        """Check if a nonce has been used"""
        return nonce in self._used_nonces
    
    def get_timeline_by_correlation(self, correlation_id: str) -> Dict[str, List[Any]]:
        """
        Get timeline of observations and beliefs for a correlation ID
        
        Args:
            correlation_id: Correlation ID to look up
            
        Returns:
            Dictionary with 'observations' and 'beliefs' lists
        """
        observations = self.list_observations(correlation_id=correlation_id)
        beliefs = self.list_beliefs(correlation_id=correlation_id)
        
        return {
            "observations": observations,
            "beliefs": beliefs
        }
    
    def cleanup_expired(self) -> Dict[str, int]:
        """
        Clean up expired observations and beliefs
        
        Returns:
            Dictionary with cleanup counts
        """
        now = self.clock.now()
        cutoff_time = now - timedelta(hours=self.config.observation_ttl_hours)
        belief_cutoff_time = now - timedelta(hours=self.config.belief_ttl_hours)
        
        expired_obs = 0
        expired_beliefs = 0
        
        # Clean up expired observations
        expired_obs_ids = []
        for obs_id, obs in self._observations.items():
            if obs.timestamp_utc < cutoff_time:
                expired_obs_ids.append(obs_id)
        
        for obs_id in expired_obs_ids:
            obs = self._observations.pop(obs_id, None)
            if obs:
                # Update indexes
                federate_id = obs.source_federate_id
                if federate_id in self._observations_by_federate:
                    try:
                        self._observations_by_federate[federate_id].remove(obs_id)
                    except ValueError:
                        pass
                
                if obs.correlation_id and obs.correlation_id in self._observations_by_correlation:
                    try:
                        self._observations_by_correlation[obs.correlation_id].remove(obs_id)
                    except ValueError:
                        pass
                
                expired_obs += 1
        
        # Clean up expired beliefs
        expired_belief_ids = []
        for belief_id, belief in self._beliefs.items():
            if belief.derived_at < belief_cutoff_time:
                expired_belief_ids.append(belief_id)
        
        for belief_id in expired_belief_ids:
            belief = self._beliefs.pop(belief_id, None)
            if belief:
                # Update correlation index
                if belief.correlation_id and belief.correlation_id in self._beliefs_by_correlation:
                    try:
                        self._beliefs_by_correlation[belief.correlation_id].remove(belief_id)
                    except ValueError:
                        pass
                
                expired_beliefs += 1
        
        # Clean up old nonces
        expired_nonces = 0
        nonce_cutoff = now - timedelta(hours=24)
        expired_nonce_keys = []
        for nonce, timestamp in self._used_nonces.items():
            if timestamp < nonce_cutoff:
                expired_nonce_keys.append(nonce)
        
        for nonce in expired_nonce_keys:
            self._used_nonces.pop(nonce, None)
            expired_nonces += 1
        
        logger.info(f"Cleanup completed: {expired_obs} observations, {expired_beliefs} beliefs, {expired_nonces} nonces")
        
        return {
            "expired_observations": expired_obs,
            "expired_beliefs": expired_beliefs,
            "expired_nonces": expired_nonces
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics"""
        return {
            "total_observations": len(self._observations),
            "total_beliefs": len(self._beliefs),
            "federates": list(self._observations_by_federate.keys()),
            "correlation_ids": list(self._observations_by_correlation.keys()),
            "used_nonces": len(self._used_nonces)
        }
