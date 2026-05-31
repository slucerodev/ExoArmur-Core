"""
External effect evidence schema for platform executor plugins.

Core defines the contract for evidence capture and replay verification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ExecutionMode(Enum):
    """Execution mode for external effects."""

    LIVE = "live"
    REPLAY = "replay"


class RollbackStrategy(Enum):
    """Rollback strategy for external effects."""

    COMPENSATING = "compensating"
    RECORD_ONLY = "record_only"
    UNSUPPORTED = "unsupported"


class ReplayVerificationStatus(Enum):
    """Replay verification status."""

    NOT_CHECKED = "not_checked"
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    MISSING = "missing"
    STALE = "stale"
    MALFORMED = "malformed"


@dataclass
class ExternalEffectEvidence:
    """
    Core evidence schema for external API calls.

    Platform executors must provide evidence in this format.
    Provider-specific fields go in provider_metadata.

    Schema version: 1.0
    """

    # Core identification fields (required - no defaults)
    execution_id: str
    intent_id: str
    trace_id: str
    provider: str  # "openai", "anthropic", "langchain", "huggingface"
    operation_type: str  # "chat_completion", "embedding", "agent_run", etc.

    # Core canonicalization fields (required - no defaults)
    request_canonical_hash: str  # SHA-256 of canonical request
    response_canonical_hash: str  # SHA-256 of canonical response

    # Core normalized fields (required - no defaults)
    normalized_request: Dict[str, Any]
    normalized_response: Dict[str, Any]

    # Core integrity fields (required - no defaults)
    evidence_timestamp: datetime

    # Core irreversibility fields (required - no defaults)
    irreversible_effect: bool
    rollback_strategy: RollbackStrategy

    # Schema version (optional - has default)
    schema_version: str = "1.0"

    # Core replay fields (optional - have defaults)
    evidence_signature: Optional[str] = (
        None  # For tamper detection (optional, not implemented)
    )
    replay_verification_status: ReplayVerificationStatus = (
        ReplayVerificationStatus.NOT_CHECKED
    )
    replay_verification_timestamp: Optional[datetime] = None

    # Provider-specific metadata (optional - has default)
    provider_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage/transmission.

        Returns:
            Dictionary representation of evidence
        """
        return {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "intent_id": self.intent_id,
            "trace_id": self.trace_id,
            "provider": self.provider,
            "operation_type": self.operation_type,
            "request_canonical_hash": self.request_canonical_hash,
            "response_canonical_hash": self.response_canonical_hash,
            "normalized_request": self.normalized_request,
            "normalized_response": self.normalized_response,
            "evidence_timestamp": self.evidence_timestamp.isoformat(),
            "evidence_signature": self.evidence_signature,
            "replay_verification_status": self.replay_verification_status.value,
            "replay_verification_timestamp": (
                self.replay_verification_timestamp.isoformat()
                if self.replay_verification_timestamp
                else None
            ),
            "irreversible_effect": self.irreversible_effect,
            "rollback_strategy": self.rollback_strategy.value,
            "provider_metadata": self.provider_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalEffectEvidence":
        """
        Create from dictionary.

        Args:
            data: Dictionary representation of evidence

        Returns:
            ExternalEffectEvidence instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = [
            "execution_id",
            "intent_id",
            "trace_id",
            "provider",
            "operation_type",
            "request_canonical_hash",
            "response_canonical_hash",
            "normalized_request",
            "normalized_response",
            "evidence_timestamp",
            "irreversible_effect",
            "rollback_strategy",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Parse enum fields
        try:
            rollback_strategy = RollbackStrategy(data["rollback_strategy"])
        except ValueError:
            raise ValueError(f"Invalid rollback_strategy: {data['rollback_strategy']}")

        try:
            replay_verification_status = ReplayVerificationStatus(
                data.get("replay_verification_status", "not_checked")
            )
        except ValueError:
            raise ValueError(
                f"Invalid replay_verification_status: {data.get('replay_verification_status')}"
            )

        # Parse timestamp
        try:
            evidence_timestamp = datetime.fromisoformat(data["evidence_timestamp"])
        except ValueError:
            raise ValueError(
                f"Invalid evidence_timestamp: {data['evidence_timestamp']}"
            )

        replay_verification_timestamp = None
        if data.get("replay_verification_timestamp"):
            try:
                replay_verification_timestamp = datetime.fromisoformat(
                    data["replay_verification_timestamp"]
                )
            except ValueError:
                raise ValueError(
                    f"Invalid replay_verification_timestamp: {data['replay_verification_timestamp']}"
                )

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            execution_id=data["execution_id"],
            intent_id=data["intent_id"],
            trace_id=data["trace_id"],
            provider=data["provider"],
            operation_type=data["operation_type"],
            request_canonical_hash=data["request_canonical_hash"],
            response_canonical_hash=data["response_canonical_hash"],
            normalized_request=data["normalized_request"],
            normalized_response=data["normalized_response"],
            evidence_timestamp=evidence_timestamp,
            evidence_signature=data.get("evidence_signature"),
            replay_verification_status=replay_verification_status,
            replay_verification_timestamp=replay_verification_timestamp,
            irreversible_effect=data["irreversible_effect"],
            rollback_strategy=rollback_strategy,
            provider_metadata=data.get("provider_metadata", {}),
        )
