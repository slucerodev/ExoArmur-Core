import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from click.testing import CliRunner

from exoarmur import cli


def test_demo_uses_sys_executable_and_prepends_src(monkeypatch, tmp_path):
    repo_root = Path(cli.__file__).resolve().parents[2]
    src_dir = repo_root / "src"
    script_path = repo_root / "scripts" / "demo_v2_restrained_autonomy.py"

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
            stdout="DEMO_RESULT=DENIED\nACTION_EXECUTED=false\nAUDIT_STREAM_ID=demo123\nREPLAY_VERIFIED=true",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["demo", "--scenario", "v2_restrained_autonomy", "--operator-decision", "deny"],
        env={"PYTHONPATH": "priorpath"},
    )

    assert result.exit_code == 0, result.output
    # Single subprocess invocation for demo path
    assert len(calls) == 1
    call = calls[0]
    assert call["cwd"] == repo_root
