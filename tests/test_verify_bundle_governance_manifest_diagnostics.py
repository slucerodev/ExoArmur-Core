"""
Tests for governance artifact manifest diagnostics in verify-bundle.

Tests that governance manifest inspection is diagnostic-only and does not
alter Core replay verdicts.
"""

import copy
import json
from datetime import datetime, timezone

from exoarmur.execution_boundary_v2.models.execution_proof_bundle import (
    ExecutionProofBundle,
)
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from exoarmur.proof.external_verifier import verify_bundle_data
from exoarmur.governance_artifacts.inspection import (
    inspect_governance_artifacts_from_bundle,
    format_inspection_result_for_output,
)


def make_exported_bundle(governance_evidence: dict | None = None) -> dict:
    """Create a minimal ExecutionProofBundle for testing."""
    intent = {
        "intent_id": "governance-diagnostics-test",
        "actor_id": "test-actor",
        "actor_type": "test",
        "action_type": "delete",
        "target": "/tmp/governance-diagnostics-test.txt",
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
            "rationale": "governance diagnostics fixture denial",
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


def make_valid_governance_manifest() -> dict:
    """Create a valid governance manifest for testing."""
    return {
        "entries": [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "a" * 64,  # Valid SHA-256 hex
                "artifact_path": "governance_artifacts/policy_snapshot/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": False,
            },
            {
                "artifact_type": "tool_invocation_proof",
                "schema_version": "tool_invocation_proof.v1",
                "artifact_hash": "b" * 64,  # Valid SHA-256 hex
                "artifact_path": "governance_artifacts/tool_invocation_proof/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": True,
            },
        ]
    }


def test_verify_bundle_without_governance_manifest_reports_not_present():
    """verify-bundle on bundle without governance manifest reports NOT_PRESENT."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance diagnostics should report NOT_PRESENT
    assert result.governance_artifacts is not None
    assert result.governance_artifacts["governance_artifacts"]["present"] is False
    assert result.governance_artifacts["governance_artifacts"]["code"] == "NOT_PRESENT"
    assert (
        result.governance_artifacts["governance_artifacts"]["verdict_effect"] == "none"
    )


def test_verify_bundle_with_valid_governance_manifest_reports_diagnostics():
    """ExecutionProofBundle with valid governance manifest reports present=true."""
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": make_valid_governance_manifest()
        }
    )

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance diagnostics should report valid manifest
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["present"] is True
    assert gov_artifacts["valid_manifest"] is True
    assert gov_artifacts["code"] == "VALID"
    assert gov_artifacts["artifact_count"] == 2
    assert gov_artifacts["required_count"] == 1
    assert gov_artifacts["optional_count"] == 1
    assert set(gov_artifacts["artifact_types"]) == {
        "policy_snapshot",
        "tool_invocation_proof",
    }
    assert gov_artifacts["verdict_effect"] == "diagnostic_only"
    assert gov_artifacts["manifest_hash"] is not None


def test_verify_bundle_with_invalid_governance_manifest_reports_invalid():
    """Invalid governance manifest reports INVALID_MANIFEST but does not change verdict."""
    # Add invalid manifest (blank artifact_type)
    invalid_manifest = {
        "entries": [
            {
                "artifact_type": "",  # Invalid: blank
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "a" * 64,
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
            }
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": invalid_manifest
        }
    )

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance diagnostics should report invalid manifest
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["present"] is True
    assert gov_artifacts["valid_manifest"] is False
    assert gov_artifacts["code"] == "INVALID_MANIFEST"
    assert "validation failed" in gov_artifacts["message"].lower()


def test_verify_bundle_with_invalid_hash_format_reports_invalid():
    """Invalid SHA-256 hash format reports INVALID_MANIFEST."""
    # Add manifest with invalid hash (wrong length)
    invalid_manifest = {
        "entries": [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "abc123",  # Invalid: not 64 chars
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
            }
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": invalid_manifest
        }
    )

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Governance diagnostics should report invalid manifest
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["valid_manifest"] is False
    assert gov_artifacts["code"] == "INVALID_MANIFEST"


def test_missing_optional_provider_does_not_crash():
    """Missing optional providers do not crash verify-bundle."""
    # Add manifest with artifact type that likely has no provider
    manifest = {
        "entries": [
            {
                "artifact_type": "unknown_artifact_type",
                "schema_version": "v1",
                "artifact_hash": "a" * 64,
                "producer_module": "test-module",
                "producer_version": "1.0.0",
                "required_for_verdict": False,  # Optional
            }
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": manifest
        }
    )

    # Should not crash
    result = verify_bundle_data(bundle)
    assert result.verify_verdict == "PASS"
    assert result.governance_artifacts is not None


def test_required_artifact_with_missing_provider_is_diagnostic_only():
    """Required artifact with missing provider is diagnostic_only for this pass."""
    # Add manifest with required artifact type that has no provider
    manifest = {
        "entries": [
            {
                "artifact_type": "unknown_artifact_type",
                "schema_version": "v1",
                "artifact_hash": "a" * 64,
                "producer_module": "test-module",
                "producer_version": "1.0.0",
                "required_for_verdict": True,  # Required but provider missing
            }
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": manifest
        }
    )

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only in this pass)
    assert result.verify_verdict == "PASS"
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["required_count"] == 1
    assert gov_artifacts["verdict_effect"] == "diagnostic_only"


def test_provider_summary_is_deterministic():
    """Provider summary is deterministic (sorted artifact types)."""
    # Add manifest with multiple artifact types
    manifest = {
        "entries": [
            {
                "artifact_type": "zzz_type",  # Last alphabetically
                "schema_version": "v1",
                "artifact_hash": "a" * 64,
                "producer_module": "test-module",
                "producer_version": "1.0.0",
                "required_for_verdict": False,
            },
            {
                "artifact_type": "aaa_type",  # First alphabetically
                "schema_version": "v1",
                "artifact_hash": "b" * 64,
                "producer_module": "test-module",
                "producer_version": "1.0.0",
                "required_for_verdict": False,
            },
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": manifest
        }
    )

    result = verify_bundle_data(bundle)

    # Artifact types should be sorted deterministically
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    artifact_types = gov_artifacts["artifact_types"]
    assert artifact_types == ["aaa_type", "zzz_type"]  # Sorted


def test_manifest_hash_is_stable_across_repeated_verification():
    """Manifest hash is stable across repeated verification."""
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": make_valid_governance_manifest()
        }
    )

    # Verify multiple times
    result1 = verify_bundle_data(bundle)
    result2 = verify_bundle_data(bundle)
    result3 = verify_bundle_data(bundle)

    # Manifest hash should be stable
    hash1 = result1.governance_artifacts["governance_artifacts"]["manifest_hash"]
    hash2 = result2.governance_artifacts["governance_artifacts"]["manifest_hash"]
    hash3 = result3.governance_artifacts["governance_artifacts"]["manifest_hash"]

    assert hash1 == hash2 == hash3
    assert hash1 is not None
    assert len(hash1) == 64  # SHA-256 hex length


def test_input_bundle_is_not_mutated():
    """Input bundle is not mutated during inspection."""
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": make_valid_governance_manifest()
        }
    )
    original_bundle_json = json.dumps(bundle, sort_keys=True)

    # Verify
    result = verify_bundle_data(bundle)

    # Bundle should not be mutated
    assert json.dumps(bundle, sort_keys=True) == original_bundle_json
    assert result.verify_verdict == "PASS"


def test_unknown_artifact_type_reported_deterministically():
    """Unknown artifact type is reported deterministically."""
    manifest = {
        "entries": [
            {
                "artifact_type": "unknown_custom_type",
                "schema_version": "v1",
                "artifact_hash": "a" * 64,
                "producer_module": "custom-module",
                "producer_version": "1.0.0",
                "required_for_verdict": False,
            }
        ]
    }
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": manifest
        }
    )

    result = verify_bundle_data(bundle)

    # Should report the unknown type deterministically
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert "unknown_custom_type" in gov_artifacts["artifact_types"]
    assert gov_artifacts["artifact_count"] == 1


def test_inspection_helper_directly():
    """Test inspection helper directly without verify_bundle_data."""
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": make_valid_governance_manifest()
        }
    )

    # Call inspection directly
    inspection = inspect_governance_artifacts_from_bundle(bundle)

    assert inspection.present is True
    assert inspection.valid_manifest is True
    assert inspection.code == "VALID"
    assert inspection.artifact_count == 2
    assert inspection.required_count == 1
    assert inspection.optional_count == 1
    assert inspection.manifest_hash is not None

    # Format for output
    formatted = format_inspection_result_for_output(inspection)
    assert "governance_artifacts" in formatted
    assert formatted["governance_artifacts"]["present"] is True
    assert formatted["governance_artifacts"]["valid_manifest"] is True


def test_inspection_without_manifest():
    """Test inspection when no manifest is present."""
    bundle = make_exported_bundle()

    inspection = inspect_governance_artifacts_from_bundle(bundle)

    assert inspection.present is False
    assert inspection.valid_manifest is False
    assert inspection.code == "NOT_PRESENT"
    assert inspection.artifact_count == 0

    formatted = format_inspection_result_for_output(inspection)
    assert formatted["governance_artifacts"]["present"] is False
    assert formatted["governance_artifacts"]["code"] == "NOT_PRESENT"


def test_governance_diagnostics_in_json_output():
    """Governance diagnostics are included in JSON output via to_dict()."""
    bundle = make_exported_bundle(
        governance_evidence={
            "governance_artifacts_manifest": make_valid_governance_manifest()
        }
    )

    result = verify_bundle_data(bundle)
    result_dict = result.to_dict()

    # Governance artifacts should be in dict output
    assert "governance_artifacts" in result_dict
    assert result_dict["governance_artifacts"]["governance_artifacts"]["present"] is True
    assert result_dict["governance_artifacts"]["governance_artifacts"]["valid_manifest"] is True


def test_governance_diagnostics_none_when_not_present():
    """Governance diagnostics are included even when manifest not present."""
    bundle = make_exported_bundle()

    result = verify_bundle_data(bundle)
    result_dict = result.to_dict()

    # Should still have governance_artifacts with NOT_PRESENT
    assert "governance_artifacts" in result_dict
    assert result_dict["governance_artifacts"]["governance_artifacts"]["present"] is False
    assert result_dict["governance_artifacts"]["governance_artifacts"]["code"] == "NOT_PRESENT"
