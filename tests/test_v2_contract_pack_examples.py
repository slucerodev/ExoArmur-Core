import json
import re
from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).parent.parent / "docs" / "contracts" / "v2"


def _load_first_json_block(doc_path: Path) -> dict:
    text = doc_path.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)
    assert blocks, f"No JSON example found in {doc_path}"
    example = blocks[0]
    return json.loads(example)


def test_federation_handshake_example_structure():
    doc = DOCS_DIR / "federation_identity_handshake.md"
    data = _load_first_json_block(doc)
    required_keys = {
        "schema",
        "federation_id",
        "cell_id",
        "nonce",
        "timestamp",
        "capabilities",
        "signatures",
    }
    assert required_keys.issubset(data.keys())
    assert isinstance(data["capabilities"], list)
    assert isinstance(data["signatures"], list)
    assert data["schema"].startswith("exoarmur.v2.federation_handshake")
    for sig in data["signatures"]:
        assert {"issuer", "algo", "signature"}.issubset(sig.keys())


def test_operator_approval_request_and_decision_examples():
    doc = DOCS_DIR / "operator_approval_envelopes.md"
    blocks = re.findall(r"```json\n(.*?)\n```", doc.read_text(encoding="utf-8"), flags=re.DOTALL)
    assert len(blocks) >= 2, "Expected request and decision examples"

    request = json.loads(blocks[0])
    decision = json.loads(blocks[1])

    req_keys = {
        "schema",
        "approval_id",
        "intent_id",
        "idempotency_key",
        "requested_by",
        "requested_at",
        "justification",
        "metadata",
    }
    dec_keys = {
        "schema",
        "approval_id",
        "decision",
        "decided_by",
        "decided_at",
        "reason",
        "idempotency_key",
        "bindings",
    }
    assert req_keys.issubset(request.keys())
    assert dec_keys.issubset(decision.keys())
    assert decision["decision"] in {"approved", "denied"}
    assert isinstance(decision["bindings"], list)
    assert request["schema"].startswith("exoarmur.v2.operator_approval.request")
    assert decision["schema"].startswith("exoarmur.v2.operator_approval.decision")


def test_durable_storage_boundary_examples():
    doc = DOCS_DIR / "durable_storage_boundary.md"
    blocks = re.findall(r"```json\n(.*?)\n```", doc.read_text(encoding="utf-8"), flags=re.DOTALL)
    assert len(blocks) >= 2, "Expected put request and history response examples"

    put_request = json.loads(blocks[0])
    history_response = json.loads(blocks[1])

    put_keys = {
        "schema",
        "operation",
        "key",
        "value",
        "timestamp",
        "idempotency_key",
    }
    assert put_keys.issubset(put_request.keys())
    assert put_request["operation"] == "put"

    history_keys = {
        "schema",
        "status",
        "key",
        "history",
    }
    assert history_keys.issubset(history_response.keys())
    assert history_response["status"] == "ok"
    assert isinstance(history_response["history"], list)
    for entry in history_response["history"]:
        assert {"version", "timestamp", "value"}.issubset(entry.keys())


def test_audit_emission_envelope_example():
    doc = DOCS_DIR / "audit_emission_envelope.md"
    data = _load_first_json_block(doc)
    required_keys = {
        "schema",
        "event_kind",
        "payload_ref",
        "correlation_id",
        "trace_id",
        "tenant_id",
        "cell_id",
        "idempotency_key",
        "timestamp",
    }
    assert required_keys.issubset(data.keys())
    assert data["schema"].startswith("exoarmur.v2.audit_emission")


def test_no_side_effects_on_import():
    # Contract pack uses docs only; ensure importing this test module does not pull transport or runtime wiring.
    forbidden_modules = ["nats", "nats.aio"]
    for mod in forbidden_modules:
        assert mod not in globals(), f"Forbidden module imported: {mod}"


@pytest.mark.parametrize(
    "doc_name",
    [
        "federation_identity_handshake.md",
        "operator_approval_envelopes.md",
        "durable_storage_boundary.md",
        "audit_emission_envelope.md",
    ],
)
def test_docs_files_exist(doc_name: str):
    doc_path = DOCS_DIR / doc_name
    assert doc_path.exists(), f"Missing contract doc: {doc_path}"
    assert doc_path.stat().st_size > 0, f"Contract doc empty: {doc_path}"
