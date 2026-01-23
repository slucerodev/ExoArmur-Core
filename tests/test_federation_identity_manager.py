"""
Tests for V2 Federation Identity Manager
Validate main coordinator with feature flag isolation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.federation_identity_manager import FederationIdentityManager
from federation.identity_handshake_state_machine import HandshakeConfig
from federation.models.federation_identity_v2 import HandshakeState


class TestFederationIdentityManager:
    """Test federation identity manager functionality"""
    
    def test_manager_initialization_disabled(self):
        """Test manager initialization when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        assert manager.feature_flag_checker() is False
        assert manager._state_machine is None
        assert manager._audit_emitter is None
    
    def test_manager_initialization_enabled(self):
        """Test manager initialization when V2 federation is enabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        assert manager.feature_flag_checker() is True
        assert manager._state_machine is not None
        assert manager._audit_emitter is not None
    
    def test_manager_initialization_with_config(self):
        """Test manager initialization with custom config"""
        config = HandshakeConfig(
            buffer_window_ms=3000,
            minimum_trust_score=0.9
        )
        
        manager = FederationIdentityManager(
            config=config,
            feature_flag_checker=lambda: True
        )
        
        assert manager.config.buffer_window_ms == 3000
        assert manager.config.minimum_trust_score == 0.9
        assert manager._state_machine is not None
    
    def test_initiate_handshake_disabled(self):
        """Test initiating handshake when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        result = manager.initiate_handshake("cell-1", "cell-2")
        
        assert result.success is False
        assert result.state == HandshakeState.UNINITIALIZED
        assert "V2 federation is disabled" in result.message
    
    def test_initiate_handshake_enabled(self):
        """Test initiating handshake when V2 federation is enabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        result = manager.initiate_handshake("cell-1", "cell-2")
        
        assert result.success is True
        assert result.state == HandshakeState.IDENTITY_EXCHANGE
        assert "Handshake initiated" in result.message
    
    def test_process_message_disabled(self):
        """Test processing message when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        result = manager.process_message("identity_exchange", {}, "incoming")
        
        assert result.success is False
        assert result.state == HandshakeState.UNINITIALIZED
        assert "V2 federation is disabled" in result.message
    
    def test_process_message_enabled(self):
        """Test processing message when V2 federation is enabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # First initiate handshake
        manager.initiate_handshake("cell-1", "cell-2")
        
        # Then process message
        message_data = {
            "cell_identity": {
                "cell_id": "cell-us-east-1-cluster-01-node-01",
                "cell_public_key": "key",
                "cell_certificate_chain": ["cert"],
                "capabilities": ["belief_aggregation"],
                "trust_score": 0.8
            },
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:00Z",
            "nonce": "nonce"
        }
        
        result = manager.process_message("identity_exchange", message_data, "incoming")
        
        assert result.success is True
        assert result.state == HandshakeState.CAPABILITY_NEGOTIATION
    
    def test_get_handshake_status_disabled(self):
        """Test getting handshake status when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        status = manager.get_handshake_status()
        
        assert status is not None
        assert status["enabled"] is False
        assert status["status"] == "disabled"
        assert "feature flag is off" in status["reason"]
    
    def test_get_handshake_status_enabled_no_session(self):
        """Test getting handshake status when enabled but no session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        status = manager.get_handshake_status()
        
        assert status is not None
        assert status["enabled"] is True
        assert status["status"] == "no_active_session"
    
    def test_get_handshake_status_active_session(self):
        """Test getting handshake status with active session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Initiate handshake to create session
        manager.initiate_handshake("cell-1", "cell-2")
        
        status = manager.get_handshake_status()
        
        assert status is not None
        assert status["enabled"] is True
        assert status["status"] == "active"
        assert "session_info" in status
        assert status["is_complete"] is False
        assert status["is_failed"] is False
        assert status["current_state"] == HandshakeState.IDENTITY_EXCHANGE
    
    def test_get_audit_trail_disabled(self):
        """Test getting audit trail when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        trail = manager.get_audit_trail("session-123")
        
        assert trail is None
    
    def test_get_audit_trail_enabled(self):
        """Test getting audit trail when V2 federation is enabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        trail = manager.get_audit_trail("session-123")
        
        # Should return something (even if empty due to no audit logger)
        assert trail is not None
        assert "session_id" in trail
    
    def test_validate_audit_integrity_disabled(self):
        """Test audit integrity validation when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        validation = manager.validate_audit_integrity("session-123", 2)
        
        assert validation["valid"] is False
        assert validation["reason"] == "V2 federation is disabled"
    
    def test_is_federation_member_disabled(self):
        """Test federation membership check when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        result = manager.is_federation_member("cell-1")
        
        assert result is False
    
    def test_is_federation_member_enabled_no_session(self):
        """Test federation membership check when enabled but no session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        result = manager.is_federation_member("cell-1")
        
        assert result is False
    
    def test_is_federation_member_active_session(self):
        """Test federation membership check with active session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Initiate handshake
        manager.initiate_handshake("cell-1", "cell-2")
        
        # Check membership for initiator
        assert manager.is_federation_member("cell-1") is False  # Not yet ACTIVE
        
        # Check membership for non-member
        assert manager.is_federation_member("cell-3") is False
    
    def test_get_federation_members_disabled(self):
        """Test getting federation members when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        members = manager.get_federation_members()
        
        assert members == []
    
    def test_get_federation_members_enabled_no_session(self):
        """Test getting federation members when enabled but no session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        members = manager.get_federation_members()
        
        assert members == []
    
    def test_get_federation_members_active_session(self):
        """Test getting federation members with active session"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Initiate handshake
        manager.initiate_handshake("cell-1", "cell-2")
        
        members = manager.get_federation_members()
        
        # Should be empty until session is ACTIVE
        assert members == []
    
    def test_shutdown_disabled(self):
        """Test shutdown when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        result = manager.shutdown()
        
        assert result is True
    
    def test_shutdown_enabled(self):
        """Test shutdown when V2 federation is enabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        result = manager.shutdown()
        
        assert result is True
        assert manager._state_machine is None
        assert manager._audit_emitter is None
    
    def test_get_config_summary(self):
        """Test getting configuration summary"""
        config = HandshakeConfig(
            buffer_window_ms=3000,
            minimum_trust_score=0.9
        )
        
        manager = FederationIdentityManager(
            config=config,
            feature_flag_checker=lambda: True
        )
        
        summary = manager.get_config_summary()
        
        assert summary["v2_federation_enabled"] is True
        assert summary["buffer_window_ms"] == 3000
        assert summary["minimum_trust_score"] == 0.9
        assert summary["step_timeout_ms"] == 10000
        assert summary["max_retry_attempts"] == 3
    
    def test_health_check_disabled(self):
        """Test health check when V2 federation is disabled"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        health = manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["v2_federation_enabled"] is False
        assert "disabled" in health["reason"]
    
    def test_health_check_enabled_healthy(self):
        """Test health check when V2 federation is enabled and healthy"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        health = manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["v2_federation_enabled"] is True
        assert "no_session" in health["current_state"]
    
    def test_health_check_enabled_degraded(self):
        """Test health check when V2 federation is enabled but degraded"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Simulate failed state by manually setting state
        manager.initiate_handshake("cell-1", "cell-2")
        manager._state_machine.session.current_state = HandshakeState.FAILED_IDENTITY
        
        health = manager.health_check()
        
        assert health["status"] == "degraded"
        assert health["v2_federation_enabled"] is True
        assert "failed state" in health["reason"]
    
    def test_complete_handshake_flow(self):
        """Test complete handshake flow through identity manager"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # 1. Initiate handshake
        result = manager.initiate_handshake("cell-1", "cell-2")
        assert result.success is True
        assert result.state == HandshakeState.IDENTITY_EXCHANGE
        
        # 2. Process identity exchange
        identity_data = {
            "cell_identity": {
                "cell_id": "cell-us-east-1-cluster-01-node-01",
                "cell_public_key": "key",
                "cell_certificate_chain": ["cert"],
                "capabilities": ["belief_aggregation"],
                "trust_score": 0.8
            },
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:00Z",
            "nonce": "nonce"
        }
        result = manager.process_message("identity_exchange", identity_data, "incoming")
        assert result.success is True
        assert result.state == HandshakeState.CAPABILITY_NEGOTIATION
        
        # 3. Process capability negotiation
        cap_data = {
            "supported_capabilities": ["belief_aggregation"],
            "required_capabilities": ["belief_aggregation"],
            "priority": 1,
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:01Z",
            "nonce": "nonce2"
        }
        result = manager.process_message("capability_negotiate", cap_data, "incoming")
        assert result.success is True
        assert result.state == HandshakeState.TRUST_ESTABLISHMENT
        
        # 4. Process trust establishment
        trust_data = {
            "trust_score": 0.8,
            "trust_reasons": ["good_behavior"],
            "expiration": "2024-01-02T00:00:00Z",
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:02Z",
            "nonce": "nonce3"
        }
        result = manager.process_message("trust_establish", trust_data, "incoming")
        assert result.success is True
        assert result.state == HandshakeState.CONFIRMED
        
        # 5. Process federation confirmation
        confirm_data = {
            "federation_id": "fed-123",
            "member_cells": ["cell-1", "cell-2"],
            "coordinator_cell": "cell-1",
            "terms": {"version": "2.0"},
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:03Z",
            "nonce": "nonce4"
        }
        result = manager.process_message("federation_confirm", confirm_data, "incoming")
        assert result.success is True
        assert result.state == HandshakeState.ACTIVE
        
        # 6. Verify final status
        status = manager.get_handshake_status()
        assert status["is_complete"] is True
        assert status["is_failed"] is False
        assert status["current_state"] == HandshakeState.ACTIVE
        
        # 7. Verify membership
        assert manager.is_federation_member("cell-1") is True
        assert manager.is_federation_member("cell-2") is True
        assert manager.is_federation_member("cell-3") is False
        
        members = manager.get_federation_members()
        assert "cell-1" in members
        assert "cell-2" in members
        assert len(members) == 2


class TestFeatureFlagIsolation:
    """Test strict feature flag isolation"""
    
    def test_no_side_effects_when_disabled(self):
        """Test that disabled manager has no side effects"""
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        # All operations should fail gracefully with no side effects
        assert manager.initiate_handshake("cell-1", "cell-2").success is False
        assert manager.process_message("test", {}, "incoming").success is False
        assert manager.get_handshake_status()["enabled"] is False
        assert manager.get_audit_trail("session-123") is None
        assert manager.is_federation_member("cell-1") is False
        assert manager.get_federation_members() == []
        assert manager.health_check()["v2_federation_enabled"] is False
        
        # Shutdown should work fine
        assert manager.shutdown() is True
    
    def test_feature_flag_boundary_crossing(self):
        """Test that operations don't cross feature flag boundaries"""
        # Create manager with disabled flag
        manager_disabled = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        # Create manager with enabled flag
        manager_enabled = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Disabled manager should not affect enabled manager
        result_disabled = manager_disabled.initiate_handshake("cell-1", "cell-2")
        result_enabled = manager_enabled.initiate_handshake("cell-1", "cell-2")
        
        assert result_disabled.success is False
        assert result_enabled.success is True
        
        # Each manager should have independent state
        assert manager_disabled.get_handshake_status()["enabled"] is False
        assert manager_enabled.get_handshake_status()["enabled"] is True
    
    def test_diagnostic_event_only_when_disabled(self):
        """Test that only diagnostic events are emitted when disabled"""
        # Create manager with disabled flag (no audit interface needed)
        manager = FederationIdentityManager(
            feature_flag_checker=lambda: False,
            audit_interface=None
        )
        
        # Try to initiate handshake
        result = manager.initiate_handshake("cell-1", "cell-2")
        
        # Should return failure result since components are not initialized
        assert result.success is False
        assert "disabled" in result.message.lower()
        
        # Health check should show disabled status
        health = manager.health_check()
        assert health["v2_federation_enabled"] is False
