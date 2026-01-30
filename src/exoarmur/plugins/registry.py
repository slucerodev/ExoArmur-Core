"""
Plugin Registry for ExoArmur Core
Discovers and manages module providers via Python entry points
"""

import importlib.metadata
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderInfo:
    """Information about a discovered provider"""
    name: str
    entry_point_group: str
    version: str
    module_name: str
    load_function: Callable
    metadata: Dict[str, Any]


class PluginRegistry:
    """Registry for discovering and loading ExoArmur module providers"""
    
    def __init__(self):
        self._providers: Dict[str, ProviderInfo] = {}
        self._discovery_complete = False
        self._entry_point_groups = [
            "exoarmur.temporal",
            "exoarmur.analyst", 
            "exoarmur.forensics"
        ]
    
    def discover_providers(self) -> None:
        """Discover available providers via entry points (no import side effects)"""
        if self._discovery_complete:
            return
            
        logger.debug("Discovering ExoArmur module providers...")
        
        for group in self._entry_point_groups:
            try:
                entry_points = importlib.metadata.entry_points(group=group)
                for ep in entry_points:
                    provider_info = ProviderInfo(
                        name=ep.name,
                        entry_point_group=group,
                        version=getattr(ep, 'version', 'unknown'),
                        module_name=ep.module,
                        load_function=ep.load,
                        metadata={
                            'dist': getattr(ep, 'dist', None),
                            'group': group
                        }
                    )
                    
                    provider_key = f"{group}.{ep.name}"
                    self._providers[provider_key] = provider_info
                    logger.debug(f"Discovered provider: {provider_key}")
                    
            except Exception as e:
                logger.debug(f"No entry points found for group {group}: {e}")
        
        self._discovery_complete = True
        logger.info(f"Provider discovery complete. Found {len(self._providers)} providers")
    
    def get_provider(self, group: str, name: str) -> Optional[ProviderInfo]:
        """Get specific provider info without loading"""
        self.discover_providers()
        provider_key = f"{group}.{name}"
        return self._providers.get(provider_key)
    
    def get_providers_by_group(self, group: str) -> List[ProviderInfo]:
        """Get all providers for a specific group"""
        self.discover_providers()
        return [p for p in self._providers.values() if p.entry_point_group == group]
    
    def load_provider(self, group: str, name: str) -> Any:
        """Load and instantiate a provider"""
        provider = self.get_provider(group, name)
        if not provider:
            raise ValueError(f"Provider not found: {group}.{name}")
        
        try:
            logger.debug(f"Loading provider: {group}.{name}")
            provider_instance = provider.load_function()
            logger.info(f"Successfully loaded provider: {group}.{name}")
            return provider_instance
        except Exception as e:
            logger.error(f"Failed to load provider {group}.{name}: {e}")
            raise
    
    def list_all_providers(self) -> Dict[str, ProviderInfo]:
        """List all discovered providers"""
        self.discover_providers()
        return self._providers.copy()
    
    def is_provider_available(self, group: str, name: str) -> bool:
        """Check if provider is available without loading"""
        return self.get_provider(group, name) is not None
    
    def get_provider_count(self) -> int:
        """Get total number of discovered providers"""
        if not self._discovery_complete:
            return 0
        self.discover_providers()
        return len(self._providers)
    
    def get_groups_count(self) -> Dict[str, int]:
        """Get provider count by group"""
        if not self._discovery_complete:
            return {}
        self.discover_providers()
        counts = {}
        for group in self._entry_point_groups:
            counts[group] = len(self.get_providers_by_group(group))
        return counts


# Global registry instance
_registry_instance: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PluginRegistry()
    return _registry_instance


@lru_cache(maxsize=1)
def is_temporal_provider_available(name: str = "default") -> bool:
    """Check if temporal provider is available"""
    registry = get_plugin_registry()
    return registry.is_provider_available("exoarmur.temporal", name)


@lru_cache(maxsize=1)
def is_analyst_provider_available(name: str = "default") -> bool:
    """Check if analyst provider is available"""
    registry = get_plugin_registry()
    return registry.is_provider_available("exoarmur.analyst", name)


@lru_cache(maxsize=1)
def is_forensics_provider_available(name: str = "default") -> bool:
    """Check if forensics provider is available"""
    registry = get_plugin_registry()
    return registry.is_provider_available("exoarmur.forensics", name)


def get_provider_summary() -> Dict[str, Any]:
    """Get summary of available providers for diagnostics"""
    registry = get_plugin_registry()
    registry.discover_providers()
    
    summary = {
        'total_providers': registry.get_provider_count(),
        'groups': registry.get_groups_count(),
        'providers': {}
    }
    
    for key, provider in registry.list_all_providers().items():
        summary['providers'][key] = {
            'name': provider.name,
            'group': provider.entry_point_group,
            'version': provider.version,
            'module': provider.module_name
        }
    
    return summary
