import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from click.testing import CliRunner

from exoarmur import cli


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
        ["demo", "--scenario", "canonical"],
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
        assert "Installed package imports successful" in cmd[2]
        assert cwd == Path(cli.__file__).resolve().parent
        assert capture_output is True
        assert text is True
        return SimpleNamespace(
            returncode=0,
            stdout="✅ Installed package imports successful\n",
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
