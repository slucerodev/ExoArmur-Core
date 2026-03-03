from pathlib import Path

import pytest

DOC_PATH = Path(__file__).parent.parent / "docs" / "PHASE_2B_EXIT_CHECKLIST.md"
REQUIRED_HEADINGS = [
    "A) Preconditions",
    "B) Required Commands",
    "C) Go/No-Go Criteria",
    "D) Authorization Rule",
    "E) Rollback Instructions",
]


def test_exit_checklist_exists_and_has_headings():
    assert DOC_PATH.exists(), "Exit checklist missing"
    text = DOC_PATH.read_text(encoding="utf-8")
    for heading in REQUIRED_HEADINGS:
        assert heading in text, f"Missing heading in checklist: {heading}"
