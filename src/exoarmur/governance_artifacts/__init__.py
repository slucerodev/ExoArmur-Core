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

__all__ = [
    "GovernanceProviderDiscoveryResult",
    "GovernanceProviderInfo",
    "discover_governance_artifact_providers",
    "get_governance_provider_summary",
    "GovernanceArtifactManifest",
    "GovernanceArtifactManifestEntry",
    "canonicalize_governance_manifest",
    "governance_manifest_hash",
    "validate_governance_manifest",
    "GovernanceArtifactInspectionResult",
    "format_inspection_result_for_output",
    "inspect_governance_artifacts_from_bundle",
]
