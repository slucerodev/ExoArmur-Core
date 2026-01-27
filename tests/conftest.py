"""
Pytest configuration and fixtures for ExoArmur constitutional guardrails
"""

import pytest
import os
import faulthandler
from unittest.mock import patch

from src.feature_flags import get_feature_flags


def pytest_sessionstart(session):
    """Add watchdog for hanging tests when env flag is set"""
    if os.environ.get("EXOARMUR_PYTEST_WATCHDOG") == "1":
        faulthandler.enable()
        faulthandler.dump_traceback_later(30, repeat=True)


@pytest.fixture(autouse=True)
def reset_feature_flags_isolation():
    """
    Autouse fixture to ensure FeatureFlags state isolation between tests.
    Prevents test pollution from environment variables or global state mutations.
    """
    # Store original environment state
    original_env = {}
    flag_keys = [
        'EXOARMUR_FLAG_V2_FEDERATION_ENABLED',
        'EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED', 
        'EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED',
        'EXOARMUR_FLAG_V2_FEDERATION_IDENTITY_ENABLED',
        'EXOARMUR_FLAG_V2_AUDIT_FEDERATION_ENABLED',
        'EXOARMUR_FAIL_OPEN_KILL_SWITCH',  # Test mode kill switch override
        'EXOARMUR_TEST_API_KEY'  # Test API key for auth tests
    ]
    
    for key in flag_keys:
        original_env[key] = os.environ.get(key)
    
    # Set test mode defaults (only if not already set)
    os.environ.setdefault('EXOARMUR_FAIL_OPEN_KILL_SWITCH', '1')
    os.environ.setdefault('EXOARMUR_TEST_API_KEY', 'test-api-key-12345')
    
    # Reset global feature flags instance
    from src.feature_flags.feature_flags import _feature_flags_instance
    original_instance = _feature_flags_instance
    _feature_flags_instance = None
    
    yield
    
    # Restore environment state
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    
    # Reset global feature flags instance
    _feature_flags_instance = original_instance


@pytest.fixture(autouse=True)
def override_execution_gate():
    """Override execution gate to allow tests without NATS"""
    from src.safety import GateDecision, DenialReason, GateResult
    from unittest.mock import patch
    
    # Create a mock enforce_execution_gate function that always allows
    async def mock_enforce_execution_gate(
        action_type,
        tenant_id=None,
        correlation_id=None,
        trace_id=None,
        principal_id=None,
        additional_context=None
    ):
        return GateResult(
            decision=GateDecision.ALLOW,
            reason=None
        )
    
    # Patch enforce_execution_gate at its source
    with patch('src.safety.execution_gate.enforce_execution_gate', mock_enforce_execution_gate):
        yield