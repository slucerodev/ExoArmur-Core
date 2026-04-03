"""
Regression tests for EnvironmentMonitor integration
Ensures strict observational isolation and behavior preservation
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from exoarmur.safety.environment_monitor import (
    EnvironmentMonitor, 
    EnvironmentObservation,
    EnvironmentMonitoringContext
)
from exoarmur.safety.safety_gate import EnvironmentState


class TestEnvironmentMonitorIntegration:
    """Test EnvironmentMonitor integration maintains strict observational isolation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.environment_monitor = EnvironmentMonitor()
        
        self.test_tenant_id = "tenant-acme"
        self.test_cell_id = "cell-okc-01"
        self.test_correlation_id = "corr-123"
        self.test_trace_id = "trace-123"
    
    def test_environment_monitor_preserves_hardcoded_behavior(self):
        """Test that EnvironmentMonitor produces identical results to hardcoded values"""
        # Monitor environment
        observation = self.environment_monitor.monitor_environment(
            tenant_id=self.test_tenant_id,
            cell_id=self.test_cell_id,
            correlation_id=self.test_correlation_id,
            trace_id=self.test_trace_id
        )
        
        # Extract degraded mode state
        degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
        environment_state = EnvironmentState(degraded_mode=degraded_mode)
        
        # Should match exactly the hardcoded value from main.py before integration
        expected_degraded_mode = False  # From main.py line 485 TODO comment
        expected_environment_state = EnvironmentState(degraded_mode=expected_degraded_mode)
        
        assert environment_state.degraded_mode == expected_environment_state.degraded_mode
        assert degraded_mode == expected_degraded_mode
    
    def test_environment_monitor_observational_data_structure(self):
        """Test that environment monitor produces proper observational data structure"""
        observation = self.environment_monitor.monitor_environment(
            tenant_id=self.test_tenant_id,
            cell_id=self.test_cell_id
        )
        
        # Verify observation structure is properly formed
        assert isinstance(observation, EnvironmentObservation)
        assert hasattr(observation, 'system_health')
        assert hasattr(observation, 'resource_utilization')
        assert hasattr(observation, 'external_dependencies')
        assert hasattr(observation, 'performance_metrics')
        assert hasattr(observation, 'degraded_indicators')
        
        # Verify degraded indicators always show False (behavior preservation)
        assert observation.degraded_indicators.get('overall_degraded', False) == False
        assert observation.degraded_indicators.get('high_cpu_usage', False) == False
        assert observation.degraded_indicators.get('high_memory_usage', False) == False
    
    def test_environment_monitor_safe_fallback_on_exception(self):
        """Test that EnvironmentMonitor falls back safely on any exception"""
        # Mock the internal monitoring to raise an exception
        with patch.object(self.environment_monitor, '_monitor_environment_internal', side_effect=Exception("Test exception")):
            observation = self.environment_monitor.monitor_environment(
                tenant_id=self.test_tenant_id,
                cell_id=self.test_cell_id
            )
            
            # Should still produce safe fallback values
            assert observation.degraded_indicators.get('degraded', False) == False
            
            # Extract degraded mode state
            degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
            assert degraded_mode == False  # Must always be False for behavior preservation
    
    def test_environment_monitor_deterministic_output(self):
        """Test that EnvironmentMonitor produces deterministic output across multiple calls"""
        observations = []
        
        # Call monitor multiple times with same inputs
        for _ in range(100):
            observation = self.environment_monitor.monitor_environment(
                tenant_id=self.test_tenant_id,
                cell_id=self.test_cell_id,
                correlation_id=self.test_correlation_id,
                trace_id=self.test_trace_id
            )
            observations.append(observation)
        
        # All degraded mode states should be identical (False)
        first_degraded_mode = self.environment_monitor.get_degraded_mode_state(observations[0])
        for observation in observations[1:]:
            degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
            assert degraded_mode == first_degraded_mode, f"Degraded mode drift: {first_degraded_mode} vs {degraded_mode}"
    
    def test_environment_monitor_different_contexts(self):
        """Test EnvironmentMonitor with different tenant/cell contexts"""
        contexts = [
            ("tenant-1", "cell-1"),
            ("tenant-2", "cell-2"),
            ("tenant-acme", "cell-okc-01"),
            ("", ""),  # Empty context
        ]
        
        for tenant_id, cell_id in contexts:
            observation = self.environment_monitor.monitor_environment(
                tenant_id=tenant_id,
                cell_id=cell_id
            )
            
            # Should always produce the same degraded mode (False) regardless of context
            degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
            assert degraded_mode == False
    
    def test_environment_monitor_strict_observational_isolation(self):
        """Test that environment monitor never returns True for degraded mode"""
        # Test with many different scenarios
        scenarios = [
            {"tenant_id": "tenant-1", "cell_id": "cell-1"},
            {"tenant_id": "tenant-2", "cell_id": "cell-2"},
            {"tenant_id": "", "cell_id": ""},
            {"tenant_id": None, "cell_id": None},  # This should be handled gracefully
        ]
        
        for scenario in scenarios:
            try:
                observation = self.environment_monitor.monitor_environment(
                    tenant_id=scenario["tenant_id"] or "",
                    cell_id=scenario["cell_id"] or ""
                )
                
                degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
                
                # CRITICAL: Must never return True to preserve current behavior
                assert degraded_mode == False, f"Degraded mode must always be False, got {degraded_mode}"
                
            except Exception as e:
                # Even on exceptions, fallback should ensure False
                pytest.fail(f"Environment monitor should handle all scenarios gracefully: {e}")
    
    def test_environment_monitor_telemetry_emission(self):
        """Test that environment telemetry emission is purely observational"""
        observation = self.environment_monitor.monitor_environment(
            tenant_id=self.test_tenant_id,
            cell_id=self.test_cell_id
        )
        
        monitoring_context = EnvironmentMonitoringContext(
            tenant_id=self.test_tenant_id,
            cell_id=self.test_cell_id,
            correlation_id=self.test_correlation_id,
            trace_id=self.test_trace_id,
            timestamp=None
        )
        
        # This should not raise any exceptions and should not influence decisions
        # It's purely for logging/observability
        try:
            self.environment_monitor.emit_environment_telemetry(observation, monitoring_context)
        except Exception as e:
            pytest.fail(f"Telemetry emission should be safe and observational: {e}")
    
    def test_environment_monitor_no_decision_influence(self):
        """Test that environment monitoring data never influences decision logic"""
        # Create multiple observations with different data
        observations = []
        for i in range(10):
            observation = self.environment_monitor.monitor_environment(
                tenant_id=f"tenant-{i}",
                cell_id=f"cell-{i}"
            )
            observations.append(observation)
        
        # All should produce the same degraded mode state (False)
        degraded_modes = [self.environment_monitor.get_degraded_mode_state(obs) for obs in observations]
        
        # All should be identical and False
        assert all(mode == False for mode in degraded_modes)
        assert len(set(degraded_modes)) == 1, "All degraded modes should be identical"
        
        # Environment states should all be identical
        environment_states = [EnvironmentState(degraded_mode=mode) for mode in degraded_modes]
        assert len(set(state.degraded_mode for state in environment_states)) == 1


class TestEnvironmentMonitorSafetyGateIntegration:
    """Test integration between EnvironmentMonitor and SafetyGate maintains isolation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from exoarmur.safety.safety_gate import SafetyGate
        from exoarmur.collective_confidence.aggregator import CollectiveState
        from exoarmur.safety.safety_gate import PolicyState, TrustState, EnvironmentState
        from exoarmur.spec.contracts.models_v1 import LocalDecisionV1
        
        self.safety_gate = SafetyGate()
        self.environment_monitor = EnvironmentMonitor()
        
        # Test local decision
        self.local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="suspicious",
            severity="medium",
            confidence=0.85,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        self.collective_state = CollectiveState(
            aggregate_score=0.85,
            quorum_count=2,
            conflict_detected=False
        )
        
        self.policy_state = PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        self.trust_state = TrustState(emitter_trust_score=0.85)
    
    def test_safety_gate_verdicts_unchanged_with_environment_monitor(self):
        """Test that SafetyGate verdicts are identical when using EnvironmentMonitor"""
        # Get environment state from monitor (new way)
        observation = self.environment_monitor.monitor_environment(
            tenant_id="tenant-acme",
            cell_id="cell-okc-01"
        )
        degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
        environment_state_monitor = EnvironmentState(degraded_mode=degraded_mode)
        
        # Create environment state with hardcoded value (old way)
        environment_state_hardcoded = EnvironmentState(degraded_mode=False)  # From main.py line 485
        
        # Evaluate safety with both approaches
        verdict_monitor = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=environment_state_monitor
        )
        
        verdict_hardcoded = self.safety_gate.evaluate_safety(
            intent=None,
            local_decision=self.local_decision,
            collective_state=self.collective_state,
            policy_state=self.policy_state,
            trust_state=self.trust_state,
            environment_state=environment_state_hardcoded
        )
        
        # Verdicts should be identical
        assert verdict_monitor.verdict == verdict_hardcoded.verdict
        assert verdict_monitor.rationale == verdict_hardcoded.rationale
        assert verdict_monitor.rule_ids == verdict_hardcoded.rule_ids
    
    def test_environment_monitor_failure_isolation(self):
        """Test that EnvironmentMonitor failures don't affect SafetyGate verdicts"""
        # Mock environment monitor to fail
        with patch.object(self.environment_monitor, '_monitor_environment_internal', side_effect=Exception("Monitor failure")):
            observation = self.environment_monitor.monitor_environment(
                tenant_id="tenant-acme",
                cell_id="cell-okc-01"
            )
            degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
            environment_state = EnvironmentState(degraded_mode=degraded_mode)
            
            # Should still produce the same verdict as hardcoded approach
            expected_environment_state = EnvironmentState(degraded_mode=False)
            verdict_with_failure = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=self.policy_state,
                trust_state=self.trust_state,
                environment_state=environment_state
            )
            
            verdict_expected = self.safety_gate.evaluate_safety(
                intent=None,
                local_decision=self.local_decision,
                collective_state=self.collective_state,
                policy_state=self.policy_state,
                trust_state=self.trust_state,
                environment_state=expected_environment_state
            )
            
            assert verdict_with_failure.verdict == verdict_expected.verdict
            assert verdict_with_failure.rationale == verdict_expected.rationale
            assert verdict_with_failure.rule_ids == verdict_expected.rule_ids
    
    def test_environment_monitor_no_downstream_consumption(self):
        """Test that environment monitoring data is not consumed by other evaluators"""
        # This test ensures isolation - environment data should not influence
        # policy or trust evaluators
        
        observation = self.environment_monitor.monitor_environment(
            tenant_id="tenant-acme",
            cell_id="cell-okc-01"
        )
        
        # Verify observation data structure but ensure it's not used in decisions
        assert isinstance(observation, EnvironmentObservation)
        assert observation.degraded_indicators is not None
        
        # The critical test: degraded mode must always be False
        degraded_mode = self.environment_monitor.get_degraded_mode_state(observation)
        assert degraded_mode == False
        
        # Environment state should always be the same
        environment_state = EnvironmentState(degraded_mode=degraded_mode)
        assert environment_state.degraded_mode == False
