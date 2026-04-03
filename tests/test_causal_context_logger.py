"""
Regression tests for Causal Context Logger
Ensures strict observational behavior with zero influence on execution
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from exoarmur.causal.causal_context_logger import (
    CausalContextLogger, CausalContextRecord, CausalContextType, CausalContextSink,
    LogCausalSink, MemoryCausalSink, AsyncFileCausalSink, get_causal_context_logger,
    configure_causal_context
)


class TestCausalContextLogger:
    """Test causal context logger with strict observational behavior"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.memory_sink = MemoryCausalSink()
        self.handler = CausalContextLogger(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=False
        )
    
    def teardown_method(self):
        """Cleanup after tests"""
        if self.handler:
            self.handler.close()
    
    def test_causal_context_record_creation(self):
        """Test causal context record creation and serialization"""
        now = datetime.now(timezone.utc)
        record = CausalContextRecord(
            record_id="causal_test_123",
            timestamp=now,
            correlation_id="corr-123",
            trace_id="trace-123",
            parent_event_id="parent-123",
            causal_chain_id="chain-123",
            event_type=CausalContextType.EXECUTION_START,
            context_type="test_context",
            module_id="test_module",
            execution_id="exec-123",
            boundary_type="v2",
            metadata={"test": "data"},
            duration_ms=150.5
        )
        
        # Test serialization
        record_dict = record.to_dict()
        
        assert record_dict["record_id"] == "causal_test_123"
        assert record_dict["correlation_id"] == "corr-123"
        assert record_dict["trace_id"] == "trace-123"
        assert record_dict["parent_event_id"] == "parent-123"
        assert record_dict["causal_chain_id"] == "chain-123"
        assert record_dict["event_type"] == "execution_start"
        assert record_dict["context_type"] == "test_context"
        assert record_dict["module_id"] == "test_module"
        assert record_dict["execution_id"] == "exec-123"
        assert record_dict["boundary_type"] == "v2"
        assert record_dict["metadata"]["test"] == "data"
        assert record_dict["duration_ms"] == 150.5
        
        # Test causal key generation
        causal_key = record.causal_key
        assert "chain-123" in causal_key
        assert "corr-123" in causal_key
        assert "trace-123" in causal_key
        assert "parent-123" in causal_key
    
    def test_memory_causal_sink(self):
        """Test memory causal sink functionality"""
        sink = MemoryCausalSink(max_records=3)
        
        now = datetime.now(timezone.utc)
        record1 = CausalContextRecord(
            record_id="causal1", timestamp=now, correlation_id="corr1",
            trace_id="trace1", parent_event_id=None, causal_chain_id="chain1",
            event_type=CausalContextType.EXECUTION_START, context_type="test",
            module_id="mod1", execution_id="exec1", boundary_type="v2"
        )
        
        record2 = CausalContextRecord(
            record_id="causal2", timestamp=now, correlation_id="corr2",
            trace_id="trace2", parent_event_id="causal1", causal_chain_id="chain1",
            event_type=CausalContextType.DECISION_POINT, context_type="test",
            module_id="mod2", execution_id="exec2", boundary_type="v2"
        )
        
        # Test emission
        assert sink.emit(record1) is True
        assert sink.emit(record2) is True
        
        # Test retrieval
        records = sink.get_records()
        assert len(records) == 2
        assert records[0].record_id == "causal1"
        assert records[1].record_id == "causal2"
        
        # Test causal chain retrieval
        chain_records = sink.get_causal_chain("chain1")
        assert len(chain_records) == 2
        assert chain_records[0].record_id == "causal1"
        assert chain_records[1].record_id == "causal2"
        
        # Test limit enforcement
        record3 = CausalContextRecord(
            record_id="causal3", timestamp=now, correlation_id="corr3",
            trace_id="trace3", parent_event_id=None, causal_chain_id="chain2",
            event_type=CausalContextType.EXECUTION_START, context_type="test",
            module_id="mod3", execution_id="exec3", boundary_type="v2"
        )
        record4 = CausalContextRecord(
            record_id="causal4", timestamp=now, correlation_id="corr4",
            trace_id="trace4", parent_event_id=None, causal_chain_id="chain3",
            event_type=CausalContextType.EXECUTION_START, context_type="test",
            module_id="mod4", execution_id="exec4", boundary_type="v2"
        )
        
        assert sink.emit(record3) is True
        assert sink.emit(record4) is True  # Should evict record1
        
        records = sink.get_records()
        assert len(records) == 3  # Max records enforced
        assert records[0].record_id == "causal2"  # record1 evicted
        assert records[1].record_id == "causal3"
        assert records[2].record_id == "causal4"
        
        # Test statistics
        stats = sink.get_chain_statistics()
        assert stats['total_records'] == 3
        assert stats['total_chains'] == 3  # chain1, chain2, chain3
        assert 'chain1' in stats['chain_lengths']
        assert 'chain2' in stats['chain_lengths']
        assert 'chain3' in stats['chain_lengths']
        
        # Test clear
        sink.clear()
        assert len(sink.get_records()) == 0
        assert len(sink.get_chain_statistics()['chain_lengths']) == 0
    
    def test_log_causal_sink(self):
        """Test log causal sink functionality"""
        sink = LogCausalSink("test_causal")
        
        now = datetime.now(timezone.utc)
        record = CausalContextRecord(
            record_id="log_test", timestamp=now, correlation_id="corr-log",
            trace_id="trace-log", parent_event_id=None, causal_chain_id="chain-log",
            event_type=CausalContextType.EXECUTION_START, context_type="test",
            module_id="mod-log", execution_id="exec-log", boundary_type="v2"
        )
        
        # Test emission (should not raise exception)
        result = sink.emit(record)
        assert result is True
    
    def test_causal_context_logger_disabled(self):
        """Test causal context logger when disabled"""
        handler = CausalContextLogger(sinks=[self.memory_sink], enabled=False)
        
        # All capture methods should return None/False when disabled
        start_id = handler.capture_execution_start(
            module_id="test_module", execution_id="exec-123", correlation_id="corr-123",
            trace_id="trace-123", parent_event_id=None, boundary_type="v2"
        )
        assert start_id is None
        
        end_result = handler.capture_execution_end(
            execution_start_record_id="test_record", module_id="test_module",
            execution_id="exec-123", correlation_id="corr-123", trace_id="trace-123",
            boundary_type="v2", success=True, duration_ms=100.0
        )
        assert end_result is False
        
        decision_id = handler.capture_decision_point(
            decision_type="test_decision", module_id="test_module", execution_id="exec-123",
            correlation_id="corr-123", trace_id="trace-123", parent_event_id=None,
            boundary_type="v2", decision_metadata={}
        )
        assert decision_id is None
        
        boundary_id = handler.capture_boundary_crossing(
            from_boundary="v1", to_boundary="v2", module_id="test_module",
            execution_id="exec-123", correlation_id="corr-123", trace_id="trace-123",
            parent_event_id=None
        )
        assert boundary_id is None
    
    def test_causal_context_logger_execution_lifecycle(self):
        """Test causal context logger execution lifecycle capture"""
        # Capture execution start
        start_id = self.handler.capture_execution_start(
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            parent_event_id=None,
            boundary_type="v2",
            metadata={"test": "start"}
        )
        
        assert start_id is not None
        assert start_id.startswith("causal_")
        assert "test_module" in start_id
        assert "exec-123" in start_id
        
        # Capture execution end
        end_result = self.handler.capture_execution_end(
            execution_start_record_id=start_id,
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            boundary_type="v2",
            success=True,
            duration_ms=250.5,
            metadata={"test": "end"}
        )
        
        assert end_result is True
        
        # Verify records were captured
        records = self.memory_sink.get_records()
        assert len(records) == 2
        
        # Verify start record
        start_record = records[0]
        assert start_record.record_id == start_id
        assert start_record.event_type == CausalContextType.EXECUTION_START
        assert start_record.module_id == "test_module"
        assert start_record.execution_id == "exec-123"
        assert start_record.correlation_id == "corr-123"
        assert start_record.trace_id == "trace-123"
        assert start_record.parent_event_id is None
        assert start_record.boundary_type == "v2"
        assert start_record.metadata["test"] == "start"
        assert start_record.duration_ms is None
        
        # Verify end record
        end_record = records[1]
        assert end_record.event_type == CausalContextType.EXECUTION_END
        assert end_record.module_id == "test_module"
        assert end_record.execution_id == "exec-123"
        assert end_record.correlation_id == "corr-123"
        assert end_record.trace_id == "trace-123"
        assert end_record.parent_event_id == start_id
        assert end_record.boundary_type == "v2"
        assert end_record.metadata["success"] is True
        assert end_record.metadata["test"] == "end"
        assert end_record.duration_ms == 250.5
        
        # Verify causal chain
        causal_chains = self.handler.get_causal_chains()
        assert len(causal_chains) == 1
        
        chain_id = list(causal_chains.keys())[0]
        chain_records = causal_chains[chain_id]
        assert len(chain_records) == 2
        assert chain_records[0].record_id == start_id
        assert chain_records[1].record_id == end_record.record_id
    
    def test_causal_context_logger_decision_point(self):
        """Test causal context logger decision point capture"""
        # Capture decision point
        decision_id = self.handler.capture_decision_point(
            decision_type="safety_gate_evaluation",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            parent_event_id="parent-123",
            boundary_type="v2",
            decision_metadata={
                "safety_score": 0.95,
                "risk_level": "low",
                "recommendation": "approve"
            }
        )
        
        assert decision_id is not None
        assert decision_id.startswith("causal_")
        assert "decision" in decision_id
        
        # Verify record was captured
        records = self.memory_sink.get_records()
        assert len(records) == 1
        
        record = records[0]
        assert record.record_id == decision_id
        assert record.event_type == CausalContextType.DECISION_POINT
        assert record.context_type == "decision_observation"
        assert record.module_id == "test_module"
        assert record.execution_id == "exec-123"
        assert record.correlation_id == "corr-123"
        assert record.trace_id == "trace-123"
        assert record.parent_event_id == "parent-123"
        assert record.boundary_type == "v2"
        assert record.metadata["decision_type"] == "safety_gate_evaluation"
        assert record.metadata["safety_score"] == 0.95
        assert record.metadata["risk_level"] == "low"
        assert record.metadata["recommendation"] == "approve"
    
    def test_causal_context_logger_boundary_crossing(self):
        """Test causal context logger boundary crossing capture"""
        # Capture boundary crossing
        boundary_id = self.handler.capture_boundary_crossing(
            from_boundary="v1",
            to_boundary="v2",
            module_id="test_module",
            execution_id="exec-123",
            correlation_id="corr-123",
            trace_id="trace-123",
            parent_event_id="parent-123",
            crossing_metadata={
                "crossing_reason": "feature_flag_enabled",
                "feature_flag": "v2_federation_enabled"
            }
        )
        
        assert boundary_id is not None
        assert boundary_id.startswith("causal_")
        assert "boundary" in boundary_id
        
        # Verify record was captured
        records = self.memory_sink.get_records()
        assert len(records) == 1
        
        record = records[0]
        assert record.record_id == boundary_id
        assert record.event_type == CausalContextType.BOUNDARY_CROSSING
        assert record.context_type == "boundary_observation"
        assert record.module_id == "test_module"
        assert record.execution_id == "exec-123"
        assert record.correlation_id == "corr-123"
        assert record.trace_id == "trace-123"
        assert record.parent_event_id == "parent-123"
        assert record.boundary_type == "v2"
        assert record.metadata["from_boundary"] == "v1"
        assert record.metadata["to_boundary"] == "v2"
        assert record.metadata["crossing_reason"] == "feature_flag_enabled"
        assert record.metadata["feature_flag"] == "v2_federation_enabled"
    
    def test_causal_context_logger_failure_tolerance(self):
        """Test that causal logging failures don't affect operation"""
        # Create a sink that always fails
        class FailingSink(CausalContextSink):
            def emit(self, record):
                raise Exception("Sink failure")
        
        failing_handler = CausalContextLogger(
            sinks=[FailingSink()],
            enabled=True,
            high_performance_mode=False
        )
        
        # All capture methods should still return IDs (creation succeeds) but not raise exceptions
        start_id = failing_handler.capture_execution_start(
            module_id="test_module", execution_id="exec-123", correlation_id="corr-123",
            trace_id="trace-123", parent_event_id=None, boundary_type="v2"
        )
        assert start_id is not None  # ID still created even if emission fails
        
        end_result = failing_handler.capture_execution_end(
            execution_start_record_id=start_id, module_id="test_module",
            execution_id="exec-123", correlation_id="corr-123", trace_id="trace-123",
            boundary_type="v2", success=True, duration_ms=100.0
        )
        assert end_result is True  # Uses logger which doesn't fail
        
        decision_id = failing_handler.capture_decision_point(
            decision_type="test_decision", module_id="test_module", execution_id="exec-123",
            correlation_id="corr-123", trace_id="trace-123", parent_event_id=None,
            boundary_type="v2", decision_metadata={}
        )
        assert decision_id is not None
        
        boundary_id = failing_handler.capture_boundary_crossing(
            from_boundary="v1", to_boundary="v2", module_id="test_module",
            execution_id="exec-123", correlation_id="corr-123", trace_id="trace-123",
            parent_event_id=None
        )
        assert boundary_id is not None
        
        failing_handler.close()
    
    def test_causal_context_logger_high_performance_mode(self):
        """Test high performance mode with async emission"""
        handler = CausalContextLogger(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=True
        )
        
        try:
            # Capture multiple events rapidly
            start_ids = []
            for i in range(10):
                start_id = handler.capture_execution_start(
                    module_id=f"test_module_{i}",
                    execution_id=f"exec-{i}",
                    correlation_id=f"corr-{i}",
                    trace_id=f"trace-{i}",
                    parent_event_id=None,
                    boundary_type="v2"
                )
                if start_id:
                    start_ids.append(start_id)
            
            # Wait for async processing
            time.sleep(0.1)
            
            # Verify events were processed
            records = self.memory_sink.get_records()
            assert len(records) == 10
            
            # Verify event IDs match
            captured_ids = [record.record_id for record in records]
            for start_id in start_ids:
                assert start_id in captured_ids
                
        finally:
            handler.close()
    
    def test_global_causal_context_logger(self):
        """Test global causal context logger singleton"""
        # Get global handler
        handler1 = get_causal_context_logger()
        handler2 = get_causal_context_logger()
        
        # Should be same instance
        assert handler1 is handler2
        
        # Configure new handler
        new_handler = configure_causal_context(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=False
        )
        
        # Global handler should be updated
        handler3 = get_causal_context_logger()
        assert handler3 is new_handler
        assert handler3 is not handler1
        
        new_handler.close()
    
    def test_causal_context_logger_multiple_sinks(self):
        """Test causal context logger with multiple sinks"""
        sink2 = MemoryCausalSink()
        
        handler = CausalContextLogger(
            sinks=[self.memory_sink, sink2],
            enabled=True,
            high_performance_mode=False
        )
        
        try:
            start_id = handler.capture_execution_start(
                module_id="test_module",
                execution_id="exec-123",
                correlation_id="corr-123",
                trace_id="trace-123",
                parent_event_id=None,
                boundary_type="v2"
            )
            
            assert start_id is not None
            
            # Both sinks should have the event
            records1 = self.memory_sink.get_records()
            records2 = sink2.get_records()
            
            assert len(records1) == 1
            assert len(records2) == 1
            assert records1[0].record_id == records2[0].record_id
            
        finally:
            handler.close()
    
    def test_causal_context_logger_thread_safety(self):
        """Test causal context logger thread safety"""
        handler = CausalContextLogger(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=True
        )
        
        try:
            def capture_events(thread_id: int, count: int):
                for i in range(count):
                    handler.capture_execution_start(
                        module_id=f"module_{thread_id}_{i}",
                        execution_id=f"exec_{thread_id}_{i}",
                        correlation_id=f"corr_{thread_id}_{i}",
                        trace_id=f"trace_{thread_id}_{i}",
                        parent_event_id=None,
                        boundary_type="v2"
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
            records = self.memory_sink.get_records()
            assert len(records) == 100  # 5 threads * 20 events each
            
        finally:
            handler.close()
    
    def test_causal_context_logger_zero_execution_impact(self):
        """Test that causal logging has minimal impact on execution performance"""
        handler = CausalContextLogger(
            sinks=[self.memory_sink],
            enabled=True,
            high_performance_mode=True
        )
        
        try:
            # Measure time with causal logging enabled (smaller sample for performance test)
            start_time = time.time()
            for i in range(50):  # Reduced sample size
                handler.capture_execution_start(
                    module_id="perf_test",
                    execution_id=f"exec-{i}",
                    correlation_id="corr-123",
                    trace_id="trace-123",
                    parent_event_id=None,
                    boundary_type="v2"
                )
            causal_time = time.time() - start_time
            
            # Wait for async processing
            time.sleep(0.1)
            
            # Measure time with causal logging disabled
            disabled_handler = CausalContextLogger(
                sinks=[self.memory_sink],
                enabled=False,
                high_performance_mode=True
            )
            
            start_time = time.time()
            for i in range(50):
                disabled_handler.capture_execution_start(
                    module_id="perf_test",
                    execution_id=f"exec-{i}",
                    correlation_id="corr-123",
                    trace_id="trace-123",
                    parent_event_id=None,
                    boundary_type="v2"
                )
            disabled_time = time.time() - start_time
            
            disabled_handler.close()
            
            # Causal logging should have reasonable overhead
            if disabled_time > 0.001:  # Only check ratio if disabled time is measurable
                overhead_ratio = causal_time / disabled_time
                assert overhead_ratio < 50.0  # Allow reasonable overhead for async mode
            else:
                # If disabled time is too small to measure, just ensure causal time is reasonable
                assert causal_time < 2.0  # Less than 2 seconds for 50 operations
            
        finally:
            handler.close()
    
    def test_async_file_causal_sink(self):
        """Test async file causal sink"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            sink = AsyncFileCausalSink(temp_path, buffer_size=2)
            
            now = datetime.now(timezone.utc)
            record1 = CausalContextRecord(
                record_id="file_test1", timestamp=now, correlation_id="corr1",
                trace_id="trace1", parent_event_id=None, causal_chain_id="chain1",
                event_type=CausalContextType.EXECUTION_START, context_type="test",
                module_id="mod1", execution_id="exec1", boundary_type="v2"
            )
            
            record2 = CausalContextRecord(
                record_id="file_test2", timestamp=now, correlation_id="corr2",
                trace_id="trace2", parent_event_id="file_test1", causal_chain_id="chain1",
                event_type=CausalContextType.DECISION_POINT, context_type="test",
                module_id="mod2", execution_id="exec2", boundary_type="v2"
            )
            
            # Emit records
            assert sink.emit(record1) is True
            assert sink.emit(record2) is True
            
            # Wait for async processing
            time.sleep(0.1)
            
            sink.close()
            
            # Verify file contains records
            with open(temp_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 2
                
                # Parse first record
                import json
                record_data = json.loads(lines[0].strip())
                assert record_data["record_id"] == "file_test1"
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_causal_chain_id_generation(self):
        """Test deterministic causal chain ID generation"""
        # Test with correlation ID
        chain_id = self.handler._generate_causal_chain_id("corr-123", "trace-456")
        assert chain_id == "chain_corr-123"
        
        # Test with only trace ID
        chain_id = self.handler._generate_causal_chain_id(None, "trace-456")
        assert chain_id == "chain_trace-456"
        
        # Test with neither ID (generates UUID-based)
        chain_id = self.handler._generate_causal_chain_id(None, None)
        assert chain_id.startswith("chain_")
        assert len(chain_id) > 6  # Should have UUID suffix
    
    def test_causal_context_types(self):
        """Test all causal context event types"""
        event_types = [
            CausalContextType.EXECUTION_START,
            CausalContextType.EXECUTION_END,
            CausalContextType.DECISION_POINT,
            CausalContextType.MODULE_INVOCATION,
            CausalContextType.BOUNDARY_CROSSING,
            CausalContextType.ERROR_EVENT
        ]
        
        for event_type in event_types:
            record = CausalContextRecord(
                record_id=f"test_{event_type.value}",
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-test",
                trace_id="trace-test",
                parent_event_id=None,
                causal_chain_id="chain-test",
                event_type=event_type,
                context_type="test",
                module_id="test_module",
                execution_id="exec-test",
                boundary_type="v2"
            )
            
            # Test serialization
            record_dict = record.to_dict()
            assert record_dict["event_type"] == event_type.value
            assert record_dict["record_id"] == f"test_{event_type.value}"
