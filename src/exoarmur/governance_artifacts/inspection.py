"""
Governance Artifact Manifest Inspection

Provides read-only inspection of governance artifact manifests in ExecutionProofBundle.
Diagnostic-only path - does not alter Core replay verdicts.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from exoarmur.governance_artifacts.manifest import (
    validate_governance_manifest,
    governance_manifest_hash,
)
from exoarmur.governance_artifacts.provider_registry import (
    discover_governance_artifact_providers,
    get_governance_provider_summary,
)


@dataclass(frozen=True)
class GovernanceArtifactInspectionResult:
    """Result of governance artifact manifest inspection."""
    present: bool
    valid_manifest: bool
    code: str
    message: str
    manifest_hash: str | None
    artifact_count: int
    required_count: int
    optional_count: int
    artifact_types: tuple[str, ...]
    provider_summary: dict[str, Any] | None
    errors: tuple[dict[str, str], ...]


def inspect_governance_artifacts_from_bundle(
    bundle: Mapping[str, Any],
) -> GovernanceArtifactInspectionResult:
    """
    Inspect governance artifact manifest from ExecutionProofBundle.

    Args:
        bundle: ExecutionProofBundle data as mapping (dict with "bundle" key or direct).

    Returns:
        Inspection result with diagnostic information.
        Does not alter bundle contents or Core replay verdict.
    """
    # Extract inner bundle if nested (SDK format)
    inner = bundle.get("bundle") if isinstance(bundle, dict) else bundle
    if not isinstance(inner, dict):
        return GovernanceArtifactInspectionResult(
            present=False,
            valid_manifest=False,
            code="INVALID_BUNDLE",
            message="Bundle is not a dict",
            manifest_hash=None,
            artifact_count=0,
            required_count=0,
            optional_count=0,
            artifact_types=(),
            provider_summary=None,
            errors=(),
        )

    # Extract governance_evidence
    governance_evidence = inner.get("governance_evidence", {})
    if not isinstance(governance_evidence, dict):
        governance_evidence = {}

    # Check for manifest in expected location
    manifest_key = "governance_artifacts_manifest"
    manifest_data = governance_evidence.get(manifest_key)

    if manifest_data is None:
        # No manifest present
        return GovernanceArtifactInspectionResult(
            present=False,
            valid_manifest=False,
            code="NOT_PRESENT",
            message="No governance artifacts manifest found",
            manifest_hash=None,
            artifact_count=0,
            required_count=0,
            optional_count=0,
            artifact_types=(),
            provider_summary=get_governance_provider_summary(),
            errors=(),
        )

    # Validate manifest shape
    try:
        manifest = validate_governance_manifest(manifest_data)
    except Exception as e:
        # Manifest invalid
        return GovernanceArtifactInspectionResult(
            present=True,
            valid_manifest=False,
            code="INVALID_MANIFEST",
            message=f"Manifest validation failed: {e}",
            manifest_hash=None,
            artifact_count=0,
            required_count=0,
            optional_count=0,
            artifact_types=(),
            provider_summary=get_governance_provider_summary(),
            errors=({"field": "manifest", "error": str(e)},),
        )

    # Compute manifest hash
    try:
        manifest_hash = governance_manifest_hash(manifest)
    except Exception:
        manifest_hash = None

    # Count artifacts
    artifact_count = len(manifest.entries)
    required_count = sum(1 for entry in manifest.entries if entry.required_for_verdict)
    optional_count = artifact_count - required_count

    # Extract artifact types (sorted deterministically)
    artifact_types = tuple(sorted(set(entry.artifact_type for entry in manifest.entries)))

    # Get provider summary (metadata-only discovery)
    provider_summary = get_governance_provider_summary()

    # Build provider availability per artifact type
    provider_availability: dict[str, str] = {}
    for artifact_type in artifact_types:
        # Check if provider is available
        discovery = discover_governance_artifact_providers(load=False)
        provider_found = False
        for provider_name, provider_info in discovery.providers.items():
            if provider_info.artifact_type == artifact_type:
                provider_found = True
                break

        if provider_found:
            provider_availability[artifact_type] = "available"
        else:
            provider_availability[artifact_type] = "unavailable"

    # Add provider availability to summary
    if provider_summary is not None:
        provider_summary = dict(provider_summary)  # Make mutable copy
        provider_summary["artifact_type_availability"] = provider_availability

    return GovernanceArtifactInspectionResult(
        present=True,
        valid_manifest=True,
        code="VALID",
        message="Governance artifacts manifest is valid",
        manifest_hash=manifest_hash,
        artifact_count=artifact_count,
        required_count=required_count,
        optional_count=optional_count,
        artifact_types=artifact_types,
        provider_summary=provider_summary,
        errors=(),
    )


def format_inspection_result_for_output(
    inspection: GovernanceArtifactInspectionResult,
) -> dict[str, Any]:
    """
    Format inspection result for structured output.

    Args:
        inspection: Inspection result from inspect_governance_artifacts_from_bundle.

    Returns:
        JSON-serializable dictionary for CLI output.
    """
    if not inspection.present:
        return {
            "governance_artifacts": {
                "present": False,
                "code": inspection.code,
                "verdict_effect": "none",
            }
        }

    result = {
        "governance_artifacts": {
            "present": True,
            "valid_manifest": inspection.valid_manifest,
            "code": inspection.code,
            "message": inspection.message,
            "manifest_hash": inspection.manifest_hash,
            "artifact_count": inspection.artifact_count,
            "required_count": inspection.required_count,
            "optional_count": inspection.optional_count,
            "artifact_types": list(inspection.artifact_types),
            "verdict_effect": "diagnostic_only",
        }
    }

    # Add provider availability if available
    if inspection.provider_summary:
        artifact_type_availability = inspection.provider_summary.get(
            "artifact_type_availability", {}
        )
        result["governance_artifacts"]["provider_availability"] = (
            artifact_type_availability
        )

    # Add errors if any
    if inspection.errors:
        result["governance_artifacts"]["errors"] = list(inspection.errors)

    return result
