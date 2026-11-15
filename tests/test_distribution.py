"""Regression tests for distribution defects found in post-merge review.

1. ``kernel/ids.py`` must use an API exposed by the declared
   ``python-ulid`` dependency across the versions allowed by packaging
   metadata, and the pin files must agree with ``pyproject.toml``.
2. Built distributions must contain the runtime assets the pilot loads
   from the package directory: ``api/gui/index.html`` and
   ``api/migrations/*.sql``.
"""

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from exoarmur.kernel.ids import IDFactory

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PKG = Path(__import__("exoarmur.api", fromlist=["x"]).__file__).parent


def _pyproject_ulid_spec() -> SpecifierSet:
    text = (REPO_ROOT / "pyproject.toml").read_text()
    for line in text.splitlines():
        line = line.strip().strip(",")
        if line.startswith('"python-ulid'):
            req = Requirement(line.strip('"'))
            return req.specifier
    pytest.fail("python-ulid dependency not found in pyproject.toml")


def _locked_ulid_version(filename: str) -> Version:
    for line in (REPO_ROOT / filename).read_text().splitlines():
        line = line.strip()
        if line.lower().startswith("python-ulid=="):
            return Version(line.split("==", 1)[1])
    pytest.fail(f"python-ulid pin not found in {filename}")


def test_pyproject_ulid_constraint_excludes_removed_api():
    """python-ulid 4.x removed module-level ``ulid.from_bytes``; the
    declared constraint must resolve to a version providing
    ``ULID.from_bytes`` (4.x), and pins must satisfy it."""
    spec = _pyproject_ulid_spec()
    for pin_file in ("requirements.txt", "requirements.lock"):
        version = _locked_ulid_version(pin_file)
        assert version in spec, (
            f"{pin_file} pins python-ulid=={version} which does not "
            f"satisfy pyproject constraint {spec}"
        )
        assert version >= Version("4.0.0"), (
            "python-ulid <4 lacks ULID.from_bytes used by kernel/ids.py"
        )


def test_id_factory_uses_installed_ulid_api():
    """make_id must produce a deterministic 26-char ULID through the
    installed python-ulid's supported API."""
    import ulid

    factory = IDFactory(seed="test-seed")
    first = factory.make_id("probe", {"a": 1})
    second = IDFactory(seed="test-seed").make_id("probe", {"a": 1})
    assert first == second
    assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", first)
    # Round-trip through the installed library's parser.
    assert str(ulid.ULID.from_str(first)) == first


def test_gui_asset_present_in_package():
    gui = API_PKG / "gui" / "index.html"
    assert gui.is_file(), f"operator GUI missing from package: {gui}"
    assert "<html" in gui.read_text()[:4096].lower()


def test_migration_assets_present_in_package():
    migrations = sorted((API_PKG / "migrations").glob("*.sql"))
    names = {p.name for p in migrations}
    assert {"001_init.sql", "002_pilot.sql", "003_session_key_binding.sql"} <= names, (
        f"expected pilot migrations missing from package, found: {names}"
    )
