import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from exoarmur import cli
from exoarmur.execution_boundary_v2.models.execution_proof_bundle import (
    ExecutionProofBundle,
)
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict

pytest.importorskip("exoarmur_governance_modules", reason="GovernanceModules not installed")

GOVERNANCE_MODULES_FIXTURES = Path("/home/oem/CascadeProjects/ExoArmur-GovernanceModules/tests/fixtures")


def test_demo_uses_sys_executable_and_prepends_src(monkeypatch, tmp_path):
    """
    Test CLI demo path resolution and environment setup.
    
    NOTE: This test is skipped when package is installed via pip because
    the path resolution logic differs between development and installed
    environments. The actual functionality works correctly in both cases.
    """
    # Skip test when running from installed package (different path resolution)
    import exoarmur
    package_path = Path(exoarmur.__file__).resolve().parent
    if "site-packages" in str(package_path) or "dist-packages" in str(package_path):
        pytest.skip("CLI path resolution differs in installed package environment")
    
    repo_root = Path(cli.__file__).resolve().parents[2]
    src_dir = repo_root / "src"
    script_path = repo_root / "demos" / "canonical_truth_reconstruction_demo.py"

    calls = []

    def fake_run(cmd, cwd=None, capture_output=False, text=False, env=None):
        calls.append({"cmd": cmd, "cwd": cwd, "env": env})
        assert cmd[0] == sys.executable
        assert cmd[1] == str(script_path)
        assert str(src_dir) in env.get("PYTHONPATH", "")
        # Existing PYTHONPATH should be preserved after the prepended src
        assert env.get("PYTHONPATH", "").split(os.pathsep)[0] == str(src_dir)
        assert "priorpath" in env.get("PYTHONPATH", "")
        # Return success with required markers so CLI passes
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "Execution boundary result: policy denied before any filesystem side effect\n"
                "Proof bundle written: demos/canonical_proof_bundle.json\n"
                "DEMO_RESULT=DENIED\n"
                "ACTION_EXECUTED=false\n"
                "AUDIT_STREAM_ID=canonical-truth-reconstruction-demo\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["demo"],
        env={"PYTHONPATH": "priorpath"},
    )

    assert result.exit_code == 0, result.output
    # Single subprocess invocation for demo path
    assert len(calls) == 1
    call = calls[0]
    assert call["cwd"] == repo_root


def test_verify_all_skips_repo_only_checks_when_installed(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, capture_output=False, text=False, env=None):
        calls.append({"cmd": cmd, "cwd": cwd, "capture_output": capture_output, "text": text})
        assert cmd[0] == sys.executable
        assert cmd[1] == "-c"
        assert "OK" in cmd[2]
        assert cwd is not None  # Runs from temp directory, not package root
        assert capture_output is True
        assert text is True
        return SimpleNamespace(
            returncode=0,
            stdout="OK\n",
            stderr="",
        )

    monkeypatch.setattr(cli, "_discover_repo_root", lambda: None)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["verify-all"])

    assert result.exit_code == 0, result.output
    assert "Running installed-package import sanity check" in result.output
    assert "Skipping boundary gate" in result.output
    assert "Skipping standalone demo proof" in result.output
    assert "repo-only checks skipped" in result.output
    assert len(calls) == 1


def make_test_bundle(governance_evidence=None):
    """Create a minimal ExecutionProofBundle for CLI testing."""
    intent = {
        "intent_id": "cli-test",
        "actor_id": "test-actor",
        "actor_type": "test",
        "action_type": "delete",
        "target": "/tmp/test.txt",
        "parameters": {"operation": "delete"},
        "timestamp": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
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
            "rationale": "CLI test denial",
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


def test_cli_verify_bundle_includes_governance_diagnostics(tmp_path):
    """verify-bundle JSON output includes governance_artifacts diagnostics when manifest is present."""
    manifest = {
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
        ]
    }
    governance_evidence = {
        "governance_artifacts_manifest": manifest,
    }
    bundle = make_test_bundle(governance_evidence=governance_evidence)

    bundle_path = tmp_path / "test_bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    runner = CliRunner()
    result = runner.invoke(cli.main, ["verify-bundle", "--bundle", str(bundle_path), "--json"])

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert "governance_artifacts" in output
    assert output["governance_artifacts"]["governance_artifacts"]["present"] is True
    assert output["governance_artifacts"]["governance_artifacts"]["valid_manifest"] is True


def test_cli_verify_bundle_governance_enforcement_disabled_by_default(tmp_path):
    """governance_enforcement appears and is disabled by default."""
    manifest = {
        "entries": [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "a" * 64,
                "artifact_path": "governance_artifacts/policy_snapshot/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": True,
            },
        ]
    }
    fixture = json.loads((GOVERNANCE_MODULES_FIXTURES / "policy_snapshot_golden.json").read_text())
    
    from exoarmur_governance_modules.providers.policy_snapshot import PolicySnapshotProvider
    provider = PolicySnapshotProvider()
    artifact_hash = provider.canonical_hash(fixture)

    governance_evidence = {
        "governance_artifacts_manifest": manifest,
        "governance_artifacts": {
            "policy_snapshot": {artifact_hash: fixture}
        },
    }
    bundle = make_test_bundle(governance_evidence=governance_evidence)

    bundle_path = tmp_path / "test_bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    runner = CliRunner()
    result = runner.invoke(cli.main, ["verify-bundle", "--bundle", str(bundle_path), "--json"])

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert "governance_enforcement" in output
    assert output["governance_enforcement"]["enabled"] is False
    assert output["governance_enforcement"]["verdict_effect"] == "none"


def test_cli_verify_bundle_enforcement_fails_closed_on_invalid(tmp_path, monkeypatch):
    """with enforcement enabled, required invalid artifact fails closed deterministically."""
    manifest = {
        "entries": [
            {
                "artifact_type": "policy_snapshot",
                "schema_version": "policy_snapshot.v1",
                "artifact_hash": "z" * 64,
                "artifact_path": "governance_artifacts/policy_snapshot/test.json",
                "producer_module": "exoarmur-governance-modules",
                "producer_version": "0.1.0",
                "required_for_verdict": True,
            },
        ]
    }
    fixture = json.loads((GOVERNANCE_MODULES_FIXTURES / "policy_snapshot_golden.json").read_text())
    
    governance_evidence = {
        "governance_artifacts_manifest": manifest,
        "governance_artifacts": {
            "policy_snapshot": {"z" * 64: fixture}
        },
    }
    bundle = make_test_bundle(governance_evidence=governance_evidence)

    bundle_path = tmp_path / "test_bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    def mock_is_enabled(flag_name):
        return flag_name == "governance_artifact_enforcement_enabled"

    with patch("exoarmur.feature_flags.feature_flags.get_feature_flags") as mock_flags:
        mock_flags_instance = Mock()
        mock_flags_instance.is_enabled = mock_is_enabled
        mock_flags.return_value = mock_flags_instance

        runner = CliRunner()
        result = runner.invoke(cli.main, ["verify-bundle", "--bundle", str(bundle_path), "--json"])

    assert result.exit_code == 1, result.output
    output = json.loads(result.output)
    assert output["verify_verdict"] == "FAIL"
    assert "GOVERNANCE_ENFORCEMENT_FAILURE" in output["error"]
    assert output["governance_enforcement"]["enabled"] is True
    assert output["governance_enforcement"]["valid"] is False
    assert output["governance_enforcement"]["verdict_effect"] == "fail_closed"
