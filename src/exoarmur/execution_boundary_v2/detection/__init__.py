"""
Detection module initialization
"""

from .execution_violation_detector import (
    ViolationSeverity,
    ExecutionViolation,
    ExecutionContextTracker,
    ViolationDetector,
    V2ExecutionContext,
    check_domain_logic_access,
    get_v2_execution_context,
    detect_domain_logic_violations,
    detect_method_violation
)

__all__ = [
    "ViolationSeverity",
    "ExecutionViolation", 
    "ExecutionContextTracker",
    "ViolationDetector",
    "V2ExecutionContext",
    "check_domain_logic_access",
    "get_v2_execution_context",
    "detect_domain_logic_violations",
    "detect_method_violation"
]
