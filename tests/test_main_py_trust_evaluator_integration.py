"""
Integration test for TrustEvaluator in main.py telemetry ingestion
Verifies that the integration works end-to-end without changing behavior
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from exoarmur.safety.trust_evaluator import TrustEvaluator
from exoarmur.safety.safety_gate import TrustState
from spec.contracts.models_v1 import TelemetryEventV1


class TestMainPyTrustEvaluatorIntegration:
    """Test integration of TrustEvaluator in main.py preserves behavior"""
    
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
    
    def test_main_py_trust_evaluator_integration_preserves_values(self):
        """Test that main.py integration produces identical trust score values"""
        # This simulates the exact code path in main.py lines 475-482
        trust_evaluator = TrustEvaluator()
        
        # Evaluate trust score exactly as done in main.py
        trust_score = trust_evaluator.evaluate_trust(
            event_source=self.telemetry_event.source,
            emitter_id=self.telemetry_event.source.get("sensor_id"),
            tenant_id=self.telemetry_event.tenant_id
        )
        trust_state = TrustState(emitter_trust_score=trust_score)
        
        # Should match exactly the hardcoded value that was in main.py before integration
        expected_trust_score = 0.85  # From main.py line 475 TODO comment
        expected_trust_state = TrustState(emitter_trust_score=expected_trust_score)
        
        assert trust_state.emitter_trust_score == expected_trust_state.emitter_trust_score
        assert trust_score == expected_trust_score
    
    def test_main_py_trust_evaluator_with_missing_sensor_id(self):
        """Test main.py integration when event source lacks sensor_id"""
        # Create event without sensor_id
        event_no_sensor = TelemetryEventV1(
            schema_version="1.0.0",
            event_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            observed_at=datetime.now(),
            received_at=datetime.now(),
            source={
                "kind": "edr",
                "name": "crowdstrike",
                "host": "sensor-01"
                # Missing sensor_id
            },
            event_type="process_start",
            severity="medium",
            attributes={},
            entity_refs=None,
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        trust_evaluator = TrustEvaluator()
        
        # This simulates main.py line 479 where .get("sensor_id") returns None
        trust_score = trust_evaluator.evaluate_trust(
            event_source=event_no_sensor.source,
            emitter_id=event_no_sensor.source.get("sensor_id"),  # Returns None
            tenant_id=event_no_sensor.tenant_id
        )
        
        # Should still produce the same hardcoded value
        assert trust_score == 0.85
    
    def test_trust_evaluator_safe_fallback_maintains_main_py_behavior(self):
        """Test that TrustEvaluator fallback preserves main.py behavior on errors"""
        trust_evaluator = TrustEvaluator()
        
        # Mock the internal evaluation to fail
        with patch.object(trust_evaluator, '_evaluate_trust_internal', side_effect=Exception("Simulated failure")):
            trust_score = trust_evaluator.evaluate_trust(
                event_source=self.telemetry_event.source,
                emitter_id=self.telemetry_event.source.get("sensor_id"),
                tenant_id=self.telemetry_event.tenant_id
            )
            
            # Should still produce the same value as the original hardcoded approach
            assert trust_score == 0.85
    
    def test_trust_evaluator_deterministic_in_main_py_context(self):
        """Test that TrustEvaluator produces deterministic results in main.py context"""
        trust_evaluator = TrustEvaluator()
        
        results = []
        
        # Simulate multiple telemetry processing calls with same event
        for _ in range(100):
            trust_score = trust_evaluator.evaluate_trust(
                event_source=self.telemetry_event.source,
                emitter_id=self.telemetry_event.source.get("sensor_id"),
                tenant_id=self.telemetry_event.tenant_id
            )
            results.append(trust_score)
        
        # All results should be identical (deterministic)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, f"Trust score drift: {first_result} vs {result}"
    
    def test_trust_evaluator_different_event_sources_in_main_py(self):
        """Test TrustEvaluator with different event sources as they would appear in main.py"""
        event_sources = [
            {
                "kind": "edr",
                "name": "crowdstrike",
                "host": "sensor-01",
                "sensor_id": "sensor-123"
            },
            {
                "kind": "siem",
                "name": "sentinel",
                "host": "sensor-02",
                "sensor_id": "sensor-456"
            },
            {
                "kind": "firewall",
                "name": "paloalto",
                "host": "sensor-03"
                # Missing sensor_id
            },
            {}  # Empty event source
        ]
        
        trust_evaluator = TrustEvaluator()
        
        for event_source in event_sources:
            trust_score = trust_evaluator.evaluate_trust(
                event_source=event_source,
                emitter_id=event_source.get("sensor_id"),
                tenant_id="tenant-acme"
            )
            
            # Should always produce the same value regardless of event source
            assert trust_score == 0.85
    
    def test_trust_evaluator_floating_point_precision_preserved(self):
        """Test that floating-point precision is preserved exactly"""
        trust_evaluator = TrustEvaluator()
        
        # Test many iterations to check for any floating-point drift
        for i in range(1000):
            trust_score = trust_evaluator.evaluate_trust(
                event_source=self.telemetry_event.source,
                emitter_id=self.telemetry_event.source.get("sensor_id"),
                tenant_id=self.telemetry_event.tenant_id
            )
            
            # Should always be exactly 0.85 with no floating-point drift
            assert trust_score == 0.85, f"Iteration {i}: {trust_score} != 0.85"
            assert isinstance(trust_score, float)
            assert trust_score == 0.85  # Exact equality test
