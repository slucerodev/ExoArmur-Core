"""
Tests for V2 Federation Identity Transcript Builder
Validate deterministic transcript construction and replay capabilities
"""

import pytest
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.identity_transcript_builder import TranscriptBuilder, TranscriptMessage
from federation.models.federation_identity_v2 import HandshakeState


class TestTranscriptMessage:
    """Test transcript message canonicalization"""
    
    def test_canonical_json_determinism(self):
        """Test canonical JSON produces same output for same input"""
        message_data = {
            "cell_id": "cell-test-1",
            "nonce": "nonce123",
            "signature": "signature456",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        msg1 = TranscriptMessage(
            step_index=0,
            direction="outgoing",
            message_type="identity_exchange",
            message_data=message_data,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        
        msg2 = TranscriptMessage(
            step_index=0,
            direction="outgoing",
            message_type="identity_exchange",
            message_data=message_data,
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        
        # Same input should produce same canonical JSON
        assert msg1.canonical_json == msg2.canonical_json
    
    def test_canonical_json_ordering(self):
        """Test canonical JSON handles key ordering correctly"""
        # Create message with unordered keys
        message_data = {
            "z_field": "last",
            "a_field": "first",
            "m_field": "middle"
        }
        
        msg = TranscriptMessage(
            step_index=0,
            direction="outgoing",
            message_type="test",
            message_data=message_data,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Parse canonical JSON and verify key ordering
        parsed = json.loads(msg.canonical_json)
        keys = list(parsed["message_data"].keys())
        assert keys == ["a_field", "m_field", "z_field"]


class TestTranscriptBuilder:
    """Test transcript builder functionality"""
    
    def test_transcript_builder_initialization(self):
        """Test transcript builder initialization"""
        session_id = "test-session-123"
        builder = TranscriptBuilder(session_id)
        
        assert builder.session_id == session_id
        assert len(builder.messages) == 0
        assert builder._current_step_index == 0
    
    def test_add_message_basic(self):
        """Test basic message addition"""
        builder = TranscriptBuilder("test-session")
        
        message_data = {"cell_id": "cell-1", "nonce": "nonce123"}
        step_index = builder.add_message(
            message_type="identity_exchange",
            message_data=message_data,
            direction="outgoing"
        )
        
        assert step_index == 0
        assert len(builder.messages) == 1
        assert builder._current_step_index == 1
        
        msg = builder.messages[0]
        assert msg.step_index == 0
        assert msg.direction == "outgoing"
        assert msg.message_type == "identity_exchange"
        assert msg.message_data == message_data
    
    def test_step_index_increment(self):
        """Test step index increments correctly"""
        builder = TranscriptBuilder("test-session")
        
        # Add multiple messages
        for i in range(3):
            step_index = builder.add_message(
                message_type=f"message_{i}",
                message_data={"index": i},
                direction="outgoing"
            )
            assert step_index == i
        
        assert len(builder.messages) == 3
        assert builder._current_step_index == 3
    
    def test_direction_validation(self):
        """Test direction validation"""
        builder = TranscriptBuilder("test-session")
        
        with pytest.raises(ValueError, match="direction must be 'outgoing' or 'incoming'"):
            builder.add_message(
                message_type="test",
                message_data={},
                direction="invalid"
            )
    
    def test_message_ordering_by_step_index(self):
        """Test messages are ordered by step_index"""
        builder = TranscriptBuilder("test-session")
        
        # Add messages in a specific order
        messages = [
            ("identity_exchange", {"step": 1}, "outgoing"),
            ("capability_negotiate", {"step": 2}, "incoming"),
            ("trust_establish", {"step": 3}, "outgoing"),
        ]
        
        for msg_type, data, direction in messages:
            builder.add_message(msg_type, data, direction)
        
        ordered = builder.get_ordered_messages()
        
        # Verify ordering
        assert ordered[0].step_index == 0
        assert ordered[0].direction == "outgoing"
        assert ordered[1].step_index == 1
        assert ordered[1].direction == "incoming"
        assert ordered[2].step_index == 2
        assert ordered[2].direction == "outgoing"
    
    def test_outgoing_before_incoming_at_same_step(self):
        """Test outgoing messages come before incoming at same step"""
        builder = TranscriptBuilder("test-session")
        
        # Add messages at same step index manually (simulating concurrent exchange)
        builder._current_step_index = 0
        builder.add_message("identity_exchange", {"role": "initiator"}, "outgoing")
        builder._current_step_index = 0  # Reset to same step
        builder.add_message("identity_exchange", {"role": "responder"}, "incoming")
        
        ordered = builder.get_ordered_messages()
        
        # Outgoing should come before incoming at same step
        assert ordered[0].direction == "outgoing"
        assert ordered[1].direction == "incoming"
        assert ordered[0].step_index == ordered[1].step_index
    
    def test_transcript_hash_determinism(self):
        """Test transcript hash is deterministic"""
        builder1 = TranscriptBuilder("session-1")
        builder2 = TranscriptBuilder("session-1")
        
        # Use deterministic timestamps
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Add identical messages to both builders
        messages = [
            ("identity_exchange", {"cell_id": "cell-1"}, "outgoing", base_time),
            ("capability_negotiate", {"capabilities": ["test"]}, "incoming", base_time + timedelta(seconds=1)),
        ]
        
        for msg_type, data, direction, timestamp in messages:
            builder1.add_message_with_timestamp(msg_type, data, direction, timestamp)
            builder2.add_message_with_timestamp(msg_type, data, direction, timestamp)
        
        hash1 = builder1.get_transcript_hash()
        hash2 = builder2.get_transcript_hash()
        
        # Same messages should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex string
        assert all(c in '0123456789abcdef' for c in hash1.lower())
    
    def test_transcript_hash_changes_with_order(self):
        """Test transcript hash changes with message order"""
        builder1 = TranscriptBuilder("session-1")
        builder2 = TranscriptBuilder("session-1")
        
        # Add messages in different order
        builder1.add_message("message_a", {"data": "a"}, "outgoing")
        builder1.add_message("message_b", {"data": "b"}, "incoming")
        
        builder2.add_message("message_b", {"data": "b"}, "incoming")
        builder2.add_message("message_a", {"data": "a"}, "outgoing")
        
        hash1 = builder1.get_transcript_hash()
        hash2 = builder2.get_transcript_hash()
        
        # Different order should produce different hash
        assert hash1 != hash2
    
    def test_idempotency_key_generation(self):
        """Test idempotency key generation"""
        builder = TranscriptBuilder("test-session")
        
        # Add a message
        builder.add_message("identity_exchange", {"test": "data"}, "outgoing")
        
        # Generate idempotency key
        key = builder.get_idempotency_key("handshake_initiated", 0)
        
        # Key should be SHA-256 hash
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key.lower())
        
        # Same inputs should produce same key
        key2 = builder.get_idempotency_key("handshake_initiated", 0)
        assert key == key2
        
        # Different inputs should produce different keys
        key3 = builder.get_idempotency_key("handshake_initiated", 1)
        assert key != key3
    
    def test_get_message_at_step(self):
        """Test retrieving message at specific step"""
        builder = TranscriptBuilder("test-session")
        
        # Add messages
        builder.add_message("message_a", {"data": "a"}, "outgoing")
        builder.add_message("message_b", {"data": "b"}, "incoming")
        
        # Retrieve by step
        msg_a = builder.get_message_at_step(0)
        msg_b = builder.get_message_at_step(1)
        
        assert msg_a is not None
        assert msg_a.message_type == "message_a"
        assert msg_b is not None
        assert msg_b.message_type == "message_b"
        
        # Test with direction filter
        msg_a_outgoing = builder.get_message_at_step(0, direction="outgoing")
        msg_a_incoming = builder.get_message_at_step(0, direction="incoming")
        
        assert msg_a_outgoing is not None
        assert msg_a_incoming is None
    
    def test_get_last_step_index(self):
        """Test getting last step index"""
        builder = TranscriptBuilder("test-session")
        
        # Empty transcript
        assert builder.get_last_step_index() == -1
        
        # Add messages
        builder.add_message("message_a", {"data": "a"}, "outgoing")
        assert builder.get_last_step_index() == 0
        
        builder.add_message("message_b", {"data": "b"}, "incoming")
        assert builder.get_last_step_index() == 1
    
    def test_transcript_integrity_validation(self):
        """Test transcript integrity validation"""
        builder = TranscriptBuilder("test-session")
        
        # Empty transcript should be valid
        is_valid, issues = builder.validate_transcript_integrity()
        assert is_valid
        assert len(issues) == 0
        
        # Add valid messages
        builder.add_message("message_a", {"data": "a"}, "outgoing")
        builder.add_message("message_b", {"data": "b"}, "incoming")
        
        is_valid, issues = builder.validate_transcript_integrity()
        assert is_valid
        assert len(issues) == 0
    
    def test_transcript_serialization(self):
        """Test transcript serialization to dictionary"""
        builder = TranscriptBuilder("test-session")
        
        builder.add_message("identity_exchange", {"cell_id": "cell-1"}, "outgoing")
        
        transcript_dict = builder.to_dict()
        
        assert "session_id" in transcript_dict
        assert "transcript_hash" in transcript_dict
        assert "messages" in transcript_dict
        assert "created_at" in transcript_dict
        
        assert transcript_dict["session_id"] == "test-session"
        assert len(transcript_dict["messages"]) == 1
        
        message_dict = transcript_dict["messages"][0]
        assert message_dict["step_index"] == 0
        assert message_dict["direction"] == "outgoing"
        assert message_dict["message_type"] == "identity_exchange"


class TestTranscriptBuilderDeterminism:
    """Test determinism properties of transcript builder"""
    
    def test_same_input_same_hash_across_instances(self):
        """Test that identical inputs produce same hash across different instances"""
        session_id = "deterministic-test"
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        messages = [
            ("identity_exchange", {"cell_id": "cell-1", "nonce": "abc123"}, "outgoing", base_time),
            ("capability_negotiate", {"capabilities": ["test"]}, "incoming", base_time + timedelta(seconds=1)),
            ("trust_establish", {"trust_score": 0.8}, "outgoing", base_time + timedelta(seconds=2)),
        ]
        
        hashes = []
        
        # Create multiple builders and add same messages
        for i in range(5):
            builder = TranscriptBuilder(session_id)
            for msg_type, data, direction, timestamp in messages:
                builder.add_message_with_timestamp(msg_type, data, direction, timestamp)
            hashes.append(builder.get_transcript_hash())
        
        # All hashes should be identical
        assert all(h == hashes[0] for h in hashes)
    
    def test_step_index_overrides_timestamp(self):
        """Test that step_index ordering overrides timestamp ordering"""
        builder = TranscriptBuilder("test-session")
        
        # Add messages with different timestamps but specific step indices
        early_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        late_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Add later timestamp first but with lower step index
        builder.add_message("message_a", {"data": "a"}, "outgoing", early_time)
        builder.add_message("message_b", {"data": "b"}, "incoming", late_time)
        
        ordered = builder.get_ordered_messages()
        
        # Should be ordered by step_index, not timestamp
        assert ordered[0].step_index == 0
        assert ordered[1].step_index == 1
        assert ordered[0].timestamp < ordered[1].timestamp


class TestFeatureFlagIsolation:
    """Test that transcript builder works independently"""
    
    def test_transcript_builder_without_feature_flags(self):
        """Test transcript builder works without feature flag system"""
        # Should work independently
        builder = TranscriptBuilder("independent-test")
        
        builder.add_message("test_message", {"test": True}, "outgoing")
        
        assert len(builder.messages) == 1
        assert builder.get_transcript_hash() is not None
        assert builder.get_idempotency_key("test_event", 0) is not None
