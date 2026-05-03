"""
Tests for governance artifact manifest validation.

Tests Core-side validation and canonicalization of governance artifact manifests.
"""

import pytest

from exoarmur.governance_artifacts.manifest import (
    canonicalize_governance_manifest,
    governance_manifest_hash,
    validate_governance_manifest,
)


class TestGovernanceManifestValidation:
    """Tests for governance manifest validation."""

    def test_valid_manifest_entry_passes(self):
        """Valid manifest entry passes validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        manifest = validate_governance_manifest([entry])

        assert len(manifest.entries) == 1
        entry_obj = manifest.entries[0]
        assert entry_obj.artifact_type == "policy_snapshot"
        assert entry_obj.schema_version == "policy_snapshot.v1"
        assert entry_obj.artifact_hash == "a" * 64
        assert entry_obj.producer_module == "exoarmur-governance-modules"
        assert entry_obj.producer_version == "0.1.0"
        assert entry_obj.required_for_verdict is False

    def test_valid_manifest_list_passes(self):
        """Valid manifest as list passes validation."""
        entries = [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "a" * 64,
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
            },
            {
                "artifact_type": "tool_invocation_proof",
                "schema_version": "tool_invocation_proof.v1",
                "artifact_hash": "b" * 64,
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
            },
        ]

        manifest = validate_governance_manifest(entries)

        assert len(manifest.entries) == 2
        assert manifest.entries[0].artifact_type == "policy_snapshot"
        assert manifest.entries[1].artifact_type == "tool_invocation_proof"

    def test_valid_manifest_dict_with_entries_passes(self):
        """Valid manifest as dict with entries key passes validation."""
        manifest_data = {
            "entries": [
                {
                    "artifact_type": "policy_snapshot",
                    "schema_version": "policy_snapshot.v1",
                    "artifact_hash": "a" * 64,
                    "producer_module": "exoarmur-governance-modules",
                    "producer_version": "0.1.0",
                }
            ]
        }

        manifest = validate_governance_manifest(manifest_data)

        assert len(manifest.entries) == 1
        assert manifest.entries[0].artifact_type == "policy_snapshot"

    def test_invalid_hash_fails(self):
        """Invalid hash fails validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "invalid_hash",  # Not 64-char hex
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        with pytest.raises(ValueError, match="artifact_hash must be 64-character"):
            validate_governance_manifest([entry])

    def test_hash_with_uppercase_fails(self):
        """Hash with uppercase characters fails validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": ("A" * 64),  # Uppercase not allowed
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        with pytest.raises(ValueError, match="artifact_hash must be 64-character"):
            validate_governance_manifest([entry])

    def test_blank_fields_fail(self):
        """Blank required fields fail validation."""
        # Blank artifact_type
        with pytest.raises(ValueError, match="artifact_type cannot be blank"):
            validate_governance_manifest([
                {
                    "artifact_type": "",
                    "schema_version": "policy_snapshot.v1",
                    "artifact_hash": "a" * 64,
                    "producer_module": "exoarmur-governance-modules",
                    "producer_version": "0.1.0",
                }
            ])

        # Blank schema_version
        with pytest.raises(ValueError, match="schema_version cannot be blank"):
            validate_governance_manifest([
                {
                    "artifact_type": "policy_snapshot",
                    "schema_version": "",
                    "artifact_hash": "a" * 64,
                    "producer_module": "exoarmur-governance-modules",
                    "producer_version": "0.1.0",
                }
            ])

    def test_absolute_artifact_path_fails(self):
        """Absolute artifact_path fails validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "artifact_path": "/absolute/path/artifact.json",  # Absolute path
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        with pytest.raises(ValueError, match="artifact_path must be relative"):
            validate_governance_manifest([entry])

    def test_path_traversal_fails(self):
        """Path traversal in artifact_path fails validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "artifact_path": "../parent/artifact.json",  # Path traversal
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        with pytest.raises(ValueError, match="artifact_path must not contain path traversal"):
            validate_governance_manifest([entry])

    def test_backslash_paths_normalize_or_fail_deterministically(self):
        """Backslash paths normalize to forward slashes deterministically."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "artifact_path": "governance\\artifacts\\artifact.json",  # Backslashes
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        manifest = validate_governance_manifest([entry])

        # Should normalize to forward slashes
        assert manifest.entries[0].artifact_path == "governance/artifacts/artifact.json"

    def test_manifest_hash_stable_across_dict_key_reordering(self):
        """Manifest hash is stable across dict key reordering."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        hash1 = governance_manifest_hash([entry])
        hash2 = governance_manifest_hash([entry])

        assert hash1 == hash2

    def test_manifest_entry_ordering_is_preserved(self):
        """Manifest entry ordering is preserved from input."""
        entries = [
            {
                "artifact_type": "z_provider",
                "schema_version": "z.v1",
                "artifact_hash": "f" * 64,
                "producer_module": "test",
                "producer_version": "1.0.0",
            },
            {
                "artifact_type": "a_provider",
                "schema_version": "a.v1",
                "artifact_hash": "e" * 64,
                "producer_module": "test",
                "producer_version": "1.0.0",
            },
        ]

        manifest = validate_governance_manifest(entries)

        # Order should be preserved, not sorted
        assert manifest.entries[0].artifact_type == "z_provider"
        assert manifest.entries[1].artifact_type == "a_provider"

    def test_unknown_artifact_type_allowed_at_shape_level(self):
        """Unknown artifact type is allowed at manifest shape level."""
        entry = {
            "artifact_type": "unknown_future_provider",
            "schema_version": "unknown.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "future-module",
            "producer_version": "1.0.0",
        }

        # Should validate successfully at shape level
        manifest = validate_governance_manifest([entry])
        assert manifest.entries[0].artifact_type == "unknown_future_provider"

    def test_required_for_verdict_default_is_false(self):
        """required_for_verdict defaults to False."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        manifest = validate_governance_manifest([entry])
        assert manifest.entries[0].required_for_verdict is False

    def test_required_for_verdict_true_is_preserved(self):
        """required_for_verdict true is preserved."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
            "required_for_verdict": True,
        }

        manifest = validate_governance_manifest([entry])
        assert manifest.entries[0].required_for_verdict is True

    def test_required_for_verdict_non_boolean_fails(self):
        """required_for_verdict non-boolean fails validation."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
            "required_for_verdict": "true",  # String, not boolean
        }

        with pytest.raises(ValueError, match="required_for_verdict must be boolean"):
            validate_governance_manifest([entry])

    def test_canonicalize_governance_manifest_provides_deterministic_dict(self):
        """canonicalize_governance_manifest provides deterministic dict."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        canonical = canonicalize_governance_manifest([entry])

        assert "canonical" in canonical
        assert isinstance(canonical["canonical"], str)

        # Should be stable across calls
        canonical2 = canonicalize_governance_manifest([entry])
        assert canonical["canonical"] == canonical2["canonical"]

    def test_governance_manifest_hash_provides_stable_sha256(self):
        """governance_manifest_hash provides stable SHA-256 hex."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        hash1 = governance_manifest_hash([entry])
        hash2 = governance_manifest_hash([entry])

        assert hash1 == hash2
        assert len(hash1) == 64
        assert hash1.islower()
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_canonicalize_with_artifact_path(self):
        """Canonicalization includes artifact_path when present."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "artifact_path": "governance/artifacts/artifact.json",
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        canonical = canonicalize_governance_manifest([entry])
        canonical_json_str = canonical["canonical"]

        assert "artifact_path" in canonical_json_str

    def test_canonicalize_without_artifact_path(self):
        """Canonicalization excludes artifact_path when absent."""
        entry = {
            "artifact_type": "policy_snapshot",
            "schema_version": "policy_snapshot.v1",
            "artifact_hash": "a" * 64,
            "producer_module": "exoarmur-governance-modules",
            "producer_version": "0.1.0",
        }

        canonical = canonicalize_governance_manifest([entry])
        canonical_json_str = canonical["canonical"]

        assert "artifact_path" not in canonical_json_str
