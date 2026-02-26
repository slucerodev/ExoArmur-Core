import importlib
import json
import re
import sys
from pathlib import Path

import pytest

from exoarmur.core.phase_gate import PhaseGate

DOCS_DIR = Path(__file__).parent.parent / "docs"
PLUGIN_DOC = DOCS_DIR / "contracts" / "v2" / "plugin_capability_interface.md"


def _load_json_blocks(path: Path):
    text = path.read_text(encoding="utf-8")
    return re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)


def test_core_imports_without_modules(monkeypatch):
    monkeypatch.setenv("EXOARMUR_PHASE", "1")
    PhaseGate._current_phase = None

    # Ensure no plugin modules are preloaded
    sys.modules.pop("exoarmur.plugins", None)

    module = importlib.import_module("exoarmur")
    assert module is not None
    assert "exoarmur.plugins" not in sys.modules, "Core must not import module/plugin paths"


@pytest.mark.parametrize("doc_name", ["CAPABILITY_BOUNDARY.md", "contracts/v2/plugin_capability_interface.md"])
def test_docs_exist(doc_name):
    path = DOCS_DIR / doc_name if "/" not in doc_name else DOCS_DIR / Path(doc_name)
    assert path.exists(), f"Missing doc: {path}"
    assert path.stat().st_size > 0, f"Doc empty: {path}"


def test_plugin_interface_examples_parse():
    blocks = _load_json_blocks(PLUGIN_DOC)
    assert len(blocks) >= 3, "Expected registration, activation, and denial examples"

    registration = json.loads(blocks[0])
    activation = json.loads(blocks[1])
    denial = json.loads(blocks[2])

    assert registration["schema"].startswith("exoarmur.v2.capability.registration")
    assert {"capability_id", "provider", "capability_class", "endpoints"}.issubset(registration)

    assert activation["schema"].startswith("exoarmur.v2.capability.activation")
    assert {"capability_id", "requested_by", "activation_context", "idempotency_key"}.issubset(activation)

    assert denial["schema"].startswith("exoarmur.v2.capability.denial")
    assert {"capability_id", "denied_by", "reason"}.issubset(denial)


def test_capability_activation_denied_phase_one(monkeypatch):
    monkeypatch.setenv("EXOARMUR_PHASE", "1")
    PhaseGate._current_phase = None
    with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
        PhaseGate.check_phase_2_eligibility("CapabilityActivation")
