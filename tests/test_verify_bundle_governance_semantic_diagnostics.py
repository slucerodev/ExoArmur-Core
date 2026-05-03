"""
Tests for governance artifact semantic verification diagnostics in verify-bundle.

Tests that semantic verification through providers is diagnostic-only and does not
alter Core replay verdicts.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from exoarmur.execution_boundary_v2.models.execution_proof_bundle import (
    ExecutionProofBundle,
)
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from exoarmur.proof.external_verifier import verify_bundle_data
from exoarmur.governance_artifacts.semantic_verification import (
    verify_governance_artifacts_semantically,
    format_semantic_verification_for_output,
)


def make_exported_bundle(governance_evidence: dict | None = None) -> dict:
    """Create a minimal ExecutionProofBundle for testing."""
    intent = {
        "intent_id": "semantic-diagnostics-test",
        "actor_id": "test-actor",
        "actor_type": "test",
        "action_type": "delete",
        "target": "/tmp/semantic-diagnostics-test.txt",
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
            "rationale": "semantic diagnostics fixture denial",
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
                "artifact_hash": "a" * 64,
                "artifact_path": "governance_artifacts/policy_snapshot/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": False,
            },
            {
                "artifact_type": "tool_invocation_proof",
                "schema_version": "tool_invocation_proof.v1",
                "artifact_hash": "b" * 64,
                "artifact_path": "governance_artifacts/tool_invocation_proof/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": True,
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
        "tool_invocation_proof": {
            "b" * 64: {
                "schema_version": "tool_invocation_proof.v1",
                "tool_name": "read_file",
                "invocation_id": "test-inv",
                "canonical_args_hash": "c" * 64,
                "args": {"path": "/etc/config.json"},
                "intent_hash": "d" * 64,
                "result_hash": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    }


def test_no_manifest_semantic_attempted_false():
    """Bundle without manifest reports semantic attempted=false."""
    bundle = make_exported_bundle()
    result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance diagnostics should report NOT_PRESENT
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["present"] is False
    assert gov_artifacts["code"] == "NOT_PRESENT"

    # Semantic verification should not be present
    assert "semantic_verification" not in gov_artifacts


def test_valid_manifest_plus_embedded_artifact_plus_mock_provider():
    """Valid manifest + embedded artifact + mock provider available → semantic_valid=true."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=True, code="VALID", message="Artifact verified successfully"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True

    # Governance diagnostics should include semantic verification
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["present"] is True
    assert gov_artifacts["valid_manifest"] is True

    # Semantic verification should be attempted
    assert "semantic_verification" in gov_artifacts
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["verdict_effect"] == "diagnostic_only"
    assert semantic["total"] == 2  # Two artifacts in manifest


def test_provider_unavailable_reports_providerr_unavailable():
    """Provider unavailable reports PROVIDER_UNAVAILABLE, no crash."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No providers available
    with patch("importlib.metadata.entry_points", return_value=[]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Semantic verification should report unavailable
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert "semantic_verification" in gov_artifacts
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["unavailable"] == 2  # Both artifacts unavailable


def test_manifest_hash_mismatch_reports_artifact_hash_mismatch():
    """Manifest artifact hash mismatch reports ARTIFACT_HASH_MISMATCH."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider that returns different hash
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "z" * 64  # Different hash
    mock_provider.verify_artifact.return_value = Mock(
        valid=True, code="VALID", message="Artifact verified successfully"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Semantic verification should report hash mismatch
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True

    # Check for hash mismatch in results
    results = semantic["results"]
    hash_mismatch_found = any(
        r["code"] == "ARTIFACT_HASH_MISMATCH" for r in results
    )
    assert hash_mismatch_found


def test_provider_verify_artifact_returns_invalid():
    """Provider verify_artifact returns invalid → SEMANTIC_INVALID."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider that returns invalid
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=False, code="INVALID_FIELD", message="Field validation failed"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only)
    assert result.verify_verdict == "PASS"

    # Semantic verification should report invalid
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["invalid"] >= 1

    # Check for semantic invalid in results
    results = semantic["results"]
    semantic_invalid_found = any(
        r["code"] == "SEMANTIC_INVALID" for r in results
    )
    assert semantic_invalid_found


def test_provider_raises_exception_reports_provider_error():
    """Provider raises exception → PROVIDER_ERROR."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
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
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Semantic verification should report provider error
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True

    # Check for provider error in results
    results = semantic["results"]
    provider_error_found = any(r["code"] == "PROVIDER_ERROR" for r in results)
    assert provider_error_found


def test_artifact_path_only_no_embedded_content():
    """artifact_path only, no embedded content → ARTIFACT_CONTENT_UNAVAILABLE."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        # No embedded content
        "governance_artifacts": {},
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Semantic verification should report content unavailable
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["unavailable"] == 2  # Both artifacts have no content

    # Check for content unavailable in results
    results = semantic["results"]
    content_unavailable_found = any(
        r["code"] == "ARTIFACT_CONTENT_UNAVAILABLE" for r in results
    )
    assert content_unavailable_found


def test_invalid_manifest_semantic_attempted_false():
    """Invalid manifest → semantic attempted=false, INVALID_MANIFEST."""
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
    governance_evidence = {
        "governance_artifacts_manifest": invalid_manifest,
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Governance diagnostics should report invalid manifest
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    assert gov_artifacts["valid_manifest"] is False
    assert gov_artifacts["code"] == "INVALID_MANIFEST"

    # Semantic verification should not be attempted
    assert "semantic_verification" not in gov_artifacts


def test_overall_core_verdict_unchanged_when_semantic_invalid():
    """Overall Core verdict unchanged when semantic invalid."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider that returns invalid
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=False, code="INVALID_FIELD", message="Field validation failed"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS (diagnostic-only)
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True


def test_overall_core_verdict_unchanged_when_provider_unavailable():
    """Overall Core verdict unchanged when provider unavailable."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No providers available
    with patch("importlib.metadata.entry_points", return_value=[]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"
    assert result.hash_match is True


def test_input_bundle_not_mutated():
    """Input bundle is not mutated during semantic verification."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)
    original_bundle_json = json.dumps(bundle, sort_keys=True)

    # Mock provider
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=True, code="VALID", message="Artifact verified successfully"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Bundle should not be mutated
    assert json.dumps(bundle, sort_keys=True) == original_bundle_json
    assert result.verify_verdict == "PASS"


def test_results_deterministic_across_repeated_runs():
    """Results deterministic across repeated runs."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=True, code="VALID", message="Artifact verified successfully"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result1 = verify_bundle_data(bundle)
        result2 = verify_bundle_data(bundle)

    # Results should be deterministic
    semantic1 = result1.governance_artifacts["governance_artifacts"][
        "semantic_verification"
    ]
    semantic2 = result2.governance_artifacts["governance_artifacts"][
        "semantic_verification"
    ]

    assert semantic1 == semantic2


def test_unknown_artifact_type_handled_deterministically():
    """Unknown artifact type handled deterministically."""
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
    governance_evidence = {
        "governance_artifacts_manifest": manifest,
        "governance_artifacts": {
            "unknown_custom_type": {
                "a" * 64: {"schema_version": "v1", "data": "test"}
            }
        },
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # No provider for unknown type
    with patch("importlib.metadata.entry_points", return_value=[]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Should report provider unavailable
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["unavailable"] == 1


def test_provider_missing_required_method_handled_deterministically():
    """Provider with missing required method handled deterministically."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider missing required methods
    mock_provider = Mock(spec=[])  # Empty spec, no methods
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)

    # Core verdict should still PASS
    assert result.verify_verdict == "PASS"

    # Should report provider error
    assert result.governance_artifacts is not None
    gov_artifacts = result.governance_artifacts["governance_artifacts"]
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True

    # Check for provider error in results
    results = semantic["results"]
    provider_error_found = any(r["code"] == "PROVIDER_ERROR" for r in results)
    assert provider_error_found


def test_semantic_diagnostics_in_json_output():
    """Semantic diagnostics appear in JSON output."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Mock provider
    mock_provider = Mock()
    mock_provider.artifact_type = "policy_snapshot"
    mock_provider.schema_versions = ("policy_snapshot.v1",)
    mock_provider.provider_version = "0.1.0"
    mock_provider.canonical_hash.return_value = "a" * 64
    mock_provider.verify_artifact.return_value = Mock(
        valid=True, code="VALID", message="Artifact verified successfully"
    )

    mock_ep = Mock()
    mock_ep.name = "policy_snapshot"
    mock_ep.load.return_value = mock_provider

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        result = verify_bundle_data(bundle)
    result_dict = result.to_dict()

    # Semantic verification should be in dict output
    assert "governance_artifacts" in result_dict
    gov_artifacts = result_dict["governance_artifacts"]["governance_artifacts"]
    assert "semantic_verification" in gov_artifacts
    semantic = gov_artifacts["semantic_verification"]
    assert semantic["attempted"] is True
    assert semantic["verdict_effect"] == "diagnostic_only"


def test_semantic_verification_helper_directly():
    """Test semantic verification helper directly without verify_bundle_data."""
    governance_evidence = {
        "governance_artifacts_manifest": make_valid_governance_manifest(),
        "governance_artifacts": make_embedded_artifacts(),
    }
    bundle = make_exported_bundle(governance_evidence=governance_evidence)

    # Call semantic verification directly
    aggregate = verify_governance_artifacts_semantically(bundle)

    assert aggregate.attempted is True
    assert aggregate.total == 2
    assert aggregate.verified == 0  # No real providers available
    assert aggregate.unavailable == 2

    # Format for output
    formatted = format_semantic_verification_for_output(aggregate)
    assert formatted["attempted"] is True
    assert formatted["verdict_effect"] == "diagnostic_only"
    assert formatted["total"] == 2
