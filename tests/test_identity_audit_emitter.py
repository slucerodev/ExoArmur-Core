"""
Tests for V2 Federation Identity Audit Emitter
Validate audit event emission and V1 integration
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.identity_audit_emitter import IdentityAuditEmitter
from federation.identity_handshake_state_machine import HandshakeEvent
from audit import NoOpAuditInterface


class TestIdentityAuditEmitter:
    """Test identity audit emitter functionality"""
    
    def test_emitter_initialization(self):
        """Test audit emitter initialization"""
        emitter = IdentityAuditEmitter()
        
        assert emitter.audit_interface is None
        assert emitter.feature_flag_checker() is False
    
    def test_emitter_with_dependencies(self):
        """Test emitter with audit interface and feature flag checker"""
        mock_audit_interface = NoOpAuditInterface()
        mock_feature_checker = Mock(return_value=True)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        assert emitter.audit_interface is mock_audit_interface
        assert emitter.feature_flag_checker is mock_feature_checker
        assert emitter.feature_flag_checker() is True
    
    def test_emit_handshake_event_enabled(self):
        """Test emitting handshake event when V2 federation is enabled"""
        
        # Mock audit interface
        mock_audit_interface = Mock()
        mock_audit_interface.log_event = Mock(return_value=True)
        mock_feature_checker = Mock(return_value=True)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        result = emitter.emit_handshake_event(event)
        
        assert result is True
        mock_audit_interface.log_event.assert_called_once()
        
        # Check audit interface call arguments
        call_args = mock_audit_interface.log_event.call_args
        assert call_args[1]["event_type"] == "federation.identity.handshake_initiated"
        assert call_args[1]["correlation_id"] == "session-123"
        assert "data" in call_args[1]
        assert call_args[1]["data"]["federation_version"] == "2.0"
        assert call_args[1]["data"]["component"] == "federation_identity"
    
    def test_emit_handshake_event_disabled(self):
        """Test emitting handshake event when V2 federation is disabled"""
                
        # Mock V1 audit logger
        mock_audit_logger = Mock()
        mock_audit_logger.log_event = Mock(return_value=True)
        
        # Create adapter
        mock_audit_interface = NoOpAuditInterface()
        mock_feature_checker = Mock(return_value=False)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        # Non-initiation event should be skipped
        event = HandshakeEvent(
            event_name="identity_verification_success",
            session_id="session-123",
            step_index=1,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"cell_id": "cell-1"}
        )
        
        result = emitter.emit_handshake_event(event)
        
        assert result is False  # Should not emit non-initiation events when disabled
        mock_audit_logger.log_event.assert_not_called()
    
    def test_emit_diagnostic_event_when_disabled(self):
        """Test diagnostic event emission when V2 federation is disabled"""
        mock_audit_logger = Mock()
        mock_feature_checker = Mock(return_value=False)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger,
            feature_flag_checker=mock_feature_checker
        )
        
        # Initiation event should trigger diagnostic event
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        result = emitter.emit_handshake_event(event)
        
        assert result is True
        mock_audit_logger.log_event.assert_called_once()
        
        # Check diagnostic event call
        call_args = mock_audit_logger.log_event.call_args
        assert call_args[1]["event_type"] == "federation.identity.disabled"
        assert call_args[1]["correlation_id"] == "diagnostic"
        assert call_args[1]["data"]["reason"] == "feature_flag_disabled"
        assert call_args[1]["data"]["component"] == "federation_identity"
    
    def test_emit_event_without_audit_logger(self):
        """Test emitting event without audit logger (fallback logging)"""
        mock_feature_checker = Mock(return_value=True)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_interface=None,
            feature_flag_checker=mock_feature_checker
        )
        
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        # Should not raise exception, should return True
        result = emitter.emit_handshake_event(event)
        assert result is True
    
    def test_create_event_handler(self):
        """Test creating event handler for state machine"""
        mock_audit_logger = Mock()
        mock_feature_checker = Mock(return_value=True)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger,
            feature_flag_checker=mock_feature_checker
        )
        
        handler = emitter.create_event_handler()
        
        # Should be callable
        assert callable(handler)
        
        # Test handler with event
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        handler(event)
        
        # Should have called audit logger
        mock_audit_logger.log_event.assert_called_once()
    
    def test_get_audit_trail_enabled(self):
        """Test retrieving audit trail when V2 federation is enabled"""
        mock_feature_checker = Mock(return_value=True)
        
        # Mock audit interface with get_events method
        mock_audit_interface = Mock()
        mock_events = [
            {
                "event_type": "federation.identity.handshake_initiated",
                "correlation_id": "session-123",
                "data": {"step_index": 0},
                "timestamp": "2024-01-01T00:00:00Z"
            },
            {
                "event_type": "federation.identity.identity_verification_success",
                "correlation_id": "session-123",
                "data": {"step_index": 1},
                "timestamp": "2024-01-01T00:00:01Z"
            }
        ]
        mock_audit_interface.get_events = Mock(return_value=mock_events)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        trail = emitter.get_audit_trail("session-123")
        
        assert trail is not None
        assert trail["session_id"] == "session-123"
        assert trail["event_count"] == 2
        assert len(trail["events"]) == 2
        assert "retrieved_at" in trail
    
    def test_get_audit_trail_disabled(self):
        """Test retrieving audit trail when V2 federation is disabled"""
        mock_audit_logger = Mock()
        mock_feature_checker = Mock(return_value=False)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger,
            feature_flag_checker=mock_feature_checker
        )
        
        trail = emitter.get_audit_trail("session-123")
        
        assert trail is None
    
    def test_get_audit_trail_without_audit_logger(self):
        """Test retrieving audit trail without audit logger"""
        mock_feature_checker = Mock(return_value=True)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_interface=None,
            feature_flag_checker=mock_feature_checker
        )
        
        trail = emitter.get_audit_trail("session-123")
        
        assert trail is not None
        assert trail["session_id"] == "session-123"
        assert trail["event_count"] == 0
        assert "note" in trail
    
    def test_validate_audit_integrity_success(self):
        """Test audit integrity validation with valid events"""
        mock_feature_checker = Mock(return_value=True)
        
        # Mock audit interface with proper events
        mock_audit_interface = Mock()
        mock_events = [
            {
                "event_type": "federation.identity.handshake_initiated",
                "data": {"step_index": 0, "idempotency_key": "key1"},
                "timestamp": "2024-01-01T00:00:00Z"
            },
            {
                "event_type": "federation.identity.identity_verification_success",
                "data": {"step_index": 1, "idempotency_key": "key2"},
                "timestamp": "2024-01-01T00:00:01Z"
            }
        ]
        mock_audit_interface.get_events = Mock(return_value=mock_events)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        validation = emitter.validate_audit_integrity("session-123", 2)
        
        assert validation["valid"] is True
        assert validation["step_count_valid"] is True
        assert validation["idempotency_valid"] is True
        assert validation["chronological_valid"] is True
        assert validation["step_order_valid"] is True
        assert len(validation["issues"]) == 0
    
    def test_validate_audit_integrity_step_count_mismatch(self):
        """Test audit integrity validation with step count mismatch"""
        mock_feature_checker = Mock(return_value=True)
        
        # Mock audit interface with wrong count
        mock_audit_interface = Mock()
        mock_events = [
            {
                "event_type": "federation.identity.handshake_initiated",
                "data": {"step_index": 0, "idempotency_key": "key1"},
                "timestamp": "2024-01-01T00:00:00Z"
            }
        ]
        mock_audit_interface.get_events = Mock(return_value=mock_events)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        validation = emitter.validate_audit_integrity("session-123", 2)
        
        assert validation["valid"] is False
        assert validation["step_count_valid"] is False
        assert validation["expected_steps"] == 2
    
def test_validate_audit_integrity_duplicate_idempotency_keys(self):
    """Test audit integrity validation with duplicate idempotency keys"""
    mock_feature_checker = Mock(return_value=True)
        
    # Mock audit interface with duplicate keys
    mock_audit_interface = Mock()
    mock_events = [
        {
            "event_type": "federation.identity.handshake_initiated",
            "data": {"step_index": 0, "idempotency_key": "key1"},
            "timestamp": "2024-01-01T00:00:00Z"
        },
        {
            "event_type": "federation.identity.identity_verification_success",
            "data": {"step_index": 1, "idempotency_key": "key1"},  # Duplicate key
            "timestamp": "2024-01-01T00:00:01Z"
        }
    ]
    mock_audit_interface.get_events = Mock(return_value=mock_events)
        
    emitter = IdentityAuditEmitter(
        audit_interface=mock_audit_interface,
        feature_flag_checker=mock_feature_checker
    )
        
    validation = emitter.validate_audit_integrity("session-123", 2)
    
    assert validation["valid"] is False
    assert validation["idempotency_valid"] is False
    assert "Duplicate idempotency keys" in validation["issues"]
    
    def test_validate_audit_integrity_chronological_violation(self):
        """Test audit integrity validation with chronological order violation"""
        mock_feature_checker = Mock(return_value=True)
        
        # Mock audit interface with wrong timestamp order
        mock_audit_interface = Mock()
        mock_events = [
            {
                "event_type": "federation.identity.handshake_initiated",
                "data": {"step_index": 0, "idempotency_key": "key1"},
                "timestamp": "2024-01-01T00:00:01Z"  # Later timestamp
            },
            {
                "event_type": "federation.identity.identity_verification_success",
                "data": {"step_index": 1, "idempotency_key": "key2"},
                "timestamp": "2024-01-01T00:00:00Z"  # Earlier timestamp
            }
        ]
        mock_audit_interface.get_events = Mock(return_value=mock_events)
        
        emitter = IdentityAuditEmitter(
            audit_interface=mock_audit_interface,
            feature_flag_checker=mock_feature_checker
        )
        
        validation = emitter.validate_audit_integrity("session-123", 2)
        
        assert validation["valid"] is False
        assert validation["chronological_valid"] is False
        assert "Timestamp order violation" in validation["issues"]
    
    def test_validate_audit_integrity_disabled(self):
        """Test audit integrity validation when V2 federation is disabled"""
        mock_audit_logger = Mock()
        mock_feature_checker = Mock(return_value=False)
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger,
            feature_flag_checker=mock_feature_checker
        )
        
        validation = emitter.validate_audit_integrity("session-123", 2)
        
        assert validation["valid"] is False
        assert validation["reason"] == "Audit trail not available"
    
    def test_emit_event_error_handling(self):
        """Test error handling during event emission"""
        mock_audit_logger = Mock()
        mock_feature_checker = Mock(return_value=True)
        
        # Make audit logger raise exception
        mock_audit_logger.log_event = Mock(side_effect=Exception("Audit error"))
        
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger,
            feature_flag_checker=mock_feature_checker
        )
        
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        # Should handle error gracefully and return False
        result = emitter.emit_handshake_event(event)
        assert result is False


class TestFeatureFlagIsolation:
    """Test that audit emitter respects feature flags"""
    
    def test_audit_emitter_respects_feature_flags(self):
        """Test audit emitter behavior with different feature flag states"""
        event = HandshakeEvent(
            event_name="handshake_initiated",
            session_id="session-123",
            step_index=0,
            timestamp=datetime.now(timezone.utc),
            data={"initiator_cell_id": "cell-1"}
        )
        
        # Test with feature flag disabled
        mock_audit_logger_disabled = Mock()
        emitter_disabled = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger_disabled,
            feature_flag_checker=lambda: False
        )
        
        # Should emit diagnostic event
        result = emitter_disabled.emit_handshake_event(event)
        assert result is True
        assert mock_audit_logger_disabled.log_event.call_count == 1
        
        # Test with feature flag enabled
        mock_audit_logger_enabled = Mock()
        emitter_enabled = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_logger=mock_audit_logger_enabled,
            feature_flag_checker=lambda: True
        )
        
        # Should emit actual event
        result = emitter_enabled.emit_handshake_event(event)
        assert result is True
        assert mock_audit_logger_enabled.log_event.call_count == 1
        
        # Check event type difference
        disabled_call = mock_audit_logger_disabled.log_event.call_args
        enabled_call = mock_audit_logger_enabled.log_event.call_args
        
        assert disabled_call[1]["event_type"] == "federation.identity.disabled"
        assert enabled_call[1]["event_type"] == "federation.identity.handshake_initiated"
    
    def test_audit_trail_access_when_disabled(self):
        """Test audit trail access when V2 federation is disabled"""
        emitter = IdentityAuditEmitter(
            audit_interface=NoOpAuditInterface(), # audit_interface=None,
            feature_flag_checker=lambda: False
        )
        
        trail = emitter.get_audit_trail("session-123")
        assert trail is None
        
        validation = emitter.validate_audit_integrity("session-123", 2)
        assert validation["valid"] is False
        assert validation["reason"] == "Audit trail not available"
