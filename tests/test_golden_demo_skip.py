import importlib


def test_live_demo_marked_and_skipped_by_default(monkeypatch):
    # Ensure opt-in is not set
    monkeypatch.delenv("EXOARMUR_LIVE_DEMO", raising=False)

    mod = importlib.import_module("tests.test_golden_demo_live")

    # Confirm live marker is present
    mark_names = [getattr(m, "name", None) for m in getattr(mod, "pytestmark", [])]
    assert "live" in mark_names

    # Confirm skipif is present when not opted-in
    skip_marks = [m for m in getattr(mod, "pytestmark", []) if getattr(m, "name", None) == "skipif"]
    assert skip_marks, "Live demo tests must be skipped by default"
    # The condition should evaluate to True when LIVE is False
    assert any(m.args and m.args[0] for m in skip_marks), "Skip condition must be active when not opted in"
