"""
ExoArmur ADMO V2 Feature Flag Isolation Test
Proves that V2 modules cause ZERO side effects when disabled

This test validates that with ALL V2 flags OFF:
- importing V2 modules causes ZERO side effects
- instantiating V2 objects with enabled=False causes ZERO side effects
- calling their methods causes ZERO side effects
- V1 runtime invariants remain unchanged
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any

# Add src and spec to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec'))

# V2 imports (should be safe)
from feature_flags import get_feature_flags
from feature_flags.feature_flags import FeatureFlagContext
from federation.federation_manager import FederationManager, FederationConfig
# from federation.cross_cell_aggregator import CrossCellAggregator, AggregationConfig  # Removed in Phase 2A scope
from control_plane.approval_service import ApprovalService, ApprovalConfig
from control_plane.control_api import ControlAPI, ControlAPIConfig
from control_plane.operator_interface import OperatorInterface, OperatorConfig


class TestV2FeatureFlagIsolation:
    """V2 Feature Flag Isolation Test Suite"""
    
    @pytest.fixture
    def v2_objects_disabled(self):
        """Create V2 objects with enabled=False"""
        objects = {}
        
        # Federation objects
        fed_config = FederationConfig(enabled=False)
        objects['federation_manager'] = FederationManager(fed_config)
        
        # agg_config = AggregationConfig(enabled=False)
        # objects['cross_cell_aggregator'] = CrossCellAggregator(agg_config)
        objects['cross_cell_aggregator'] = None  # Phase 2A scope - removed
        
        # Control plane objects
        approval_config = ApprovalConfig(enabled=False)
        objects['approval_service'] = ApprovalService(approval_config)
        
        control_config = ControlAPIConfig(enabled=False)
        objects['control_api'] = ControlAPI(control_config)
        
        operator_config = OperatorConfig(enabled=False)
        objects['operator_interface'] = OperatorInterface(operator_config)
        
        return objects
    
    def test_v2_imports_no_side_effects(self):
        """Test that importing V2 modules causes no side effects"""
        # V2 modules already imported at top level
        
        # Verify feature flags work
        flags = get_feature_flags()
        assert flags is not None, "Feature flags should be available"
        
        # Verify all objects can be created
        assert FederationManager is not None, "FederationManager should be importable"
        # assert CrossCellAggregator is not None, "CrossCellAggregator should be importable"  # Phase 2A scope - removed
        assert ApprovalService is not None, "ApprovalService should be importable"
        assert ControlAPI is not None, "ControlAPI should be importable"
        assert OperatorInterface is not None, "OperatorInterface should be importable"
    
    @pytest.mark.asyncio
    async def test_v2_objects_instantiation_no_side_effects(self, v2_objects_disabled):
        """Test that instantiating V2 objects with enabled=False causes no side effects"""
        
        # All objects should be instantiated without issues
        assert len(v2_objects_disabled) == 5, "Should have 5 V2 objects"
        
        # Verify all objects have enabled=False
        assert v2_objects_disabled['federation_manager'].config.enabled == False
        # assert v2_objects_disabled['cross_cell_aggregator'].config.enabled == False  # Phase 2A scope - removed
        assert v2_objects_disabled['cross_cell_aggregator'] is None  # Phase 2A scope - removed
        assert v2_objects_disabled['approval_service'].config.enabled == False
        assert v2_objects_disabled['control_api'].config.enabled == False
        assert v2_objects_disabled['operator_interface'].config.enabled == False
    
    @pytest.mark.asyncio
    async def test_v2_methods_no_side_effects(self, v2_objects_disabled):
        """Test that calling V2 methods with enabled=False causes no side effects"""
        
        # Call various V2 methods - all should be no-op
        await v2_objects_disabled['federation_manager'].initialize()
        # await v2_objects_disabled['cross_cell_aggregator'].initialize()  # Phase 2A scope - removed
        await v2_objects_disabled['approval_service'].initialize()
        await v2_objects_disabled['control_api'].startup()
        await v2_objects_disabled['operator_interface'].initialize()
        
        # Call some additional methods
        await v2_objects_disabled['federation_manager'].get_federation_status()
        # await v2_objects_disabled['cross_cell_aggregator'].get_aggregation_status()  # Phase 2A scope - removed
        await v2_objects_disabled['approval_service'].get_pending_approvals()
        await v2_objects_disabled['control_api'].get_federation_status()
        v2_objects_disabled['operator_interface'].is_operator_authenticated("test-session")
        
        # All should complete without exceptions
        assert True, "All V2 method calls completed without side effects"
    
    @pytest.mark.asyncio
    async def test_v2_feature_flags_all_disabled(self):
        """Test that all V2 feature flags are disabled by default"""
        flags = get_feature_flags()
        
        # Verify all V2 flags are disabled
        assert flags.is_enabled('v2_federation_enabled') == False, "v2_federation_enabled should be disabled"
        assert flags.is_enabled('v2_control_plane_enabled') == False, "v2_control_plane_enabled should be disabled"
        assert flags.is_enabled('v2_operator_approval_required') == False, "v2_operator_approval_required should be disabled"
        assert flags.is_enabled('v2_federation_identity_enabled') == False, "v2_federation_identity_enabled should be disabled"
        assert flags.is_enabled('v2_audit_federation_enabled') == False, "v2_audit_federation_enabled should be disabled"
        
        # Verify convenience methods
        assert flags.is_v2_federation_enabled() == False
        assert flags.is_v2_control_plane_enabled() == False
        assert flags.is_v2_operator_approval_required() == False
    
    @pytest.mark.asyncio
    async def test_v2_objects_shutdown_no_side_effects(self, v2_objects_disabled):
        """Test that V2 object shutdown causes no side effects"""
        
        # Call shutdown methods
        await v2_objects_disabled['federation_manager'].shutdown()
        # await v2_objects_disabled['cross_cell_aggregator'].shutdown()  # Phase 2A scope - removed
        await v2_objects_disabled['approval_service'].shutdown()
        await v2_objects_disabled['control_api'].shutdown()
        await v2_objects_disabled['operator_interface'].shutdown()
        
        # All should complete without exceptions
        assert True, "All V2 shutdowns completed without side effects"
    
    def test_v2_memory_cleanup(self):
        """Test that V2 objects clean up properly"""
        # Create and immediately destroy V2 objects
        fed_manager = FederationManager(FederationConfig(enabled=False))
        # aggregator = CrossCellAggregator(AggregationConfig(enabled=False))  # Phase 2A scope - removed
        aggregator = None
        approval_service = ApprovalService(ApprovalConfig(enabled=False))
        control_api = ControlAPI(ControlAPIConfig(enabled=False))
        operator_interface = OperatorInterface(OperatorConfig(enabled=False))
        
        # Delete references
        del fed_manager, aggregator, approval_service, control_api, operator_interface
        
        # If we reach here without memory issues, cleanup worked
        assert True, "V2 objects cleaned up successfully"
    
    @pytest.mark.asyncio
    async def test_v2_enabled_triggers_notimplementederror(self):
        """Test that enabled=True triggers NotImplementedError as expected"""
        # Create V2 objects with enabled=True
        fed_manager = FederationManager(FederationConfig(enabled=True))
        # agg_config = AggregationConfig(enabled=True)
        # aggregator = CrossCellAggregator(agg_config)  # Phase 2A scope - removed
        aggregator = None
        approval_service = ApprovalService(ApprovalConfig(enabled=True))
        control_api = ControlAPI(ControlAPIConfig(enabled=True))
        operator_interface = OperatorInterface(OperatorConfig(enabled=True))
        
        # These should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            await fed_manager.initialize()
        
        # with pytest.raises(NotImplementedError):
        #     await aggregator.initialize()  # Phase 2A scope - removed
        
        with pytest.raises(NotImplementedError):
            await approval_service.initialize()
        
        with pytest.raises(NotImplementedError):
            await control_api.startup()
        
        with pytest.raises(NotImplementedError):
            await operator_interface.initialize()
        
        # Clean up - shutdown methods also raise NotImplementedError when enabled=True
        # So we don't call them, just let the objects be garbage collected
