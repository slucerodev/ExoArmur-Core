"""
Integration test for EnvironmentMonitor in main.py telemetry ingestion
Verifies strict observational isolation and behavior preservation
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from exoarmur.safety.environment_monitor import (
    EnvironmentMonitor, 
    EnvironmentObservation,
    EnvironmentMonitoringContext
)
from exoarmur.safety.safety_gate import EnvironmentState
from spec.contracts.models_v1 import TelemetryEventV1


class TestMainPyEnvironmentMonitorIntegration:
    """Test integration of EnvironmentMonitor in main.py maintains strict isolation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Sample telemetry event matching main.py context
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
                "process_path": "C:\\Windows\\System32\\svchost.exe"
            },
            entity_refs=None,
            correlation_id="corr-123",
            trace_id="trace-123"
        )
    
    def test_main_py_environment_monitor_integration_preserves_values(self):
        """Test that main.py integration produces identical environment state values"""
        # This simulates the exact code path in main.py lines 486-508
        environment_monitor = EnvironmentMonitor()
        
        # Monitor environment exactly as done in main.py
        environment_observation = environment_monitor.monitor_environment(
            tenant_id=self.telemetry_event.tenant_id,
            cell_id=self.telemetry_event.cell_id,
            correlation_id=self.telemetry_event.correlation_id,
            trace_id=self.telemetry_event.trace_id
        )
        
        # Extract degraded mode state exactly as done in main.py
        degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
        environment_state = EnvironmentState(degraded_mode=degraded_mode)
        
        # Should match exactly the hardcoded value that was in main.py before integration
        expected_degraded_mode = False  # From main.py line 485 TODO comment
        expected_environment_state = EnvironmentState(degraded_mode=expected_degraded_mode)
        
        assert environment_state.degraded_mode == expected_environment_state.degraded_mode
        assert degraded_mode == expected_degraded_mode
    
    def test_main_py_environment_monitor_telemetry_emission(self):
        """Test that main.py telemetry emission works without influencing decisions"""
        environment_monitor = EnvironmentMonitor()
        
        # Get observation and context exactly as in main.py
        environment_observation = environment_monitor.monitor_environment(
            tenant_id=self.telemetry_event.tenant_id,
            cell_id=self.telemetry_event.cell_id,
            correlation_id=self.telemetry_event.correlation_id,
            trace_id=self.telemetry_event.trace_id
        )
        
        monitoring_context = EnvironmentMonitoringContext(
            tenant_id=self.telemetry_event.tenant_id,
            cell_id=self.telemetry_event.cell_id,
            correlation_id=self.telemetry_event.correlation_id,
            trace_id=self.telemetry_event.trace_id,
            timestamp=None
        )
        
        # This should not raise exceptions and should be purely observational
        try:
            environment_monitor.emit_environment_telemetry(environment_observation, monitoring_context)
        except Exception as e:
            pytest.fail(f"Environment telemetry emission should be safe: {e}")
    
    def test_environment_monitor_safe_fallback_maintains_main_py_behavior(self):
        """Test that EnvironmentMonitor fallback preserves main.py behavior on errors"""
        environment_monitor = EnvironmentMonitor()
        
        # Mock the internal monitoring to fail
        with patch.object(environment_monitor, '_monitor_environment_internal', side_effect=Exception("Simulated failure")):
            environment_observation = environment_monitor.monitor_environment(
                tenant_id=self.telemetry_event.tenant_id,
                cell_id=self.telemetry_event.cell_id,
                correlation_id=self.telemetry_event.correlation_id,
                trace_id=self.telemetry_event.trace_id
            )
            
            # Should still produce the same environment state as hardcoded approach
            degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
            environment_state = EnvironmentState(degraded_mode=degraded_mode)
            
            expected_environment_state = EnvironmentState(degraded_mode=False)
            assert environment_state.degraded_mode == expected_environment_state.degraded_mode
    
    def test_environment_monitor_deterministic_in_main_py_context(self):
        """Test that EnvironmentMonitor produces deterministic results in main.py context"""
        environment_monitor = EnvironmentMonitor()
        
        results = []
        
        # Simulate multiple telemetry processing calls with same event
        for _ in range(100):
            environment_observation = environment_monitor.monitor_environment(
                tenant_id=self.telemetry_event.tenant_id,
                cell_id=self.telemetry_event.cell_id,
                correlation_id=self.telemetry_event.correlation_id,
                trace_id=self.telemetry_event.trace_id
            )
            degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
            environment_state = EnvironmentState(degraded_mode=degraded_mode)
            results.append(environment_state)
        
        # All results should be identical (deterministic)
        first_result = results[0]
        for result in results[1:]:
            assert result.degraded_mode == first_result.degraded_mode, f"Environment state drift: {first_result.degraded_mode} vs {result.degraded_mode}"
    
    def test_environment_monitor_different_tenant_cell_contexts_in_main_py(self):
        """Test EnvironmentMonitor with different tenant/cell contexts as they would appear in main.py"""
        contexts = [
            ("tenant-1", "cell-1"),
            ("tenant-2", "cell-2"),
            ("tenant-acme", "cell-okc-01"),
            ("", ""),  # Empty context
        ]
        
        environment_monitor = EnvironmentMonitor()
        
        for tenant_id, cell_id in contexts:
            environment_observation = environment_monitor.monitor_environment(
                tenant_id=tenant_id,
                cell_id=cell_id,
                correlation_id="test-corr",
                trace_id="test-trace"
            )
            degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
            environment_state = EnvironmentState(degraded_mode=degraded_mode)
            
            # Should always produce the same environment state regardless of context
            assert environment_state.degraded_mode == False
    
    def test_environment_monitor_strict_observational_isolation_in_main_py(self):
        """Test that environment monitoring in main.py never influences decision logic"""
        environment_monitor = EnvironmentMonitor()
        
        # Create observations with potentially different data
        observations = []
        for i in range(10):
            observation = environment_monitor.monitor_environment(
                tenant_id=f"tenant-{i}",
                cell_id=f"cell-{i}",
                correlation_id=f"corr-{i}",
                trace_id=f"trace-{i}"
            )
            observations.append(observation)
        
        # All should produce the same degraded mode (False)
        degraded_modes = [environment_monitor.get_degraded_mode_state(obs) for obs in observations]
        
        # CRITICAL: All must be False to preserve current behavior
        assert all(mode == False for mode in degraded_modes), "All degraded modes must be False"
        
        # Environment states should all be identical
        environment_states = [EnvironmentState(degraded_mode=mode) for mode in degraded_modes]
        assert len(set(state.degraded_mode for state in environment_states)) == 1
        assert list(set(state.degraded_mode for state in environment_states))[0] == False
    
    def test_environment_monitor_no_safety_gate_influence(self):
        """Test that environment monitoring in main.py doesn't affect safety gate decisions"""
        from exoarmur.safety.safety_gate import SafetyGate
        from exoarmur.collective_confidence.aggregator import CollectiveState
        from exoarmur.safety.safety_gate import PolicyState, TrustState
        from exoarmur.spec.contracts.models_v1 import LocalDecisionV1
        
        safety_gate = SafetyGate()
        environment_monitor = EnvironmentMonitor()
        
        # Test components
        local_decision = LocalDecisionV1(
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
        
        collective_state = CollectiveState(
            aggregate_score=0.85,
            quorum_count=2,
            conflict_detected=False
        )
        
        policy_state = PolicyState(
            policy_verified=True,
            kill_switch_global=False,
            kill_switch_tenant=False,
            required_approval="none"
        )
        
        trust_state = TrustState(emitter_trust_score=0.85)
        
        # Test with environment monitor
        environment_observation = environment_monitor.monitor_environment(
            tenant_id=self.telemetry_event.tenant_id,
            cell_id=self.telemetry_event.cell_id
        )
        degraded_mode = environment_monitor.get_degraded_mode_state(environment_observation)
        environment_state_monitor = EnvironmentState(degraded_mode=degraded_mode)
        
        # Test with hardcoded environment state
        environment_state_hardcoded = EnvironmentState(degraded_mode=False)
        
        # Both should produce identical safety verdicts
        verdict_monitor = safety_gate.evaluate_safety(
            intent=None,
            local_decision=local_decision,
            collective_state=collective_state,
            policy_state=policy_state,
            trust_state=trust_state,
            environment_state=environment_state_monitor
        )
        
        verdict_hardcoded = safety_gate.evaluate_safety(
            intent=None,
            local_decision=local_decision,
            collective_state=collective_state,
            policy_state=policy_state,
            trust_state=trust_state,
            environment_state=environment_state_hardcoded
        )
        
        # Verdicts should be identical
        assert verdict_monitor.verdict == verdict_hardcoded.verdict
        assert verdict_monitor.rationale == verdict_hardcoded.rationale
        assert verdict_monitor.rule_ids == verdict_hardcoded.rule_ids
