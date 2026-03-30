from importlib import metadata
import platform

import pytest

from exoarmur.stability.env_parity import EnvironmentParityError, ensure_environment_parity, load_locked_dependencies


def test_load_locked_dependencies_rejects_non_exact_pins(tmp_path):
    lock_file = tmp_path / "requirements.lock"
    lock_file.write_text("pytest>=7.0.0\n", encoding="utf-8")

    with pytest.raises(EnvironmentParityError):
        load_locked_dependencies(lock_file)


def test_ensure_environment_parity_accepts_exact_pins(tmp_path, monkeypatch):
    lock_file = tmp_path / "requirements.lock"
    lock_file.write_text(
        "\n".join(
            [
                f"packaging=={metadata.version('packaging')}",
                f"pytest=={metadata.version('pytest')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONHASHSEED", "0")

    report = ensure_environment_parity(
        lock_file=lock_file,
        expected_python_version=platform.python_version(),
        expected_platform=platform.system(),
        expected_hash_seed="0",
    )

    assert report.mismatches == []
    assert [item.name for item in report.locked_dependencies] == ["packaging", "pytest"]
