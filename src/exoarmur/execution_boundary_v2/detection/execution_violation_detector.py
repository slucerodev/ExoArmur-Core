"""
Execution Violation Detection - STEP 1: Detection Only

Lightweight detection mechanism for domain logic execution outside V2EntryGate.
This is a visibility layer only - NO behavior changes, NO blocking, NO routing changes.
"""

import logging
import threading
import traceback
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    """Severity levels for execution violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionViolation:
    """Structured violation signal for domain logic execution outside V2EntryGate"""
    
    def __init__(
        self,
        component_name: str,
        method_name: str,
        call_origin: str,
        execution_context: str,
        severity: ViolationSeverity,
        stack_trace: Optional[str] = None
    ):
        self.component_name = component_name
        self.method_name = method_name
        self.call_origin = call_origin
        self.execution_context = execution_context
        self.severity = severity
        self.timestamp = datetime.now(timezone.utc)
        self.stack_trace = stack_trace or traceback.format_stack()[-5:]  # Last 5 frames
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to structured format"""
        return {
            "component": self.component_name,
            "method": self.method_name,
            "origin": self.call_origin,
            "context": self.execution_context,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace
        }
    
    def emit(self):
        """Emit violation signal to logging"""
        violation_data = self.to_dict()
        logger.warning(
            f"EXECUTION VIOLATION DETECTED: {self.component_name}.{self.method_name} "
            f"called from {self.call_origin} in {self.execution_context} context "
            f"[severity: {self.severity.value}]"
        )
        logger.debug(f"Violation details: {violation_data}")


class ExecutionContextTracker:
    """
    Thread-local execution context tracker.
    
    Tracks whether execution is currently within V2EntryGate context.
    This is detection-only - NO enforcement.
    """
    
    def __init__(self):
        self._context = threading.local()
    
    def enter_v2_context(self):
        """Mark entry into V2EntryGate context"""
        self._context.in_v2_gate = True
        self._context.v2_entry_time = datetime.now(timezone.utc)
    
    def exit_v2_context(self):
        """Mark exit from V2EntryGate context"""
        self._context.in_v2_gate = False
    
    def is_in_v2_context(self) -> bool:
        """Check if currently in V2EntryGate context"""
        return getattr(self._context, 'in_v2_gate', False)
    
    def get_call_origin(self) -> str:
        """Get best-effort call origin from stack trace"""
        try:
            stack = traceback.extract_stack()
            # Skip detection frames and find first meaningful frame
            for frame in reversed(stack[-10:]):  # Last 10 frames
                if not any(skip in frame.filename for skip in [
                    'execution_violation_detector.py',
                    'v2_entry_gate.py',
                    'contextlib.py'
                ]):
                    return f"{frame.filename}:{frame.lineno}:{frame.name}"
            return "unknown"
        except Exception:
            return "unknown"


# Global tracker instance
_tracker = ExecutionContextTracker()


class ViolationDetector:
    """
    Domain logic violation detector.
    
    Detects when domain logic is accessed outside V2EntryGate context.
    This is detection-only - NO blocking or enforcement.
    """
    
    @staticmethod
    def check_domain_logic_access(
        component_name: str,
        method_name: str,
        severity: ViolationSeverity = ViolationSeverity.MEDIUM
    ) -> Optional[ExecutionViolation]:
        """
        Check if domain logic access is outside V2EntryGate.
        
        Returns violation if access is outside V2 context, None otherwise.
        This is detection-only - NO behavior changes.
        """
        if _tracker.is_in_v2_context():
            # Inside V2EntryGate - this is allowed
            return None
        
        # Outside V2EntryGate - emit violation signal
        call_origin = _tracker.get_call_origin()
        violation = ExecutionViolation(
            component_name=component_name,
            method_name=method_name,
            call_origin=call_origin,
            execution_context="NON-V2",
            severity=severity
        )
        
        violation.emit()
        return violation


# Context manager for V2EntryGate execution
class V2ExecutionContext:
    """Context manager for V2EntryGate execution tracking"""
    
    def __enter__(self):
        _tracker.enter_v2_context()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _tracker.exit_v2_context()


# Public API for detection
def check_domain_logic_access(
    component_name: str,
    method_name: str,
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
) -> Optional[ExecutionViolation]:
    """
    Public API to check domain logic access.
    
    Usage: Add this at the start of domain logic methods:
    
    def some_domain_method(self):
        check_domain_logic_access("ComponentName", "some_domain_method")
        # ... existing method logic
    """
    return ViolationDetector.check_domain_logic_access(
        component_name=component_name,
        method_name=method_name,
        severity=severity
    )


def get_v2_execution_context() -> V2ExecutionContext:
    """Get V2 execution context manager"""
    return V2ExecutionContext()


# Convenience decorators for automatic detection
def detect_domain_logic_violations(component_name: str, severity: ViolationSeverity = ViolationSeverity.MEDIUM):
    """
    Decorator to automatically detect violations for all methods in a class.
    
    Usage:
    
    @detect_domain_logic_violations("ExecutionKernel")
    class ExecutionKernel:
        def some_method(self):
            # Violation detection automatically applied
    """
    def decorator(cls):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                # Wrap method with violation detection
                original_method = attr
                
                def wrapped_method(self, *args, **kwargs):
                    check_domain_logic_access(component_name, attr_name, severity)
                    return original_method(self, *args, **kwargs)
                
                setattr(cls, attr_name, wrapped_method)
        return cls
    return decorator


def detect_method_violation(component_name: str, method_name: str, severity: ViolationSeverity = ViolationSeverity.MEDIUM):
    """
    Decorator for individual method violation detection.
    
    Usage:
    
    @detect_method_violation("AuditLogger", "emit_audit_record")
    def emit_audit_record(self, ...):
        # Method logic
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            check_domain_logic_access(component_name, method_name, severity)
            return func(*args, **kwargs)
        return wrapper
    return decorator
