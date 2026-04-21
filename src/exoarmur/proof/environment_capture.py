"""
Environment Capture for Determinism Proof

This module provides functions to capture the execution environment
for determinism proof reporting, ensuring all external dependencies
and environmental factors are documented.
"""

import sys
import platform
from typing import Dict, Any


def capture_environment() -> Dict[str, Any]:
    """
    Capture environment snapshot for determinism proof.
    
    This function:
    - Captures Python version
    - Captures OS/platform information
    - Captures key dependency versions
    - Captures determinism guard status
    - Captures relevant environment variables
    
    Returns:
        Dictionary containing environment snapshot
    """
    environment = {}
    
    # Python version
    environment["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # OS/Platform
    environment["os"] = platform.system()
    environment["platform"] = platform.platform()
    environment["architecture"] = platform.machine()
    
    # Dependency versions
    environment["dependencies"] = {}
    try:
        import fastapi
        environment["dependencies"]["fastapi"] = fastapi.__version__
    except:
        pass
    try:
        import pydantic
        environment["dependencies"]["pydantic"] = pydantic.__version__
    except:
        pass
    try:
        import cryptography
        environment["dependencies"]["cryptography"] = cryptography.__version__
    except:
        pass
    
    # Determinism guard status
    environment["determinism_guards"] = {}
    try:
        from exoarmur.stability.runtime_determinism_guard import get_guard_status
        environment["determinism_guards"]["status"] = get_guard_status()
    except:
        environment["determinism_guards"]["status"] = "unknown"
    
    # Environment variables
    environment["environment_variables"] = {
        "PYTHONHASHSEED": __import__("os").environ.get("PYTHONHASHSEED", "not_set"),
        "DETERMINISM_GUARD_ENABLED": __import__("os").environ.get("DETERMINISM_GUARD_ENABLED", "not_set"),
    }
    
    return environment
