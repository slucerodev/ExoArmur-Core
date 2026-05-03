"""
Governance Artifacts Module for ExoArmur Core

Provides optional discovery and validation of governance artifact providers
from ExoArmur-GovernanceModules via Python entry points.

This module does not import GovernanceModules directly. Discovery is lazy
and optional - Core runs successfully without GovernanceModules installed.
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
]
