"""
Tests for V2 Federation Identity Integration
Test integration between FederationManager and IdentityManager
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.federation_manager import FederationManager, FederationConfig
from federation.federation_identity_manager import FederationIdentityManager


class TestFederationIdentityIntegration:
    """Test integration between FederationManager and IdentityManager"""
    
    @pytest.mark.asyncio
    async def test_federation_manager_respects_phase_gate(self):
        """Test that FederationManager respects Phase Gate for Phase 2 behavior"""
        config = FederationConfig(
            enabled=True,
            cell_id="test-cell-1",
            nats_url="nats://localhost:4222"
        )
        
        manager = FederationManager(config)
        
        # Initialize should fail due to Phase Gate (Phase 1 isolation)
        with pytest.raises(NotImplementedError, match="Phase 2 behavior requires EXOARMUR_PHASE=2"):
            await manager.initialize()
        
        # Identity manager should not exist due to Phase Gate
        identity_manager = manager.get_identity_manager()
        assert identity_manager is None
        
        # Clean up
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_federation_manager_disabled_no_phase_gate(self):
        """Test that disabled FederationManager bypasses Phase Gate"""
        config = FederationConfig(
            enabled=False,  # Disabled
            cell_id="test-cell-1",
            nats_url="nats://localhost:4222"
        )
        
        manager = FederationManager(config)
        
        # Initialize should succeed (no Phase Gate check when disabled)
        await manager.initialize()
        
        # Identity manager should not exist when disabled
        identity_manager = manager.get_identity_manager()
        assert identity_manager is None
        
        # Clean up
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_phase_2_integration_with_phase_gate_mock(self):
        """Test Phase 2 integration when Phase Gate is mocked to allow Phase 2"""
        
        # Mock Phase Gate to allow Phase 2
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
        from core.phase_gate import SystemPhase
        
        # Mock NATS completely to avoid all connection issues
        mock_nats = Mock()
        mock_nc = Mock()
        
        # Make all NATS methods async
        async def mock_connect(url):
            return mock_nc
        
        async def mock_subscribe(subject, cb):
            return Mock()
        
        async def mock_close():
            pass
        
        mock_nats.connect = mock_connect
        mock_nc.subscribe = mock_subscribe
        mock_nc.close = mock_close
        
        # Mock JetStream
        mock_js = Mock()
        mock_nc.jetstream = Mock(return_value=mock_js)
        async def mock_stream_info(name):
            raise Exception("Stream not found")
        mock_js.stream_info = mock_stream_info
        async def mock_add_stream(config):
            pass
        mock_js.add_stream = mock_add_stream
        
        with patch('core.phase_gate.PhaseGate.current_phase', return_value=SystemPhase.PHASE_2):
            with patch('federation.federation_manager.nats', mock_nats):
                # Mock feature flags to return enabled
                mock_flags = {
                    'v2_federation_enabled': {
                        'current_value': True,
                        'description': 'Enable multi-cell federation capabilities'
                    }
                }
                
                with patch('feature_flags.get_feature_flags', return_value=mock_flags):
                    config = FederationConfig(
                        enabled=True,
                        cell_id="test-cell-1",
                        nats_url="nats://localhost:4222"
                    )
                    
                    manager = FederationManager(config)
                    
                    # Initialize should succeed with Phase 2 allowed
                    await manager.initialize()
                    
                    # Identity manager should be created
                    identity_manager = manager.get_identity_manager()
                    assert identity_manager is not None
                    assert isinstance(identity_manager, FederationIdentityManager)
                    
                    # Clean up
                    await manager.shutdown()


class TestFeatureFlagBoundary:
    """Test feature flag boundary enforcement"""
    
    def test_feature_flag_boundary_enforced_at_runtime(self):
        """Test that feature flag boundary is enforced at runtime"""
        config = FederationConfig(enabled=True)
        
        # Create manager with disabled flag
        manager_disabled = FederationIdentityManager(
            feature_flag_checker=lambda: False
        )
        
        # Create manager with enabled flag
        manager_enabled = FederationIdentityManager(
            feature_flag_checker=lambda: True
        )
        
        # Each manager should respect its own flag checker
        assert manager_disabled.get_handshake_status()["enabled"] is False
        assert manager_enabled.get_handshake_status()["enabled"] is True
        
        # Operations should fail appropriately
        result_disabled = manager_disabled.initiate_handshake("cell-1", "cell-2")
        result_enabled = manager_enabled.initiate_handshake("cell-1", "cell-2")
        
        assert result_disabled.success is False
        assert result_enabled.success is True
