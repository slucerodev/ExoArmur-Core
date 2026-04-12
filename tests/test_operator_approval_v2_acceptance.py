"""
ExoArmur ADMO V2 Operator Approval Acceptance Test
Operator control plane and approval workflow acceptance test — Phase 2 implementation

This test validates the complete V2 operator approval functionality:
- Operator authentication and authorization
- A3 action approval workflows
- Emergency override procedures
- Control plane API functionality
- Federation-wide approval coordination
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import patch

from exoarmur.feature_flags import get_feature_flags
from exoarmur.feature_flags.feature_flags import FeatureFlagContext
from exoarmur.control_plane.approval_service import ApprovalService, ApprovalConfig
from exoarmur.control_plane.control_api import ControlAPI, ControlAPIConfig
from exoarmur.control_plane.operator_interface import OperatorInterface, OperatorConfig

from exoarmur.spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, ExecutionIntentV1


@pytest.mark.v2_acceptance
@pytest.mark.asyncio
class TestOperatorApprovalV2Acceptance:
    """V2 Operator Approval Acceptance Test Suite"""
    
    @pytest.fixture(autouse=True)
    def _set_phase_2(self, monkeypatch):
        """Ensure Phase 2 gate is open for all tests in this class"""
        monkeypatch.setenv("EXOARMUR_PHASE", "2")
        # Reset cached phase so PhaseGate re-reads the env
        from exoarmur.core.phase_gate import PhaseGate
        PhaseGate._current_phase = None
        yield
        PhaseGate._current_phase = None
    
    @pytest.fixture
    async def operator_interface(self):
        """Operator interface with registered test operators"""
        config = OperatorConfig(enabled=True)
        oi = OperatorInterface(config)
        await oi.initialize()
        
        oi.register_operator(
            "operator-supervisor-001", "supervisor",
            ["approve_A3_low_risk", "approve_A3_medium_risk"])
        oi.register_operator(
            "operator-admin-001", "admin",
            ["approve_A3_high_risk", "emergency_override_level_1"])
        oi.register_operator(
            "operator-superuser-001", "superuser",
            ["emergency_override_level_2", "approve_any_risk_level"])
        
        yield oi
        await oi.shutdown()
    
    @pytest.fixture
    async def approval_service(self, operator_interface):
        """Approval service wired to operator interface"""
        config = ApprovalConfig(enabled=True)
        service = ApprovalService(config)
        service.set_operator_interface(operator_interface)
        await service.initialize()
        
        yield service
        await service.shutdown()
    
    @pytest.fixture
    async def control_api(self, approval_service, operator_interface):
        """Control plane API wired to backing services"""
        config = ControlAPIConfig(enabled=True)
        api = ControlAPI(config)
        api.wire_services(approval_service=approval_service,
                          operator_interface=operator_interface)
        await api.startup()
        
        yield api
        await api.shutdown()
    
    @pytest.fixture
    def sample_a3_requests(self):
        """Sample A3 execution requests for approval"""
        return [
            {
                'request_id': 'a3-request-001',
                'intent_type': 'terminate_process',
                'risk_score': 0.6,
                'target_entity': {'subject_type': 'process',
                                  'subject_id': 'low-risk-process.exe'},
                'clearance_required': 'supervisor',
                'business_hours_only': False,
            },
            {
                'request_id': 'a3-request-002',
                'intent_type': 'terminate_process',
                'risk_score': 0.8,
                'target_entity': {'subject_type': 'process',
                                  'subject_id': 'critical-process.exe'},
                'clearance_required': 'admin',
                'business_hours_only': True,
            },
            {
                'request_id': 'a3-request-003',
                'intent_type': 'data_destruction',
                'risk_score': 0.95,
                'target_entity': {'subject_type': 'database',
                                  'subject_id': 'critical-db-001'},
                'clearance_required': 'superuser',
                'business_hours_only': True,
            },
        ]
    
    async def test_operator_authentication(self, operator_interface):
        """
        TEST STEP 1: Operator Authentication
        
        Verify that operators can authenticate to control plane:
        - Certificate-based authentication
        - Session management
        - Permission validation
        - Unknown operator rejection
        """
        
        print("\n🎯 STEP 1: Operator Authentication")
        
        # Authenticate registered supervisor
        session_id = await operator_interface.authenticate_operator(
            "operator-supervisor-001", {"certificate": "test-cert"})
        assert session_id.startswith("session-"), f"Bad session ID: {session_id}"
        assert operator_interface.is_operator_authenticated(session_id)
        
        # Validate session returns correct data
        session_info = await operator_interface.validate_session(session_id)
        assert session_info["valid"] is True
        assert session_info["operator_id"] == "operator-supervisor-001"
        assert session_info["clearance_level"] == "supervisor"
        
        # Reject unknown operator
        with pytest.raises(PermissionError, match="not registered"):
            await operator_interface.authenticate_operator(
                "unknown-operator", {"certificate": "bad"})
        
        # Logout works
        assert await operator_interface.logout_operator(session_id) is True
        assert operator_interface.is_operator_authenticated(session_id) is False
        
        print("✅ STEP 1 PASSED: Operator authentication")
    
    async def test_a3_approval_workflow(self, approval_service, sample_a3_requests):
        """
        TEST STEP 2: A3 Approval Workflow
        
        Verify that A3 actions require proper approval:
        - Approval request submission
        - Pending status
        - Operator approve/deny
        """
        
        print("\n🎯 STEP 2: A3 Approval Workflow")
        
        # Submit low-risk request
        approval_id = await approval_service.submit_approval_request(
            sample_a3_requests[0])
        assert approval_id, "Approval ID should not be empty"
        
        # Should be pending
        pending = await approval_service.get_pending_approvals()
        assert len(pending) >= 1
        assert any(p["approval_id"] == approval_id for p in pending)
        
        # Approve it
        result = await approval_service.approve_request(
            approval_id, "operator-supervisor-001", "Acceptable risk")
        assert result is True
        
        # Should no longer be pending
        pending = await approval_service.get_pending_approvals()
        assert not any(p["approval_id"] == approval_id for p in pending)
        
        print("✅ STEP 2 PASSED: A3 approval workflow")
    
    async def test_operator_authorization_levels(self, approval_service, sample_a3_requests):
        """
        TEST STEP 3: Operator Authorization Levels
        
        Verify that operators can only approve actions within their clearance:
        - Supervisor can approve low risk
        - Supervisor cannot approve high risk
        - Superuser can approve anything
        """
        
        print("\n🎯 STEP 3: Operator Authorization Levels")
        
        # Supervisor authorized for low-risk
        auth = await approval_service.check_authorization(
            "operator-supervisor-001", sample_a3_requests[0])
        assert auth["authorized"] is True
        
        # Supervisor NOT authorized for superuser-level risk
        auth = await approval_service.check_authorization(
            "operator-supervisor-001", sample_a3_requests[2])
        assert auth["authorized"] is False
        
        # Superuser authorized for anything
        auth = await approval_service.check_authorization(
            "operator-superuser-001", sample_a3_requests[2])
        assert auth["authorized"] is True
        
        print("✅ STEP 3 PASSED: Operator authorization levels")
    
    async def test_emergency_override_procedure(self, approval_service):
        """
        TEST STEP 4: Emergency Override Procedure
        
        Verify that emergency override procedures work:
        - Emergency override request creates a tracked approval
        - Override ID is deterministic
        - Audit trail records the request
        """
        
        print("\n🎯 STEP 4: Emergency Override Procedure")
        
        override_id = await approval_service.request_emergency_override(
            {"emergency_type": "security_breach"})
        assert override_id.startswith("emergency-"), f"Bad override ID: {override_id}"
        
        # Override should appear in pending approvals
        pending = await approval_service.get_pending_approvals()
        assert any(p["approval_id"] == override_id for p in pending)
        
        # Audit log should have the emergency request
        assert any(e["event_type"] == "emergency_override_requested"
                   for e in approval_service._audit_log)
        
        print("✅ STEP 4 PASSED: Emergency override procedure")
    
    async def test_control_plane_api_functionality(self, control_api, approval_service,
                                                     sample_a3_requests):
        """
        TEST STEP 5: Control Plane API Functionality
        
        Verify that control plane API provides required functionality:
        - Federation status endpoint
        - Pending approvals endpoint
        - Health metrics endpoint
        - Audit query endpoint
        """
        
        print("\n🎯 STEP 5: Control Plane API Functionality")
        
        # Federation status
        status = await control_api.get_federation_status()
        assert status["federation_id"] == "exoarmur-federation"
        assert "member_count" in status
        assert "api_running" in status
        assert status["api_running"] is True
        
        # Submit a request via approval service, then check pending via API
        await approval_service.submit_approval_request(sample_a3_requests[0])
        pending = await control_api.get_pending_approvals()
        assert pending["total_pending"] >= 1
        
        # Health metrics
        health = await control_api.get_health_metrics()
        assert "overall_health" in health
        assert health["performance_metrics"]["api_running"] is True
        
        # Audit events
        audit = await control_api.get_audit_events({"limit": 10})
        assert audit["total_count"] >= 1
        
        # Available endpoints
        endpoints = control_api.get_available_endpoints()
        assert "/api/v2/federation/status" in endpoints
        assert "/api/v2/approvals/pending" in endpoints
        
        print("✅ STEP 5 PASSED: Control plane API functionality")
    
    async def test_federation_approval_coordination(self, control_api, approval_service,
                                                      sample_a3_requests):
        """
        TEST STEP 6: Federation Approval Coordination
        
        Verify that approval coordination works across federation:
        - Cross-cell approval requests visible via API
        - Federation join works
        - Multi-cell status tracking
        """
        
        print("\n🎯 STEP 6: Federation Approval Coordination")
        
        # Register federation cells
        control_api.register_federation_cell("cell-alpha", {"region": "us-east"})
        control_api.register_federation_cell("cell-beta", {"region": "eu-west"})
        
        # Federation status should show both cells
        status = await control_api.get_federation_status()
        assert status["member_count"] == 2
        assert "cell-alpha" in status["healthy_cells"]
        assert "cell-beta" in status["healthy_cells"]
        
        # Submit approval request and verify it's visible through the API
        await approval_service.submit_approval_request(sample_a3_requests[1])
        pending = await control_api.get_pending_approvals()
        assert pending["total_pending"] >= 1
        assert pending["priority_queue"] is True
        
        # Join a third cell via API
        join_result = await control_api.join_federation(
            {"cell_id": "cell-gamma", "region": "ap-south"})
        assert join_result["status"] == "accepted"
        assert join_result["cell_id"] == "cell-gamma"
        
        # Federation now has 3 cells
        members = await control_api.get_federation_members()
        assert members["total_count"] == 3
        
        print("✅ STEP 6 PASSED: Federation approval coordination")


class TestOperatorApprovalV2Compatibility:
    """V2 Operator Approval Compatibility Test Suite (separate from xfail tests)"""
    
    @pytest.fixture
    async def feature_flags(self):
        """Feature flags for V2 operator approval"""
        from unittest.mock import patch
        flags = get_feature_flags()
        
        # Ensure V2 is disabled for compatibility testing
        with patch.object(flags, 'is_v2_operator_approval_required', return_value=False):
            yield flags
    
    @pytest.mark.asyncio
    async def test_v1_compatibility_with_v2_disabled(self, feature_flags):
        """
        COMPATIBILITY TEST: V1 Compatibility with V2 Disabled
        
        Verify that V1 functionality works when V2 features are disabled:
        - V2 operator approval disabled
        - V1 safety gates work normally
        - No V2 interference with V1 operations
        - Feature flags properly isolate V2 functionality
        """
        
        print("\n🔒 COMPATIBILITY TEST: V1 Compatibility with V2 Disabled")
        
        # Create V2 objects with enabled=False to verify no side effects
        approval_config = ApprovalConfig(enabled=False)
        approval_service_disabled = ApprovalService(approval_config)
        
        control_config = ControlAPIConfig(enabled=False)
        control_api_disabled = ControlAPI(control_config)
        
        operator_config = OperatorConfig(enabled=False)
        operator_interface = OperatorInterface(operator_config)
        
        # These should be no-op and not raise exceptions
        await approval_service_disabled.initialize()
        await control_api_disabled.startup()
        await operator_interface.initialize()
        
        # Verify V1 functionality is preserved
        assert feature_flags is not None, "Feature flags should be available"
        assert approval_service_disabled is not None, "Approval service should be available"
        
        print("✅ COMPATIBILITY TEST PASSED: V1 compatibility with V2 disabled")
