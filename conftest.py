"""
Pytest configuration for ExoArmur
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

collect_ignore = [
    "tests/test_integration.py",
    "tests/test_intent_freeze_binding.py",
    "tests/test_approval_wiring.py",
]

import pytest
import warnings
import random


def pytest_configure(config):
    """Configure pytest with strict settings"""
    random.seed(0)

    # Treat warnings as errors in sensitive runs
    if config.getoption("-m") and "sensitive" in config.getoption("-m"):
        warnings.filterwarnings("error", category=DeprecationWarning)
        warnings.filterwarnings("error", category=PendingDeprecationWarning)

    # Add custom markers
    config.addinivalue_line(
        "markers", "sensitive: Tests that must be deterministic and isolated"
    )
    config.addinivalue_line(
        "markers", "boundary: Tests that verify boundary enforcement"
    )
