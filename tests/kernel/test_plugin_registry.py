"""
Tests for plugin registry.

These tests verify that Core can discover and load plugins without importing vendor SDKs.
"""

import pytest
from exoarmur.kernel.plugin_registry import PluginRegistry, PluginLoadError, PluginDiscoveryError, set_plugin_registry
from exoarmur.kernel.boundary import ExecutorPlugin, ActionIntent, ExecutorResult, TargetValidationResult, ValidationResult


class MockExecutorPlugin(ExecutorPlugin):
    """Mock executor plugin for testing."""
    
    def name(self) -> str:
        return "mock_executor"
    
    def capabilities(self) -> dict:
        return {
            "executor_name": "mock_executor",
            "version": "1.0.0",
            "capabilities": ["mock_operation"],
            "constraints": {},
            "supported_targets": ["mock://"],
            "required_parameters": []
        }
    
    def validate_target(self, intent: ActionIntent) -> TargetValidationResult:
        return TargetValidationResult(
            result=ValidationResult.VALID,
            evidence={"target": intent.target},
            validation_id="mock_validation_id"
        )
    
    def execute(self, intent: ActionIntent, policy_decision, governance_context) -> ExecutorResult:
        return ExecutorResult(
            success=True,
            output={"mock": "result"},
            execution_id="mock_execution_id"
        )
    
    def supports_capability(self, capability: str) -> bool:
        return capability in self.capabilities()["capabilities"]


class InvalidPlugin:
    """Plugin that does not implement ExecutorPlugin."""
    pass


def test_plugin_registry_manual_registration():
    """Test manual plugin registration."""
    registry = PluginRegistry()
    registry.register_plugin("mock", MockExecutorPlugin)
    
    assert "mock" in registry.list_available_plugins()
    
    plugin = registry.load_plugin("mock")
    assert plugin is not None
    assert plugin.name() == "mock_executor"


def test_plugin_registry_load_nonexistent():
    """Test loading non-existent plugin returns None."""
    registry = PluginRegistry()
    registry.register_plugin("mock", MockExecutorPlugin)
    
    plugin = registry.load_plugin("nonexistent")
    assert plugin is None


def test_plugin_registry_get_plugin_info():
    """Test getting plugin info without loading."""
    registry = PluginRegistry()
    registry.register_plugin("mock", MockExecutorPlugin)
    
    info = registry.get_plugin_info("mock")
    assert info is not None
    assert info["name"] == "mock"
    assert isinstance(info["value"], str)  # Value is a string for both entry points and manual registration
    assert "MockExecutorPlugin" in info["value"]


def test_plugin_registry_get_plugin_info_nonexistent():
    """Test getting plugin info for non-existent plugin."""
    registry = PluginRegistry()
    registry.register_plugin("mock", MockExecutorPlugin)
    
    info = registry.get_plugin_info("nonexistent")
    assert info is None


def test_plugin_registry_invalid_plugin():
    """Test that invalid plugin fails to load."""
    registry = PluginRegistry()
    registry.register_plugin("invalid", InvalidPlugin)
    
    with pytest.raises(PluginLoadError):
        registry.load_plugin("invalid")


def test_plugin_registry_caching():
    """Test that plugin instances are cached."""
    registry = PluginRegistry()
    registry.register_plugin("mock", MockExecutorPlugin)
    
    plugin1 = registry.load_plugin("mock")
    plugin2 = registry.load_plugin("mock")
    
    # Should return same instance
    assert plugin1 is plugin2


def test_plugin_registry_global_instance():
    """Test global plugin registry instance."""
    from exoarmur.kernel.plugin_registry import get_plugin_registry, set_plugin_registry
    
    registry1 = get_plugin_registry()
    registry2 = get_plugin_registry()
    
    # Should return same instance
    assert registry1 is registry2
    
    # Test setting global registry
    custom_registry = PluginRegistry()
    set_plugin_registry(custom_registry)
    
    registry3 = get_plugin_registry()
    assert registry3 is custom_registry


def test_plugin_registry_discovery_without_entry_points():
    """Test that discovery fails gracefully without entry points."""
    registry = PluginRegistry()
    
    # In test environment, entry points may not be available
    # This should not crash
    try:
        registry.discover_plugins()
    except PluginDiscoveryError:
        # Expected in environments without entry points
        pass


def test_plugin_executor_plugin_verification():
    """Test that executor plugin verification works."""
    registry = PluginRegistry()
    
    # Valid plugin should pass verification
    assert registry._verify_executor_plugin(MockExecutorPlugin())
    
    # Invalid plugin should fail verification
    assert not registry._verify_executor_plugin(InvalidPlugin())
