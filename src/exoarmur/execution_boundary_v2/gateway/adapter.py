"""
Agent gateway adapter for governed tool execution.

Provides framework-agnostic wrapper to route tool execution through
ExoArmur's ProxyPipeline without modifying Core runtime entrypoints.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional, Union
from inspect import iscoroutinefunction

from ..models.action_intent import ActionIntent
from ..pipeline.proxy_pipeline import ProxyPipeline
from .types import Clock, FixedClock, ToolContext, ToolCall


def default_pipeline_factory() -> ProxyPipeline:
    """Default factory for creating ProxyPipeline instances."""
    # This should be configured based on the specific environment
    # For now, raise to require explicit injection
    raise NotImplementedError(
        "pipeline_factory must be explicitly provided to guard_tools. "
        "Use a factory that returns a properly configured ProxyPipeline."
    )


def guard_tools(
    tools: Mapping[str, Callable],
    *,
    policy_context: Optional[Dict[str, Any]] = None,
    approval_context: Optional[Dict[str, Any]] = None,
    safety_context: Optional[Dict[str, Any]] = None,
    pipeline_factory: Optional[Callable[[], ProxyPipeline]] = None,
    clock: Optional[Clock] = None
) -> Mapping[str, Callable]:
    """
    Wrap tools to route execution through ExoArmur's ProxyPipeline.
    
    Args:
        tools: Mapping of tool names to callable functions
        policy_context: Optional policy evaluation context
        approval_context: Optional approval context
        safety_context: Optional safety evaluation context
        pipeline_factory: Factory function for creating ProxyPipeline instances
        clock: Clock for deterministic timestamp generation
        
    Returns:
        New mapping with each tool wrapped for governed execution
    """
    if pipeline_factory is None:
        pipeline_factory = default_pipeline_factory
    
    # Create tool context
    context = ToolContext(
        policy_context=policy_context,
        approval_context=approval_context,
        safety_context=safety_context
    )
    
    # Wrap each tool
    wrapped_tools = {}
    for tool_name, tool_func in tools.items():
        if iscoroutinefunction(tool_func):
            wrapped_tools[tool_name] = _wrap_async_tool(
                tool_name, tool_func, context, pipeline_factory, clock
            )
        else:
            wrapped_tools[tool_name] = _wrap_sync_tool(
                tool_name, tool_func, context, pipeline_factory, clock
            )
    
    return wrapped_tools


def _wrap_sync_tool(
    tool_name: str,
    tool_func: Callable,
    context: ToolContext,
    pipeline_factory: Callable[[], ProxyPipeline],
    clock: Optional[Clock]
) -> Callable:
    """Wrap a synchronous tool for governed execution."""
    
    def wrapped_tool(*args, **kwargs):
        # Create ActionIntent
        intent = _create_action_intent(tool_name, args, kwargs, clock)
        
        # Execute through pipeline
        pipeline = pipeline_factory()
        result = pipeline.execute(intent)
        
        # Return the executor result output
        return result.output
    
    return wrapped_tool


def _wrap_async_tool(
    tool_name: str,
    tool_func: Callable,
    context: ToolContext,
    pipeline_factory: Callable[[], ProxyPipeline],
    clock: Optional[Clock]
) -> Callable:
    """Wrap an asynchronous tool for governed execution."""
    
    async def wrapped_tool(*args, **kwargs):
        # Create ActionIntent
        intent = _create_action_intent(tool_name, args, kwargs, clock)
        
        # Execute through pipeline (run sync pipeline in async context)
        pipeline = pipeline_factory()
        # Run the sync execute method in the async context
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: pipeline.execute(intent)
        )
        
        # Return the executor result output
        return result.output
    
    return wrapped_tool


def _create_action_intent(
    tool_name: str,
    args: tuple,
    kwargs: dict,
    clock: Optional[Clock]
) -> ActionIntent:
    """Create ActionIntent for tool execution."""
    # Generate timestamp
    if clock is None:
        raise ValueError("Clock must be provided for deterministic timestamp generation")
    
    timestamp_str = clock.now_iso8601()
    # Parse ISO 8601 string to datetime
    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    # Create tool call
    tool_call = ToolCall(tool_name, args, kwargs)
    
    # Create ActionIntent
    return ActionIntent(
        intent_id=f"tool-{tool_name}-{timestamp_str}",
        actor_id="agent-gateway",
        actor_type="agent",
        action_type=f"tool.{tool_name}",
        target="tool_execution",
        parameters=tool_call.to_parameters(),
        timestamp=timestamp
    )
