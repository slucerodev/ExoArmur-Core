"""
V1Adapter - Top-level adapter for V1/V2 compatibility.

This module provides the main V1Adapter interface that tests expect.
The actual implementation is delegated to the execution_boundary_v2.v1_adapter.
"""

from typing import Any, Dict, Optional

# Import the actual implementation from execution_boundary_v2
from .execution_boundary_v2.v1_adapter import V1CompatibilityLayer


class V1Adapter:
    """
    Minimal V1Adapter class skeleton for test compatibility.
    
    This provides the interface that tests expect without implementing
    full V1/V2 conversion logic.
    """
    
    def __init__(self):
        self._compatibility = V1CompatibilityLayer()
    
    def create_v1_audit_record(self, *args, **kwargs) -> Any:
        """Create V1 audit record - delegates to compatibility layer."""
        return self._compatibility.create_v1_audit_record(*args, **kwargs)
    
    def create_v1_policy_decision(self, *args, **kwargs) -> Any:
        """Create V1 policy decision - delegates to compatibility layer."""
        return self._compatibility.create_v1_policy_decision(*args, **kwargs)
    
    def create_v1_execution_intent(self, *args, **kwargs) -> Any:
        """Create V1 execution intent - delegates to compatibility layer."""
        return self._compatibility.create_v1_execution_intent(*args, **kwargs)
