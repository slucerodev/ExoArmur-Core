"""
Governance Artifact Semantic Verification

Provides optional semantic verification of governance artifacts through discovered providers.
Diagnostic-only path - does not alter Core replay verdicts.
"""

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from exoarmur.governance_artifacts.manifest import (
    validate_governance_manifest,
)
from exoarmur.governance_artifacts.provider_registry import (
    GovernanceProviderDiscoveryResult,
    GovernanceProviderInfo,
    discover_governance_artifact_providers,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GovernanceArtifactSemanticResult:
    """Result of semantic verification for a single artifact."""
    attempted: bool
    artifact_type: str
    schema_version: str
    artifact_hash: str
    provider_available: bool
    provider_version: str | None
    content_available: bool
    hash_matches: bool | None
    semantic_valid: bool | None
    code: str
    message: str


@dataclass(frozen=True)
class GovernanceArtifactSemanticAggregateResult:
    """Aggregate result of semantic verification for all artifacts."""
    attempted: bool
    total: int
    verified: int
    valid: int
    invalid: int
    unavailable: int
    results: tuple[GovernanceArtifactSemanticResult, ...]


def _extract_governance_artifacts_content(
    governance_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Extract embedded artifact content from governance_evidence.

    Expected structure:
    governance_evidence["governance_artifacts"] = {
        "<artifact_type>": {
            "<artifact_id_or_name>": { ... artifact json ... }
        }
    }

    Args:
        governance_evidence: The governance_evidence dict from ExecutionProofBundle.

    Returns:
        Nested dict of artifact content, or empty dict if not present.
    """
    if not isinstance(governance_evidence, dict):
        return {}

    artifacts = governance_evidence.get("governance_artifacts", {})
    if not isinstance(artifacts, dict):
        return {}

    return artifacts


def _find_provider_for_artifact_type(
    artifact_type: str,
    discovery_result: GovernanceProviderDiscoveryResult,
) -> GovernanceProviderInfo | None:
    """
    Find provider info for a given artifact type.

    Args:
        artifact_type: The artifact type to find a provider for.
        discovery_result: Result from discover_governance_artifact_providers.

    Returns:
        ProviderInfo if found, None otherwise.
    """
    for provider_name, provider_info in discovery_result.providers.items():
        if provider_info.artifact_type == artifact_type:
            return provider_info
    return None


def _load_provider_and_verify(
    provider_info: GovernanceProviderInfo,
    artifact_content: Mapping[str, Any],
    expected_hash: str,
) -> GovernanceArtifactSemanticResult:
    """
    Load provider and verify artifact.

    Args:
        provider_info: Provider info from discovery.
        artifact_content: The artifact content as mapping.
        expected_hash: Expected hash from manifest.

    Returns:
        Semantic verification result.
    """
    import importlib.metadata

    try:
        # Load provider via entry point
        entry_points = importlib.metadata.entry_points(
            group=provider_info.entry_point_group
        )
        ep = None
        for entry_point in entry_points:
            if entry_point.name == provider_info.name:
                ep = entry_point
                break

        if ep is None:
            return GovernanceArtifactSemanticResult(
                attempted=True,
                artifact_type=provider_info.artifact_type,
                schema_version=artifact_content.get("schema_version", "unknown"),
                artifact_hash=expected_hash,
                provider_available=False,
                provider_version=None,
                content_available=True,
                hash_matches=None,
                semantic_valid=None,
                code="PROVIDER_UNAVAILABLE",
                message=f"Provider entry point not found: {provider_info.name}",
            )

        provider = ep.load()

        # Check provider has required methods
        if not hasattr(provider, "canonical_hash") or not hasattr(
            provider, "verify_artifact"
        ):
            return GovernanceArtifactSemanticResult(
                attempted=True,
                artifact_type=provider_info.artifact_type,
                schema_version=artifact_content.get("schema_version", "unknown"),
                artifact_hash=expected_hash,
                provider_available=True,
                provider_version=provider_info.provider_version,
                content_available=True,
                hash_matches=None,
                semantic_valid=None,
                code="PROVIDER_ERROR",
                message="Provider missing required methods: canonical_hash or verify_artifact",
            )

        # Compute canonical hash using provider
        try:
            computed_hash = provider.canonical_hash(artifact_content)
        except Exception as e:
            logger.debug(f"Provider canonical_hash failed: {e}")
            return GovernanceArtifactSemanticResult(
                attempted=True,
                artifact_type=provider_info.artifact_type,
                schema_version=artifact_content.get("schema_version", "unknown"),
                artifact_hash=expected_hash,
                provider_available=True,
                provider_version=provider_info.provider_version,
                content_available=True,
                hash_matches=None,
                semantic_valid=None,
                code="PROVIDER_ERROR",
                message=f"Provider canonical_hash error: {e}",
            )

        # Check hash match
        hash_matches = computed_hash == expected_hash

        if not hash_matches:
            return GovernanceArtifactSemanticResult(
                attempted=True,
                artifact_type=provider_info.artifact_type,
                schema_version=artifact_content.get("schema_version", "unknown"),
                artifact_hash=expected_hash,
                provider_available=True,
                provider_version=provider_info.provider_version,
                content_available=True,
                hash_matches=False,
                semantic_valid=None,
                code="ARTIFACT_HASH_MISMATCH",
                message=f"Hash mismatch: expected {expected_hash}, computed {computed_hash}",
            )

        # Run semantic verification
        try:
            verification_result = provider.verify_artifact(artifact_content)

            # Convert provider result to Core-owned structure
            # Provider returns VerificationResult with: valid, code, message, artifact_hash
            valid = getattr(verification_result, "valid", False)
            message = getattr(verification_result, "message", "")

            if valid:
                return GovernanceArtifactSemanticResult(
                    attempted=True,
                    artifact_type=provider_info.artifact_type,
                    schema_version=artifact_content.get("schema_version", "unknown"),
                    artifact_hash=expected_hash,
                    provider_available=True,
                    provider_version=provider_info.provider_version,
                    content_available=True,
                    hash_matches=True,
                    semantic_valid=True,
                    code="SEMANTIC_VALID",
                    message=message or "Artifact verified successfully",
                )
            else:
                return GovernanceArtifactSemanticResult(
                    attempted=True,
                    artifact_type=provider_info.artifact_type,
                    schema_version=artifact_content.get("schema_version", "unknown"),
                    artifact_hash=expected_hash,
                    provider_available=True,
                    provider_version=provider_info.provider_version,
                    content_available=True,
                    hash_matches=True,
                    semantic_valid=False,
                    code="SEMANTIC_INVALID",
                    message=message or "Artifact verification failed",
                )

        except Exception as e:
            logger.debug(f"Provider verify_artifact failed: {e}")
            return GovernanceArtifactSemanticResult(
                attempted=True,
                artifact_type=provider_info.artifact_type,
                schema_version=artifact_content.get("schema_version", "unknown"),
                artifact_hash=expected_hash,
                provider_available=True,
                provider_version=provider_info.provider_version,
                content_available=True,
                hash_matches=True,
                semantic_valid=None,
                code="PROVIDER_ERROR",
                message=f"Provider verification error: {e}",
            )

    except Exception as e:
        logger.debug(f"Failed to load provider {provider_info.name}: {e}")
        return GovernanceArtifactSemanticResult(
            attempted=True,
            artifact_type=provider_info.artifact_type,
            schema_version=artifact_content.get("schema_version", "unknown"),
            artifact_hash=expected_hash,
            provider_available=False,
            provider_version=None,
            content_available=True,
            hash_matches=None,
            semantic_valid=None,
            code="PROVIDER_ERROR",
            message=f"Provider load error: {e}",
        )


def verify_governance_artifacts_semantically(
    bundle: Mapping[str, Any],
) -> GovernanceArtifactSemanticAggregateResult:
    """
    Verify governance artifacts semantically through discovered providers.

    Args:
        bundle: ExecutionProofBundle data as mapping (dict with "bundle" key or direct).

    Returns:
        Aggregate semantic verification result.
        Does not alter bundle contents or Core replay verdict.
    """
    # Extract inner bundle if nested (SDK format)
    inner = bundle.get("bundle") if isinstance(bundle, dict) else bundle
    if not isinstance(inner, dict):
        return GovernanceArtifactSemanticAggregateResult(
            attempted=False,
            total=0,
            verified=0,
            valid=0,
            invalid=0,
            unavailable=0,
            results=(),
        )

    # Extract governance_evidence
    governance_evidence = inner.get("governance_evidence", {})
    if not isinstance(governance_evidence, dict):
        governance_evidence = {}

    # Check for manifest
    manifest_key = "governance_artifacts_manifest"
    manifest_data = governance_evidence.get(manifest_key)

    if manifest_data is None:
        # No manifest - no semantic verification attempted
        return GovernanceArtifactSemanticAggregateResult(
            attempted=False,
            total=0,
            verified=0,
            valid=0,
            invalid=0,
            unavailable=0,
            results=(),
        )

    # Validate manifest
    try:
        manifest = validate_governance_manifest(manifest_data)
    except Exception:
        # Invalid manifest - no semantic verification attempted
        return GovernanceArtifactSemanticAggregateResult(
            attempted=False,
            total=0,
            verified=0,
            valid=0,
            invalid=0,
            unavailable=0,
            results=(),
        )

    # Extract embedded artifact content
    artifacts_content = _extract_governance_artifacts_content(governance_evidence)

    # Discover providers (with load=False for metadata-only)
    discovery = discover_governance_artifact_providers(load=False)

    # Process each manifest entry
    results_list: list[GovernanceArtifactSemanticResult] = []
    total = len(manifest.entries)
    verified = 0
    valid = 0
    invalid = 0
    unavailable = 0

    # Sort deterministically by artifact_type, schema_version, artifact_hash
    sorted_entries = sorted(
        manifest.entries,
        key=lambda e: (e.artifact_type, e.schema_version, e.artifact_hash),
    )

    for entry in sorted_entries:
        # Check if artifact content is embedded
        # Use artifact_hash as the key for content lookup
        artifact_content = None
        content_available = False

        if artifacts_content:
            # Try to find content by artifact_type and artifact_hash
            type_content = artifacts_content.get(entry.artifact_type, {})
            if isinstance(type_content, dict):
                # Look for content keyed by artifact_hash
                for content_key, content_value in type_content.items():
                    if isinstance(content_value, dict):
                        # Check if this content matches the expected hash
                        # For now, we use artifact_hash as the key
                        if content_key == entry.artifact_hash:
                            artifact_content = content_value
                            content_available = True
                            break

        if not content_available:
            # Artifact content not embedded
            results_list.append(
                GovernanceArtifactSemanticResult(
                    attempted=True,
                    artifact_type=entry.artifact_type,
                    schema_version=entry.schema_version,
                    artifact_hash=entry.artifact_hash,
                    provider_available=False,
                    provider_version=None,
                    content_available=False,
                    hash_matches=None,
                    semantic_valid=None,
                    code="ARTIFACT_CONTENT_UNAVAILABLE",
                    message="Artifact content not embedded in bundle",
                )
            )
            unavailable += 1
            continue

        # Find provider for this artifact type
        provider_info = _find_provider_for_artifact_type(
            entry.artifact_type, discovery
        )

        if provider_info is None:
            # Provider not available
            results_list.append(
                GovernanceArtifactSemanticResult(
                    attempted=True,
                    artifact_type=entry.artifact_type,
                    schema_version=entry.schema_version,
                    artifact_hash=entry.artifact_hash,
                    provider_available=False,
                    provider_version=None,
                    content_available=True,
                    hash_matches=None,
                    semantic_valid=None,
                    code="PROVIDER_UNAVAILABLE",
                    message=f"No provider available for artifact type: {entry.artifact_type}",
                )
            )
            unavailable += 1
            continue

        # Load provider and verify artifact
        # artifact_content is guaranteed to be non-None here due to the content_available check above
        assert artifact_content is not None
        result = _load_provider_and_verify(
            provider_info, artifact_content, entry.artifact_hash
        )
        results_list.append(result)

        if result.semantic_valid is True:
            verified += 1
            valid += 1
        elif result.semantic_valid is False:
            verified += 1
            invalid += 1
        else:
            # Verification did not complete (error, hash mismatch, provider unavailable, etc.)
            unavailable += 1

    return GovernanceArtifactSemanticAggregateResult(
        attempted=True,
        total=total,
        verified=verified,
        valid=valid,
        invalid=invalid,
        unavailable=unavailable,
        results=tuple(results_list),
    )


def format_semantic_verification_for_output(
    aggregate: GovernanceArtifactSemanticAggregateResult,
) -> dict[str, Any]:
    """
    Format semantic verification result for structured output.

    Args:
        aggregate: Aggregate result from verify_governance_artifacts_semantically.

    Returns:
        JSON-serializable dictionary for CLI output.
    """
    if not aggregate.attempted:
        return {
            "attempted": False,
            "code": "NOT_ATTEMPTED",
            "verdict_effect": "none",
        }

    results_list = []
    for result in aggregate.results:
        result_dict = {
            "artifact_type": result.artifact_type,
            "schema_version": result.schema_version,
            "artifact_hash": result.artifact_hash,
            "provider_available": result.provider_available,
            "provider_version": result.provider_version,
            "content_available": result.content_available,
            "hash_matches": result.hash_matches,
            "semantic_valid": result.semantic_valid,
            "code": result.code,
            "message": result.message,
        }
        results_list.append(result_dict)

    return {
        "attempted": True,
        "verdict_effect": "diagnostic_only",
        "total": aggregate.total,
        "verified": aggregate.verified,
        "valid": aggregate.valid,
        "invalid": aggregate.invalid,
        "unavailable": aggregate.unavailable,
        "results": results_list,
    }
