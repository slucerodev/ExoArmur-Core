"""
ExoArmur Agent Gateway - Thin adapter for governed tool execution.

Provides framework-agnostic wrapper to route tool execution through
ExoArmur's ProxyPipeline without modifying Core runtime entrypoints.
"""

from .adapter import guard_tools
from .types import Clock, FixedClock

__all__ = ["guard_tools", "Clock", "FixedClock"]
