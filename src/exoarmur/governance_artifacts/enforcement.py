"""
Governance Artifact Enforcement

Provides fail-closed enforcement of required governance artifacts when enabled.
Consumes existing manifest and semantic diagnostic results to enforce required_for_verdict entries.
"""

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from exoarmur.governance_artifacts.inspection import (
    GovernanceArtifactInspectionResult,
)
from exoarmur.governance_artifacts.manifest import (
    validate_governance_manifest,
)
from exoarmur.governance_artifacts.semantic_verification import (
    GovernanceArtifactSemanticAggregateResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GovernanceArtifactEnforcementResult:
    """Result of enforcement evaluation for governance artifacts."""
    enabled: bool
    verdict_effect: str  # "none" | "fail_closed"
    valid: bool
    code: str
    message: str
    required_total: int
    required_valid: int
    required_invalid: int
    failures: tuple[dict[str, str], ...]


def enforce_governance_artifacts(
    bundle: Mapping[str, Any],
    inspection: GovernanceArtifactInspectionResult,
    semantic_verification: GovernanceArtifactSemanticAggregateResult | None,
    enforcement_enabled: bool,
) -> GovernanceArtifactEnforcementResult:
    """
    Enforce governance artifacts based on manifest and semantic verification results.

    Args:
        bundle: ExecutionProofBundle data as mapping (dict with "bundle" key or direct).
        inspection: Result from inspect_governance_artifacts_from_bundle.
        semantic_verification: Result from verify_governance_artifacts_semantically (may be None).
        enforcement_enabled: Whether enforcement is enabled via feature flag.

    Returns:
        Enforcement result with verdict effect and failure details.
    """
    if not enforcement_enabled:
        return GovernanceArtifactEnforcementResult(
            enabled=False,
            verdict_effect="none",
            valid=True,
            code="ENFORCEMENT_DISABLED",
            message="Governance artifact enforcement is disabled",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(),
        )

    # Enforcement is enabled - check manifest and required artifacts
    if not inspection.present:
        # Manifest absent - do not fail in this task (per mission spec)
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="none",
            valid=True,
            code="ENFORCEMENT_VALID",
            message="Governance manifest absent - no enforcement applied",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(),
        )

    if not inspection.valid_manifest:
        # Manifest invalid but present - fail closed
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="fail_closed",
            valid=False,
            code="REQUIRED_ARTIFACT_MANIFEST_INVALID",
            message="Governance manifest is invalid",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(
                {
                    "code": "REQUIRED_ARTIFACT_MANIFEST_INVALID",
                    "message": "Governance manifest is invalid",
                },
            ),
        )

    # Manifest is valid - extract manifest entries to check required_for_verdict
    # Extract inner bundle if nested (SDK format)
    inner = bundle.get("bundle") if isinstance(bundle, dict) else bundle
    if not isinstance(inner, dict):
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="fail_closed",
            valid=False,
            code="REQUIRED_ARTIFACT_MANIFEST_INVALID",
            message="Invalid bundle format for enforcement",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(
                {
                    "code": "REQUIRED_ARTIFACT_MANIFEST_INVALID",
                    "message": "Invalid bundle format for enforcement",
                },
            ),
        )

    # Extract governance_evidence and manifest
    governance_evidence = inner.get("governance_evidence", {})
    if not isinstance(governance_evidence, dict):
        governance_evidence = {}

    manifest_data = governance_evidence.get("governance_artifacts_manifest")
    if manifest_data is None:
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="none",
            valid=True,
            code="ENFORCEMENT_VALID",
            message="Governance manifest absent - no enforcement applied",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(),
        )

    # Validate manifest to get entries
    try:
        manifest = validate_governance_manifest(manifest_data)
    except Exception as e:
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="fail_closed",
            valid=False,
            code="REQUIRED_ARTIFACT_MANIFEST_INVALID",
            message=f"Manifest validation failed: {e}",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(
                {
                    "code": "REQUIRED_ARTIFACT_MANIFEST_INVALID",
                    "message": f"Manifest validation failed: {e}",
                },
            ),
        )

    # Build a map of (artifact_type, artifact_hash) -> required_for_verdict
    required_map: dict[tuple[str, str], bool] = {}
    for entry in manifest.entries:
        key = (entry.artifact_type, entry.artifact_hash)
        required_map[key] = entry.required_for_verdict

    # Check semantic verification results for required artifacts
    failures_list: list[dict[str, str]] = []
    required_total = 0
    required_valid = 0
    required_invalid = 0

    if semantic_verification is None or not semantic_verification.attempted:
        # Semantic verification not attempted - cannot enforce required artifacts
        # Check if there are any required artifacts
        required_count = sum(1 for entry in manifest.entries if entry.required_for_verdict)
        if required_count > 0:
            return GovernanceArtifactEnforcementResult(
                enabled=True,
                verdict_effect="fail_closed",
                valid=False,
                code="REQUIRED_ARTIFACT_MANIFEST_INVALID",
                message=f"Semantic verification not attempted but {required_count} required artifacts exist",
                required_total=required_count,
                required_valid=0,
                required_invalid=required_count,
                failures=(
                    {
                        "code": "REQUIRED_ARTIFACT_MANIFEST_INVALID",
                        "message": f"Semantic verification not attempted but {required_count} required artifacts exist",
                    },
                ),
            )
        # No required artifacts - valid
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="none",
            valid=True,
            code="ENFORCEMENT_VALID",
            message="No required artifacts to enforce",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(),
        )

    # Process semantic verification results
    for result in semantic_verification.results:
        key = (result.artifact_type, result.artifact_hash)
        is_required = required_map.get(key, False)

        if not is_required:
            # Optional artifact - skip enforcement
            continue

        required_total += 1

        if result.semantic_valid is False:
            failures_list.append(
                {
                    "code": "REQUIRED_ARTIFACT_SEMANTIC_INVALID",
                    "message": f"Required artifact semantic verification failed: {result.artifact_type}",
                    "artifact_type": result.artifact_type,
                    "artifact_hash": result.artifact_hash,
                }
            )
            required_invalid += 1
        elif result.code == "PROVIDER_UNAVAILABLE":
            failures_list.append(
                {
                    "code": "REQUIRED_ARTIFACT_PROVIDER_UNAVAILABLE",
                    "message": f"Required artifact provider unavailable: {result.artifact_type}",
                    "artifact_type": result.artifact_type,
                    "artifact_hash": result.artifact_hash,
                }
            )
            required_invalid += 1
        elif result.code == "ARTIFACT_CONTENT_UNAVAILABLE":
            failures_list.append(
                {
                    "code": "REQUIRED_ARTIFACT_CONTENT_UNAVAILABLE",
                    "message": f"Required artifact content unavailable: {result.artifact_type}",
                    "artifact_type": result.artifact_type,
                    "artifact_hash": result.artifact_hash,
                }
            )
            required_invalid += 1
        elif result.code == "ARTIFACT_HASH_MISMATCH":
            failures_list.append(
                {
                    "code": "REQUIRED_ARTIFACT_HASH_MISMATCH",
                    "message": f"Required artifact hash mismatch: {result.artifact_type}",
                    "artifact_type": result.artifact_type,
                    "artifact_hash": result.artifact_hash,
                }
            )
            required_invalid += 1
        elif result.code == "PROVIDER_ERROR":
            failures_list.append(
                {
                    "code": "REQUIRED_ARTIFACT_PROVIDER_ERROR",
                    "message": f"Required artifact provider error: {result.artifact_type} - {result.message}",
                    "artifact_type": result.artifact_type,
                    "artifact_hash": result.artifact_hash,
                }
            )
            required_invalid += 1
        elif result.semantic_valid is True:
            required_valid += 1

    if required_total == 0:
        # No required artifacts - valid
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="none",
            valid=True,
            code="ENFORCEMENT_VALID",
            message="No required artifacts to enforce",
            required_total=0,
            required_valid=0,
            required_invalid=0,
            failures=(),
        )

    if required_invalid > 0:
        return GovernanceArtifactEnforcementResult(
            enabled=True,
            verdict_effect="fail_closed",
            valid=False,
            code="REQUIRED_ARTIFACT_SEMANTIC_INVALID",
            message=f"Required artifact enforcement failed: {required_invalid} of {required_total} artifacts invalid",
            required_total=required_total,
            required_valid=required_valid,
            required_invalid=required_invalid,
            failures=tuple(failures_list),
        )

    return GovernanceArtifactEnforcementResult(
        enabled=True,
        verdict_effect="none",
        valid=True,
        code="ENFORCEMENT_VALID",
        message=f"All required artifacts valid: {required_valid} of {required_total}",
        required_total=required_total,
        required_valid=required_valid,
        required_invalid=required_invalid,
        failures=(),
    )


def format_enforcement_for_output(
    enforcement: GovernanceArtifactEnforcementResult,
) -> dict[str, Any]:
    """
    Format enforcement result for structured output.

    Args:
        enforcement: Enforcement result from enforce_governance_artifacts.

    Returns:
        JSON-serializable dictionary for CLI output.
    """
    return {
        "enabled": enforcement.enabled,
        "verdict_effect": enforcement.verdict_effect,
        "valid": enforcement.valid,
        "code": enforcement.code,
        "message": enforcement.message,
        "required_total": enforcement.required_total,
        "required_valid": enforcement.required_valid,
        "required_invalid": enforcement.required_invalid,
        "failures": enforcement.failures,
    }
