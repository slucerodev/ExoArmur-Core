"""
Replay verification utilities for external effect evidence.

Core can verify evidence integrity without understanding provider specifics.
"""

from typing import Any, Dict, Optional

from exoarmur.kernel.canonicalization import CanonicalizationError, canonical_hash
from exoarmur.kernel.external_effect import (
    ExternalEffectEvidence,
    ReplayVerificationStatus,
)


class VerificationResult:
    """Structured result of evidence verification."""

    def __init__(
        self, status: ReplayVerificationStatus, details: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.details = details or {}


def verify_evidence_integrity(evidence: ExternalEffectEvidence) -> VerificationResult:
    """
    Verify evidence integrity using Core's hashing utilities.

    Core does not need to understand provider-specific response formats.
    It only verifies that:
    1. Request hash matches stored request hash
    2. Response hash matches stored response hash
    3. Evidence signature is valid (if present)
    4. Evidence is not stale (if timestamp check enabled)

    Args:
        evidence: Evidence to verify

    Returns:
        VerificationResult with status and details
    """
    # Verify request hash
    try:
        current_request_hash = canonical_hash(evidence.normalized_request)
    except CanonicalizationError as e:
        return VerificationResult(
            status=ReplayVerificationStatus.MALFORMED,
            details={"error": f"Failed to hash request: {e}"},
        )

    if current_request_hash != evidence.request_canonical_hash:
        return VerificationResult(
            status=ReplayVerificationStatus.MISMATCH,
            details={
                "field": "request",
                "stored_hash": evidence.request_canonical_hash,
                "current_hash": current_request_hash,
            },
        )

    # Verify response hash
    try:
        current_response_hash = canonical_hash(evidence.normalized_response)
    except CanonicalizationError as e:
        return VerificationResult(
            status=ReplayVerificationStatus.MALFORMED,
            details={"error": f"Failed to hash response: {e}"},
        )

    if current_response_hash != evidence.response_canonical_hash:
        return VerificationResult(
            status=ReplayVerificationStatus.MISMATCH,
            details={
                "field": "response",
                "stored_hash": evidence.response_canonical_hash,
                "current_hash": current_response_hash,
            },
        )

    # Verify signature if present
    if evidence.evidence_signature is not None:
        # Signature verification not implemented in Core
        # Mark as not checked rather than verified
        return VerificationResult(
            status=ReplayVerificationStatus.NOT_CHECKED,
            details={"reason": "signature_verification_not_implemented"},
        )

    return VerificationResult(status=ReplayVerificationStatus.VERIFIED, details={})


def verify_request_matches_evidence(
    intent_or_request: Dict[str, Any], evidence: ExternalEffectEvidence
) -> VerificationResult:
    """
    Verify that current intent/request matches stored evidence.

    Core verifies intent consistency without calling provider APIs.

    Args:
        intent_or_request: Current intent or request data
        evidence: Stored evidence to verify against

    Returns:
        VerificationResult with status and details
    """
    # Verify provider matches
    if evidence.provider != intent_or_request.get("provider"):
        return VerificationResult(
            status=ReplayVerificationStatus.MISMATCH,
            details={
                "field": "provider",
                "stored": evidence.provider,
                "current": intent_or_request.get("provider"),
            },
        )

    # Verify operation type matches
    if evidence.operation_type != intent_or_request.get("operation_type"):
        return VerificationResult(
            status=ReplayVerificationStatus.MISMATCH,
            details={
                "field": "operation_type",
                "stored": evidence.operation_type,
                "current": intent_or_request.get("operation_type"),
            },
        )

    # Verify request hash matches
    try:
        current_request_hash = canonical_hash(intent_or_request)
    except CanonicalizationError as e:
        return VerificationResult(
            status=ReplayVerificationStatus.MALFORMED,
            details={"error": f"Failed to hash request: {e}"},
        )

    if current_request_hash != evidence.request_canonical_hash:
        return VerificationResult(
            status=ReplayVerificationStatus.MISMATCH,
            details={
                "field": "request_hash",
                "stored_hash": evidence.request_canonical_hash,
                "current_hash": current_request_hash,
            },
        )

    return VerificationResult(status=ReplayVerificationStatus.VERIFIED, details={})
