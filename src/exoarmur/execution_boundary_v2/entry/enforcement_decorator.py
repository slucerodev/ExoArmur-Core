"""
Execution Enforcement Decorator - Structural Enforcement Mechanism

This decorator enforces that all execution must route through the canonical
execution spine (CanonicalExecutionRouter → V2EntryGate).

PRINCIPLES:
- Structural enforcement, not conventional
- No bypass possible at runtime
- Fail-fast on direct execution attempts
"""

import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class ExecutionBypassError(RuntimeError):
    """Raised when direct execution bypass is detected"""
    pass

def enforce_canonical_routing(module_name: str = None):
    """
    Decorator that enforces canonical routing for execution functions
    
    This decorator transforms any function into a canonical routing wrapper,
    ensuring all execution goes through V2EntryGate.
    
    Args:
        module_name: Optional module identifier for routing
        
    Raises:
        ExecutionBypassError: If function attempts direct execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            try:
                from .canonical_router import CanonicalExecutionRouter
            except ImportError as e:
                raise ExecutionBypassError(
                    f"Canonical router not available for {func.__name__}. "
                    f"Cannot enforce execution routing: {e}"
                )
            
            # Check if router is available
            if not CanonicalExecutionRouter.is_available():
                raise ExecutionBypassError(
                    f"V2EntryGate not available for {func.__name__}. "
                    "Execution cannot proceed without canonical routing."
                )
            
            logger.info(f"Enforcing canonical routing for {func.__name__}")
            
            # Extract execution context from function arguments
            # This is a simplified extraction - real implementation would be more sophisticated
            execution_context = {
                "execution_id": f"exec_{func.__name__}_{int(time.time())}",
                "module_id": module_name or func.__module__,
                "deterministic_seed": 42,
                "logical_timestamp": int(time.time()),
                "correlation_id": f"decorator_{func.__name__}"
            }
            
            # Extract action data from function arguments
            action_data = {
                "function_name": func.__name__,
                "args": args,
                "kwargs": kwargs,
                "enforced_by": "decorator"
            }
            
            # Route through canonical spine - ONLY VALID PATH
            result = CanonicalExecutionRouter.route_to_v2_entry_gate(
                module_id=execution_context["module_id"],
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            return result
        
        return wrapper
    return decorator

def prevent_direct_execution(cls_name: str = None):
    """
    Class decorator that prevents direct execution of executor classes
    
    This decorator patches all execute methods to raise errors if called directly,
    forcing all execution through canonical routing.
    
    Args:
        cls_name: Optional class identifier for error messages
    """
    def decorator(cls) -> Any:
        # Patch all execute methods
        for attr_name in dir(cls):
            if attr_name == 'execute' and callable(getattr(cls, attr_name)):
                original_execute = getattr(cls, attr_name)
                
                @functools.wraps(original_execute)
                def bypass_prevention_execute(*args, **kwargs):
                    class_identifier = cls_name or cls.__name__
                    raise ExecutionBypassError(
                        f"DIRECT EXECUTOR BYPASS DETECTED in {class_identifier}. "
                        f"Use CanonicalExecutionRouter.route_to_v2_entry_gate() instead. "
                        f"Direct executor.execute() calls are forbidden."
                    )
                
                setattr(cls, attr_name, bypass_prevention_execute)
                logger.info(f"Patched {class_identifier}.{attr_name} to prevent bypass")
        
        return cls
    return decorator

# Global enforcement registry
_enforced_functions = set()
_enforced_classes = set()

def register_enforced_function(func_name: str):
    """Register a function as enforced"""
    _enforced_functions.add(func_name)
    logger.info(f"Registered enforced function: {func_name}")

def register_enforced_class(cls_name: str):
    """Register a class as enforced"""
    _enforced_classes.add(cls_name)
    logger.info(f"Registered enforced class: {cls_name}")

def get_enforced_functions() -> set:
    """Get all enforced functions"""
    return _enforced_functions.copy()

def get_enforced_classes() -> set:
    """Get all enforced classes"""
    return _enforced_classes.copy()

def is_enforced_function(func_name: str) -> bool:
    """Check if a function is enforced"""
    return func_name in _enforced_functions

def is_enforced_class(cls_name: str) -> bool:
    """Check if a class is enforced"""
    return cls_name in _enforced_classes
