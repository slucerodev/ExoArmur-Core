"""
Governance Artifact Manifest Validation

Validates and canonicalizes governance artifact manifests for Core integration.
Manifests describe optional governance artifacts that may be included in proof bundles.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from exoarmur.replay.canonical_utils import canonical_json, stable_hash


@dataclass(frozen=True)
class GovernanceArtifactManifestEntry:
    """Single entry in a governance artifact manifest."""
    artifact_type: str
    schema_version: str
    artifact_hash: str
    artifact_path: str | None = None
    producer_module: str = ""
    producer_version: str = ""
    required_for_verdict: bool = False


@dataclass(frozen=True)
class GovernanceArtifactManifest:
    """Governance artifact manifest with validation and canonicalization."""
    entries: tuple[GovernanceArtifactManifestEntry, ...]


# SHA-256 hex pattern: exactly 64 lowercase hex characters
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _validate_sha256_hex(value: str, field_name: str) -> None:
    """Validate that a string is a valid SHA-256 hex string."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be string, got {type(value).__name__}")
    if not SHA256_HEX_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must be 64-character lowercase SHA-256 hex, got: {value}"
        )


def _validate_not_blank(value: str, field_name: str) -> None:
    """Validate that a string is not blank."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be string, got {type(value).__name__}")
    if not value or value.strip() == "":
        raise ValueError(f"{field_name} cannot be blank")


def _validate_artifact_path(path: str | None) -> str | None:
    """
    Validate artifact path is relative and safe.

    Rejects:
    - Absolute paths
    - Path traversal (..)
    - Windows backslashes (normalize or fail)

    Returns:
        Normalized POSIX-style path or None if path is None.
    """
    if path is None:
        return None

    if not isinstance(path, str):
        raise ValueError(f"artifact_path must be string or None, got {type(path).__name__}")

    # Reject absolute paths
    if Path(path).is_absolute():
        raise ValueError(f"artifact_path must be relative, got absolute: {path}")

    # Reject path traversal
    if ".." in path:
        raise ValueError(f"artifact_path must not contain path traversal: {path}")

    # Normalize backslashes to forward slashes (POSIX-style)
    normalized = path.replace("\\", "/")

    return normalized


def validate_governance_manifest(
    data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> GovernanceArtifactManifest:
    """
    Validate governance manifest data and return typed model.

    Args:
        data: Manifest data as mapping (dict with entries) or sequence of entries.

    Returns:
        Validated GovernanceArtifactManifest.

    Raises:
        ValueError: If manifest structure or values are invalid.
    """
    entries_list: list[GovernanceArtifactManifestEntry] = []

    # Handle both dict (with "entries" key) and sequence of entries
    if isinstance(data, Mapping):
        raw_entries = data.get("entries", [])
        if not isinstance(raw_entries, (list, tuple)):
            raise ValueError("manifest entries must be a list or tuple")
    elif isinstance(data, (list, tuple)):
        raw_entries = data
    else:
        raise ValueError("manifest must be a mapping or sequence")

    for idx, entry in enumerate(raw_entries):
        if not isinstance(entry, Mapping):
            raise ValueError(f"manifest entry {idx} must be a mapping")

        artifact_type = entry.get("artifact_type", "")
        schema_version = entry.get("schema_version", "")
        artifact_hash = entry.get("artifact_hash", "")
        artifact_path = entry.get("artifact_path")
        producer_module = entry.get("producer_module", "")
        producer_version = entry.get("producer_version", "")
        required_for_verdict = entry.get("required_for_verdict", False)

        # Validate required fields
        _validate_not_blank(artifact_type, "artifact_type")
        _validate_not_blank(schema_version, "schema_version")
        _validate_sha256_hex(artifact_hash, "artifact_hash")

        # Validate optional fields
        if artifact_path is not None:
            artifact_path = _validate_artifact_path(artifact_path)

        # Validate producer fields
        _validate_not_blank(producer_module, "producer_module")
        _validate_not_blank(producer_version, "producer_version")

        # Validate required_for_verdict is boolean
        if not isinstance(required_for_verdict, bool):
            raise ValueError(
                f"required_for_verdict must be boolean, got {type(required_for_verdict).__name__}"
            )

        entries_list.append(
            GovernanceArtifactManifestEntry(
                artifact_type=artifact_type,
                schema_version=schema_version,
                artifact_hash=artifact_hash,
                artifact_path=artifact_path,
                producer_module=producer_module,
                producer_version=producer_version,
                required_for_verdict=required_for_verdict,
            )
        )

    # Preserve order from input (do not sort entries)
    return GovernanceArtifactManifest(entries=tuple(entries_list))


def canonicalize_governance_manifest(
    manifest: GovernanceArtifactManifest | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Canonicalize governance manifest for deterministic hashing.

    Args:
        manifest: Manifest as typed model or raw data.

    Returns:
        Canonical dictionary representation.
    """
    # Convert to typed model if needed
    if not isinstance(manifest, GovernanceArtifactManifest):
        manifest = validate_governance_manifest(manifest)

    # Convert to canonical dict
    entries_list = []
    for entry in manifest.entries:
        entry_dict = {
            "artifact_type": entry.artifact_type,
            "schema_version": entry.schema_version,
            "artifact_hash": entry.artifact_hash,
            "producer_module": entry.producer_module,
            "producer_version": entry.producer_version,
            "required_for_verdict": entry.required_for_verdict,
        }
        if entry.artifact_path is not None:
            entry_dict["artifact_path"] = entry.artifact_path
        entries_list.append(entry_dict)

    canonical_dict = {
        "entries": entries_list,
    }

    # Use Core's canonical JSON for deterministic serialization
    canonical_json_str = canonical_json(canonical_dict)
    return {"canonical": canonical_json_str}


def governance_manifest_hash(
    manifest: GovernanceArtifactManifest | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> str:
    """
    Compute SHA-256 hash of canonical governance manifest.

    Args:
        manifest: Manifest as typed model or raw data.

    Returns:
        64-character lowercase SHA-256 hex hash.
    """
    canonical_data = canonicalize_governance_manifest(manifest)
    canonical_json_str = canonical_data["canonical"]
    return stable_hash(canonical_json_str)
