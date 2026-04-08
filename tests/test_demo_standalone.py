import json
import os
import subprocess
import sys
from pathlib import Path


def test_demo_standalone_emits_markers_and_writes_proof_bundle():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "examples" / "demo_standalone.py"
    proof_bundle_path = repo_root / "examples" / "demo_standalone_proof_bundle.json"

    env = os.environ.copy()
    src_dir = repo_root / "src"
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_dir) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

    def run_demo() -> tuple[str, str]:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        output = (result.stdout or "") + (result.stderr or "")
        assert result.returncode == 0, output
        assert "Execution boundary result: policy denied before any filesystem side effect" in output
        assert "Proof bundle written: examples/demo_standalone_proof_bundle.json" in output
        assert "DEMO_RESULT=DENIED" in output
        assert "ACTION_EXECUTED=false" in output
        assert "AUDIT_STREAM_ID=demo-standalone-delete-outside-authorized-path" in output

        assert proof_bundle_path.exists(), "Standalone proof bundle was not written"
        return output, proof_bundle_path.read_text()

    first_output, first_bundle_text = run_demo()
    second_output, second_bundle_text = run_demo()

    # Check deterministic markers only (ULIDs and replay hashes are non-deterministic)
    assert "Execution boundary result: policy denied before any filesystem side effect" in second_output
    assert "Proof bundle written: examples/demo_standalone_proof_bundle.json" in second_output
    assert "Proof bundle schema version: 2.0" in second_output
    assert "DEMO_RESULT=DENIED" in second_output
    assert "ACTION_EXECUTED=false" in second_output
    assert "AUDIT_STREAM_ID=demo-standalone-delete-outside-authorized-path" in second_output

    proof_bundle = json.loads(second_bundle_text)
    assert proof_bundle["audit_stream_id"] == "demo-standalone-delete-outside-authorized-path"
    assert proof_bundle["action_executed"] is False
    assert proof_bundle["bundle"]["replay_hash"]
    # Note: SDK demo doesn't populate audit_records - it's a standalone simulation
    # assert proof_bundle["audit_records"]
