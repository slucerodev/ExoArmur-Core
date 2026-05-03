"""
Tests for governance artifact enforcement in verify-bundle.

Tests that enforcement of required artifacts is feature-flagged and fail-closed when enabled.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from exoarmur.execution_boundary_v2.models.execution_proof_bundle import (
    ExecutionProofBundle,
)
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from exoarmur.proof.external_verifier import verify_bundle_data


def make_exported_bundle(governance_evidence: dict | None = None) -> dict:
    """Create a minimal ExecutionProofBundle for testing."""
    intent = {
        "intent_id": "enforcement-test",
        "actor_id": "test-actor",
        "actor_type": "test",
        "action_type": "delete",
        "target": "/tmp/enforcement-test.txt",
        "parameters": {"operation": "delete"},
        "timestamp": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
    }
    execution_trace = {
        "events": [
            {
                "stage": "policy_evaluated",
                "ok": True,
                "code": "DENIED",
                "details": {"final_verdict": "deny"},
            }
        ],
        "final_verdict": "deny",
    }
    bundle = ExecutionProofBundle.create(
        intent=intent,
        policy_decision={
            "verdict": "deny",
            "rationale": "enforcement fixture denial",
            "approval_required": False,
        },
        safety_verdict={"verdict": "deny", "rationale": "test safety denial"},
        final_verdict=FinalVerdict.DENY,
        approval_records=[],
        execution_trace=execution_trace,
        executor_result={
            "success": False,
            "output": {},
            "error": "DENIED",
            "evidence": {"final_verdict": "deny"},
        },
        governance_evidence=governance_evidence or {},
    )
    return {"bundle": bundle.model_dump(mode="json")}


def make_valid_governance_manifest(required_for_verdict: bool = False) -> dict:
    """Create a valid governance manifest for testing."""
    return {
        "entries": [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "a" * 64,
                "artifact_path": "governance_artifacts/policy_snapshot/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": required_for_verdict,
            },
        ]
    }


def make_embedded_artifacts() -> dict:
    """Create embedded artifact content for testing."""
    return {
        "policy_snapshot": {
            "a" * 64: {
                "schema_version": "policy_snapshot.v1",
                "policy_id": "test-policy",
                "policy_version": "1.0.0",
                "policy_body": {"allow": ["read"], "deny": ["delete"]},
                "policy_body_hash": "a" * 64,
                "created_by": "system",
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    }


def make_mock_provider(valid: bool = True) -> Mock:
    """Create a mock provider for testing."""
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=valid, code="VALID" if valid else "INVALID", 
        message="Artifact verified successfully" if valid else "Artifact verification failed"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider
    return mock_ep


def test_enforcement_disabled_by_default():
    """Enforcement disabled by default."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Core verdict should PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report ENFORCEMENT_DISABLED
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is False
    assert result.governance_enforcement["code"] == "ENFORCEMENT_DISABLED"
    assert result.governance_enforcement["verdict_effect"] == "none"


def test_existing_bundle_without_manifest_keeps_verdict():
    """Existing bundle without manifest keeps existing verdict when enforcement disabled."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Core verdict should PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should not affect verdict
    assert result.governance_enforcement["verdict_effect"] == "none"


def test_invalid_required_artifact_keeps_verdict_when_disabled():
    """Bundle with invalid required governance artifact still keeps existing verdict when enforcement disabled."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No providers available - would fail if enforcement enabled
    with patch("importlib.metadata.entry_points", return_value=[]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS (enforcement disabled)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report disabled
    assert result.governance_enforcement["enabled"] is False


def test_governance_enforcement_reports_disabled():
    """governance_enforcement reports ENFORCEMENT_DISABLED when flag is off."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is False
    assert result.governance_enforcement["code"] == "ENFORCEMENT_DISABLED"
    assert result.governance_enforcement["message"] == "Governance artifact enforcement is disabled"


def test_enforcement_enabled_required_valid_passes():
    """Enforcement enabled + required valid artifact + provider available → enforcement valid."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report valid
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is True
    assert result.governance_enforcement["code"] == "ENFORCEMENT_VALID"
    assert result.governance_enforcement["verdict_effect"] == "none"
    assert result.governance_enforcement["required_total"] == 1
    assert result.governance_enforcement["required_valid"] == 1
    assert result.governance_enforcement["required_invalid"] == 0


def test_enforcement_enabled_provider_unavailable_fails_closed():
    """Enforcement enabled + required artifact provider unavailable → fail closed."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No providers available
    with patch("importlib.metadata.entry_points", return_value=[]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report failure
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["required_invalid"] == 1


def test_enforcement_enabled_content_unavailable_fails_closed():
    """Enforcement enabled + required artifact content unavailable → fail closed."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        # No embedded artifacts
        "governance_artifacts": {},
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report content unavailable
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["required_invalid"] == 1


def test_enforcement_enabled_hash_mismatch_fails_closed():
    """Enforcement enabled + required artifact hash mismatch → fail closed."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider that returns different hash
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "z" * 64  # Different hash

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report hash mismatch
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["required_invalid"] == 1


def test_enforcement_enabled_semantic_invalid_fails_closed():
    """Enforcement enabled + required artifact semantic invalid → fail closed."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=False)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report semantic invalid
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["required_invalid"] == 1


def test_enforcement_enabled_provider_error_fails_closed():
    """Enforcement enabled + provider error → fail closed."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider that raises exception
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.side_effect = Exception("Provider error")

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report provider error
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["required_invalid"] == 1


def test_enforcement_enabled_optional_invalid_does_not_fail():
    """Enforcement enabled + optional artifact invalid → does not fail enforcement."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=False),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No providers available - optional artifact
    with patch("importlib.metadata.entry_points", return_value=[]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should PASS (optional artifact doesn't fail enforcement)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report valid (no required artifacts)
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is True
    assert result.governance_enforcement["verdict_effect"] == "none"
    assert result.governance_enforcement["required_total"] == 0


def test_enforcement_enabled_no_required_artifacts_valid():
    """Enforcement enabled + no required artifacts → valid."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=False),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result = verify_bundle_data(bundle)

    # Core verdict should PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report valid
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is True
    assert result.governance_enforcement["verdict_effect"] == "none"
    assert result.governance_enforcement["required_total"] == 0


def test_enforcement_enabled_manifest_absent_does_not_fail():
    """Enforcement enabled + manifest absent → does not fail in this task."""
    bundle = make_exported_bundle()  # No manifest

    with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
        mock_flags_instance = Mock()
        mock_flags_instance.is_enabled.return_value = True
        mock_flags.return_value = mock_flags_instance

        result = verify_bundle_data(bundle)

    # Core verdict should PASS (manifest absent is not a failure)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance enforcement should report valid
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is True
    assert result.governance_enforcement["verdict_effect"] == "none"
    assert "manifest absent" in result.governance_enforcement["message"]


def test_enforcement_enabled_manifest_invalid_fails_closed():
    """Enforcement enabled + manifest invalid → deterministic enforcement failure if manifest present."""
    governance_evidence = {
        "governance_artifacts_manifest": {
            "entries": [
                {
                    # Invalid entry - missing required fields
                    "artifact_type": "policy_snapshot",
                }
            ]
        },
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
        mock_flags_instance = Mock()
        mock_flags_instance.is_enabled.return_value = True
        mock_flags.return_value = mock_flags_instance

        result = verify_bundle_data(bundle)

    # Core verdict should FAIL due to enforcement
    assert result.verify_verdict == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in result.error

    # Governance enforcement should report manifest invalid
    assert result.governance_enforcement is not None
    assert result.governance_enforcement["enabled"] is True
    assert result.governance_enforcement["valid"] is False
    assert result.governance_enforcement["verdict_effect"] == "fail_closed"
    assert result.governance_enforcement["code"] == "REQUIRED_ARTIFACT_MANIFEST_INVALID"


def test_replay_hash_unchanged_under_enforcement():
    """Replay hash unchanged under enforcement."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        # Get hash without enforcement
        result_disabled = verify_bundle_data(bundle)
        hash_disabled = result_disabled.computed_hash

        # Get hash with enforcement enabled
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result_enabled = verify_bundle_data(bundle)
            hash_enabled = result_enabled.computed_hash

    # Hash should be unchanged
    assert hash_disabled == hash_enabled


def test_input_bundle_not_mutated():
    """Input bundle not mutated."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)
    original_bundle_json = json.dumps(bundle)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            verify_bundle_data(bundle)

    # Bundle should not be mutated
    assert json.dumps(bundle) == original_bundle_json


def test_results_deterministic_across_repeated_runs():
    """Results deterministic across repeated runs."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(required_for_verdict=True),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    mock_provider = make_mock_provider(valid=True)

    with patch("importlib.metadata.entry_points", return_value=[mock_provider]):
        with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
            mock_flags_instance = Mock()
            mock_flags_instance.is_enabled.return_value = True
            mock_flags.return_value = mock_flags_instance

            result1 = verify_bundle_data(bundle)
            result2 = verify_bundle_data(bundle)

    # Results should be identical
    assert result1.verify_verdict == result2.verify_verdict
    assert result1.computed_hash == result2.computed_hash
    assert result1.governance_enforcement == result2.governance_enforcement


def test_json_output_includes_governance_enforcement():
    """JSON output includes governance_enforcement."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Convert to dict
    result_dict = result.to_dict()

    # Should include governance_enforcement
    assert "governance_enforcement" in result_dict
    assert result_dict["governance_enforcement"]["enabled"] is False
    assert result_dict["governance_enforcement"]["code"] == "ENFORCEMENT_DISABLED"


def test_cli_backward_compatible():
    """CLI verify-bundle behavior remains backward-compatible except for additive structured fields."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Core fields should be present
    assert result.verify_verdict in ["PASS", "FAIL"]
    assert result.bundle_format == "EXECUTION_PROOF_BUNDLE"
    assert result.hash_algorithm == "sha256"
    assert result.expected_hash is not None
    assert result.computed_hash is not None
    assert result.hash_match is not None

    # New field is additive
    assert result.governance_enforcement is not None
