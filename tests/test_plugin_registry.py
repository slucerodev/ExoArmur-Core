"""
Tests for Plugin Registry
Verifies discovery works with zero providers and no import side effects
"""

from unittest.mock import MagicMock, patch

import pytest

from exoarmur.plugins.registry import (
    PluginRegistry,
    get_plugin_registry,
    get_provider_summary,
)


class TestPluginRegistry:
    """Test plugin registry functionality"""
    
    def test_registry_initializes_empty(self):
        """Registry should initialize with no providers"""
        registry = PluginRegistry()
        assert registry.get_provider_count() == 0
        # Before discovery, groups should be empty (not initialized)
        assert registry.get_groups_count() == {}
    
    def test_boot_with_zero_providers(self):
        """Core must boot with zero providers installed"""
        registry = PluginRegistry()
        
        # Mock entry_points to return empty lists
        with patch('importlib.metadata.entry_points') as mock_entry_points:
            mock_entry_points.return_value = []
            
            registry.discover_providers()
            
            assert registry.get_provider_count() == 0
            assert len(registry.list_all_providers()) == 0
            assert registry.get_groups_count() == {
                "exoarmur.temporal": 0,
                "exoarmur.analyst": 0,
                "exoarmur.forensics": 0
            }
    
    def test_no_import_side_effects_during_discovery(self):
        """Discovery should not import provider modules"""
        registry = PluginRegistry()
        
        # Mock entry point but don't allow loading
        mock_ep = MagicMock()
        mock_ep.name = "test_provider"
        mock_ep.module = "test_module"
        mock_ep.load = MagicMock()
        
        with patch('importlib.metadata.entry_points') as mock_entry_points:
            # Mock to return empty list for other groups, one provider for temporal
            def mock_entry_points_side_effect(group):
                if group == "exoarmur.temporal":
                    return [mock_ep]
                else:
                    return []
            
            mock_entry_points.side_effect = mock_entry_points_side_effect
            
            # Discovery should not call load()
            registry.discover_providers()
            
            mock_ep.load.assert_not_called()
            assert registry.get_provider_count() == 1
    
    def test_provider_discovery_and_loading(self):
        """Test provider discovery and loading"""
        registry = PluginRegistry()
        
        # Create a mock provider instance
        mock_provider_instance = MagicMock()
        
        mock_ep = MagicMock()
        mock_ep.name = "test_provider"
        mock_ep.module = "test_module"
        mock_ep.load = MagicMock(return_value=mock_provider_instance)
        
        with patch('importlib.metadata.entry_points') as mock_entry_points:
            # Mock to return empty list for other groups, one provider for temporal
            def mock_entry_points_side_effect(group):
                if group == "exoarmur.temporal":
                    return [mock_ep]
                else:
                    return []
            
            mock_entry_points.side_effect = mock_entry_points_side_effect
            
            # Test discovery
            registry.discover_providers()
            provider = registry.get_provider("exoarmur.temporal", "test_provider")
            
            assert provider is not None
            assert provider.name == "test_provider"
            assert provider.entry_point_group == "exoarmur.temporal"
            
            # Test loading
            loaded_instance = registry.load_provider("exoarmur.temporal", "test_provider")
            assert loaded_instance == mock_provider_instance
            mock_ep.load.assert_called_once()
    
    def test_get_providers_by_group(self):
        """Test getting providers by group"""
        registry = PluginRegistry()
        
        mock_ep1 = MagicMock()
        mock_ep1.name = "provider1"
        mock_ep1.module = "module1"
        mock_ep1.load = MagicMock()
        
        mock_ep2 = MagicMock()
        mock_ep2.name = "provider2"
        mock_ep2.module = "module2"
        mock_ep2.load = MagicMock()
        
        with patch('importlib.metadata.entry_points') as mock_entry_points:
            # Mock different groups
            def mock_entry_points_side_effect(group):
                if group == "exoarmur.temporal":
                    return [mock_ep1]
                elif group == "exoarmur.analyst":
                    return [mock_ep2]
                else:
                    return []
            
            mock_entry_points.side_effect = mock_entry_points_side_effect
            
            registry.discover_providers()
            
            temporal_providers = registry.get_providers_by_group("exoarmur.temporal")
            analyst_providers = registry.get_providers_by_group("exoarmur.analyst")
            
            assert len(temporal_providers) == 1
            assert temporal_providers[0].name == "provider1"
            
            assert len(analyst_providers) == 1
            assert analyst_providers[0].name == "provider2"
    
    def test_provider_not_found_errors(self):
        """Test proper error handling for missing providers"""
        registry = PluginRegistry()
        registry.discover_providers()
        
        # Test get_provider returns None for missing
        provider = registry.get_provider("exoarmur.temporal", "nonexistent")
        assert provider is None
        
        # Test load_provider raises error for missing
        with pytest.raises(ValueError, match="Provider not found"):
            registry.load_provider("exoarmur.temporal", "nonexistent")
    
    def test_global_registry_singleton(self):
        """Test global registry is singleton"""
        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()
        
        assert registry1 is registry2
    
    def test_provider_summary(self):
        """Test provider summary functionality"""
        with patch('exoarmur.plugins.registry.get_plugin_registry') as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get_provider_count.return_value = 2
            mock_registry.get_groups_count.return_value = {"exoarmur.temporal": 1, "exoarmur.analyst": 1}
            mock_registry.list_all_providers.return_value = {
                "exoarmur.temporal.provider1": MagicMock(name="provider1", entry_point_group="exoarmur.temporal", version="1.0.0", module_name="temporal_module"),
                "exoarmur.analyst.provider1": MagicMock(name="provider1", entry_point_group="exoarmur.analyst", version="1.0.0", module_name="analyst_module")
            }
            mock_get_registry.return_value = mock_registry
            
            summary = get_provider_summary()
            
            assert summary['total_providers'] == 2
            assert summary['groups']['exoarmur.temporal'] == 1
            assert summary['groups']['exoarmur.analyst'] == 1
            assert 'exoarmur.temporal.provider1' in summary['providers']
            assert 'exoarmur.analyst.provider1' in summary['providers']
    
    def test_entry_point_discovery_error_handling(self):
        """Test graceful handling of entry point discovery errors"""
        registry = PluginRegistry()
        
        # Mock entry_points to raise exception
        with patch('importlib.metadata.entry_points') as mock_entry_points:
            mock_entry_points.side_effect = Exception("Discovery error")
            
            # Should not raise exception, should handle gracefully
            registry.discover_providers()
            
            # Registry should still be functional
            assert registry.get_provider_count() == 0
            assert registry.is_provider_available("exoarmur.temporal", "any") is False
