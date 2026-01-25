"""
Tests for federation coordination state machine
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.coordination.coordination_state_machine import (
    CoordinationStateMachine, CoordinationConfig, CoordinationResult
)
from federation.coordination.coordination_models_v2 import (
    CoordinationType, CoordinationState, CoordinationRole,
    CoordinationScope, CoordinationAnnouncement, CoordinationClaim,
    CoordinationRelease, CoordinationObservation, CoordinationIntentBroadcast
)


class TestCoordinationStateMachine:
    """Test coordination state machine"""
    
    def test_state_machine_initialization(self):
        """Test state machine initialization"""
        config = CoordinationConfig(
            max_session_duration_hours=12,
            max_claim_duration_hours=2,
            cleanup_interval_seconds=60
        )
        
        machine = CoordinationStateMachine(config)
        
        assert machine.config.max_session_duration_hours == 12
        assert machine.config.max_claim_duration_hours == 2
        assert len(machine._sessions) == 0
        assert len(machine._announcements) == 0
        assert len(machine._claims) == 0
    
    def test_create_announcement_success(self):
        """Test successful announcement creation"""
        machine = CoordinationStateMachine()
        
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1", "cell-2"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        result = machine.create_announcement(announcement)
        
        assert result.success is True
        assert result.state == CoordinationState.UNCLAIMED
        assert "coordination_id" in result.data
        
        # Verify session created
        session = machine._sessions.get(result.data["coordination_id"])
        assert session is not None
        assert session.state == CoordinationState.UNCLAIMED
        assert session.coordinator_cell_id == "cell-1"
        
        # Verify announcement stored
        stored_announcement = machine._announcements.get(result.data["coordination_id"])
        assert stored_announcement is not None
        assert stored_announcement.owner_cell_id == "cell-1"
    
    def test_create_announcement_invalid_expiration(self):
        """Test announcement creation with invalid expiration"""
        machine = CoordinationStateMachine()
        
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        # Past expiration should fail at validation
        with pytest.raises(ValidationError, match="Expiration must be in the future"):
            announcement = CoordinationAnnouncement(
                owner_cell_id="cell-1",
                coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
                scope=scope,
                expiration_timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
            )
    
    def test_claim_coordination_success(self):
        """Test successful coordination claim"""
        machine = CoordinationStateMachine()
        
        # First create announcement
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1", "cell-2"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement_result = machine.create_announcement(announcement)
        coordination_id = announcement_result.data["coordination_id"]
        
        # Now claim coordination
        claim_scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1", "cell-2"]
        )
        
        claim = CoordinationClaim(
            owner_cell_id="cell-2",
            coordination_id=coordination_id,
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.COORDINATOR,
            claimed_resources=["compute"],
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        result = machine.claim_coordination(claim)
        
        assert result.success is True
        assert result.state == CoordinationState.CLAIMED
        assert "coordination_id" in result.data
        assert result.data["role"] == CoordinationRole.COORDINATOR
        
        # Verify session updated
        session = machine._sessions.get(coordination_id)
        assert session.state == CoordinationState.CLAIMED
        assert session.current_claim is not None
        assert session.current_claim.owner_cell_id == "cell-2"
        assert "cell-2" in session.participants
    
    def test_claim_coordination_already_claimed(self):
        """Test claiming already claimed coordination"""
        machine = CoordinationStateMachine()
        
        # Create announcement
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement_result = machine.create_announcement(announcement)
        coordination_id = announcement_result.data["coordination_id"]
        
        # First claim
        claim_scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        claim1 = CoordinationClaim(
            owner_cell_id="cell-1",
            coordination_id=coordination_id,
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.COORDINATOR,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        result1 = machine.claim_coordination(claim1)
        assert result1.success is True
        
        # Second claim should fail
        claim2 = CoordinationClaim(
            owner_cell_id="cell-2",
            coordination_id=coordination_id,
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.PARTICIPANT,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        result2 = machine.claim_coordination(claim2)
        assert result2.success is False
        assert result2.state == CoordinationState.CLAIMED
        assert "already claimed" in result2.message
    
    def test_release_coordination_success(self):
        """Test successful coordination release"""
        machine = CoordinationStateMachine()
        
        # Create and claim coordination
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement_result = machine.create_announcement(announcement)
        coordination_id = announcement_result.data["coordination_id"]
        
        claim_scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        claim = CoordinationClaim(
            owner_cell_id="cell-1",
            coordination_id=coordination_id,
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.COORDINATOR,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        machine.claim_coordination(claim)
        
        # Now release
        release = CoordinationRelease(
            coordination_id=coordination_id,
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            release_reason="Task completed",
            final_state=CoordinationState.RELEASED
        )
        
        result = machine.release_coordination(release)
        
        assert result.success is True
        assert result.state == CoordinationState.RELEASED
        
        # Verify session updated
        session = machine._sessions.get(coordination_id)
        assert session.state == CoordinationState.RELEASED
        assert session.current_claim is None
        assert session.final_state == CoordinationState.RELEASED
    
    def test_release_coordination_unauthorized(self):
        """Test releasing coordination without authorization"""
        machine = CoordinationStateMachine()
        
        # Create and claim coordination
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement_result = machine.create_announcement(announcement)
        coordination_id = announcement_result.data["coordination_id"]
        
        claim_scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        claim = CoordinationClaim(
            owner_cell_id="cell-1",
            coordination_id=coordination_id,
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=claim_scope,
            coordination_role=CoordinationRole.COORDINATOR,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        machine.claim_coordination(claim)
        
        # Try to release with different cell
        release = CoordinationRelease(
            coordination_id=coordination_id,
            owner_cell_id="cell-2",  # Different cell
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            release_reason="Unauthorized release",
            final_state=CoordinationState.RELEASED
        )
        
        result = machine.release_coordination(release)
        
        assert result.success is False
        assert "Not authorized" in result.message
    
    def test_add_observation_success(self):
        """Test successful observation addition"""
        machine = CoordinationStateMachine()
        
        # Create coordination
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1", "cell-2"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement_result = machine.create_announcement(announcement)
        coordination_id = announcement_result.data["coordination_id"]
        
        # Add observation
        obs_scope = CoordinationScope(
            coordination_type=CoordinationType.OBSERVATION_SHARING,
            affected_cells=["cell-1", "cell-2"]
        )
        
        observation = CoordinationObservation(
            observer_cell_id="cell-2",
            coordination_id=coordination_id,
            observation_type="resource_usage",
            observed_data={"cpu": 0.8, "memory": 0.6},
            confidence_score=0.9,
            observation_scope=obs_scope
        )
        
        result = machine.add_observation(observation)
        
        assert result.success is True
        assert "observation_id" in result.data
        
        # Verify observation added
        session = machine._sessions.get(coordination_id)
        assert len(session.observations) == 1
        assert session.observations[0].observer_cell_id == "cell-2"
        assert "cell-2" in session.participants
    
    def test_broadcast_intent_success(self):
        """Test successful intent broadcast"""
        machine = CoordinationStateMachine()
        
        intent = CoordinationIntentBroadcast(
            broadcaster_cell_id="cell-1",
            coordination_type=CoordinationType.INTENT_BROADCAST,
            intent_type="scale_up",
            intent_data={"target_instances": 5},
            target_cells=["cell-2", "cell-3"],
            priority=7,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        
        result = machine.broadcast_intent(intent)
        
        assert result.success is True
        assert "intent_id" in result.data
    
    def test_get_coordination_status(self):
        """Test getting coordination status"""
        machine = CoordinationStateMachine()
        
        # Create coordination
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        result = machine.create_announcement(announcement)
        coordination_id = result.data["coordination_id"]
        
        # Get status
        status = machine.get_coordination_status(coordination_id)
        
        assert status is not None
        assert status["coordination_id"] == coordination_id
        assert status["state"] == "unclaimed"
        assert status["coordinator_cell_id"] == "cell-1"
        assert status["coordination_type"] == "temporary_coordination"
        assert status["participants"] == ["cell-1"]
        assert status["is_expired"] is False
        assert status["observation_count"] == 0
        assert status["intent_count"] == 0
        assert status["current_claim"] is None
    
    def test_get_coordination_status_not_found(self):
        """Test getting status for non-existent coordination"""
        machine = CoordinationStateMachine()
        
        status = machine.get_coordination_status("non-existent")
        
        assert status is None
    
    def test_get_active_coordinations(self):
        """Test getting active coordinations"""
        machine = CoordinationStateMachine()
        
        # Create multiple coordinations
        scope1 = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        scope2 = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-2"]
        )
        
        announcement1 = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope1,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        announcement2 = CoordinationAnnouncement(
            owner_cell_id="cell-2",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope2,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        result1 = machine.create_announcement(announcement1)
        result2 = machine.create_announcement(announcement2)
        
        # Get all active coordinations
        all_active = machine.get_active_coordinations()
        assert len(all_active) == 2
        
        # Get coordinations for specific cell
        cell1_active = machine.get_active_coordinations("cell-1")
        assert len(cell1_active) == 1
        assert cell1_active[0]["coordinator_cell_id"] == "cell-1"
        
        cell2_active = machine.get_active_coordinations("cell-2")
        assert len(cell2_active) == 1
        assert cell2_active[0]["coordinator_cell_id"] == "cell-2"
    
    def test_event_handler_integration(self):
        """Test event handler integration"""
        machine = CoordinationStateMachine()
        
        # Mock event handler
        events_received = []
        
        def mock_handler(event):
            events_received.append(event)
        
        machine.add_event_handler(mock_handler)
        
        # Create announcement (should emit event)
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        machine.create_announcement(announcement)
        
        # Verify event was emitted
        assert len(events_received) == 1
        assert events_received[0].event_name == "announcement_created"
        assert events_received[0].owner_cell_id == "cell-1"
        
        # Remove handler
        machine.remove_event_handler(mock_handler)
        
        # Create another announcement (should not emit event)
        announcement2 = CoordinationAnnouncement(
            owner_cell_id="cell-2",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        machine.create_announcement(announcement2)
        
        # Should still have only one event
        assert len(events_received) == 1


class TestCoordinationStateMachineCleanup:
    """Test coordination state machine cleanup functionality"""
    
    @pytest.mark.asyncio
    async def test_expired_session_cleanup(self):
        """Test cleanup of expired sessions"""
        config = CoordinationConfig(cleanup_interval_seconds=1)  # Fast cleanup for testing
        machine = CoordinationStateMachine(config)
        
        # Create coordination that will expire quickly
        scope = CoordinationScope(
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.TEMPORARY_COORDINATION,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(seconds=2)  # Expire quickly
        )
        
        result = machine.create_announcement(announcement)
        coordination_id = result.data["coordination_id"]
        
        # Verify session exists and is not expired
        session = machine._sessions.get(coordination_id)
        assert session is not None
        assert not session.is_expired()
        assert session.state == CoordinationState.UNCLAIMED
        
        # Start cleanup task
        await machine.start_cleanup_task()
        
        # Wait for expiration and cleanup
        await asyncio.sleep(3)
        
        # Verify session is now expired
        session = machine._sessions.get(coordination_id)
        assert session is not None
        assert session.is_expired()
        assert session.state == CoordinationState.EXPIRED
        
        # Stop cleanup task
        await machine.stop_cleanup_task()
    
    def test_shutdown(self):
        """Test state machine shutdown"""
        machine = CoordinationStateMachine()
        
        # Add some data
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        machine.create_announcement(announcement)
        
        # Verify data exists
        assert len(machine._sessions) == 1
        assert len(machine._announcements) == 1
        
        # Shutdown
        machine.shutdown()
        
        # Verify data cleared
        assert len(machine._sessions) == 0
        assert len(machine._announcements) == 0
        assert len(machine._claims) == 0
        assert len(machine._event_handlers) == 0


class TestCoordinationStateMachineFeatureFlagIsolation:
    """Test that state machine respects feature flags"""
    
    def test_state_machine_without_feature_flags(self):
        """Test that state machine works without feature flags"""
        # State machine should work regardless of feature flags
        # Feature flag isolation is handled at the manager level
        machine = CoordinationStateMachine()
        
        scope = CoordinationScope(
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            affected_cells=["cell-1"]
        )
        
        announcement = CoordinationAnnouncement(
            owner_cell_id="cell-1",
            coordination_type=CoordinationType.AVAILABILITY_ANNOUNCEMENT,
            scope=scope,
            expiration_timestamp=datetime.now(timezone.utc) + timedelta(hours=6)
        )
        
        result = machine.create_announcement(announcement)
        
        assert result.success is True
        assert result.state == CoordinationState.UNCLAIMED
