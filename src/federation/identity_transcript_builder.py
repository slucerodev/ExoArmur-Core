"""
# PHASE 2A — LOCKED
# Identity handshake logic must not be modified without governance approval.

ExoArmur ADMO V2 Federation Identity Transcript Builder
Deterministic transcript construction for federation identity handshake
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .models.federation_identity_v2 import (
    HandshakeState,
    IdentityExchangeMessage,
    CapabilityNegotiateMessage,
    TrustEstablishMessage,
    FederationConfirmMessage,
    FederationIdentityMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class TranscriptMessage:
    """Message in handshake transcript with ordering metadata"""
    step_index: int
    direction: str  # "outgoing" or "incoming"
    message_type: str
    message_data: Dict[str, Any]
    timestamp: datetime
    canonical_json: str = field(init=False)
    
    def __post_init__(self):
        """Generate canonical JSON after initialization"""
        self.canonical_json = self._to_canonical_json()
    
    def _to_canonical_json(self) -> str:
        """Convert message to canonical JSON (RFC 8785)"""
        # Create canonical representation
        canonical_data = {
            "step_index": self.step_index,
            "direction": self.direction,
            "message_type": self.message_type,
            "message_data": self.message_data,
            "timestamp": self.timestamp.isoformat()
        }
        
        # Use orjson for deterministic serialization if available, fallback to json
        try:
            import orjson
            return orjson.dumps(canonical_data, option=orjson.OPT_SERIALIZE_UUID | orjson.OPT_SORT_KEYS)
        except ImportError:
            # Fallback to standard library json with manual sorting
            return json.dumps(canonical_data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


class TranscriptBuilder:
    """Deterministic transcript builder for federation identity handshake"""
    
    def __init__(self, session_id: str):
        """Initialize transcript builder for session"""
        self.session_id = session_id
        self.messages: List[TranscriptMessage] = []
        self._current_step_index = 0
    
    def add_message(
        self,
        message_type: str,
        message_data: Dict[str, Any],
        direction: str = "outgoing",
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Add a message to the transcript
        
        Args:
            message_type: Type of message (identity_exchange, capability_negotiate, etc.)
            message_data: Message payload as dictionary
            direction: "outgoing" or "incoming"
            timestamp: Message timestamp (defaults to now)
            
        Returns:
            step_index assigned to the message
        """
        if direction not in ["outgoing", "incoming"]:
            raise ValueError("direction must be 'outgoing' or 'incoming'")
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Create transcript message
        transcript_msg = TranscriptMessage(
            step_index=self._current_step_index,
            direction=direction,
            message_type=message_type,
            message_data=message_data,
            timestamp=timestamp
        )
        
        self.messages.append(transcript_msg)
        
        # Increment step index for next message
        self._current_step_index += 1
        
        logger.debug(f"Added message {message_type} at step {transcript_msg.step_index}")
        
        return transcript_msg.step_index
    
    def add_message_with_timestamp(
        self,
        message_type: str,
        message_data: Dict[str, Any],
        direction: str = "outgoing",
        timestamp: datetime = None
    ) -> int:
        """
        Add a message with explicit timestamp (for deterministic testing)
        
        Args:
            message_type: Type of message
            message_data: Message payload as dictionary
            direction: "outgoing" or "incoming"
            timestamp: Explicit timestamp (required)
            
        Returns:
            step_index assigned to the message
        """
        if timestamp is None:
            raise ValueError("timestamp is required for add_message_with_timestamp")
        
        return self.add_message(message_type, message_data, direction, timestamp)
    
    def get_transcript_hash(self) -> str:
        """
        Compute SHA-256 hash of the complete transcript
        
        Returns:
            Hexadecimal SHA-256 hash
        """
        if not self.messages:
            return hashlib.sha256(b"").hexdigest()
        
        # Order messages by step_index, then direction (outgoing before incoming)
        ordered_messages = sorted(
            self.messages,
            key=lambda m: (m.step_index, 0 if m.direction == "outgoing" else 1)
        )
        
        # Concatenate canonical JSON representations
        transcript_data = "".join(msg.canonical_json for msg in ordered_messages)
        
        # Compute SHA-256 hash
        return hashlib.sha256(transcript_data.encode('utf-8')).hexdigest()
    
    def get_ordered_messages(self) -> List[TranscriptMessage]:
        """
        Get messages in canonical order for replay
        
        Returns:
            List of messages ordered by step_index and direction
        """
        return sorted(
            self.messages,
            key=lambda m: (m.step_index, 0 if m.direction == "outgoing" else 1)
        )
    
    def get_idempotency_key(self, event_name: str, step_index: int) -> str:
        """
        Generate idempotency key for an event
        
        Args:
            event_name: Name of the event
            step_index: Step index of the event
            
        Returns:
            SHA-256 hash for idempotency
        """
        key_data = f"{self.session_id}:{event_name}:{step_index}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
    
    def get_message_at_step(self, step_index: int, direction: Optional[str] = None) -> Optional[TranscriptMessage]:
        """
        Get message at specific step index
        
        Args:
            step_index: Step index to retrieve
            direction: Optional direction filter
            
        Returns:
            Transcript message if found, None otherwise
        """
        for msg in self.messages:
            if msg.step_index == step_index:
                if direction is None or msg.direction == direction:
                    return msg
        return None
    
    def get_last_step_index(self) -> int:
        """
        Get the last step index in the transcript
        
        Returns:
            Last step index, or -1 if no messages
        """
        if not self.messages:
            return -1
        return max(msg.step_index for msg in self.messages)
    
    def validate_transcript_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate transcript integrity
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for duplicate step indices
        step_indices = [msg.step_index for msg in self.messages]
        if len(step_indices) != len(set(step_indices)):
            issues.append("Duplicate step indices found")
        
        # Check for missing step indices
        if step_indices:
            expected_indices = set(range(min(step_indices), max(step_indices) + 1))
            missing_indices = expected_indices - set(step_indices)
            if missing_indices:
                issues.append(f"Missing step indices: {sorted(missing_indices)}")
        
        # Check direction validity
        for msg in self.messages:
            if msg.direction not in ["outgoing", "incoming"]:
                issues.append(f"Invalid direction '{msg.direction}' at step {msg.step_index}")
        
        return len(issues) == 0, issues
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert transcript to dictionary for serialization
        
        Returns:
            Dictionary representation of transcript
        """
        return {
            "session_id": self.session_id,
            "transcript_hash": self.get_transcript_hash(),
            "messages": [
                {
                    "step_index": msg.step_index,
                    "direction": msg.direction,
                    "message_type": msg.message_type,
                    "message_data": msg.message_data,
                    "timestamp": msg.timestamp.isoformat(),
                    "canonical_json": msg.canonical_json
                }
                for msg in self.get_ordered_messages()
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
