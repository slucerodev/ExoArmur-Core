import copy
import json
from datetime import datetime, timezone

from click.testing import CliRunner

from exoarmur import cli
from exoarmur.execution_boundary_v2.models.execution_proof_bundle import (
    ExecutionProofBundle,
)
from exoarmur.execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from exoarmur.proof.external_verifier import verify_bundle_data


def make_exported_bundle() -> dict:
    intent = {
        "intent_id": "external-verifier-test",
        "actor_id": "test-actor",
        "actor_type": "test",
        "action_type": "delete",
        "target": "/tmp/external-verifier-test.txt",
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
            "rationale": "external verifier fixture denial",
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
    )
    return {"bundle": bundle.model_dump(mode="json")}


def test_external_verifier_passes_valid_exported_bundle():
    result = verify_bundle_data(make_exported_bundle())

    assert result.verify_verdict == "PASS"
    assert result.hash_algorithm == "sha256"
    assert result.hash_match is True
    assert result.expected_hash == result.computed_hash
    assert result.checksum_match is True


def test_external_verifier_fails_semantic_tamper():
    exported = make_exported_bundle()
    tampered = copy.deepcopy(exported)
    tampered["bundle"]["intent"]["target"] = "/tmp/tampered-target.txt"

    result = verify_bundle_data(tampered)

    assert result.verify_verdict == "FAIL"
    assert result.hash_match is False
    assert result.expected_hash != result.computed_hash
    assert "REPLAY_HASH_MISMATCH" in result.error


def test_verify_bundle_cli_outputs_machine_readable_key_values(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(make_exported_bundle()), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli.main, ["verify-bundle", "--bundle", str(bundle_path)])

    assert result.exit_code == 0, result.output
    assert "VERIFY_VERDICT=PASS" in result.output
    assert "HASH_ALGORITHM=sha256" in result.output
    assert "HASH_MATCH=true" in result.output


def test_verify_bundle_cli_fails_invalid_json(tmp_path):
    bundle_path = tmp_path / "invalid.json"
    bundle_path.write_text("{invalid", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli.main, ["verify-bundle", "--bundle", str(bundle_path)])

    assert result.exit_code == 1
    assert "VERIFY_VERDICT=FAIL" in result.output
    assert "INVALID_JSON" in result.output
