"""
Regression tests for V2 Entry Gate Telemetry Handler
Ensures strict observational behavior with zero influence on execution
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from exoarmur.telemetry.v2_telemetry_handler import (
    V2TelemetryHandler, V2TelemetryEvent, TelemetrySink, LogTelemetrySink, 
    MemoryTelemetrySink, AsyncFileTelemetrySink, get_v2_telemetry_handler,
    configure_v2_telemetry
)


class TestV2TelemetryHandler:
    """Test V2 telemetry handler with strict observational behavior"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.memory_sink = MemoryTelemetrySink()
        self.handler = V2TelemetryHandler(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=False
        )
    
    def teardown_method(self):
        """Cleanup after tests"""
        if self.handler:
            self.handler.close()
    
    def test_telemetry_event_creation(self):
        """Test V2 telemetry event creation and serialization"""
        now = datetime.now(timezone.utc)
        event = V2TelemetryEvent(
            event_id="test_event_123",
            timestamp=now,
            correlation_id="corr-123",
            trace_id="trace-123",
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec-123",
            feature_flags={"v2_federation_enabled": True, "v2_temporal_enabled": False},
            routing_decision="v2_governance_active",
            routing_context={"module_id": "test_module", "execution_id": "exec-123"},
            entry_timestamp=now,
            processing_start=now,
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        # Test serialization
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "test_event_123"
        assert event_dict["correlation_id"] == "corr-123"
        assert event_dict["entry_path"] == "v2_wrapped"
        assert event_dict["feature_flags"]["v2_federation_enabled"] is True
        assert event_dict["feature_flags"]["v2_temporal_enabled"] is False
        assert event_dict["v2_governance_active"] is True
        assert event_dict["v2_validation_passed"] is True
    
    def test_memory_telemetry_sink(self):
        """Test memory telemetry sink functionality"""
        sink = MemoryTelemetrySink(max_events=3)
        
        now = datetime.now(timezone.utc)
        event1 = V2TelemetryEvent(
            event_id="event1", timestamp=now, correlation_id="corr1",
            trace_id="trace1", entry_path="v2_wrapped", module_id="mod1",
            execution_id="exec1", feature_flags={}, routing_decision="test",
            routing_context={}, entry_timestamp=now, processing_start=now,
            v2_governance_active=True, v2_validation_passed=True
        )
        
        event2 = V2TelemetryEvent(
            event_id="event2", timestamp=now, correlation_id="corr2",
            trace_id="trace2", entry_path="v2_wrapped", module_id="mod2",
            execution_id="exec2", feature_flags={}, routing_decision="test",
            routing_context={}, entry_timestamp=now, processing_start=now,
            v2_governance_active=True, v2_validation_passed=True
        )
        
        # Test emission
        assert sink.emit(event1) is True
        assert sink.emit(event2) is True
        
        # Test retrieval
        events = sink.get_events()
        assert len(events) == 2
        assert events[0].event_id == "event1"
        assert events[1].event_id == "event2"
        
        # Test limit enforcement
        event3 = V2TelemetryEvent(
            event_id="event3", timestamp=now, correlation_id="corr3",
            trace_id="trace3", entry_path="v2_wrapped", module_id="mod3",
            execution_id="exec3", feature_flags={}, routing_decision="test",
            routing_context={}, entry_timestamp=now, processing_start=now,
            v2_governance_active=True, v2_validation_passed=True
        )
        event4 = V2TelemetryEvent(
            event_id="event4", timestamp=now, correlation_id="corr4",
            trace_id="trace4", entry_path="v2_wrapped", module_id="mod4",
            execution_id="exec4", feature_flags={}, routing_decision="test",
            routing_context={}, entry_timestamp=now, processing_start=now,
            v2_governance_active=True, v2_validation_passed=True
        )
        
        assert sink.emit(event3) is True
        assert sink.emit(event4) is True  # Should evict event1
        
        events = sink.get_events()
        assert len(events) == 3  # Max events enforced
        assert events[0].event_id == "event2"  # event1 evicted
        assert events[1].event_id == "event3"
        assert events[2].event_id == "event4"
        
        # Test clear
        sink.clear()
        assert len(sink.get_events()) == 0
    
    def test_log_telemetry_sink(self):
        """Test log telemetry sink functionality"""
        sink = LogTelemetrySink("test_telemetry")
        
        now = datetime.now(timezone.utc)
        event = V2TelemetryEvent(
            event_id="log_test", timestamp=now, correlation_id="corr-log",
            trace_id="trace-log", entry_path="v2_wrapped", module_id="mod-log",
            execution_id="exec-log", feature_flags={}, routing_decision="test",
            routing_context={}, entry_timestamp=now, processing_start=now,
            v2_governance_active=True, v2_validation_passed=True
        )
        
        # Test emission (should not raise exception)
        result = sink.emit(event)
        assert result is True
    
    def test_telemetry_handler_disabled(self):
        """Test telemetry handler when disabled"""
        handler = V2TelemetryHandler(sinks=[self.memory_sink], enabled=False)
        
        # Capture should return None when disabled
        event_id = handler.capture_entry_observation(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            feature_flags={"v2_federation_enabled": True},
            routing_decision="test",
            routing_context={},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        assert event_id is None
        
        # Exit capture should return False when disabled
        result = handler.capture_exit_observation(
            event_id="test_event",
            success=True,
            result_summary={}
        )
        
        assert result is False
    
    def test_telemetry_handler_entry_capture(self):
        """Test telemetry entry observation capture"""
        event_id = self.handler.capture_entry_observation(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            feature_flags={"v2_federation_enabled": True, "v2_temporal_enabled": False},
            routing_decision="v2_governance_active",
            routing_context={"module_id": "test_module", "execution_id": "exec-123"},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        assert event_id is not None
        assert event_id.startswith("v2_telemetry_")
        assert "test_module" in event_id
        assert "exec-123" in event_id
        
        # Verify event was captured in memory sink
        events = self.memory_sink.get_events()
        assert len(events) == 1
        assert events[0].event_id == event_id
        assert events[0].entry_path == "v2_wrapped"
        assert events[0].module_id == "test_module"
        assert events[0].execution_id == "exec-123"
        assert events[0].correlation_id == "corr-123"
        assert events[0].trace_id == "trace-123"
        assert events[0].feature_flags["v2_federation_enabled"] is True
        assert events[0].feature_flags["v2_temporal_enabled"] is False
        assert events[0].routing_decision == "v2_governance_active"
        assert events[0].v2_governance_active is True
        assert events[0].v2_validation_passed is True
    
    def test_telemetry_handler_exit_capture(self):
        """Test telemetry exit observation capture"""
        # First capture entry
        event_id = self.handler.capture_entry_observation(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            feature_flags={},
            routing_decision="test",
            routing_context={},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        assert event_id is not None
        
        # Capture exit
        result = self.handler.capture_exit_observation(
            event_id=event_id,
            success=True,
            result_summary={"key": "value"},
            processing_duration_ms=150.5
        )
        
        assert result is True
    
    def test_telemetry_handler_failure_tolerance(self):
        """Test that telemetry failures don't affect operation"""
        # Create a sink that always fails
        class FailingSink(TelemetrySink):
            def emit(self, event):
                raise Exception("Sink failure")
        
        failing_handler = V2TelemetryHandler(
            sinks=[FailingSink()],
            enabled=True,
            high_performance_mode=False
        )
        
        # Entry capture should still return event ID (creation succeeds) but not raise exception
        event_id = failing_handler.capture_entry_observation(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            feature_flags={},
            routing_decision="test",
            routing_context={},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        # Event ID should still be created even if emission fails
        assert event_id is not None
        
        # Exit capture should return True when enabled (uses logger which doesn't fail)
        result = failing_handler.capture_exit_observation(
            event_id="test_event",
            success=True,
            result_summary={}
        )
        
        # Exit capture uses logger.info which doesn't fail, so it returns True
        assert result is True
        
        # Test with disabled handler
        disabled_handler = V2TelemetryHandler(
            sinks=[FailingSink()],
            enabled=False,
            high_performance_mode=False
        )
        
        # Exit capture should return False when disabled
        result = disabled_handler.capture_exit_observation(
            event_id="test_event",
            success=True,
            result_summary={}
        )
        
        assert result is False
        
        failing_handler.close()
        disabled_handler.close()
    
    def test_telemetry_handler_high_performance_mode(self):
        """Test high performance mode with async emission"""
        handler = V2TelemetryHandler(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=True
        )
        
        try:
            # Capture multiple events rapidly
            event_ids = []
            for i in range(10):
                event_id = handler.capture_entry_observation(
                    entry_path="v2_wrapped",
                    module_id=f"test_module_{i}",
                    execution_id=f"exec-{i}",
                    correlation_id=f"corr-{i}",
                    trace_id=f"trace-{i}",
                    feature_flags={"flag": i % 2 == 0},
                    routing_decision="test",
                    routing_context={},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
                if event_id:
                    event_ids.append(event_id)
            
            # Wait for async processing
            time.sleep(0.1)
            
            # Verify events were processed
            events = self.memory_sink.get_events()
            assert len(events) == 10
            
            # Verify event IDs match
            captured_ids = [event.event_id for event in events]
            for event_id in event_ids:
                assert event_id in captured_ids
                
        finally:
            handler.close()
    
    def test_global_telemetry_handler(self):
        """Test global telemetry handler singleton"""
        # Get global handler
        handler1 = get_v2_telemetry_handler()
        handler2 = get_v2_telemetry_handler()
        
        # Should be same instance
        assert handler1 is handler2
        
        # Configure new handler
        new_handler = configure_v2_telemetry(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=False
        )
        
        # Global handler should be updated
        handler3 = get_v2_telemetry_handler()
        assert handler3 is new_handler
        assert handler3 is not handler1
        
        new_handler.close()
    
    def test_telemetry_handler_multiple_sinks(self):
        """Test telemetry handler with multiple sinks"""
        sink2 = MemoryTelemetrySink()
        
        handler = V2TelemetryHandler(
            sinks=[self.memory_sink, sink2],
            enabled=True,
            high_performance_mode=False
        )
        
        try:
            event_id = handler.capture_entry_observation(
                entry_path="v2_wrapped",
                module_id="test_module",
                execution_id="exec-123",
                correlation_id="corr-123",
                trace_id="trace-123",
                feature_flags={},
                routing_decision="test",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            
            assert event_id is not None
            
            # Both sinks should have the event
            events1 = self.memory_sink.get_events()
            events2 = sink2.get_events()
            
            assert len(events1) == 1
            assert len(events2) == 1
            assert events1[0].event_id == events2[0].event_id
            
        finally:
            handler.close()
    
    def test_telemetry_handler_thread_safety(self):
        """Test telemetry handler thread safety"""
        handler = V2TelemetryHandler(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=True
        )
        
        try:
            def capture_events(thread_id: int, count: int):
                for i in range(count):
                    handler.capture_entry_observation(
                        entry_path="v2_wrapped",
                        module_id=f"module_{thread_id}_{i}",
                        execution_id=f"exec_{thread_id}_{i}",
                        correlation_id=f"corr_{thread_id}_{i}",
                        trace_id=f"trace_{thread_id}_{i}",
                        feature_flags={"thread": thread_id % 2 == 0},
                        routing_decision="test",
                        routing_context={},
                        v2_governance_active=True,
                        v2_validation_passed=True
                    )
            
            # Run multiple threads
            threads = []
            for thread_id in range(5):
                thread = threading.Thread(target=capture_events, args=(thread_id, 20))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Wait for async processing
            time.sleep(0.2)
            
            # Verify all events were captured
            events = self.memory_sink.get_events()
            assert len(events) == 100  # 5 threads * 20 events each
            
        finally:
            handler.close()
    
    def test_telemetry_handler_zero_execution_impact(self):
        """Test that telemetry has minimal impact on execution performance"""
        # Test with synchronous mode for better performance characteristics
        handler = V2TelemetryHandler(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=False  # Use sync mode for this test
        )
        
        try:
            # Measure time with telemetry enabled (smaller sample for performance test)
            start_time = time.time()
            for i in range(50):  # Reduced sample size
                handler.capture_entry_observation(
                    entry_path="v2_wrapped",
                    module_id="perf_test",
                    execution_id=f"exec-{i}",
                    correlation_id="corr-123",
                    trace_id="trace-123",
                    feature_flags={},
                    routing_decision="test",
                    routing_context={},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
            telemetry_time = time.time() - start_time
            
            # Measure time with telemetry disabled
            disabled_handler = V2TelemetryHandler(
                sinks=[self.memory_sink],
                enabled=False,
                high_performance_mode=False
            )
            
            start_time = time.time()
            for i in range(50):
                disabled_handler.capture_entry_observation(
                    entry_path="v2_wrapped",
                    module_id="perf_test",
                    execution_id=f"exec-{i}",
                    correlation_id="corr-123",
                    trace_id="trace-123",
                    feature_flags={},
                    routing_decision="test",
                    routing_context={},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
            disabled_time = time.time() - start_time
            
            disabled_handler.close()
            
            # Telemetry should have reasonable overhead
            if disabled_time > 0.001:  # Only check ratio if disabled time is measurable
                overhead_ratio = telemetry_time / disabled_time
                assert overhead_ratio < 50.0  # Allow reasonable overhead for sync mode
            else:
                # If disabled time is too small to measure, just ensure telemetry time is reasonable
                assert telemetry_time < 2.0  # Less than 2 seconds for 50 operations
            
        finally:
            handler.close()
    
    def test_async_file_telemetry_sink(self):
        """Test async file telemetry sink"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            sink = AsyncFileTelemetrySink(temp_path, buffer_size=2)
            
            now = datetime.now(timezone.utc)
            event1 = V2TelemetryEvent(
                event_id="file_test1", timestamp=now, correlation_id="corr1",
                trace_id="trace1", entry_path="v2_wrapped", module_id="mod1",
                execution_id="exec1", feature_flags={}, routing_decision="test",
                routing_context={}, entry_timestamp=now, processing_start=now,
                v2_governance_active=True, v2_validation_passed=True
            )
            
            event2 = V2TelemetryEvent(
                event_id="file_test2", timestamp=now, correlation_id="corr2",
                trace_id="trace2", entry_path="v2_wrapped", module_id="mod2",
                execution_id="exec2", feature_flags={}, routing_decision="test",
                routing_context={}, entry_timestamp=now, processing_start=now,
                v2_governance_active=True, v2_validation_passed=True
            )
            
            # Emit events
            assert sink.emit(event1) is True
            assert sink.emit(event2) is True
            
            # Wait for async processing
            time.sleep(0.1)
            
            sink.close()
            
            # Verify file contains events
            with open(temp_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 2
                
                # Parse first event
                import json
                event_data = json.loads(lines[0].strip())
                assert event_data["event_id"] == "file_test1"
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
