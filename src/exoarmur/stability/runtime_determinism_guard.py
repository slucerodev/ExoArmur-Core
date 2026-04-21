"""
Runtime Determinism Guard

Provides runtime enforcement to detect wall-clock usage in critical contexts.
Fails fast if nondeterministic behavior is detected during execution.

Automatic Guard Activation:
- Guards activate automatically when code runs in protected modules
- No decorator reliance - enforcement based on call stack inspection
- Monkey-patches at import time for datetime.now, time.time, random.*, hash()
"""

import sys
import functools
import warnings
import inspect
import time as time_module
import random as random_module
import hashlib
import builtins
from typing import Callable, Optional, Any
from datetime import datetime, timezone

from exoarmur.stability.determinism_protected_modules import (
    is_module_protected,
    get_protection_level,
    is_module_exempt,
    ProtectionLevel,
    get_protected_module_paths
)


class DeterminismViolationError(RuntimeError):
    """Raised when a determinism violation is detected at runtime"""
    
    def __init__(self, violation_type: str, description: str, fix_suggestion: str):
        self.violation_type = violation_type
        self.description = description
        self.fix_suggestion = fix_suggestion
        message = f"[DETERMINISM VIOLATION] {violation_type}: {description}\nFix: {fix_suggestion}"
        super().__init__(message)


class RuntimeDeterminismGuard:
    """Runtime guard that detects wall-clock usage in protected contexts"""
    
    _enabled: bool = True
    _protected_call_stack: list = []
    _protected_module_prefixes: set = get_protected_module_paths()
    
    @classmethod
    def enable(cls):
        """Enable runtime determinism guard"""
        cls._enabled = True
    
    @classmethod
    def disable(cls):
        """Disable runtime determinism guard (for testing only)"""
        cls._enabled = False
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if guard is enabled"""
        return cls._enabled
    
    @classmethod
    def enter_protected_context(cls, context_name: str):
        """Enter a protected execution context"""
        cls._protected_call_stack.append(context_name)
    
    @classmethod
    def exit_protected_context(cls):
        """Exit a protected execution context"""
        if cls._protected_call_stack:
            cls._protected_call_stack.pop()
    
    @classmethod
    def in_protected_context(cls) -> bool:
        """Check if currently in a protected context"""
        return len(cls._protected_call_stack) > 0
    
    @classmethod
    def _is_caller_in_protected_module(cls) -> bool:
        """Check if the current call stack is in a protected module"""
        # Get the current call stack
        stack = inspect.stack()
        
        for frame_info in stack:
            # Get the module name from the frame
            frame = frame_info.frame
            module_name = frame.f_globals.get('__name__', '')
            
            # Check if this module is protected
            if is_module_protected(module_name):
                # Check if it's exempt
                if not is_module_exempt(module_name):
                    return True
        
        return False
    
    @classmethod
    def _get_caller_module(cls) -> str:
        """Get the module name of the caller"""
        stack = inspect.stack()
        # Skip the current frame and the guard frame
        for frame_info in stack[2:]:
            frame = frame_info.frame
            module_name = frame.f_globals.get('__name__', '')
            if module_name:
                return module_name
        return "unknown"
    
    @classmethod
    def check_datetime_now(cls):
        """Check if datetime.now() is being called in protected context"""
        if not cls._enabled:
            return
        
        # Check both explicit protected context and automatic module-based protection
        if cls.in_protected_context() or cls._is_caller_in_protected_module():
            context = cls._protected_call_stack[-1] if cls._protected_call_stack else cls._get_caller_module()
            raise DeterminismViolationError(
                violation_type="DATETIME_NOW_CALL",
                description=f"datetime.now() called in protected context: {context}",
                fix_suggestion="Use get_federation_clock().now() or DeterministicClock instead"
            )
    
    @classmethod
    def check_time_time(cls):
        """Check if time.time() is being called in protected context"""
        if not cls._enabled:
            return
        
        # Check both explicit protected context and automatic module-based protection
        if cls.in_protected_context() or cls._is_caller_in_protected_module():
            context = cls._protected_call_stack[-1] if cls._protected_call_stack else cls._get_caller_module()
            raise DeterminismViolationError(
                violation_type="TIME_TIME_CALL",
                description=f"time.time() called in protected context: {context}",
                fix_suggestion="Use DeterministicClock instead of wall-clock time"
            )
    
    @classmethod
    def check_time_monotonic(cls):
        """Check if time.monotonic() is being called in protected context"""
        if not cls._enabled:
            return
        
        # Check both explicit protected context and automatic module-based protection
        if cls.in_protected_context() or cls._is_caller_in_protected_module():
            context = cls._protected_call_stack[-1] if cls._protected_call_stack else cls._get_caller_module()
            raise DeterminismViolationError(
                violation_type="TIME_MONOTONIC_CALL",
                description=f"time.monotonic() called in protected context: {context}",
                fix_suggestion="Use DeterministicClock instead of wall-clock time"
            )
    
    @classmethod
    def check_random_call(cls):
        """Check if random module is being called in protected context"""
        if not cls._enabled:
            return
        
        # Check both explicit protected context and automatic module-based protection
        if cls.in_protected_context() or cls._is_caller_in_protected_module():
            context = cls._protected_call_stack[-1] if cls._protected_call_stack else cls._get_caller_module()
            raise DeterminismViolationError(
                violation_type="RANDOM_CALL",
                description=f"random module called in protected context: {context}",
                fix_suggestion="Use seeded random or deterministic alternative instead"
            )
    
    @classmethod
    def check_hash_call(cls):
        """Check if hash() is being called in protected context"""
        if not cls._enabled:
            return
        
        # Check both explicit protected context and automatic module-based protection
        if cls.in_protected_context() or cls._is_caller_in_protected_module():
            context = cls._protected_call_stack[-1] if cls._protected_call_stack else cls._get_caller_module()
            raise DeterminismViolationError(
                violation_type="HASH_CALL",
                description=f"hash() called in protected context: {context}",
                fix_suggestion="Use stable_hash() from exoarmur.replay.canonical_utils instead"
            )


def protected_context(context_name: str):
    """Decorator to mark a function as running in a protected context"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            RuntimeDeterminismGuard.enter_protected_context(context_name)
            try:
                return func(*args, **kwargs)
            finally:
                RuntimeDeterminismGuard.exit_protected_context()
        return wrapper
    return decorator


def async_protected_context(context_name: str):
    """Decorator to mark an async function as running in a protected context"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            RuntimeDeterminismGuard.enter_protected_context(context_name)
            try:
                return await func(*args, **kwargs)
            finally:
                RuntimeDeterminismGuard.exit_protected_context()
        return wrapper
    return decorator


class DeterministicClockGuard:
    """Guard that ensures DeterministicClock is active in critical paths"""
    
    @staticmethod
    def assert_deterministic_clock_active(clock_instance: Any):
        """Assert that the clock is a DeterministicClock instance"""
        from exoarmur.stability.deterministic_clock import DeterministicClock
        
        if not isinstance(clock_instance, DeterministicClock):
            raise DeterminismViolationError(
                violation_type="NON_DETERMINISTIC_CLOCK",
                description=f"Non-deterministic clock used: {type(clock_instance).__name__}",
                fix_suggestion="Use DeterministicClock or get_federation_clock() for deterministic time"
            )
    
    @staticmethod
    def assert_clock_context():
        """Assert that we're in a deterministic clock context"""
        from exoarmur.stability.deterministic_clock import get_clock, DeterministicClock
        
        clock = get_clock()
        if not isinstance(clock, DeterministicClock):
            raise DeterminismViolationError(
                violation_type="WALL_CLOCK_ACTIVE",
                description="Wall clock is active in critical path",
                fix_suggestion="Use deterministic_clock_context() or set_clock(DeterministicClock())"
            )


def enforce_determinism(func: Callable) -> Callable:
    """
    Decorator that enforces determinism for a function.
    Ensures:
    1. Function runs in a protected context
    2. DeterministicClock is active
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Enter protected context
        context_name = f"{func.__module__}.{func.__name__}"
        RuntimeDeterminismGuard.enter_protected_context(context_name)
        
        try:
            # Assert deterministic clock
            DeterministicClockGuard.assert_clock_context()
            
            # Execute function
            return func(*args, **kwargs)
        finally:
            # Exit protected context
            RuntimeDeterminismGuard.exit_protected_context()
    
    return wrapper


def async_enforce_determinism(func: Callable) -> Callable:
    """
    Async decorator that enforces determinism for a function.
    Ensures:
    1. Function runs in a protected context
    2. DeterministicClock is active
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Enter protected context
        context_name = f"{func.__module__}.{func.__name__}"
        RuntimeDeterminismGuard.enter_protected_context(context_name)
        
        try:
            # Assert deterministic clock
            DeterministicClockGuard.assert_clock_context()
            
            # Execute function
            return await func(*args, **kwargs)
        finally:
            # Exit protected context
            RuntimeDeterminismGuard.exit_protected_context()
    
    return wrapper


# Monkey-patch datetime.now() to detect calls in protected contexts
_original_datetime_now = datetime.now
_original_datetime_utcnow = datetime.utcnow

# Monkey-patch time functions
_original_time_time = time_module.time
_original_time_monotonic = time_module.monotonic

# Monkey-patch random module
_original_random_seed = random_module.seed
_original_random_random = random_module.random
_original_random_randint = random_module.randint
_original_random_choice = random_module.choice

# Monkey-patch built-in hash
_original_hash = hash


def _guarded_datetime_now(tz=None):
    """Guarded datetime.now() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_datetime_now()
    return _original_datetime_now(tz)


def _guarded_datetime_utcnow():
    """Guarded datetime.utcnow() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_datetime_now()
    return _original_datetime_utcnow()


def _guarded_time_time():
    """Guarded time.time() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_time_time()
    return _original_time_time()


def _guarded_time_monotonic():
    """Guarded time.monotonic() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_time_monotonic()
    return _original_time_monotonic()


def _guarded_random_seed(*args, **kwargs):
    """Guarded random.seed() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_random_call()
    return _original_random_seed(*args, **kwargs)


def _guarded_random_random():
    """Guarded random.random() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_random_call()
    return _original_random_random()


def _guarded_random_randint(*args, **kwargs):
    """Guarded random.randint() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_random_call()
    return _original_random_randint(*args, **kwargs)


def _guarded_random_choice(*args, **kwargs):
    """Guarded random.choice() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_random_call()
    return _original_random_choice(*args, **kwargs)


def _guarded_hash(*args, **kwargs):
    """Guarded hash() that detects calls in protected contexts"""
    RuntimeDeterminismGuard.check_hash_call()
    return _original_hash(*args, **kwargs)


def enable_runtime_guards():
    """Enable runtime determinism guards by monkey-patching at import time"""
    # Patch datetime
    datetime.now = _guarded_datetime_now
    datetime.utcnow = _guarded_datetime_utcnow
    
    # Patch time module
    time_module.time = _guarded_time_time
    time_module.monotonic = _guarded_time_monotonic
    
    # Patch random module
    random_module.seed = _guarded_random_seed
    random_module.random = _guarded_random_random
    random_module.randint = _guarded_random_randint
    random_module.choice = _guarded_random_choice
    
    # Patch built-in hash
    builtins.hash = _guarded_hash


def disable_runtime_guards():
    """Disable runtime determinism guards by restoring original functions"""
    # Restore datetime
    datetime.now = _original_datetime_now
    datetime.utcnow = _original_datetime_utcnow
    
    # Restore time module
    time_module.time = _original_time_time
    time_module.monotonic = _original_time_monotonic
    
    # Restore random module
    random_module.seed = _original_random_seed
    random_module.random = _original_random_random
    random_module.randint = _original_random_randint
    random_module.choice = _original_random_choice
    
    # Restore built-in hash
    builtins.hash = _original_hash
