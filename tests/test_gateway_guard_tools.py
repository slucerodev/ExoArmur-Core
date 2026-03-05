"""Tests for agent gateway guard_tools functionality."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from exoarmur.execution_boundary_v2.gateway import guard_tools, FixedClock
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorPlugin, ExecutorResult
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict


class TestGatewayGuardTools:
    """Test guard_tools wrapper functionality."""
    
    def test_wrap_sync_tool(self):
        """Test wrapping a simple synchronous tool."""
        # Create original tool
        original_called = []
        def echo_tool(message: str) -> str:
            original_called.append(True)
            return f"echo: {message}"
        
        # Create mock pipeline factory
        pipeline_calls = []
        
        def mock_pipeline_factory():
            pipeline = MockProxyPipeline(pipeline_calls)
            return pipeline
        
        # Wrap tools
        tools = {"echo": echo_tool}
        clock = FixedClock("2026-01-01T00:00:00Z")
        guarded = guard_tools(
            tools,
            clock=clock,
            pipeline_factory=mock_pipeline_factory
        )
        
        # Call guarded tool
        result = guarded["echo"]("hello world")
        
        # Verify results
        assert result == {"mock_output": "echo_result"}
        assert len(pipeline_calls) == 1
        
        # Verify ActionIntent was created correctly
        intent = pipeline_calls[0]
        assert intent.action_type == "tool.echo"
        assert intent.parameters["tool_name"] == "echo"
        assert intent.parameters["args"] == ["hello world"]
        assert intent.parameters["kwargs"] == {}
        assert intent.actor_id == "agent-gateway"
        assert intent.actor_type == "agent"
        assert intent.target == "tool_execution"
        
        # Verify original tool was NOT called directly (bypass prevention)
        assert len(original_called) == 0
    
    @pytest.mark.asyncio
    async def test_wrap_async_tool(self):
        """Test wrapping an asynchronous tool."""
        # Create original async tool
        original_called = []
        async def async_echo_tool(message: str) -> str:
            original_called.append(True)
            await asyncio.sleep(0.001)  # Simulate async work
            return f"async echo: {message}"
        
        # Create mock pipeline factory
        pipeline_calls = []
        
        def mock_pipeline_factory():
            pipeline = MockProxyPipeline(pipeline_calls)
            return pipeline
        
        # Wrap tools
        tools = {"async_echo": async_echo_tool}
        clock = FixedClock("2026-01-01T00:00:00Z")
        guarded = guard_tools(
            tools,
            clock=clock,
            pipeline_factory=mock_pipeline_factory
        )
        
        # Call guarded async tool
        result = await guarded["async_echo"]("hello async")
        
        # Verify results
        assert result == {"mock_output": "async_echo_result"}
        assert len(pipeline_calls) == 1
        
        # Verify ActionIntent was created correctly
        intent = pipeline_calls[0]
        assert intent.action_type == "tool.async_echo"
        assert intent.parameters["tool_name"] == "async_echo"
        assert intent.parameters["args"] == ["hello async"]
        assert intent.parameters["kwargs"] == {}
        
        # Verify original tool was NOT called directly (bypass prevention)
        assert len(original_called) == 0
    
    def test_bypass_prevention(self):
        """Test that original tools cannot be called directly when guarded."""
        # Create tool that raises if called directly
        def sensitive_tool(data: str) -> str:
            raise RuntimeError("Tool called directly - bypass detected!")
        
        # Create mock pipeline factory
        pipeline_calls = []
        
        def mock_pipeline_factory():
            pipeline = MockProxyPipeline(pipeline_calls)
            return pipeline
        
        # Wrap tools
        tools = {"sensitive": sensitive_tool}
        clock = FixedClock("2026-01-01T00:00:00Z")
        guarded = guard_tools(
            tools,
            clock=clock,
            pipeline_factory=mock_pipeline_factory
        )
        
        # Call guarded tool - should work through pipeline
        result = guarded["sensitive"]("test data")
        
        # Verify pipeline was used and no direct call occurred
        assert result == {"mock_output": "sensitive_result"}
        assert len(pipeline_calls) == 1
    
    def test_multiple_tools(self):
        """Test wrapping multiple tools with different signatures."""
        def add(a: int, b: int) -> int:
            return a + b
        
        def greet(name: str, *, greeting: str = "hello") -> str:
            return f"{greeting}, {name}!"
        
        # Create mock pipeline factory
        pipeline_calls = []
        
        def mock_pipeline_factory():
            pipeline = MockProxyPipeline(pipeline_calls)
            return pipeline
        
        # Wrap tools
        tools = {"add": add, "greet": greet}
        clock = FixedClock("2026-01-01T00:00:00Z")
        guarded = guard_tools(
            tools,
            clock=clock,
            pipeline_factory=mock_pipeline_factory
        )
        
        # Call tools
        result1 = guarded["add"](2, 3)
        result2 = guarded["greet"]("world", greeting="hi")
        
        # Verify results
        assert result1 == {"mock_output": "add_result"}
        assert result2 == {"mock_output": "greet_result"}
        assert len(pipeline_calls) == 2
        
        # Verify ActionIntents
        intent1 = pipeline_calls[0]
        assert intent1.action_type == "tool.add"
        assert intent1.parameters["args"] == [2, 3]
        assert intent1.parameters["kwargs"] == {}
        
        intent2 = pipeline_calls[1]
        assert intent2.action_type == "tool.greet"
        assert intent2.parameters["args"] == ["world"]
        assert intent2.parameters["kwargs"] == {"greeting": "hi"}
    
    def test_clock_required(self):
        """Test that clock is required for deterministic behavior."""
        def simple_tool(x: str) -> str:
            return x
        
        tools = {"simple": simple_tool}
        
        # Should raise when no clock provided (when calling the wrapped tool)
        with pytest.raises(ValueError, match="Clock must be provided"):
            guarded = guard_tools(tools, pipeline_factory=lambda: MockProxyPipeline([]))
            guarded["simple"]("test")  # Error occurs when calling, not when wrapping
    
    def test_pipeline_factory_required(self):
        """Test that pipeline_factory is required."""
        def simple_tool(x: str) -> str:
            return x
        
        tools = {"simple": simple_tool}
        clock = FixedClock("2026-01-01T00:00:00Z")
        
        # Should raise when no pipeline_factory provided (when calling the wrapped tool)
        with pytest.raises(NotImplementedError, match="pipeline_factory must be explicitly provided"):
            guarded = guard_tools(tools, clock=clock)
            guarded["simple"]("test")  # Error occurs when calling, not when wrapping


class MockProxyPipeline:
    """Mock ProxyPipeline for testing."""
    
    def __init__(self, call_tracker: list):
        self.call_tracker = call_tracker
    
    def execute(self, intent: ActionIntent) -> ExecutorResult:
        """Mock execution that records the intent and returns deterministic result."""
        self.call_tracker.append(intent)
        
        # Return deterministic result based on tool name
        tool_name = intent.action_type.replace("tool.", "")
        output_data = {"mock_output": f"{tool_name}_result"}
        
        return ExecutorResult(
            success=True,
            output=output_data,
            error=None
        )


class MockPolicyDecisionPoint(PolicyDecisionPoint):
    """Mock PDP for testing."""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale="Mock allow for testing",
            policy_version="test-1.0"
        )


class MockSafetyGate(SafetyGate):
    """Mock SafetyGate for testing."""
    
    def evaluate(self, intent: ActionIntent, policy_decision: PolicyDecision) -> SafetyVerdict:
        return SafetyVerdict(
            verdict="allow",
            rationale="Mock safety allow",
            rule_ids=[]
        )


class MockExecutor(ExecutorPlugin):
    """Mock executor for testing."""
    
    def name(self) -> str:
        return "mock-executor"
    
    def capabilities(self) -> Dict[str, Any]:
        return {
            "executor_name": "mock-executor",
            "version": "1.0.0",
            "capabilities": ["tool.*"],
            "constraints": {}
        }
    
    def execute(self, intent: ActionIntent) -> ExecutorResult:
        tool_name = intent.action_type.replace("tool.", "")
        output_data = {"mock_output": f"{tool_name}_result"}
        
        return ExecutorResult(
            success=True,
            output=output_data,
            error=None
        )
