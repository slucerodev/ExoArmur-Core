"""
# PHASE 2B — LOCKED
# Coordination logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Coordination Models
Pydantic v2 models for federation coordination matching coordination_v2.yaml contract
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid


class CoordinationType(str, Enum):
    """Types of coordination activities"""
    AVAILABILITY_ANNOUNCEMENT = "availability_announcement"
    CAPABILITY_SHARING = "capability_sharing"
    OBSERVATION_SHARING = "observation_sharing"
    INTENT_BROADCAST = "intent_broadcast"
    TEMPORARY_COORDINATION = "temporary_coordination"


class CoordinationState(str, Enum):
    """Coordination lifecycle states (minimal required set)"""
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    EXPIRED = "expired"
    RELEASED = "released"


class CoordinationRole(str, Enum):
    """Coordination roles a cell may assume"""
    COORDINATOR = "coordinator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class CoordinationScope(BaseModel):
    """Defines the scope and boundaries of coordination"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True  # Immutable scope definitions
    )
    
    coordination_type: CoordinationType
    affected_cells: List[str] = Field(default_factory=list)
    resource_types: List[str] = Field(default_factory=list)
    geographic_scope: Optional[str] = None
    temporal_scope: Optional[str] = None
    
    @field_validator('affected_cells')
    @classmethod
    def validate_affected_cells(cls, v):
        if len(v) > 50:  # Reasonable limit
            raise ValueError("Too many cells in coordination scope")
        return v


class CoordinationAnnouncement(BaseModel):
    """Announcement of availability for coordination"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True
    )
    
    coordination_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_cell_id: str
    coordination_type: CoordinationType
    scope: CoordinationScope
    announced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capabilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    expiration_timestamp: datetime
    
    @field_validator('expiration_timestamp')
    @classmethod
    def validate_expiration(cls, v, info):
        if v <= datetime.now(timezone.utc):
            raise ValueError("Expiration must be in the future")
        # Max 24 hour coordination announcements
        max_duration = datetime.now(timezone.utc) + timedelta(hours=24)
        if v > max_duration:
            raise ValueError("Expiration too far in future")
        return v


class CoordinationClaim(BaseModel):
    """Claim of temporary coordination role"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True
    )
    
    coordination_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_cell_id: str
    coordination_type: CoordinationType
    scope: CoordinationScope
    claimed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiration_timestamp: datetime
    coordination_role: CoordinationRole
    claimed_resources: List[str] = Field(default_factory=list)
    
    @field_validator('expiration_timestamp')
    @classmethod
    def validate_expiration(cls, v, info):
        if v <= datetime.now(timezone.utc):
            raise ValueError("Expiration must be in the future")
        # Max 1 hour coordination claims
        max_duration = datetime.now(timezone.utc) + timedelta(hours=1)
        if v > max_duration:
            raise ValueError("Claim duration too long")
        return v


class CoordinationRelease(BaseModel):
    """Release of coordination role"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True
    )
    
    coordination_id: str
    owner_cell_id: str
    coordination_type: CoordinationType
    released_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    release_reason: str = Field(max_length=200)
    final_state: CoordinationState


class CoordinationObservation(BaseModel):
    """Non-authoritative observation sharing"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True
    )
    
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observer_cell_id: str
    coordination_id: Optional[str] = None
    observation_type: str
    observed_data: Dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    observation_scope: CoordinationScope
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class CoordinationIntentBroadcast(BaseModel):
    """Non-binding intent broadcast"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        frozen=True
    )
    
    intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    broadcaster_cell_id: str
    coordination_type: CoordinationType
    intent_type: str
    intent_data: Dict[str, Any] = Field(default_factory=dict)
    broadcast_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime
    target_cells: List[str] = Field(default_factory=list)
    priority: int = Field(ge=1, le=10, default=5)
    
    @field_validator('valid_until')
    @classmethod
    def validate_valid_until(cls, v):
        if v <= datetime.now(timezone.utc):
            raise ValueError("Intent must be valid in the future")
        # Max 4 hour intent validity
        max_duration = datetime.now(timezone.utc) + timedelta(hours=4)
        if v > max_duration:
            raise ValueError("Intent validity too long")
        return v


class CoordinationEvent(BaseModel):
    """Audit event for coordination activities"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str
    coordination_id: str
    owner_cell_id: str
    coordination_type: CoordinationType
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_data: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Generate idempotency key after initialization
        if self.idempotency_key is None:
            self.idempotency_key = hashlib.sha256(
                f"{self.coordination_id}:{self.event_name}:{self.event_timestamp}".encode('utf-8')
            ).hexdigest()


class CoordinationSession(BaseModel):
    """Coordination session tracking"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    coordination_id: str
    coordinator_cell_id: str
    coordination_type: CoordinationType
    scope: CoordinationScope
    state: CoordinationState = CoordinationState.UNCLAIMED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiration_timestamp: datetime
    participants: List[str] = Field(default_factory=list)
    observations: List[CoordinationObservation] = Field(default_factory=list)
    intents: List[CoordinationIntentBroadcast] = Field(default_factory=list)
    current_claim: Optional[CoordinationClaim] = None
    final_state: Optional[CoordinationState] = None
    
    @field_validator('expiration_timestamp')
    @classmethod
    def validate_expiration(cls, v):
        if v <= datetime.now(timezone.utc):
            raise ValueError("Expiration must be in the future")
        # Max 24 hour coordination sessions
        max_duration = datetime.now(timezone.utc) + timedelta(hours=24)
        if v > max_duration:
            raise ValueError("Expiration too far in future")
        return v
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expiration_timestamp
    
    def can_participate(self, cell_id: str) -> bool:
        """Check if cell can participate in this coordination"""
        return (self.state in [CoordinationState.UNCLAIMED, CoordinationState.CLAIMED] and
                not self.is_expired() and
                (len(self.scope.affected_cells) == 0 or cell_id in self.scope.affected_cells))


# Import for idempotency key generation
import hashlib
