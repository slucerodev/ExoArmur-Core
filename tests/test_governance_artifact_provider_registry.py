"""
Tests for governance artifact provider registry.

Tests Core-side discovery of optional governance artifact providers
from ExoArmur-GovernanceModules via Python entry points.
"""

import sys
from unittest.mock import Mock, patch

from exoarmur.governance_artifacts.provider_registry import (
    ENTRY_POINT_GROUP,
    GovernanceProviderInfo,
    discover_governance_artifact_providers,
    get_governance_provider_summary,
)


class TestGovernanceProviderDiscovery:
    """Tests for governance artifact provider discovery."""

    def test_missing_governance_modules_returns_empty_result(self):
        """Missing GovernanceModules package returns empty discovery result."""
        # Mock entry_points to raise exception (group not found)
        with patch("importlib.metadata.entry_points", side_effect=Exception("Group not found")):
            result = discover_governance_artifact_providers(load=False)

            assert result.entry_point_group == ENTRY_POINT_GROUP
            assert result.providers == {}
            assert result.unavailable == {}
            assert result.total_discovered == 0

    def test_discovery_does_not_import_governance_modules_when_load_false(self):
        """Discovery does not import exoarmur_governance_modules when load=False."""
        # Track imports before discovery
        modules_before = set(sys.modules.keys())

        # Mock entry points to simulate GovernanceModules being available
        mock_ep = Mock()
        mock_ep.name = "policy_snapshot"
        mock_ep.module = "exoarmur_governance_modules.providers.policy_snapshot"
        mock_ep.version = "0.1.0"

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            result = discover_governance_artifact_providers(load=False)

            modules_after = set(sys.modules.keys())
            new_modules = modules_after - modules_before

            # Should not have imported exoarmur_governance_modules
            for module in new_modules:
                assert not module.startswith("exoarmur_governance_modules")

            assert result.total_discovered == 1
            assert "policy_snapshot" in result.providers

    def test_discovery_sorts_provider_names_deterministically(self):
        """Discovery sorts provider names deterministically."""
        # Mock entry points with unsorted names
        mock_eps = []
        for name, module in [
            ("compliance_export", "module1"),
            ("policy_snapshot", "module2"),
            ("approval_ceremony", "module3"),
        ]:
            mock_ep = Mock()
            mock_ep.name = name
            mock_ep.module = module
            mock_ep.version = "0.1.0"
            # Make mock sortable by name
            mock_ep.__lt__ = lambda self, other: self.name < other.name
            mock_eps.append(mock_ep)

        with patch("importlib.metadata.entry_points", return_value=mock_eps):
            result = discover_governance_artifact_providers(load=False)

            # Check that providers are sorted by name
            provider_names = list(result.providers.keys())
            assert provider_names == ["approval_ceremony", "compliance_export", "policy_snapshot"]

    def test_mocked_entry_points_produce_deterministic_provider_info(self):
        """Mocked entry points produce deterministic ProviderInfo."""
        mock_ep = Mock()
        mock_ep.name = "test_provider"
        mock_ep.module = "test.module"
        mock_ep.version = "1.0.0"

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            result = discover_governance_artifact_providers(load=False)

            assert "test_provider" in result.providers
            info = result.providers["test_provider"]
            assert isinstance(info, GovernanceProviderInfo)
            assert info.name == "test_provider"
            assert info.artifact_type == "test_provider"  # Default to name when not loaded
            assert info.schema_versions == ()
            assert info.provider_version == "1.0.0"
            assert info.entry_point_group == ENTRY_POINT_GROUP
            assert info.module == "test.module"
            assert info.loadable is True

    def test_load_true_catches_provider_load_exceptions(self):
        """load=True catches provider load exceptions and records unavailable status."""
        mock_ep = Mock()
        mock_ep.name = "failing_provider"
        mock_ep.module = "failing.module"
        mock_ep.version = "1.0.0"
        mock_ep.load = Mock(side_effect=ImportError("Module not found"))

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            result = discover_governance_artifact_providers(load=True)

            assert result.total_discovered == 0
            assert "failing_provider" in result.unavailable
            assert "ImportError" in result.unavailable["failing_provider"]

    def test_get_governance_provider_summary_returns_json_serializable_data(self):
        """get_governance_provider_summary returns JSON-serializable deterministic data."""
        mock_ep = Mock()
        mock_ep.name = "test_provider"
        mock_ep.module = "test.module"
        mock_ep.version = "1.0.0"

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            summary = get_governance_provider_summary()

            # Check that summary is JSON-serializable (all basic types)
            assert isinstance(summary, dict)
            assert "entry_point_group" in summary
            assert "total_discovered" in summary
            assert "unavailable_count" in summary
            assert "providers" in summary

            # Check provider entry structure
            assert "test_provider" in summary["providers"]
            provider_summary = summary["providers"]["test_provider"]
            assert isinstance(provider_summary["artifact_type"], str)
            assert isinstance(provider_summary["schema_versions"], list)
            assert isinstance(provider_summary["provider_version"], str)
            assert isinstance(provider_summary["module"], str)
            assert isinstance(provider_summary["loadable"], bool)

    def test_no_discovery_happens_at_import_time(self):
        """No discovery happens at import time."""
        # Reload to ensure fresh import
        if "exoarmur.governance_artifacts.provider_registry" in sys.modules:
            del sys.modules["exoarmur.governance_artifacts.provider_registry"]

        # Mock entry_points to track if it was called
        with patch("importlib.metadata.entry_points") as mock_entry_points:
            from exoarmur.governance_artifacts import provider_registry

            # Entry points should not have been called during import
            mock_entry_points.assert_not_called()

            # Discovery should only happen when explicitly called
            provider_registry.discover_governance_artifact_providers(load=False)
            mock_entry_points.assert_called_once_with(group=ENTRY_POINT_GROUP)
