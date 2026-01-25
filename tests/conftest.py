"""
Pytest configuration and fixtures for ExoArmur constitutional guardrails
"""

import pytest
import os
from unittest.mock import patch

from src.feature_flags import get_feature_flags


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
        'EXOARMUR_FLAG_V2_AUDIT_FEDERATION_ENABLED'
    ]
    
    for key in flag_keys:
        original_env[key] = os.environ.get(key)
    
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