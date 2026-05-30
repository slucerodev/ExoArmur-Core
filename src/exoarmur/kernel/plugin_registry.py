"""
Plugin registry for external executor modules.

Core provides plugin discovery and loading without importing vendor SDKs.
"""

from typing import Dict, Type, Optional, Protocol, Any
from exoarmur.kernel.boundary import ExecutorPlugin, ActionIntent, TargetValidationResult, ExecutorResult

try:
    from importlib.metadata import entry_points
    ENTRY_POINTS_AVAILABLE = True
except ImportError:
    # Python < 3.10
    ENTRY_POINTS_AVAILABLE = False


class PluginLoadError(Exception):
    """Error loading a plugin."""
    pass


class PluginDiscoveryError(Exception):
    """Error discovering plugins."""
    pass


class _ManualPluginEntry:
    """Wrapper for manually registered plugins to mimic entry point interface."""
    
    def __init__(self, plugin_class: Type[ExecutorPlugin], name: str):
        self._plugin_class = plugin_class
        self.name = name
        self.value = f"{plugin_class.__module__}:{plugin_class.__name__}"
        self.group = "manual"
    
    def load(self) -> Type[ExecutorPlugin]:
        """Load the plugin class."""
        return self._plugin_class


class PluginRegistry:
    """Registry for discovering and loading executor plugins."""
    
    ENTRY_POINT_GROUP = "exoarmur.executors"
    
    def __init__(self):
        self._plugins: Dict[str, Any] = {}  # Store entry points, not loaded classes
        self._loaded_instances: Dict[str, ExecutorPlugin] = {}
        self._discovered = False
    
    def discover_plugins(self) -> None:
        """Discover plugins via Python entry points."""
        if not ENTRY_POINTS_AVAILABLE:
            raise PluginDiscoveryError(
                "Entry points not available (Python < 3.10). "
                "Plugins must be registered manually."
            )
        
        try:
            eps = entry_points(group=self.ENTRY_POINT_GROUP)
            for ep in eps:
                self._plugins[ep.name] = ep
        except Exception as e:
            raise PluginDiscoveryError(f"Failed to discover plugins: {e}")
        
        self._discovered = True
    
    def load_plugin(self, name: str) -> Optional[ExecutorPlugin]:
        """
        Load a specific plugin by name.
        
        Args:
            name: Plugin name (e.g., "openai", "anthropic")
        
        Returns:
            ExecutorPlugin instance if found and loadable, None otherwise
        
        Raises:
            PluginLoadError: If plugin fails to load
        """
        if not self._discovered:
            self.discover_plugins()
        
        if name not in self._plugins:
            return None
        
        # Return cached instance if already loaded
        if name in self._loaded_instances:
            return self._loaded_instances[name]
        
        try:
            ep = self._plugins[name]
            plugin_class = ep.load()
            plugin_instance = plugin_class()
            
            # Verify it implements ExecutorPlugin protocol
            if not self._verify_executor_plugin(plugin_instance):
                raise PluginLoadError(
                    f"Plugin '{name}' does not implement ExecutorPlugin protocol"
                )
            
            self._loaded_instances[name] = plugin_instance
            return plugin_instance
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin '{name}': {e}")
    
    def _verify_executor_plugin(self, instance: Any) -> bool:
        """Verify that instance implements ExecutorPlugin protocol."""
        required_methods = ['name', 'capabilities', 'validate_target', 'execute', 'supports_capability']
        for method in required_methods:
            if not hasattr(instance, method) or not callable(getattr(instance, method)):
                return False
        return True
    
    def list_available_plugins(self) -> list[str]:
        """List names of available plugins."""
        if not self._discovered:
            self.discover_plugins()
        
        return list(self._plugins.keys())
    
    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a plugin without loading it.
        
        Args:
            name: Plugin name
        
        Returns:
            Plugin metadata if found, None otherwise
        """
        if not self._discovered:
            self.discover_plugins()
        
        if name not in self._plugins:
            return None
        
        ep = self._plugins[name]
        return {
            "name": ep.name,
            "value": ep.value,
            "group": ep.group
        }
    
    def register_plugin(self, name: str, plugin_class: Type[ExecutorPlugin]) -> None:
        """
        Manually register a plugin (for testing or environments without entry points).
        
        Args:
            name: Plugin name
            plugin_class: ExecutorPlugin class
        """
        self._plugins[name] = _ManualPluginEntry(plugin_class, name)
        self._discovered = True


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def set_plugin_registry(registry: PluginRegistry) -> None:
    """Set global plugin registry instance (for testing)."""
    global _registry
    _registry = registry
