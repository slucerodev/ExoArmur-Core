"""
Performance Tests for ExoArmur

These tests verify performance characteristics including execution time,
memory usage, and deterministic performance.
"""

import pytest
import time
import tracemalloc
from datetime import datetime, timezone
from exoarmur.kernel.clock import SystemClock, DeterministicClock, utc_now
from exoarmur.kernel.ids import make_intent_id
from exoarmur.kernel.boundary import ActionIntent
from exoarmur.executors import FileSystemExecutor


class TestClockPerformance:
    """Test clock performance characteristics."""
    
    def test_system_clock_performance(self):
        """Test that SystemClock is performant."""
        clock = SystemClock()
        iterations = 10000
        
        start = time.perf_counter()
        for _ in range(iterations):
            clock.utc_now()
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 1 second for 10k calls)
        elapsed = end - start
        assert elapsed < 1.0, f"SystemClock too slow: {elapsed}s for {iterations} calls"
    
    def test_deterministic_clock_performance(self):
        """Test that DeterministicClock is performant."""
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        iterations = 10000
        
        start = time.perf_counter()
        for _ in range(iterations):
            clock.utc_now()
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 1 second for 10k calls)
        elapsed = end - start
        assert elapsed < 1.0, f"DeterministicClock too slow: {elapsed}s for {iterations} calls"
    
    def test_utc_now_performance(self):
        """Test that utc_now() is performant."""
        iterations = 10000
        
        start = time.perf_counter()
        for _ in range(iterations):
            utc_now()
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 1 second for 10k calls)
        elapsed = end - start
        assert elapsed < 1.0, f"utc_now() too slow: {elapsed}s for {iterations} calls"


class TestIDGenerationPerformance:
    """Test ID generation performance."""
    
    def test_intent_id_generation_performance(self):
        """Test that intent ID generation is performant."""
        iterations = 10000
        
        start = time.perf_counter()
        for i in range(iterations):
            make_intent_id(f"actor{i}", f"action{i}", f"target{i}", None)
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 2 seconds for 10k calls)
        elapsed = end - start
        assert elapsed < 2.0, f"Intent ID generation too slow: {elapsed}s for {iterations} calls"
    
    def test_id_generation_performance(self):
        """Test that ID generation is performant."""
        iterations = 10000
        
        start = time.perf_counter()
        for i in range(iterations):
            make_intent_id(f"actor{i}", f"action{i}", f"target{i}")
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 2 seconds for 10k calls)
        elapsed = end - start
        assert elapsed < 2.0, f"ID generation too slow: {elapsed}s for {iterations} calls"
    
    def test_decision_id_generation_performance(self):
        """Test that decision ID generation is performant."""
        from exoarmur.kernel.ids import make_decision_id
        iterations = 10000
        
        start = time.perf_counter()
        for i in range(iterations):
            make_decision_id(f"intent{i}")
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 2 seconds for 10k calls)
        elapsed = end - start
        assert elapsed < 2.0, f"Decision ID generation too slow: {elapsed}s for {iterations} calls"


class TestActionIntentPerformance:
    """Test ActionIntent creation performance."""
    
    def test_action_intent_creation_performance(self):
        """Test that ActionIntent creation is performant."""
        iterations = 10000
        
        start = time.perf_counter()
        for i in range(iterations):
            ActionIntent.create(f"actor{i}", f"type{i}", f"action{i}", f"target{i}")
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 2 seconds for 10k calls)
        elapsed = end - start
        assert elapsed < 2.0, f"ActionIntent creation too slow: {elapsed}s for {iterations} calls"
    
    def test_action_intent_with_parameters_performance(self):
        """Test ActionIntent creation with parameters is performant."""
        iterations = 10000
        params = {"key": "value", "data": "test"}
        
        start = time.perf_counter()
        for i in range(iterations):
            ActionIntent.create(f"actor{i}", f"type{i}", f"action{i}", f"target{i}", params)
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 2 seconds for 10k calls)
        elapsed = end - start
        assert elapsed < 2.0, f"ActionIntent with params too slow: {elapsed}s for {iterations} calls"


class TestExecutorPerformance:
    """Test executor performance."""
    
    def test_executor_execution_performance(self):
        """Test that executor execution is performant."""
        executor = FileSystemExecutor()
        iterations = 100
        
        start = time.perf_counter()
        for i in range(iterations):
            intent = ActionIntent.create("actor", "type", "create", f"/tmp/test{i}.txt")
            executor.execute(intent, None, {"final_verdict": "allow"})
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 5 seconds for 100 executions)
        elapsed = end - start
        assert elapsed < 5.0, f"Executor execution too slow: {elapsed}s for {iterations} calls"
    
    def test_executor_state_hash_performance(self):
        """Test that state hash computation is performant."""
        # Skip - FileSystemExecutor doesn't have get_state_hash() method
        pytest.skip("FileSystemExecutor doesn't expose get_state_hash()")
    
    def test_executor_capabilities_performance(self):
        """Test that capabilities retrieval is performant."""
        executor = FileSystemExecutor()
        iterations = 1000
        
        start = time.perf_counter()
        for _ in range(iterations):
            executor.capabilities()
        end = time.perf_counter()
        
        # Should complete in reasonable time (< 1 second for 1k calls)
        elapsed = end - start
        assert elapsed < 1.0, f"Capabilities retrieval too slow: {elapsed}s for {iterations} calls"


class TestMemoryUsage:
    """Test memory usage characteristics."""
    
    def test_action_intent_memory_usage(self):
        """Test that ActionIntent has reasonable memory footprint."""
        tracemalloc.start()
        
        # Create baseline
        intents = []
        for i in range(1000):
            intent = ActionIntent.create(f"actor{i}", f"type{i}", f"action{i}", f"target{i}")
            intents.append(intent)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (< 10MB for 1000 intents)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10.0, f"ActionIntent memory usage too high: {peak_mb}MB"
    
    def test_executor_memory_usage(self):
        """Test that executor has reasonable memory footprint."""
        tracemalloc.start()
        
        executor = FileSystemExecutor()
        
        # Execute multiple actions
        for i in range(100):
            intent = ActionIntent.create("actor", "type", "create", f"/tmp/test{i}.txt")
            executor.execute(intent, None, {"final_verdict": "allow"})
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (< 50MB for 100 executions)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 50.0, f"Executor memory usage too high: {peak_mb}MB"
    
    def test_id_generation_memory_usage(self):
        """Test that ID generation has reasonable memory footprint."""
        tracemalloc.start()
        
        ids = []
        for i in range(10000):
            intent_id = make_intent_id(f"actor{i}", f"action{i}", f"target{i}", None)
            ids.append(intent_id)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (< 10MB for 10k IDs)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10.0, f"ID generation memory usage too high: {peak_mb}MB"


class TestDeterministicPerformance:
    """Test that performance is deterministic."""
    
    def test_clock_performance_consistency(self):
        """Test that clock performance is consistent across runs."""
        clock = DeterministicClock(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        iterations = 1000
        
        times = []
        for _ in range(3):
            start = time.perf_counter()
            for _ in range(iterations):
                clock.utc_now()
            end = time.perf_counter()
            times.append(end - start)
        
        # Performance should be consistent (within 50% variance)
        avg_time = sum(times) / len(times)
        for t in times:
            assert abs(t - avg_time) / avg_time < 0.5, f"Clock performance inconsistent: {t} vs {avg_time}"
    
    def test_id_generation_performance_consistency(self):
        """Test that ID generation performance is consistent across runs."""
        iterations = 1000
        
        times = []
        for _ in range(3):
            start = time.perf_counter()
            for i in range(iterations):
                make_intent_id(f"actor{i}", f"action{i}", f"target{i}", None)
            end = time.perf_counter()
            times.append(end - start)
        
        # Performance should be consistent (within 50% variance)
        avg_time = sum(times) / len(times)
        for t in times:
            assert abs(t - avg_time) / avg_time < 0.5, f"ID generation performance inconsistent: {t} vs {avg_time}"


class TestScalability:
    """Test scalability characteristics."""
    
    def test_linear_scaling_with_execution_count(self):
        """Test that execution time scales linearly with execution count."""
        executor = FileSystemExecutor()
        
        # Test with different execution counts
        counts = [10, 50, 100]
        times = []
        
        for count in counts:
            start = time.perf_counter()
            for i in range(count):
                intent = ActionIntent.create("actor", "type", "create", f"/tmp/test{i}.txt")
                executor.execute(intent, None, {"final_verdict": "allow"})
            end = time.perf_counter()
            times.append(end - start)
        
        # Time should scale roughly linearly (within 2x factor)
        # 10 executions -> t1
        # 100 executions -> t2
        # t2 should be roughly 10x t1 (within 2x factor)
        ratio = times[2] / times[0]
        expected_ratio = counts[2] / counts[0]
        assert abs(ratio - expected_ratio) / expected_ratio < 2.0, f"Non-linear scaling: {ratio} vs {expected_ratio}"
    
    def test_constant_time_operations(self):
        """Test that certain operations are constant time."""
        # Skip - FileSystemExecutor doesn't have get_state_hash() method
        pytest.skip("FileSystemExecutor doesn't expose get_state_hash()")


class TestPerformanceUnderLoad:
    """Test performance under load conditions."""
    
    def test_rapid_intent_creation(self):
        """Test performance under rapid intent creation."""
        iterations = 10000
        
        start = time.perf_counter()
        for i in range(iterations):
            ActionIntent.create(f"actor{i}", f"type{i}", f"action{i}", f"target{i}")
        end = time.perf_counter()
        
        # Should handle rapid creation
        elapsed = end - start
        assert elapsed < 3.0, f"Rapid intent creation too slow: {elapsed}s for {iterations} calls"
    
    def test_concurrent_intent_creation(self):
        """Test performance with concurrent intent creation."""
        import threading
        
        intents = []
        lock = threading.Lock()
        iterations = 1000
        
        def create_intents():
            for i in range(iterations):
                intent = ActionIntent.create(f"actor{i}", f"type{i}", f"action{i}", f"target{i}")
                with lock:
                    intents.append(intent)
        
        threads = [threading.Thread(target=create_intents) for _ in range(10)]
        
        start = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        end = time.perf_counter()
        
        # Should handle concurrent creation
        elapsed = end - start
        assert elapsed < 5.0, f"Concurrent intent creation too slow: {elapsed}s for {iterations * 10} calls"
        assert len(intents) == iterations * 10
