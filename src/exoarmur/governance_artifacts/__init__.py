"""
Core Governance Artifacts Integration

This module provides optional governance artifact provider discovery and manifest validation
for ExoArmur Core. It does not import GovernanceModules directly.

Discovery is lazy and optional - Core runs successfully without GovernanceModules installed.
"""

from .provider_registry import (
    GovernanceProviderDiscoveryResult,
    GovernanceProviderInfo,
    discover_governance_artifact_providers,
    get_governance_provider_summary,
)

from .manifest import (
    GovernanceArtifactManifest,
    GovernanceArtifactManifestEntry,
    canonicalize_governance_manifest,
    governance_manifest_hash,
    validate_governance_manifest,
)

from .inspection import (
    GovernanceArtifactInspectionResult,
    format_inspection_result_for_output,
    inspect_governance_artifacts_from_bundle,
)

from .semantic_verification import (
    GovernanceArtifactSemanticResult,
    GovernanceArtifactSemanticAggregateResult,
    verify_governance_artifacts_semantically,
    format_semantic_verification_for_output,
)

from .enforcement import (
    GovernanceArtifactEnforcementResult,
    enforce_governance_artifacts,
    format_enforcement_for_output,
)

__all__ = [
    # Provider registry
    "GovernanceProviderInfo",
    "GovernanceProviderDiscoveryResult",
    "discover_governance_artifact_providers",
    "get_governance_provider_summary",
    # Manifest
    "GovernanceArtifactManifestEntry",
    "GovernanceArtifactManifest",
    "validate_governance_manifest",
    "canonicalize_governance_manifest",
    "governance_manifest_hash",
    # Inspection
    "GovernanceArtifactInspectionResult",
    "inspect_governance_artifacts_from_bundle",
    "format_inspection_result_for_output",
    # Semantic verification
    "GovernanceArtifactSemanticResult",
    "GovernanceArtifactSemanticAggregateResult",
    "verify_governance_artifacts_semantically",
    "format_semantic_verification_for_output",
    # Enforcement
    "GovernanceArtifactEnforcementResult",
    "enforce_governance_artifacts",
    "format_enforcement_for_output",
]
