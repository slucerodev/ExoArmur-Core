"""
Gateway types and abstractions for agent tool execution.

Provides minimal abstractions for deterministic clock and tool wrapping.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional, Callable
from datetime import datetime, timezone


class Clock(ABC):
    """Abstract clock protocol for deterministic timestamp generation."""
    
    @abstractmethod
    def now_iso8601(self) -> str:
        """Return current time in ISO 8601 format."""
        pass


class FixedClock(Clock):
    """Deterministic clock that returns a constant timestamp."""
    
    def __init__(self, fixed_time: str):
        """Initialize with a fixed ISO 8601 timestamp."""
        self.fixed_time = fixed_time
    
    def now_iso8601(self) -> str:
        """Return the fixed timestamp."""
        return self.fixed_time


class ToolContext:
    """Context for tool execution through gateway."""
    
    def __init__(
        self,
        policy_context: Optional[Dict[str, Any]] = None,
        approval_context: Optional[Dict[str, Any]] = None,
        safety_context: Optional[Dict[str, Any]] = None
    ):
        self.policy_context = policy_context or {}
        self.approval_context = approval_context or {}
        self.safety_context = safety_context or {}


class ToolCall:
    """Represents a tool call with arguments."""
    
    def __init__(self, tool_name: str, args: tuple, kwargs: dict):
        self.tool_name = tool_name
        self.args = args
        self.kwargs = kwargs
    
    def to_parameters(self) -> Dict[str, Any]:
        """Convert to ActionIntent parameters format."""
        return {
            "tool_name": self.tool_name,
            "args": list(self.args),
            "kwargs": self.kwargs
        }
