"""
Tests for federation coordination models
"""

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

# Add src to path

from exoarmur.federation.coordination.coordination_models_v2 import (
    CoordinationType, CoordinationState, CoordinationRole,
    CoordinationScope, CoordinationAnnouncement, CoordinationClaim,
    CoordinationRelease, CoordinationObservation, CoordinationIntentBroadcast,
    CoordinationEvent, CoordinationSession
)


class TestCoordinationModels:
    """Test federation coordination models"""
    
    def test_coordination_scope_creation(self):
        """Test coordination scope creation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1", "cell-2"],
            resource_types=["compute", "storage"],
            geographic_scope="us-west",
            temporal_scope="business-hours"
        )
        
        assert scope.coordination_type == CoordinationType.AVAILABILITY_ANNOUNCEMENT
        assert len(scope.affected_cells) == 2
        assert "compute" in scope.resource_types
        assert scope.geographic_scope == "us-west"
        assert scope.temporal_scope == "business-hours"
    
    def test_coordination_scope_too_many_cells(self):
        """Test coordination scope with too many cells"""
        with pytest.raises(ValidationError, match="Too many cells"):
            CoordinationScope(
                coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
                affected_cells=[f"cell-{i}" for i in range(51)]  # Too many
            )
    
    def test_coordination_announcement_creation(self):
        """Test coordination announcement creation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            capabilities=["federation", "compute"],
            requirements=["trust-score>0.7"],
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        
        assert announcement.owner_cell_id == "cell-1"
        assert announcement.coordination_type == CoordinationType.AVAILABILITY_ANNOUNCEMENT
        assert len(announcement.capabilities) == 2
        assert announcement.expiration_timestamp > datetime.now(timezone.utc)
        assert announcement.coordination_id is not None
    
    def test_coordination_announcement_expiration_validation(self):
        """Test coordination announcement expiration validation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        # Past expiration should fail
        with pytest.raises(ValidationError, match="Expiration must be in the future"):
            CoordinationAnnouncement(
                owner_cell_id="cell-1",
                coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
                scope=scope,
                expiration_timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
            )
        
        # Too far in future should fail
        with pytest.raises(ValidationError, match="Expiration too far in future"):
            CoordinationAnnouncement(
                owner_cell_id="cell-1",
                coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
                scope=scope,
                expiration_timestamp=datetime.now(timezone.utc) + timedelta(days=2)
            )
    
    def test_coordination_claim_creation(self):
        """Test coordination claim creation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1", "cell-2"]
        )
        
        claim = CoordinationClaim(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            coordination_role=CoordinationRole.COORDINATOR,
            claimed_resources=["compute"],
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        assert claim.owner_cell_id == "cell-1"
        assert claim.coordination_role == CoordinationRole.COORDINATOR
        assert len(claim.claimed_resources) == 1
        assert claim.expiration_timestamp > datetime.now(timezone.utc)
    
    def test_coordination_release_creation(self):
        """Test coordination release creation"""
        release = CoordinationRelease(
            coordination_id="test-coord-123",
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            release_reason="Task completed",
            final_state=CoordinationState.RELEASED
        )
        
        assert release.coordination_id == "test-coord-123"
        assert release.owner_cell_id == "cell-1"
        assert release.release_reason == "Task completed"
        assert release.final_state == CoordinationState.RELEASED
    
    def test_coordination_observation_creation(self):
        """Test coordination observation creation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.OBSERVATION_SHARING,
            affected_cells=["cell-1"]
        )
        
        observation = CoordinationObservation(
            observer_cell_id="cell-2",
            coordination_id="test-coord-123",
            observation_type="resource_usage",
            observed_data={"cpu": 0.8, "memory": 0.6},
            confidence_score=0.9,
            observation_scope=scope
        )
        
        assert observation.observer_cell_id == "cell-2"
        assert observation.observation_type == "resource_usage"
        assert observation.confidence_score == 0.9
        assert "cpu" in observation.observed_data
    
    def test_coordination_observation_confidence_validation(self):
        """Test coordination observation confidence validation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.OBSERVATION_SHARING,
            affected_cells=["cell-1"]
        )
        
        # Invalid confidence should fail
        with pytest.raises(ValidationError, match="Input should be less than or equal to 1"):
            CoordinationObservation(
                observer_cell_id="cell-2",
                observation_type="resource_usage",
                observed_data={"cpu": 0.8},
                confidence_score=1.5,  # Invalid
                observation_scope=scope
            )
    
    def test_coordination_intent_broadcast_creation(self):
        """Test coordination intent broadcast creation"""
        intent = CoordinationIntentBroadcast(
            broadcaster_cell_id="cell-1",
            coordination_type=CoordinationType.INTENT_BROADCAST,
            intent_type="scale_up",
            intent_data={"target_instances": 5},
            target_cells=["cell-2", "cell-3"],
            priority=7,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        
        assert intent.broadcaster_cell_id == "cell-1"
        assert intent.intent_type == "scale_up"
        assert intent.target_cells == ["cell-2", "cell-3"]
        assert intent.priority == 7
        assert intent.valid_until > datetime.now(timezone.utc)
    
    def test_coordination_intent_priority_validation(self):
        """Test coordination intent priority validation"""
        # Invalid priority should fail
        with pytest.raises(ValidationError, match="priority"):
            CoordinationIntentBroadcast(
                broadcaster_cell_id="cell-1",
                coordination_type=CoordinationType.INTENT_BROADCAST,
                intent_type="scale_up",
                intent_data={"target_instances": 5},
                priority=15  # Invalid (> 10)
            )
    
    def test_coordination_session_creation(self):
        """Test coordination session creation"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1", "cell-2"]
        )
        
        session = CoordinationSession(
            coordination_id="test-session-123",
            coordinator_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert session.coordination_id == "test-session-123"
        assert session.coordinator_cell_id == "cell-1"
        assert session.state == CoordinationState.UNCLAIMED
        assert not session.is_expired()
        assert session.can_participate("cell-1")
        assert session.can_participate("cell-2")
        assert not session.can_participate("cell-3")
    
    def test_coordination_session_expiration(self):
        """Test coordination session expiration"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        # Expired session
        expired_session = CoordinationSession(
            coordination_id="expired-session",
            coordinator_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        assert expired_session.is_expired()
        assert not expired_session.can_participate("cell-1")
    
    def test_coordination_event_idempotency_key(self):
        """Test coordination event idempotency key generation"""
        event = CoordinationEvent(
            event_name="test_event",
            coordination_id="test-coord-123",
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            event_data={"test": "data"}
        )
        
        assert event.idempotency_key is not None
        assert len(event.idempotency_key) == 64  # SHA256 hex length
        
        # Same event should generate same key
        event2 = CoordinationEvent(
            event_name="test_event",
            coordination_id="test-coord-123",
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            event_data={"test": "data"}
        )
        
        assert event.idempotency_key == event2.idempotency_key


class TestCoordinationModelSerialization:
    """Test coordination model serialization"""
    
    def test_coordination_announcement_serialization(self):
        """Test coordination announcement serialization"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Test JSON serialization
        json_data = announcement.model_dump()
        
        assert json_data["owner_cell_id"] == "cell-1"
        assert json_data["coordination_type"] == "availability_announcement"
        assert "scope" in json_data
        assert "expiration_timestamp" in json_data
        
        # Test deserialization
        announcement2 = CoordinationAnnouncement(**json_data)
        assert announcement2.owner_cell_id == announcement.owner_cell_id
        assert announcement2.coordination_id == announcement.coordination_id
    
    def test_coordination_session_serialization(self):
        """Test coordination session serialization"""
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        session = CoordinationSession(
            coordination_id="test-session",
            coordinator_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Test JSON serialization
        json_data = session.model_dump()
        
        assert json_data["coordination_id"] == "test-session"
        assert json_data["state"] == "unclaimed"
        assert json_data["participants"] == []
        
        # Test deserialization
        session2 = CoordinationSession(**json_data)
        assert session2.coordination_id == session.coordination_id
        assert session2.state == session.state


class TestCoordinationFeatureFlagIsolation:
    """Test that coordination models work without feature flags"""
    
    def test_models_work_without_feature_flags(self):
        """Test that models can be created without feature flags"""
        # All models should be instantiable without any feature flag checks
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        claim_scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        claim = CoordinationClaim(
            owner_cell_id="cell-1",
            coordination_id="test-claim-123",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.PARTICIPANT,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        # All should work without any feature flag dependencies
        assert scope.coordination_type == CoordinationType.AVAILABILITY_ANNOUNCEMENT
        assert announcement.coordination_id is not None
        assert claim.coordination_id is not None
