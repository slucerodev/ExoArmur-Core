"""
Integration test for PolicyEvaluator in main.py telemetry ingestion
Verifies that the integration works end-to-end without changing behavior
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from exoarmur.safety.policy_evaluator import PolicyEvaluator
from exoarmur.safety.safety_gate import PolicyState
from spec.contracts.models_v1 import TelemetryEventV1


class TestMainPyPolicyEvaluatorIntegration:
    """Test integration of PolicyEvaluator in main.py preserves behavior"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Sample telemetry event
        self.telemetry_event = TelemetryEventV1(
            schema_version="1.0.0",
            event_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            observed_at=datetime.now(),
            received_at=datetime.now(),
            source={
                "kind": "edr",
                "name": "crowdstrike",
                "host": "sensor-01",
                "sensor_id": "sensor-123"
            },
            event_type="process_start",
            severity="medium",
            attributes={
                "process_name": "svchost.exe",
                "process_path": "C:\\Windows\\System32\\svchost.exe",
                "command_line": "svchost.exe -k LocalService"
            },
            entity_refs=None,
            correlation_id="corr-123",
            trace_id="trace-123"
        )
    
    def test_main_py_policy_evaluator_integration_preserves_values(self):
        """Test that main.py integration produces identical policy state values"""
        # This simulates the exact code path in main.py lines 466-473
        policy_evaluator = PolicyEvaluator()
        
        # Evaluate policy state exactly as done in main.py
        policy_state = policy_evaluator.evaluate_policy(
            intent=None,  # Will be created in execution step (as in main.py)
            tenant_id=self.telemetry_event.tenant_id,
            cell_id=self.telemetry_event.cell_id
        )
        
        # Should match exactly the hardcoded values that were in main.py before integration
        expected_policy_state = PolicyState(
            policy_verified=True,  # From main.py line 465 TODO comment
            kill_switch_global=False,  # From main.py line 466 TODO comment
            kill_switch_tenant=False,  # From main.py line 467 TODO comment
            required_approval="none"  # From main.py line 468 TODO comment
        )
        
        assert policy_state.policy_verified == expected_policy_state.policy_verified
        assert policy_state.kill_switch_global == expected_policy_state.kill_switch_global
        assert policy_state.kill_switch_tenant == expected_policy_state.kill_switch_tenant
        assert policy_state.required_approval == expected_policy_state.required_approval
    
    def test_policy_evaluator_safe_fallback_maintains_main_py_behavior(self):
        """Test that PolicyEvaluator fallback preserves main.py behavior on errors"""
        policy_evaluator = PolicyEvaluator()
        
        # Mock the internal evaluation to fail
        with patch.object(policy_evaluator, '_evaluate_policy_internal', side_effect=Exception("Simulated failure")):
            policy_state = policy_evaluator.evaluate_policy(
                intent=None,
                tenant_id=self.telemetry_event.tenant_id,
                cell_id=self.telemetry_event.cell_id
            )
            
            # Should still produce the same values as the original hardcoded approach
            expected_policy_state = PolicyState(
                policy_verified=True,
                kill_switch_global=False,
                kill_switch_tenant=False,
                required_approval="none"
            )
            
            assert policy_state.policy_verified == expected_policy_state.policy_verified
            assert policy_state.kill_switch_global == expected_policy_state.kill_switch_global
            assert policy_state.kill_switch_tenant == expected_policy_state.kill_switch_tenant
            assert policy_state.required_approval == expected_policy_state.required_approval
    
    def test_policy_evaluator_deterministic_in_main_py_context(self):
        """Test that PolicyEvaluator produces deterministic results in main.py context"""
        policy_evaluator = PolicyEvaluator()
        
        results = []
        
        # Simulate multiple telemetry processing calls with same event
        for _ in range(5):
            policy_state = policy_evaluator.evaluate_policy(
                intent=None,
                tenant_id=self.telemetry_event.tenant_id,
                cell_id=self.telemetry_event.cell_id
            )
            results.append(policy_state)
        
        # All results should be identical (deterministic)
        first_result = results[0]
        for result in results[1:]:
            assert result.policy_verified == first_result.policy_verified
            assert result.kill_switch_global == first_result.kill_switch_global
            assert result.kill_switch_tenant == first_result.kill_switch_tenant
            assert result.required_approval == first_result.required_approval
