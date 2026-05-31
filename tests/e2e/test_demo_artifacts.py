"""
Tests for demo artifact generation.

Validates that demo artifacts are generated correctly and contain no sensitive data.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "examples" / "demo_artifacts"
GENERATOR_SCRIPT = (
    Path(__file__).parent.parent.parent / "examples" / "generate_demo_artifacts.py"
)


def test_generator_runs():
    """Test that the generator script runs successfully."""
    result = subprocess.run(
        [sys.executable, str(GENERATOR_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )
    assert result.returncode == 0, f"Generator script failed: {result.stderr}"
    assert "All artifacts generated" in result.stdout


def test_all_artifacts_created():
    """Test that all required artifact files are created."""
    required_artifacts = [
        "manifest.json",
        "filesystem_allow_trace.json",
        "filesystem_deny_trace.json",
        "database_allow_trace.json",
        "external_effect_replay_verified.json",
        "external_effect_tamper_detected.json",
    ]

    for artifact in required_artifacts:
        artifact_path = ARTIFACTS_DIR / artifact
        assert artifact_path.exists(), f"Artifact {artifact} not found"
        assert artifact_path.is_file(), f"Artifact {artifact} is not a file"


def test_json_is_valid():
    """Test that all artifacts are valid JSON."""
    for artifact_path in ARTIFACTS_DIR.glob("*.json"):
        with open(artifact_path) as f:
            try:
                data = json.load(f)
                assert isinstance(
                    data, (dict, list)
                ), f"Artifact {artifact_path.name} is not a dict or list"
            except json.JSONDecodeError as e:
                pytest.fail(f"Artifact {artifact_path.name} is not valid JSON: {e}")


def test_no_sensitive_paths():
    """Test that artifacts contain no sensitive paths."""
    forbidden_patterns = [
        "/home/",  # User home directories
        str(Path.home()),  # Actual home directory
    ]

    for artifact_path in ARTIFACTS_DIR.glob("*.json"):
        with open(artifact_path) as f:
            content = f.read()
            for pattern in forbidden_patterns:
                if pattern in content:
                    pytest.fail(
                        f"Artifact {artifact_path.name} contains sensitive path: {pattern}"
                    )


def test_no_secrets():
    """Test that artifacts contain no API keys or secrets."""
    secret_patterns = [
        "api_key",
        "secret",
        "password",
        "token",
        "private_key",
    ]

    for artifact_path in ARTIFACTS_DIR.glob("*.json"):
        with open(artifact_path) as f:
            content = f.read().lower()
            for pattern in secret_patterns:
                # Allow the pattern if it's part of a key name in a demo context
                # but check if it has a value that looks like a real secret
                if pattern in content:
                    # Check if the pattern is followed by a colon and a long alphanumeric string
                    import re

                    if re.search(
                        rf'{pattern}["\']?\s*:\s*["\']?[a-zA-Z0-9]{{20,}}', content
                    ):
                        pytest.fail(
                            f"Artifact {artifact_path.name} may contain a secret: {pattern}"
                        )


def test_external_effect_replay_verified():
    """Test that the verified external effect artifact has correct structure."""
    artifact_path = ARTIFACTS_DIR / "external_effect_replay_verified.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert data["replay_verification_status"] == "verified"
    assert data["irreversible_effect"] == True
    assert data["rollback_strategy"] in ["record_only", "unsupported"]
    assert "request_canonical_hash" in data
    assert "response_canonical_hash" in data
    assert "normalized_request" in data
    assert "normalized_response" in data


def test_external_effect_tamper_detected():
    """Test that the tampered external effect artifact shows mismatch."""
    artifact_path = ARTIFACTS_DIR / "external_effect_tamper_detected.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert data["replay_verification_status"] in ["mismatch", "malformed"]
    assert data["irreversible_effect"] == True
    assert "request_canonical_hash" in data
    assert "response_canonical_hash" in data
    assert "normalized_request" in data
    assert "normalized_response" in data


def test_manifest_structure():
    """Test that manifest.json has correct structure."""
    artifact_path = ARTIFACTS_DIR / "manifest.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert "schema_version" in data
    assert "generated_at" in data
    assert "description" in data
    assert "artifacts" in data
    assert isinstance(data["artifacts"], list)

    # Check that all artifacts listed in manifest exist
    for artifact_info in data["artifacts"]:
        artifact_name = artifact_info["name"]
        artifact_path = ARTIFACTS_DIR / artifact_name
        assert (
            artifact_path.exists()
        ), f"Manifest lists {artifact_name} but file does not exist"


def test_filesystem_allow_trace_structure():
    """Test that filesystem allow trace has required fields."""
    artifact_path = ARTIFACTS_DIR / "filesystem_allow_trace.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert "intent_id" in data
    assert "trace_id" in data
    assert "events" in data
    assert "final_verdict" in data
    assert "executor_result" in data


def test_filesystem_deny_trace_structure():
    """Test that filesystem deny trace has required fields."""
    artifact_path = ARTIFACTS_DIR / "filesystem_deny_trace.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert "intent_id" in data
    assert "trace_id" in data
    assert "events" in data
    assert "final_verdict" in data
    assert "dispatch_status" in data


def test_database_allow_trace_structure():
    """Test that database allow trace has required fields."""
    artifact_path = ARTIFACTS_DIR / "database_allow_trace.json"
    with open(artifact_path) as f:
        data = json.load(f)

    assert "intent_id" in data
    assert "trace_id" in data
    assert "events" in data
    assert "final_verdict" in data
    assert "executor_result" in data
