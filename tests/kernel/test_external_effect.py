"""
Tests for external effect evidence schema.

These tests verify that Core's evidence schema works correctly.
"""

import pytest
from datetime import datetime, timezone
from exoarmur.kernel.external_effect import (
    ExternalEffectEvidence,
    ExecutionMode,
    RollbackStrategy,
    ReplayVerificationStatus
)


def test_external_effect_evidence_serialization():
    """Test that evidence can be serialized and deserialized."""
    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash="abc123",
        response_canonical_hash="def456",
        normalized_request={"model": "gpt-4", "messages": []},
        normalized_response={"content": "test response"},
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY
    )
    
    # Serialize
    data = evidence.to_dict()
    
    # Verify required fields
    assert data["execution_id"] == "test-exec-id"
    assert data["intent_id"] == "test-intent-id"
    assert data["trace_id"] == "test-trace-id"
    assert data["provider"] == "openai"
    assert data["operation_type"] == "chat_completion"
    assert data["request_canonical_hash"] == "abc123"
    assert data["response_canonical_hash"] == "def456"
    assert data["irreversible_effect"] == True
    assert data["rollback_strategy"] == "record_only"
    
    # Deserialize
    restored = ExternalEffectEvidence.from_dict(data)
    
    # Verify restored evidence matches original
    assert restored.execution_id == evidence.execution_id
    assert restored.intent_id == evidence.intent_id
    assert restored.trace_id == evidence.trace_id
    assert restored.provider == evidence.provider
    assert restored.operation_type == evidence.operation_type
    assert restored.request_canonical_hash == evidence.request_canonical_hash
    assert restored.response_canonical_hash == evidence.response_canonical_hash
    assert restored.irreversible_effect == evidence.irreversible_effect
    assert restored.rollback_strategy == evidence.rollback_strategy


def test_external_effect_evidence_missing_required_field():
    """Test that deserialization fails with missing required field."""
    data = {
        "execution_id": "test-exec-id",
        "intent_id": "test-intent-id",
        # Missing trace_id
        "provider": "openai",
        "operation_type": "chat_completion",
        "request_canonical_hash": "abc123",
        "response_canonical_hash": "def456",
        "normalized_request": {},
        "normalized_response": {},
        "evidence_timestamp": "2024-01-01T00:00:00+00:00",
        "irreversible_effect": True,
        "rollback_strategy": "record_only"
    }
    
    with pytest.raises(ValueError, match="Missing required field"):
        ExternalEffectEvidence.from_dict(data)


def test_external_effect_evidence_invalid_rollback_strategy():
    """Test that deserialization fails with invalid rollback strategy."""
    data = {
        "execution_id": "test-exec-id",
        "intent_id": "test-intent-id",
        "trace_id": "test-trace-id",
        "provider": "openai",
        "operation_type": "chat_completion",
        "request_canonical_hash": "abc123",
        "response_canonical_hash": "def456",
        "normalized_request": {},
        "normalized_response": {},
        "evidence_timestamp": "2024-01-01T00:00:00+00:00",
        "irreversible_effect": True,
        "rollback_strategy": "invalid_strategy"
    }
    
    with pytest.raises(ValueError, match="Invalid rollback_strategy"):
        ExternalEffectEvidence.from_dict(data)


def test_external_effect_evidence_invalid_timestamp():
    """Test that deserialization fails with invalid timestamp."""
    data = {
        "execution_id": "test-exec-id",
        "intent_id": "test-intent-id",
        "trace_id": "test-trace-id",
        "provider": "openai",
        "operation_type": "chat_completion",
        "request_canonical_hash": "abc123",
        "response_canonical_hash": "def456",
        "normalized_request": {},
        "normalized_response": {},
        "evidence_timestamp": "invalid-timestamp",
        "irreversible_effect": True,
        "rollback_strategy": "record_only"
    }
    
    with pytest.raises(ValueError, match="Invalid evidence_timestamp"):
        ExternalEffectEvidence.from_dict(data)


def test_external_effect_evidence_provider_metadata():
    """Test that provider metadata is extensible."""
    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash="abc123",
        response_canonical_hash="def456",
        normalized_request={},
        normalized_response={},
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
        provider_metadata={
            "model": "gpt-4",
            "finish_reason": "stop",
            "prompt_tokens": 100,
            "completion_tokens": 50
        }
    )
    
    data = evidence.to_dict()
    assert data["provider_metadata"]["model"] == "gpt-4"
    assert data["provider_metadata"]["finish_reason"] == "stop"
    assert data["provider_metadata"]["prompt_tokens"] == 100
    assert data["provider_metadata"]["completion_tokens"] == 50


def test_external_effect_evidence_default_values():
    """Test that optional fields have correct defaults."""
    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash="abc123",
        response_canonical_hash="def456",
        normalized_request={},
        normalized_response={},
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY
    )
    
    # Check defaults
    assert evidence.evidence_signature is None
    assert evidence.replay_verification_status == ReplayVerificationStatus.NOT_CHECKED
    assert evidence.replay_verification_timestamp is None
    assert evidence.provider_metadata == {}


def test_execution_mode_enum():
    """Test ExecutionMode enum values."""
    assert ExecutionMode.LIVE.value == "live"
    assert ExecutionMode.REPLAY.value == "replay"


def test_rollback_strategy_enum():
    """Test RollbackStrategy enum values."""
    assert RollbackStrategy.COMPENSATING.value == "compensating"
    assert RollbackStrategy.RECORD_ONLY.value == "record_only"
    assert RollbackStrategy.UNSUPPORTED.value == "unsupported"


def test_replay_verification_status_enum():
    """Test ReplayVerificationStatus enum values."""
    assert ReplayVerificationStatus.NOT_CHECKED.value == "not_checked"
    assert ReplayVerificationStatus.VERIFIED.value == "verified"
    assert ReplayVerificationStatus.MISMATCH.value == "mismatch"
    assert ReplayVerificationStatus.MISSING.value == "missing"
    assert ReplayVerificationStatus.STALE.value == "stale"
    assert ReplayVerificationStatus.MALFORMED.value == "malformed"
