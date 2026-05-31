"""
Tests for replay/evidence verification helpers.

These tests verify that Core's replay verification works correctly.
"""

from datetime import datetime, timezone

import pytest

from exoarmur.kernel.canonicalization import canonical_hash
from exoarmur.kernel.external_effect import (
    ExternalEffectEvidence,
    ReplayVerificationStatus,
    RollbackStrategy,
)
from exoarmur.kernel.replay_verification import (
    VerificationResult,
    verify_evidence_integrity,
    verify_request_matches_evidence,
)


def test_verify_evidence_integrity_verified():
    """Test verification with matching hashes."""
    normalized_request = {"model": "gpt-4"}
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.VERIFIED
    assert result.details == {}


def test_verify_evidence_integrity_request_mismatch():
    """Test verification detects request hash mismatch."""
    normalized_request = {"model": "gpt-4"}
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),  # Stored hash
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,  # Current data
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    # Tamper with normalized_request
    evidence.normalized_request = {"model": "gpt-3.5"}

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.MISMATCH
    assert result.details["field"] == "request"
    assert "stored_hash" in result.details
    assert "current_hash" in result.details


def test_verify_evidence_integrity_response_mismatch():
    """Test verification detects response hash mismatch."""
    normalized_request = {"model": "gpt-4"}
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),  # Stored hash
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    # Tamper with normalized_response
    evidence.normalized_response = {"content": "tampered"}

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.MISMATCH
    assert result.details["field"] == "response"
    assert "stored_hash" in result.details
    assert "current_hash" in result.details


def test_verify_evidence_integrity_malformed_request():
    """Test verification detects malformed request."""
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash="abc123",  # Placeholder - will fail before hash check
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request={"model": float("nan")},  # Malformed
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.MALFORMED
    assert "error" in result.details


def test_verify_evidence_integrity_malformed_response():
    """Test verification detects malformed response."""
    normalized_request = {"model": "gpt-4"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash="def456",  # Placeholder - will fail before hash check
        normalized_request=normalized_request,
        normalized_response={"content": float("inf")},  # Malformed
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.MALFORMED
    assert "error" in result.details


def test_verify_evidence_integrity_signature_not_checked():
    """Test that signature verification is marked as not checked."""
    normalized_request = {"model": "gpt-4"}
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        evidence_signature="test_signature",  # Present but not verified
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    result = verify_evidence_integrity(evidence)

    assert result.status == ReplayVerificationStatus.NOT_CHECKED
    assert result.details["reason"] == "signature_verification_not_implemented"


def test_verify_request_matches_evidence_verified():
    """Test request matching verification with matching data."""
    normalized_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    # Current request must match normalized_request structure for hash comparison
    current_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }

    result = verify_request_matches_evidence(current_request, evidence)

    assert result.status == ReplayVerificationStatus.VERIFIED
    assert result.details == {}


def test_verify_request_matches_evidence_provider_mismatch():
    """Test request matching detects provider mismatch."""
    normalized_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    current_request = {
        "provider": "anthropic",  # Mismatch
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }

    result = verify_request_matches_evidence(current_request, evidence)

    assert result.status == ReplayVerificationStatus.MISMATCH
    assert result.details["field"] == "provider"
    assert result.details["stored"] == "openai"
    assert result.details["current"] == "anthropic"


def test_verify_request_matches_evidence_operation_mismatch():
    """Test request matching detects operation type mismatch."""
    normalized_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    current_request = {
        "provider": "openai",
        "operation_type": "embedding",  # Mismatch
        "model": "gpt-4",
    }

    result = verify_request_matches_evidence(current_request, evidence)

    assert result.status == ReplayVerificationStatus.MISMATCH
    assert result.details["field"] == "operation_type"
    assert result.details["stored"] == "chat_completion"
    assert result.details["current"] == "embedding"


def test_verify_request_matches_evidence_hash_mismatch():
    """Test request matching detects hash mismatch."""
    normalized_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    current_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-3.5",  # Different data, different hash
    }

    result = verify_request_matches_evidence(current_request, evidence)

    assert result.status == ReplayVerificationStatus.MISMATCH
    assert result.details["field"] == "request_hash"
    assert "stored_hash" in result.details
    assert "current_hash" in result.details


def test_verify_request_matches_evidence_malformed_request():
    """Test request matching detects malformed request."""
    normalized_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": "gpt-4",
    }
    normalized_response = {"content": "test"}

    evidence = ExternalEffectEvidence(
        schema_version="1.0",
        execution_id="test-exec-id",
        intent_id="test-intent-id",
        trace_id="test-trace-id",
        provider="openai",
        operation_type="chat_completion",
        request_canonical_hash=canonical_hash(normalized_request),
        response_canonical_hash=canonical_hash(normalized_response),
        normalized_request=normalized_request,
        normalized_response=normalized_response,
        evidence_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
    )

    current_request = {
        "provider": "openai",
        "operation_type": "chat_completion",
        "model": float("nan"),  # Malformed
    }

    result = verify_request_matches_evidence(current_request, evidence)

    assert result.status == ReplayVerificationStatus.MALFORMED
    assert "error" in result.details
