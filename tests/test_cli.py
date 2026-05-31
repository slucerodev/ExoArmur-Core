"""Tests for ExoArmur CLI."""

import subprocess
import sys
from pathlib import Path


def test_cli_module_imports():
    """Test that CLI module can be imported."""
    from exoarmur import cli

    assert cli is not None
    assert hasattr(cli, "main")
    assert hasattr(cli, "cli")


def test_cli_help():
    """Test that exoarmur --help exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "exoarmur.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI --help failed: {result.stderr}"
    assert "ExoArmur Core" in result.stdout
    assert "deterministic governance" in result.stdout


def test_cli_version():
    """Test that exoarmur version exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "exoarmur.cli", "version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI version failed: {result.stderr}"
    assert "version:" in result.stdout.lower()


def test_cli_info():
    """Test that exoarmur info exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "exoarmur.cli", "info"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI info failed: {result.stderr}"
    assert "ExoArmur Core" in result.stdout
    assert "Deterministic execution governance" in result.stdout


def test_cli_version_flag():
    """Test that exoarmur --version exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "exoarmur.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI --version failed: {result.stderr}"
