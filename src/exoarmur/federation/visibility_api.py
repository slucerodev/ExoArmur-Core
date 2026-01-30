"""
ExoArmur ADMO V2 Visibility API
Read-only endpoints for federation coordination visibility
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    ArbitrationV1,
    ArbitrationStatus,
    ArbitrationConflictType,
    FederateIdentityV1,
    ObservationType
)
from .observation_store import ObservationStore
from .federate_identity_store import FederateIdentityStore
from .belief_aggregation import BeliefAggregationService
from .observation_ingest import ObservationIngestService
from .clock import Clock

logger = logging.getLogger(__name__)

# API Models for responses
class FederateInfo(BaseModel):
    """Information about a federate"""
    federate_id: str = Field(description="Federate identifier")
    federation_role: str = Field(description="Federation role")
    cell_status: str = Field(description="Cell status")
    created_at: datetime = Field(description="When federate was created")
    updated_at: datetime = Field(description="When federate was last updated")
    public_key: str = Field(description="Public key fingerprint")


class ObservationInfo(BaseModel):
    """Information about an observation"""
    observation_id: str = Field(description="Observation identifier")
    source_federate_id: str = Field(description="Source federate ID")
    timestamp_utc: datetime = Field(description="Observation timestamp")
    correlation_id: Optional[str] = Field(description="Correlation ID")
    observation_type: str = Field(description="Observation type")
    confidence: float = Field(description="Confidence score")
    evidence_refs: List[str] = Field(description="Evidence references")
    payload_type: str = Field(description="Payload type")
    payload_data: Dict[str, Any] = Field(description="Payload data")


class BeliefInfo(BaseModel):
    """Information about a belief"""
    belief_id: str = Field(description="Belief identifier")
    belief_type: str = Field(description="Belief type")
    confidence: float = Field(description="Confidence score")
    source_observations: List[str] = Field(description="Source observation IDs")
    derived_at: datetime = Field(description="When belief was derived")
    correlation_id: Optional[str] = Field(description="Correlation ID")
    evidence_summary: str = Field(description="Evidence summary")
    conflicts: List[str] = Field(description="Conflicting belief IDs")
    metadata: Dict[str, Any] = Field(description="Additional metadata")


class TimelineInfo(BaseModel):
    """Timeline information for correlation ID"""
    correlation_id: str = Field(description="Correlation ID")
    observations: List[ObservationInfo] = Field(description="Observations")
    beliefs: List[BeliefInfo] = Field(description="Beliefs")


class ArbitrationInfo(BaseModel):
    """Information about an arbitration"""
    arbitration_id: str = Field(description="Arbitration identifier")
    created_at_utc: datetime = Field(description="When arbitration was created")
    status: ArbitrationStatus = Field(description="Current arbitration status")
    conflict_type: ArbitrationConflictType = Field(description="Type of conflict")
    subject_key: str = Field(description="Subject of the conflict")
    conflict_key: str = Field(description="Deterministic conflict key")
    claims: List[Dict[str, Any]] = Field(description="Conflicting claims/beliefs")
    evidence_refs: List[str] = Field(description="Evidence references")
    correlation_id: Optional[str] = Field(description="Correlation ID")
    conflicts_detected: List[Dict[str, Any]] = Field(description="Detected conflicts")
    proposed_resolution: Optional[Dict[str, Any]] = Field(description="Proposed resolution")
    decision: Optional[Dict[str, Any]] = Field(description="Final decision after approval")
    approval_id: Optional[str] = Field(description="Approval request ID")
    resolved_at_utc: Optional[datetime] = Field(description="When arbitration was resolved")
    resolver_federate_id: Optional[str] = Field(description="Federate that resolved the conflict")
    resolution_applied_at_utc: Optional[datetime] = Field(description="When resolution was applied")
    metadata: Dict[str, Any] = Field(description="Additional metadata")


class VisibilityAPI:
    """Read-only API for federation coordination visibility"""
    
    def __init__(
        self,
        observation_store: ObservationStore,
        identity_store: FederateIdentityStore,
        belief_service: BeliefAggregationService,
        ingest_service: ObservationIngestService,
        clock: Clock,
        arbitration_service=None
    ):
        self.observation_store = observation_store
        self.identity_store = identity_store
        self.belief_service = belief_service
        self.ingest_service = ingest_service
        self.clock = clock
        self.arbitration_service = arbitration_service
        
        # Create FastAPI router
        self.router = APIRouter(prefix="/api/v2/visibility", tags=["visibility"])
        
        # Register endpoints
        self._register_endpoints()
        
        logger.info("VisibilityAPI initialized")
    
    def _register_endpoints(self):
        """Register all API endpoints"""
        
        @self.router.get("/federates", response_model=List[FederateInfo])
        async def list_federates():
            """List all federates with their status"""
            try:
                federates = []
                
                # Get all federate identities
                # Note: FederateIdentityStore would need a list_all method
                # For now, we'll return an empty list as placeholder
                
                return federates
                
            except Exception as e:
                logger.error(f"Error listing federates: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/observations", response_model=List[ObservationInfo])
        async def list_observations(
            federate_id: Optional[str] = Query(None, description="Filter by federate ID"),
            correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
            observation_type: Optional[str] = Query(None, description="Filter by observation type"),
            limit: Optional[int] = Query(100, description="Maximum number to return"),
            since: Optional[str] = Query(None, description="Filter by timestamp (ISO format)")
        ):
            """List observations with optional filters"""
            try:
                # Parse since timestamp
                since_dt = None
                if since:
                    try:
                        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid since timestamp format")
                
                # Get observations
                observations = self.observation_store.list_observations(
                    federate_id=federate_id,
                    correlation_id=correlation_id,
                    observation_type=observation_type,
                    limit=limit,
                    since=since_dt
                )
                
                # Convert to response format
                observation_infos = []
                for obs in observations:
                    info = ObservationInfo(
                        observation_id=obs.observation_id,
                        source_federate_id=obs.source_federate_id,
                        timestamp_utc=obs.timestamp_utc,
                        correlation_id=obs.correlation_id,
                        observation_type=obs.observation_type,
                        confidence=obs.confidence,
                        evidence_refs=obs.evidence_refs,
                        payload_type=obs.payload.payload_type,
                        payload_data=obs.payload.data if hasattr(obs.payload, 'data') else {}
                    )
                    observation_infos.append(info)
                
                return observation_infos
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error listing observations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/beliefs", response_model=List[BeliefInfo])
        async def list_beliefs(
            correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
            belief_type: Optional[str] = Query(None, description="Filter by belief type"),
            limit: Optional[int] = Query(100, description="Maximum number to return"),
            since: Optional[str] = Query(None, description="Filter by timestamp (ISO format)")
        ):
            """List beliefs with optional filters"""
            try:
                # Parse since timestamp
                since_dt = None
                if since:
                    try:
                        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid since timestamp format")
                
                # Get beliefs
                beliefs = self.observation_store.list_beliefs(
                    correlation_id=correlation_id,
                    belief_type=belief_type,
                    limit=limit,
                    since=since_dt
                )
                
                # Convert to response format
                belief_infos = []
                for belief in beliefs:
                    # Handle both BeliefTelemetryV1 and BeliefV1
                    if hasattr(belief, 'belief_type'):
                        # BeliefV1
                        info = BeliefInfo(
                            belief_id=belief.belief_id,
                            belief_type=belief.belief_type,
                            confidence=belief.confidence,
                            source_observations=belief.source_observations,
                            derived_at=belief.derived_at,
                            correlation_id=belief.correlation_id,
                            evidence_summary=belief.evidence_summary,
                            conflicts=getattr(belief, 'conflicts', []),
                            metadata=getattr(belief, 'metadata', {})
                        )
                    else:
                        # BeliefTelemetryV1 - convert to BeliefInfo format
                        info = BeliefInfo(
                            belief_id=belief.belief_id,
                            belief_type=belief.claim_type,  # Map claim_type to belief_type
                            confidence=belief.confidence,
                            source_observations=list(belief.evidence_refs.get('event_ids', [])),  # Convert evidence_refs
                            derived_at=belief.first_seen,  # Use first_seen as derived_at
                            correlation_id=belief.correlation_id,
                            evidence_summary=f"Claim: {belief.claim_type}",  # Generate summary
                            conflicts=[],  # BeliefTelemetryV1 doesn't have conflicts
                            metadata={}  # BeliefTelemetryV1 doesn't have metadata
                        )
                    belief_infos.append(info)
                
                return belief_infos
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error listing beliefs: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/timeline/{correlation_id}", response_model=TimelineInfo)
        async def get_timeline_by_correlation_id(correlation_id: str):
            """Get timeline of observations and beliefs for a correlation ID"""
            try:
                # Get timeline data
                timeline = self.observation_store.get_timeline_by_correlation(correlation_id)
                
                # Convert observations
                observation_infos = []
                for obs in timeline["observations"]:
                    info = ObservationInfo(
                        observation_id=obs.observation_id,
                        source_federate_id=obs.source_federate_id,
                        timestamp_utc=obs.timestamp_utc,
                        correlation_id=obs.correlation_id,
                        observation_type=obs.observation_type,
                        confidence=obs.confidence,
                        evidence_refs=obs.evidence_refs,
                        payload_type=obs.payload.payload_type,
                        payload_data=obs.payload.data if hasattr(obs.payload, 'data') else {}
                    )
                    observation_infos.append(info)
                
                # Convert beliefs
                belief_infos = []
                for belief in timeline["beliefs"]:
                    info = BeliefInfo(
                        belief_id=belief.belief_id,
                        belief_type=belief.belief_type,
                        confidence=belief.confidence,
                        source_observations=belief.source_observations,
                        derived_at=belief.derived_at,
                        correlation_id=belief.correlation_id,
                        evidence_summary=belief.evidence_summary,
                        conflicts=belief.conflicts,
                        metadata=belief.metadata
                    )
                    belief_infos.append(info)
                
                # Sort by timestamp for proper timeline order
                all_events = []
                for obs_info in observation_infos:
                    all_events.append((obs_info.timestamp_utc, "observation", obs_info))
                for belief_info in belief_infos:
                    all_events.append((belief_info.derived_at, "belief", belief_info))
                
                all_events.sort(key=lambda x: x[0])
                
                # Reconstruct sorted lists
                sorted_observations = []
                sorted_beliefs = []
                for timestamp, event_type, data in all_events:
                    if event_type == "observation":
                        sorted_observations.append(data)
                    else:
                        sorted_beliefs.append(data)
                
                return TimelineInfo(
                    correlation_id=correlation_id,
                    observations=sorted_observations,
                    beliefs=sorted_beliefs
                )
                
            except Exception as e:
                logger.error(f"Error getting timeline: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/statistics")
        async def get_statistics():
            """Get visibility system statistics"""
            try:
                ingest_stats = self.ingest_service.get_ingest_statistics()
                belief_stats = self.belief_service.get_aggregation_statistics()
                store_stats = self.observation_store.get_statistics()
                
                stats = {
                    "ingest_statistics": ingest_stats,
                    "belief_statistics": belief_stats,
                    "store_statistics": store_stats,
                    "timestamp": self.clock.now().isoformat().replace('+00:00', 'Z')
                }
                
                # Add arbitration statistics if service is available
                if self.arbitration_service:
                    arb_stats = self.arbitration_service.get_statistics()
                    stats["arbitration_statistics"] = arb_stats
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Arbitration endpoints (feature flagged)
        if self.arbitration_service:
            self._register_arbitration_endpoints()
    
    def _register_arbitration_endpoints(self):
        """Register arbitration endpoints"""
        
        @self.router.get("/arbitrations", response_model=List[ArbitrationInfo])
        async def list_arbitrations(
            status: Optional[ArbitrationStatus] = Query(None, description="Filter by status"),
            conflict_type: Optional[ArbitrationConflictType] = Query(None, description="Filter by conflict type"),
            correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
            limit: Optional[int] = Query(100, description="Maximum number to return")
        ):
            """List arbitrations with optional filters"""
            try:
                arbitrations = self.arbitration_service.list_arbitrations(
                    status=status,
                    conflict_type=conflict_type,
                    correlation_id=correlation_id,
                    limit=limit
                )
                
                # Convert to response format
                arbitration_infos = []
                for arb in arbitrations:
                    info = ArbitrationInfo(
                        arbitration_id=arb.arbitration_id,
                        created_at_utc=arb.created_at_utc,
                        status=arb.status,
                        conflict_type=arb.conflict_type,
                        subject_key=arb.subject_key,
                        conflict_key=arb.conflict_key,
                        claims=arb.claims,
                        evidence_refs=arb.evidence_refs,
                        correlation_id=arb.correlation_id,
                        conflicts_detected=arb.conflicts_detected,
                        proposed_resolution=arb.proposed_resolution,
                        decision=arb.decision,
                        approval_id=arb.approval_id,
                        resolved_at_utc=arb.resolved_at_utc,
                        resolver_federate_id=arb.resolver_federate_id,
                        resolution_applied_at_utc=arb.resolution_applied_at_utc,
                        metadata=arb.metadata
                    )
                    arbitration_infos.append(info)
                
                return arbitration_infos
                
            except Exception as e:
                logger.error(f"Error listing arbitrations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/arbitrations/{arbitration_id}", response_model=ArbitrationInfo)
        async def get_arbitration(arbitration_id: str):
            """Get arbitration by ID"""
            try:
                arbitration = self.arbitration_service.get_arbitration(arbitration_id)
                if not arbitration:
                    raise HTTPException(status_code=404, detail="Arbitration not found")
                
                return ArbitrationInfo(
                    arbitration_id=arbitration.arbitration_id,
                    created_at_utc=arbitration.created_at_utc,
                    status=arbitration.status,
                    conflict_type=arbitration.conflict_type,
                    subject_key=arbitration.subject_key,
                    conflict_key=arbitration.conflict_key,
                    claims=arbitration.claims,
                    evidence_refs=arbitration.evidence_refs,
                    correlation_id=arbitration.correlation_id,
                    conflicts_detected=arbitration.conflicts_detected,
                    proposed_resolution=arbitration.proposed_resolution,
                    decision=arbitration.decision,
                    approval_id=arbitration.approval_id,
                    resolved_at_utc=arbitration.resolved_at_utc,
                    resolver_federate_id=arbitration.resolver_federate_id,
                    resolution_applied_at_utc=arbitration.resolution_applied_at_utc,
                    metadata=arbitration.metadata
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting arbitration {arbitration_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router"""
        return self.router
