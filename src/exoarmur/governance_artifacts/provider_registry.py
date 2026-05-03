"""
Provider Registry for Governance Artifact Discovery

Discovers optional governance artifact providers from ExoArmur-GovernanceModules
via Python entry points. Core does not import GovernanceModules directly.

Entry point group: exoarmur.governance_artifacts
"""

import importlib.metadata
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "exoarmur.governance_artifacts"


@dataclass(frozen=True)
class GovernanceProviderInfo:
    """Information about a discovered governance artifact provider."""
    name: str
    artifact_type: str
    schema_versions: tuple[str, ...]
    provider_version: str
    entry_point_group: str
    module: Optional[str]
    loadable: bool


@dataclass(frozen=True)
class GovernanceProviderDiscoveryResult:
    """Result of governance artifact provider discovery."""
    entry_point_group: str
    providers: Dict[str, GovernanceProviderInfo]
    unavailable: Dict[str, str]
    total_discovered: int


def discover_governance_artifact_providers(load: bool = False) -> GovernanceProviderDiscoveryResult:
    """
    Discover governance artifact providers via entry points.

    Args:
        load: If True, attempt to load provider objects. If False, only inspect metadata.

    Returns:
        Discovery result with provider info and unavailable status.
    """
    providers: Dict[str, GovernanceProviderInfo] = {}
    unavailable: Dict[str, str] = {}

    try:
        entry_points = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as e:
        # Entry point group not found is expected when GovernanceModules is not installed
        logger.debug(f"No entry points found for group {ENTRY_POINT_GROUP}: {e}")
        return GovernanceProviderDiscoveryResult(
            entry_point_group=ENTRY_POINT_GROUP,
            providers={},
            unavailable={},
            total_discovered=0,
        )

    # Sort provider names deterministically
    sorted_entry_points = sorted(entry_points, key=lambda ep: ep.name)

    for ep in sorted_entry_points:
        provider_name = ep.name
        module_name = getattr(ep, "module", None)

        if load:
            # Try to load the provider
            try:
                provider_instance = ep.load()
                # Extract metadata from loaded provider if possible
                artifact_type = getattr(provider_instance, "artifact_type", provider_name)
                schema_versions = tuple(getattr(provider_instance, "schema_versions", ()))
                provider_version = getattr(provider_instance, "provider_version", "unknown")

                providers[provider_name] = GovernanceProviderInfo(
                    name=provider_name,
                    artifact_type=artifact_type,
                    schema_versions=schema_versions,
                    provider_version=provider_version,
                    entry_point_group=ENTRY_POINT_GROUP,
                    module=module_name,
                    loadable=True,
                )
            except Exception as e:
                # Provider load failed - record as unavailable but don't crash
                error_msg = f"{type(e).__name__}: {e}"
                unavailable[provider_name] = error_msg
                logger.debug(f"Failed to load provider {provider_name}: {error_msg}")
        else:
            # Only inspect metadata without loading
            artifact_type = provider_name  # Default to provider name if not loaded
            schema_versions = ()  # Unknown without loading
            provider_version = getattr(ep, "version", "unknown")

            providers[provider_name] = GovernanceProviderInfo(
                name=provider_name,
                artifact_type=artifact_type,
                schema_versions=schema_versions,
                provider_version=provider_version,
                entry_point_group=ENTRY_POINT_GROUP,
                module=module_name,
                loadable=True,  # Assume loadable until proven otherwise
            )

    return GovernanceProviderDiscoveryResult(
        entry_point_group=ENTRY_POINT_GROUP,
        providers=providers,
        unavailable=unavailable,
        total_discovered=len(providers),
    )


def get_governance_provider_summary() -> Dict[str, Any]:
    """
    Get a JSON-serializable summary of governance artifact providers.

    Returns:
        Dictionary with provider summary for diagnostics.
    """
    result = discover_governance_artifact_providers(load=False)

    summary = {
        "entry_point_group": result.entry_point_group,
        "total_discovered": result.total_discovered,
        "unavailable_count": len(result.unavailable),
        "providers": {},
    }

    for name, info in result.providers.items():
        summary["providers"][name] = {
            "artifact_type": info.artifact_type,
            "schema_versions": list(info.schema_versions),
            "provider_version": info.provider_version,
            "module": info.module,
            "loadable": info.loadable,
        }

    if result.unavailable:
        summary["unavailable"] = result.unavailable

    return summary
