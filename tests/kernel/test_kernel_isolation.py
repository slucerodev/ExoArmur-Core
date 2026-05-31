"""
Test that Core kernel has no vendor SDK imports.

This test ensures DACT Level 5 kernel isolation is maintained.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_kernel_no_vendor_sdk_imports():
    """Test that kernel modules have no vendor SDK imports."""
    # Check for network-related imports in kernel
    result = subprocess.run(
        [
            "grep",
            "-r",
            "import urllib\\|import requests\\|import socket\\|import nats\\|import fastapi\\|import pydantic\\|import httpx",
            "src/exoarmur/kernel",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no network imports in kernel
    assert result.returncode != 0, "Found network imports in kernel: " + result.stdout


def test_kernel_no_openai_imports():
    """Test that kernel does not import OpenAI SDK."""
    result = subprocess.run(
        ["grep", "-r", "import openai", "src/exoarmur/kernel"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no OpenAI imports in kernel
    assert result.returncode != 0, "Found OpenAI imports in kernel: " + result.stdout


def test_kernel_no_anthropic_imports():
    """Test that kernel does not import Anthropic SDK."""
    result = subprocess.run(
        ["grep", "-r", "import anthropic", "src/exoarmur/kernel"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no Anthropic imports in kernel
    assert result.returncode != 0, "Found Anthropic imports in kernel: " + result.stdout


def test_kernel_no_langchain_imports():
    """Test that kernel does not import LangChain."""
    result = subprocess.run(
        ["grep", "-r", "import langchain", "src/exoarmur/kernel"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no LangChain imports in kernel
    assert result.returncode != 0, "Found LangChain imports in kernel: " + result.stdout


def test_kernel_no_transformers_imports():
    """Test that kernel does not import transformers."""
    result = subprocess.run(
        ["grep", "-r", "import transformers", "src/exoarmur/kernel"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no transformers imports in kernel
    assert result.returncode != 0, (
        "Found transformers imports in kernel: " + result.stdout
    )


def test_kernel_no_torch_imports():
    """Test that kernel does not import torch."""
    result = subprocess.run(
        ["grep", "-r", "import torch", "src/exoarmur/kernel"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Should find no torch imports in kernel
    assert result.returncode != 0, "Found torch imports in kernel: " + result.stdout
