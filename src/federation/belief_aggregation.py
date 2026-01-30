"""
ExoArmur ADMO V2 Belief Aggregation Service
Deterministic aggregation of observations into beliefs
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import uuid

from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    BeliefTelemetryV1,
    ObservationType
)
from federation.conflict_detection import ConflictDetectionService
from .observation_store import ObservationStore
from .clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class BeliefAggregationConfig:
    """Configuration for belief aggregation behavior"""
    feature_enabled: bool = False  # V2 additive feature flag
    min_observations_for_belief: int = 1
    confidence_threshold: float = 0.5
    max_beliefs_per_type: int = 100
    aggregation_window_minutes: int = 60


class BeliefAggregationService:
    """
    Service for deterministic aggregation of observations into beliefs
    
    Derives beliefs from observations with provenance tracking
    and deterministic scoring rules.
    """
    
    def __init__(
        self,
        observation_store: ObservationStore,
        clock: Clock,
        config: Optional[BeliefAggregationConfig] = None,
        conflict_detection_service: Optional[ConflictDetectionService] = None
    ):
        self.observation_store = observation_store
        self.clock = clock
        self.config = config or BeliefAggregationConfig()
        self.conflict_detection_service = conflict_detection_service
        
        # Aggregation rules for different observation types
        self._aggregation_rules = {
            ObservationType.TELEMETRY_SUMMARY: self._aggregate_telemetry_summary,
            ObservationType.THREAT_INTEL: self._aggregate_threat_intel,
            ObservationType.ANOMALY_DETECTION: self._aggregate_anomaly_detection,
            ObservationType.SYSTEM_HEALTH: self._aggregate_system_health,
            ObservationType.NETWORK_ACTIVITY: self._aggregate_network_activity,
            ObservationType.CUSTOM: self._aggregate_custom
        }
        
        logger.info("BeliefAggregationService initialized")
    
    def aggregate_observations(
        self,
        observation_type: Optional[ObservationType] = None,
        correlation_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[BeliefV1]:
        """
        Aggregate observations into beliefs
        
        Args:
            observation_type: Filter by observation type
            correlation_id: Filter by correlation ID
            since: Filter by observation timestamp
            
        Returns:
            List of newly created beliefs
        """
        if not self.config.feature_enabled:
            return []
        
        # Get observations to aggregate
        observations = self.observation_store.list_observations(
            observation_type=observation_type,
            correlation_id=correlation_id,
            since=since
        )
        
        if not observations:
            return []
        
        # Group observations for aggregation
        groups = self._group_observations_for_aggregation(observations)
        
        beliefs = []
        for group_key, obs_group in groups.items():
            belief = self._create_belief_from_group(obs_group)
            if belief:
                beliefs.append(belief)
                logger.info(f"Created belief {belief.belief_id} from {len(obs_group)} observations")
        
        # Store beliefs
        for belief in beliefs:
            self.observation_store.store_belief(belief)
        
        # Detect conflicts if service is available
        if self.conflict_detection_service:
            arbitrations = self.conflict_detection_service.detect_belief_conflicts(beliefs)
            if arbitrations:
                logger.info(f"Detected {len(arbitrations)} conflicts from {len(beliefs)} beliefs")
        
        return beliefs
    
    def _group_observations_for_aggregation(
        self, observations: List[ObservationV1]
    ) -> Dict[str, List[ObservationV1]]:
        """
        Group observations for deterministic aggregation
        
        Groups by observation type, correlation ID, and time window
        to ensure deterministic results.
        """
        groups = defaultdict(list)
        
        for obs in observations:
            # Create deterministic grouping key
            group_key_parts = [
                obs.observation_type,
                obs.correlation_id or "no_correlation",
                self._get_time_window(obs.timestamp_utc)
            ]
            
            # Add payload-specific grouping for more granular aggregation
            payload_key = self._get_payload_grouping_key(obs)
            if payload_key:
                group_key_parts.append(payload_key)
            
            group_key = "|".join(str(part) for part in group_key_parts)
            groups[group_key].append(obs)
        
        return dict(groups)
    
    def _get_time_window(self, timestamp: datetime) -> str:
        """Get time window for aggregation (deterministic)"""
        # Group by hour for deterministic results
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        return hour.isoformat()
    
    def _get_payload_grouping_key(self, observation: ObservationV1) -> Optional[str]:
        """Get payload-specific grouping key"""
        payload = observation.payload
        
        # Group by specific payload attributes based on type
        if observation.observation_type == ObservationType.THREAT_INTEL:
            # Group by threat types
            if hasattr(payload, 'threat_types'):
                return ",".join(sorted(payload.threat_types))
        
        elif observation.observation_type == ObservationType.ANOMALY_DETECTION:
            # Group by anomaly type
            if hasattr(payload, 'anomaly_type'):
                return payload.anomaly_type
        
        elif observation.observation_type == ObservationType.SYSTEM_HEALTH:
            # Group by service status summary
            if hasattr(payload, 'service_status'):
                healthy_services = sum(1 for status in payload.service_status.values() if status == "healthy")
                total_services = len(payload.service_status)
                return f"{healthy_services}/{total_services}"
        
        return None
    
    def _create_belief_from_group(self, observations: List[ObservationV1]) -> Optional[BeliefV1]:
        """Create a belief from a group of observations"""
        if not observations:
            return None
        
        # Use the first observation's type as the belief type
        obs_type = observations[0].observation_type
        
        # Get aggregation rule for this observation type
        aggregation_func = self._aggregation_rules.get(obs_type, self._aggregate_custom)
        
        try:
            belief_data = aggregation_func(observations)
            
            # Create belief with deterministic ID
            belief_id = self._generate_belief_id(observations)
            
            # Extract deterministic derived_at from observations (max timestamp)
            derived_at = max(obs.timestamp_utc for obs in observations)
            
            # Create sorted list of source observations
            source_observations = sorted([obs.observation_id for obs in observations])
            
            # Create deterministic evidence summary
            evidence_summary = f"Aggregated from {len(observations)} {obs_type} observations"
            
            belief = BeliefV1(
                schema_version="1.0.0",
                belief_id=belief_id,
                belief_type=f"derived_from_{obs_type}",
                confidence=belief_data["confidence"],
                source_observations=source_observations,
                derived_at=derived_at,
                correlation_id=observations[0].correlation_id or "no-correlation",
                evidence_summary=evidence_summary,
                metadata=belief_data.get("metadata", {}),
                conflicts=[]  # No conflicts in aggregated beliefs
            )
            
            return belief
            
        except Exception as e:
            logger.error(f"Error creating belief from observations: {e}")
            return None
    
    def _generate_belief_id(self, observations: List[ObservationV1]) -> str:
        """Generate deterministic belief ID from observations"""
        # Sort observations for deterministic ID generation
        sorted_obs = sorted(observations, key=lambda x: (x.observation_id, x.timestamp_utc))
        
        # Create deterministic hash from observation IDs and timestamps
        hash_input = "|".join(
            f"{obs.observation_id}:{obs.timestamp_utc.isoformat()}"
            for obs in sorted_obs
        )
        
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
        # Generate a valid ULID format (26 chars, Crockford base32)
        ulid_chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        # Convert first 14 chars of hash to valid ULID chars to make 26 total
        ulid_part = ""
        for i in range(14):
            char_index = int(hash_digest[i*2:i*2+2], 16) % len(ulid_chars)
            ulid_part += ulid_chars[char_index]
        
        # Return exactly 26 characters
        return f"01J4NR5X9Z8G{ulid_part}"
    
    def _aggregate_telemetry_summary(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Aggregate telemetry summary observations"""
        total_events = sum(
            getattr(obs.payload, 'event_count', 0) 
            for obs in observations
        )
        
        # Average confidence
        avg_confidence = sum(obs.confidence for obs in observations) / len(observations)
        
        # Combine severity distributions
        severity_dist = defaultdict(int)
        for obs in observations:
            if hasattr(obs.payload, 'severity_distribution'):
                for severity, count in obs.payload.severity_distribution.items():
                    severity_dist[severity] += count
        
        evidence_summary = (
            f"Aggregated {total_events} telemetry events from {len(observations)} observations. "
            f"Severity distribution: {dict(severity_dist)}"
        )
        
        return {
            "confidence": min(avg_confidence, 1.0),
            "evidence_summary": evidence_summary,
            "metadata": {
                "total_events": total_events,
                "observation_count": len(observations),
                "severity_distribution": dict(severity_dist)
            }
        }
    
    def _aggregate_threat_intel(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Aggregate threat intelligence observations"""
        total_iocs = sum(
            getattr(obs.payload, 'ioc_count', 0) 
            for obs in observations
        )
        
        # Combine threat types
        all_threat_types = set()
        for obs in observations:
            if hasattr(obs.payload, 'threat_types'):
                all_threat_types.update(obs.payload.threat_types)
        
        # Average confidence scores
        confidence_scores = [
            getattr(obs.payload, 'confidence_score', 0.0) 
            for obs in observations
        ]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Combine sources
        all_sources = set()
        for obs in observations:
            if hasattr(obs.payload, 'sources'):
                all_sources.update(obs.payload.sources)
        
        evidence_summary = (
            f"Aggregated {total_iocs} IOCs from {len(observations)} threat intel observations. "
            f"Threat types: {sorted(all_threat_types)}. Sources: {sorted(all_sources)}"
        )
        
        return {
            "confidence": min(avg_confidence, 1.0),
            "evidence_summary": evidence_summary,
            "metadata": {
                "total_iocs": total_iocs,
                "threat_types": sorted(all_threat_types),
                "sources": sorted(all_sources),
                "observation_count": len(observations)
            }
        }
    
    def _aggregate_anomaly_detection(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Aggregate anomaly detection observations"""
        # Average anomaly scores
        anomaly_scores = [
            getattr(obs.payload, 'anomaly_score', 0.0) 
            for obs in observations
        ]
        avg_anomaly_score = sum(anomaly_scores) / len(anomaly_scores) if anomaly_scores else 0.0
        
        # Combine affected entities
        all_entities = set()
        for obs in observations:
            if hasattr(obs.payload, 'affected_entities'):
                all_entities.update(obs.payload.affected_entities)
        
        # Average baseline deviation
        deviations = [
            getattr(obs.payload, 'baseline_deviation', 0.0) 
            for obs in observations
        ]
        avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0
        
        evidence_summary = (
            f"Aggregated anomaly detection from {len(observations)} observations. "
            f"Average anomaly score: {avg_anomaly_score:.3f}. "
            f"Affected entities: {len(all_entities)}. "
            f"Average baseline deviation: {avg_deviation:.3f}"
        )
        
        return {
            "confidence": min(avg_anomaly_score, 1.0),
            "evidence_summary": evidence_summary,
            "metadata": {
                "average_anomaly_score": avg_anomaly_score,
                "affected_entities": list(all_entities),
                "average_baseline_deviation": avg_deviation,
                "observation_count": len(observations)
            }
        }
    
    def _aggregate_system_health(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Aggregate system health observations"""
        # Average utilization metrics
        cpu_utils = [
            getattr(obs.payload, 'cpu_utilization', 0.0) 
            for obs in observations
        ]
        mem_utils = [
            getattr(obs.payload, 'memory_utilization', 0.0) 
            for obs in observations
        ]
        disk_utils = [
            getattr(obs.payload, 'disk_utilization', 0.0) 
            for obs in observations
        ]
        network_latencies = [
            getattr(obs.payload, 'network_latency_ms', 0.0) 
            for obs in observations
        ]
        
        avg_cpu = sum(cpu_utils) / len(cpu_utils) if cpu_utils else 0.0
        avg_mem = sum(mem_utils) / len(mem_utils) if mem_utils else 0.0
        avg_disk = sum(disk_utils) / len(disk_utils) if disk_utils else 0.0
        avg_latency = sum(network_latencies) / len(network_latencies) if network_latencies else 0.0
        
        # Determine overall health status
        health_score = 1.0 - ((avg_cpu + avg_mem + avg_disk) / 300.0)  # Simple scoring
        health_score = max(0.0, health_score)
        
        evidence_summary = (
            f"System health aggregated from {len(observations)} observations. "
            f"CPU: {avg_cpu:.1f}%, Memory: {avg_mem:.1f}%, Disk: {avg_disk:.1f}%, "
            f"Network Latency: {avg_latency:.1f}ms. Health Score: {health_score:.3f}"
        )
        
        return {
            "confidence": health_score,
            "evidence_summary": evidence_summary,
            "metadata": {
                "average_cpu_utilization": avg_cpu,
                "average_memory_utilization": avg_mem,
                "average_disk_utilization": avg_disk,
                "average_network_latency": avg_latency,
                "health_score": health_score,
                "observation_count": len(observations)
            }
        }
    
    def _aggregate_network_activity(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Aggregate network activity observations"""
        total_connections = sum(
            getattr(obs.payload, 'connection_count', 0) 
            for obs in observations
        )
        
        total_bytes = sum(
            getattr(obs.payload, 'bytes_transferred', 0) 
            for obs in observations
        )
        
        # Combine protocols
        all_protocols = set()
        for obs in observations:
            if hasattr(obs.payload, 'top_protocols'):
                all_protocols.update(obs.payload.top_protocols)
        
        # Combine suspicious IPs
        all_suspicious_ips = set()
        for obs in observations:
            if hasattr(obs.payload, 'suspicious_ips'):
                all_suspicious_ips.update(obs.payload.suspicious_ips)
        
        evidence_summary = (
            f"Network activity aggregated from {len(observations)} observations. "
            f"Total connections: {total_connections}, Total bytes: {total_bytes}. "
            f"Protocols: {sorted(all_protocols)}. "
            f"Suspicious IPs detected: {len(all_suspicious_ips)}"
        )
        
        return {
            "confidence": min(len(observations) / 10.0, 1.0),  # Confidence based on observation count
            "evidence_summary": evidence_summary,
            "metadata": {
                "total_connections": total_connections,
                "total_bytes_transferred": total_bytes,
                "protocols": sorted(all_protocols),
                "suspicious_ip_count": len(all_suspicious_ips),
                "observation_count": len(observations)
            }
        }
    
    def _aggregate_custom(self, observations: List[ObservationV1]) -> Dict[str, Any]:
        """Default aggregation for custom observation types"""
        # Simple average confidence for custom types
        avg_confidence = sum(obs.confidence for obs in observations) / len(observations)
        
        evidence_summary = (
            f"Custom observation aggregated from {len(observations)} observations. "
            f"Average confidence: {avg_confidence:.3f}"
        )
        
        return {
            "confidence": avg_confidence,
            "evidence_summary": evidence_summary,
            "metadata": {
                "observation_count": len(observations),
                "observation_type": observations[0].observation_type
            }
        }
    
    def get_aggregation_statistics(self) -> Dict[str, Any]:
        """Get aggregation service statistics"""
        store_stats = self.observation_store.get_statistics()
        
        return {
            "feature_enabled": self.config.feature_enabled,
            "min_observations_for_belief": self.config.min_observations_for_belief,
            "confidence_threshold": self.config.confidence_threshold,
            "store_statistics": store_stats
        }
