"""
Tests for V2 Federation Identity Handshake State Machine
Validate deterministic state transitions and event emission
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.identity_handshake_state_machine import (
    IdentityHandshakeStateMachine,
    HandshakeConfig,
    HandshakeEvent,
    HandshakeResult,
)
from federation.models.federation_identity_v2 import (
    HandshakeState,
    CellIdentity,
    CapabilityType,
)


class TestHandshakeConfig:
    """Test handshake configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = HandshakeConfig()
        
        assert config.buffer_window_ms == 5000
        assert config.step_timeout_ms == 10000
        assert config.minimum_trust_score == 0.7
        assert config.max_retry_attempts == 3
        assert config.retry_backoff_base_ms == 1000
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = HandshakeConfig(
            buffer_window_ms=3000,
            step_timeout_ms=15000,
            minimum_trust_score=0.8,
            max_retry_attempts=5,
            retry_backoff_base_ms=2000
        )
        
        assert config.buffer_window_ms == 3000
        assert config.step_timeout_ms == 15000
        assert config.minimum_trust_score == 0.8
        assert config.max_retry_attempts == 5
        assert config.retry_backoff_base_ms == 2000


class TestHandshakeEvent:
    """Test handshake event creation and idempotency"""
    
    def test_event_creation(self):
        """Test event creation with required fields"""
        event = HandshakeEvent(
            event_name="test_event",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"test": "data"}
        )
        
        assert event.event_name == "test_event"
        assert event.session_id == "session-123"
        assert event.step_index == 0
        assert event.data["test"] == "data"
        assert len(event.idempotency_key) == 64  # SHA-256 hex string
    
    def test_idempotency_key_determinism(self):
        """Test idempotency key is deterministic"""
        event1 = HandshakeEvent(
            event_name="test_event",
            session_id="session-123",
            step_index=0,
            timestamp=datetime.now(timezone.utc)
        )
        
        event2 = HandshakeEvent(
            event_name="test_event",
            session_id="session-123",
            step_index=0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Same inputs should produce same idempotency key
        assert event1.idempotency_key == event2.idempotency_key
        
        # Different inputs should produce different keys
        event3 = HandshakeEvent(
            event_name="test_event",
            session_id="session-123",
            step_index=1,  # Different step index
            timestamp=datetime.now(timezone.utc)
        )
        
        assert event1.idempotency_key != event3.idempotency_key


class TestHandshakeResult:
    """Test handshake result creation"""
    
    def test_success_result(self):
        """Test successful result"""
        result = HandshakeResult(True, HandshakeState.ACTIVE, "Success", {"key": "value"})
        
        assert result.success is True
        assert result.state == HandshakeState.ACTIVE
        assert result.message == "Success"
        assert result.data["key"] == "value"
        assert bool(result) is True
    
    def test_failure_result(self):
        """Test failed result"""
        result = HandshakeResult(False, HandshakeState.FAILED_IDENTITY, "Failed")
        
        assert result.success is False
        assert result.state == HandshakeState.FAILED_IDENTITY
        assert result.message == "Failed"
        assert result.data == {}
        assert bool(result) is False


class TestIdentityHandshakeStateMachine:
    """Test identity handshake state machine"""
    
    def test_state_machine_initialization(self):
        """Test state machine initialization"""
        machine = IdentityHandshakeStateMachine()
        
        assert machine.session is None
        assert machine.transcript_builder is None
        assert len(machine.event_handlers) == 0
        assert len(machine._message_buffer) == 0
        assert len(machine._retry_attempts) == 0
    
    def test_state_machine_with_config(self):
        """Test state machine with custom configuration"""
        config = HandshakeConfig(minimum_trust_score=0.9)
        machine = IdentityHandshakeStateMachine(config)
        
        assert machine.config.minimum_trust_score == 0.9
    
    def test_initiate_handshake_success(self):
        """Test successful handshake initiation"""
        machine = IdentityHandshakeStateMachine()
        
        result = machine.initiate_handshake("cell-1", "cell-2")
        
        assert result.success is True
        assert result.state == HandshakeState.IDENTITY_EXCHANGE
        assert "Handshake initiated" in result.message
        
        # Check session creation
        assert machine.session is not None
        assert machine.session.initiator_cell_id == "cell-1"
        assert machine.session.responder_cell_id == "cell-2"
        assert machine.session.current_state == HandshakeState.IDENTITY_EXCHANGE
        assert machine.session.step_index == 0  # Step index starts at 0
        
        assert len(machine.session.session_id) == 64  # SHA-256 hex
        assert len(machine.session.session_nonce) == 32  # 128-bit hex
        
        # Check transcript builder
        assert machine.transcript_builder is not None
        assert len(machine.transcript_builder.messages) == 1  # Session initiation message
    
    def test_initiate_handshake_event_emission(self):
        """Test event emission during handshake initiation"""
        events = []
        
        def event_handler(event):
            events.append(event)
        
        machine = IdentityHandshakeStateMachine()
        machine.add_event_handler(event_handler)
        
        result = machine.initiate_handshake("cell-1", "cell-2")
        
        assert result.success is True
        assert len(events) == 1
        assert events[0].event_name == "handshake_initiated"
        assert events[0].session_id == machine.session.session_id
        assert events[0].step_index == 0  # Step index should be 0 at initiation
        assert "session_nonce" in events[0].data
    
    def test_process_identity_exchange_success(self):
        """Test successful identity exchange processing"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Create valid identity exchange message
        base64_public_identifier = "ZXhhbXBsZV9wdWJsaWNfaWRlbnRpZmllcg=="  # "example_public_identifier" in base64
        
        message_data = {
            "cell_identity": {
                "cell_id": "cell-us-east-1-cluster-01-node-01",
                "cell_public_key": base64_public_key,
                "cell_certificate_chain": ["-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"],
                "capabilities": ["belief_aggregation"],
                "trust_score": 0.8
            },
            "signature": "signature123",
            "timestamp": "2024-01-01T00:00:00Z",
            "nonce": "nonce456"
        }
        
        result = machine.process_message("identity_exchange", message_data, "incoming")
        
        assert result.success is True
        assert result.state == HandshakeState.CAPABILITY_NEGOTIATION
        assert "Identity verification completed" in result.message
    
    def test_process_identity_exchange_missing_fields(self):
        """Test identity exchange with missing required fields"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Missing required fields
        message_data = {
            "cell_identity": {"cell_id": "cell-1"},
            # Missing signature, timestamp, nonce
        }
        
        result = machine.process_message("identity_exchange", message_data, "incoming")
        
        assert result.success is False
        assert result.state == HandshakeState.IDENTITY_EXCHANGE
        assert "Missing required field" in result.message
    
    def test_process_capability_negotiation_success(self):
        """Test successful capability negotiation"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # First complete identity exchange
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
        machine.process_message("identity_exchange", identity_data, "incoming")
        
        # Process capability negotiation
        cap_data = {
            "supported_capabilities": ["belief_aggregation", "policy_distribution"],
            "required_capabilities": ["belief_aggregation"],
            "priority": 1,
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:01Z",
            "nonce": "nonce2"
        }
        
        result = machine.process_message("capability_negotiate", cap_data, "incoming")
        
        assert result.success is True
        assert result.state == HandshakeState.TRUST_ESTABLISHMENT
        assert "Capability negotiation completed" in result.message
    
    def test_process_trust_establish_success(self):
        """Test successful trust establishment"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Complete previous steps
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
        machine.process_message("identity_exchange", identity_data, "incoming")
        
        cap_data = {
            "supported_capabilities": ["belief_aggregation"],
            "required_capabilities": ["belief_aggregation"],
            "priority": 1,
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:01Z",
            "nonce": "nonce2"
        }
        machine.process_message("capability_negotiate", cap_data, "incoming")
        
        # Process trust establishment
        trust_data = {
            "trust_score": 0.8,
            "trust_reasons": ["good_behavior", "successful_interactions"],
            "expiration": "2024-01-02T00:00:00Z",
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:02Z",
            "nonce": "nonce3"
        }
        
        result = machine.process_message("trust_establish", trust_data, "incoming")
        
        assert result.success is True
        assert result.state == HandshakeState.CONFIRMED
        assert "Trust establishment completed" in result.message
    
    def test_process_trust_establish_below_threshold(self):
        """Test trust establishment with score below minimum"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Complete previous steps
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
        machine.process_message("identity_exchange", identity_data, "incoming")
        
        cap_data = {
            "supported_capabilities": ["belief_aggregation"],
            "required_capabilities": ["belief_aggregation"],
            "priority": 1,
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:01Z",
            "nonce": "nonce2"
        }
        machine.process_message("capability_negotiate", cap_data, "incoming")
        
        # Process trust establishment with low score
        trust_data = {
            "trust_score": 0.5,  # Below minimum 0.7
            "trust_reasons": ["suspicious_behavior"],
            "expiration": "2024-01-02T00:00:00Z",
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:02Z",
            "nonce": "nonce3"
        }
        
        result = machine.process_message("trust_establish", trust_data, "incoming")
        
        assert result.success is False  # Should fail due to low trust score
        assert result.state == HandshakeState.FAILED_TRUST
        assert "Trust score 0.5 below minimum 0.7" in result.message
    
    def test_process_federation_confirm_success(self):
        """Test successful federation confirmation"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Complete all previous steps
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
        machine.process_message("identity_exchange", identity_data, "incoming")
        
        cap_data = {
            "supported_capabilities": ["belief_aggregation"],
            "required_capabilities": ["belief_aggregation"],
            "priority": 1,
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:01Z",
            "nonce": "nonce2"
        }
        machine.process_message("capability_negotiate", cap_data, "incoming")
        
        trust_data = {
            "trust_score": 0.8,
            "trust_reasons": ["good_behavior"],
            "expiration": "2024-01-02T00:00:00Z",
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:02Z",
            "nonce": "nonce3"
        }
        machine.process_message("trust_establish", trust_data, "incoming")
        
        # Process federation confirmation
        confirm_data = {
            "federation_id": "fed-123",
            "member_cells": ["cell-1", "cell-2"],
            "coordinator_cell": "cell-1",
            "terms": {"version": "2.0"},
            "signature": "sig",
            "timestamp": "2024-01-01T00:00:03Z",
            "nonce": "nonce4"
        }
        
        result = machine.process_message("federation_confirm", confirm_data, "incoming")
        
        assert result.success is True
        assert result.state == HandshakeState.ACTIVE
        assert "Federation confirmed and active" in result.message
    
    def test_get_current_state(self):
        """Test getting current state"""
        machine = IdentityHandshakeStateMachine()
        
        # No session yet
        assert machine.get_current_state() is None
        
        # Initiate handshake
        machine.initiate_handshake("cell-1", "cell-2")
        assert machine.get_current_state() == HandshakeState.IDENTITY_EXCHANGE
    
    def test_get_session_info(self):
        """Test getting session information"""
        machine = IdentityHandshakeStateMachine()
        
        # No session yet
        assert machine.get_session_info() is None
        
        # Initiate handshake
        machine.initiate_handshake("cell-1", "cell-2")
        info = machine.get_session_info()
        
        assert info is not None
        assert info["initiator_cell_id"] == "cell-1"
        assert info["responder_cell_id"] == "cell-2"
        assert info["current_state"] == HandshakeState.IDENTITY_EXCHANGE
        assert info["step_index"] == 0  # Should still be 0 at initiation
        assert "session_id" in info
        assert "session_nonce" in info
        assert "transcript_hash" in info
    
    def test_is_complete(self):
        """Test completion status"""
        machine = IdentityHandshakeStateMachine()
        
        # Not started
        assert machine.is_complete() is False
        assert machine.is_failed() is False
        
        # Initiated
        machine.initiate_handshake("cell-1", "cell-2")
        assert machine.is_complete() is False
        assert machine.is_failed() is False
        
        # Failed state
        # Simulate failure by setting state directly
        machine.session.current_state = HandshakeState.FAILED_IDENTITY
        assert machine.is_complete() is False
        assert machine.is_failed() is True
        
        # Active state
        machine.session.current_state = HandshakeState.ACTIVE
        assert machine.is_complete() is True
        assert machine.is_failed() is False
    
    def test_process_message_without_session(self):
        """Test processing message without active session"""
        machine = IdentityHandshakeStateMachine()
        
        result = machine.process_message("identity_exchange", {}, "incoming")
        
        assert result.success is False
        assert result.state == HandshakeState.UNINITIALIZED
        assert "No active session" in result.message


class TestStateMachineDeterminism:
    """Test deterministic properties of state machine"""
    
    def test_session_id_determinism(self):
        """Test session ID is deterministic for same inputs"""
        machine1 = IdentityHandshakeStateMachine()
        machine2 = IdentityHandshakeStateMachine()
        
        result1 = machine1.initiate_handshake("cell-1", "cell-2")
        result2 = machine2.initiate_handshake("cell-1", "cell-2")
        
        # Same inputs should produce different session IDs (due to random nonce)
        assert result1.success is True
        assert result2.success is True
        assert machine1.session.session_id != machine2.session.session_id
        
        # But both should be valid SHA-256 hashes
        assert len(machine1.session.session_id) == 64
        assert len(machine2.session.session_id) == 64
        assert all(c in '0123456789abcdef' for c in machine1.session.session_id.lower())
        assert all(c in '0123456789abcdef' for c in machine2.session.session_id.lower())
    
    def test_step_index_progression(self):
        """Test step index progression is deterministic"""
        machine = IdentityHandshakeStateMachine()
        machine.initiate_handshake("cell-1", "cell-2")
        
        # Initial step index should be 0
        assert machine.session.step_index == 0
        
        # Complete identity exchange (should increment step)
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
        machine.process_message("identity_exchange", identity_data, "incoming")
        
        # Step index should be 1 after successful transition
        assert machine.session.step_index == 1


class TestFeatureFlagIsolation:
    """Test that state machine works independently"""
    
    def test_state_machine_without_feature_flags(self):
        """Test state machine works without feature flag system"""
        # Should work independently
        machine = IdentityHandshakeStateMachine()
        
        result = machine.initiate_handshake("cell-test-1", "cell-test-2")
        
        assert result.success is True
        assert machine.session is not None
        assert machine.transcript_builder is not None
