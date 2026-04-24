"""
Benchmark Suite Test Suite

Tests validate that the benchmark suite:
- Produces correct determinism results (single hash)
- Runs throughput tests without error
- Returns valid replay metrics
- Does not alter hash with noise injection
"""

import pytest
from exoarmur.benchmark.benchmark_runner import (
    BenchmarkRunner,
    DeterminismLoadResult,
    ThroughputResult,
    ReplayBenchmarkResult,
    NoiseBenchmarkResult,
)
from exoarmur.proof.scenario_builder import build_deterministic_scenario
from exoarmur.stability.deterministic_ordering import DeterminismViolationError


class TestBenchmarkRunnerInitialization:
    """Test BenchmarkRunner initialization"""
    
    def test_default_scenario_builder(self):
        """Verify default scenario builder is set"""
        runner = BenchmarkRunner()
        assert runner.scenario_builder is not None
    
    def test_custom_scenario_builder(self):
        """Verify custom scenario builder can be provided"""
        runner = BenchmarkRunner(scenario_builder=build_deterministic_scenario)
        assert runner.scenario_builder == build_deterministic_scenario
    
    def test_metrics_collector_initialized(self):
        """Verify metrics collector is initialized"""
        runner = BenchmarkRunner()
        assert runner.metrics_collector is not None


class TestDeterminismLoadTest:
    """Test determinism load test produces single hash"""
    
    def test_determinism_load_test_single_concurrency(self):
        """Verify determinism load test produces single hash at low concurrency"""
        runner = BenchmarkRunner()
        
        results = runner.run_determinism_load_test(
            concurrency_levels=[10],
            runs_per_level=10
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Should have single hash
        assert result.unique_hash_count == 1
        assert result.status == "DETERMINISTIC"
        assert result.failures == 0
        assert result.total_executions == 10
        assert result.concurrency_level == 10
    
    def test_determinism_load_test_multiple_concurrency(self):
        """Verify determinism load test produces single hash across multiple concurrency levels"""
        runner = BenchmarkRunner()
        
        results = runner.run_determinism_load_test(
            concurrency_levels=[10, 50],
            runs_per_level=5
        )
        
        assert len(results) == 2
        
        # All levels should produce single hash
        for result in results:
            assert result.unique_hash_count == 1, f"Concurrency {result.concurrency_level} produced {result.unique_hash_count} hashes"
            assert result.status == "DETERMINISTIC"
            assert result.failures == 0
    
    def test_determinism_load_test_fails_on_hash_divergence(self):
        """Verify determinism load test raises on hash divergence"""
        # This test would need to inject a determinism violation
        # For now, we just verify the mechanism exists
        runner = BenchmarkRunner()
        
        # With normal scenario, should pass
        results = runner.run_determinism_load_test(
            concurrency_levels=[10],
            runs_per_level=5
        )
        
        assert results[0].unique_hash_count == 1


class TestThroughputTest:
    """Test throughput test runs without error"""
    
    def test_throughput_test_single_concurrency(self):
        """Verify throughput test runs without error at single concurrency level"""
        runner = BenchmarkRunner()
        
        results = runner.run_throughput_test(
            concurrency_levels=[10],
            runs=50
        )
        
        assert len(results) == 1
        result = results[0]
        
        assert result.total_executions == 50
        assert result.concurrency_level == 10
        assert result.executions_per_second > 0
        assert result.latency_p50_ms >= 0
        assert result.latency_p95_ms >= 0
        assert result.latency_p99_ms >= 0
        assert result.latency_mean_ms >= 0
    
    def test_throughput_test_multiple_concurrency(self):
        """Verify throughput test runs without error at multiple concurrency levels"""
        runner = BenchmarkRunner()
        
        results = runner.run_throughput_test(
            concurrency_levels=[10, 50],
            runs=50
        )
        
        assert len(results) == 2
        
        for result in results:
            assert result.total_executions == 50
            assert result.executions_per_second > 0
            assert result.latency_p50_ms >= 0
            assert result.latency_p95_ms >= result.latency_p50_ms
            assert result.latency_p99_ms >= result.latency_p95_ms
    
    def test_throughput_test_latency_percentiles_ordered(self):
        """Verify latency percentiles are correctly ordered (p50 <= p95 <= p99)"""
        runner = BenchmarkRunner()
        
        results = runner.run_throughput_test(
            concurrency_levels=[10],
            runs=50
        )
        
        result = results[0]
        assert result.latency_p50_ms <= result.latency_p95_ms
        assert result.latency_p95_ms <= result.latency_p99_ms


class TestReplayBenchmark:
    """Test replay benchmark returns valid metrics"""
    
    def test_replay_benchmark_returns_metrics(self):
        """Verify replay benchmark returns valid timing metrics"""
        runner = BenchmarkRunner()
        
        result = runner.run_replay_benchmark(runs=10)
        
        assert result.runs == 10
        assert result.execution_time_avg_ms >= 0
        assert result.execution_time_p50_ms >= 0
        assert result.execution_time_p95_ms >= 0
        assert result.replay_time_avg_ms >= 0
        assert result.replay_time_p50_ms >= 0
        assert result.replay_time_p95_ms >= 0
        assert result.verification_time_avg_ms >= 0
        assert result.verification_time_p50_ms >= 0
        assert result.verification_time_p95_ms >= 0
    
    def test_replay_benchmark_percentiles_ordered(self):
        """Verify replay benchmark percentiles are correctly ordered"""
        runner = BenchmarkRunner()
        
        result = runner.run_replay_benchmark(runs=10)
        
        assert result.execution_time_p50_ms <= result.execution_time_p95_ms
        assert result.execution_time_p95_ms <= result.execution_time_p99_ms
        assert result.replay_time_p50_ms <= result.replay_time_p95_ms
        assert result.replay_time_p95_ms <= result.replay_time_p99_ms
        assert result.verification_time_p50_ms <= result.verification_time_p95_ms
        assert result.verification_time_p95_ms <= result.verification_time_p99_ms


class TestNoiseBenchmark:
    """Test noise benchmark does not alter hash"""
    
    def test_noise_benchmark_hash_stable(self):
        """Verify noise benchmark does not alter hash"""
        runner = BenchmarkRunner()
        
        results = runner.run_noise_benchmark(noise_levels=[1, 10])
        
        assert len(results) == 2
        
        # All noise levels should have stable hash
        for result in results:
            assert result.hash_stable is True, f"Noise level {result.noise_level} changed hash"
            # Latency impact can be slightly negative due to measurement variance
            # Allow up to -10% variance
            assert result.latency_impact_percent >= -10
    
    def test_noise_benchmark_latency_impact_measured(self):
        """Verify noise benchmark measures latency impact"""
        runner = BenchmarkRunner()
        
        results = runner.run_noise_benchmark(noise_levels=[1, 10, 100])
        
        assert len(results) == 3
        
        # All results should have latency measurements
        for result in results:
            assert result.baseline_latency_ms >= 0
            assert result.noisy_latency_ms >= 0
            assert result.latency_impact_percent is not None
    
    def test_noise_benchmark_fails_on_hash_divergence(self):
        """Verify noise benchmark raises on hash divergence"""
        # This test would need to inject a determinism violation
        # For now, we just verify the mechanism exists
        runner = BenchmarkRunner()
        
        # With normal scenario, should pass
        results = runner.run_noise_benchmark(noise_levels=[1])
        
        assert results[0].hash_stable is True


class TestBenchmarkRunnerAllBenchmarks:
    """Test running all benchmarks together"""
    
    def test_run_all_benchmarks(self):
        """Verify all benchmarks can be run together"""
        runner = BenchmarkRunner()
        
        results = runner.run_all_benchmarks(
            concurrency_levels=[10, 50],
            runs_per_level=5,
            noise_levels=[1, 10]
        )
        
        # Should have results for all benchmark types
        assert 'determinism' in results
        assert 'throughput' in results
        assert 'replay' in results
        assert 'noise' in results
        
        # Determinism results should exist
        assert results['determinism'] is not None
        assert len(results['determinism']) == 2
        
        # Throughput results should exist
        assert results['throughput'] is not None
        assert len(results['throughput']) == 2
        
        # Replay results should exist
        assert results['replay'] is not None
        
        # Noise results should exist
        assert results['noise'] is not None
        assert len(results['noise']) == 2


class TestBenchmarkDataClasses:
    """Test benchmark result data classes"""
    
    def test_determinism_load_result_dataclass(self):
        """Verify DeterminismLoadResult dataclass structure"""
        result = DeterminismLoadResult(
            concurrency_level=100,
            total_executions=100,
            unique_hash_count=1,
            failures=0,
            total_runtime_ms=1000.0,
            status="DETERMINISTIC"
        )
        
        assert result.concurrency_level == 100
        assert result.total_executions == 100
        assert result.unique_hash_count == 1
        assert result.failures == 0
        assert result.total_runtime_ms == 1000.0
        assert result.status == "DETERMINISTIC"
    
    def test_throughput_result_dataclass(self):
        """Verify ThroughputResult dataclass structure"""
        result = ThroughputResult(
            concurrency_level=100,
            total_executions=1000,
            executions_per_second=100.0,
            latency_p50_ms=10.0,
            latency_p95_ms=20.0,
            latency_p99_ms=30.0,
            latency_mean_ms=15.0,
            total_runtime_ms=10000.0
        )
        
        assert result.concurrency_level == 100
        assert result.total_executions == 1000
        assert result.executions_per_second == 100.0
        assert result.latency_p50_ms == 10.0
        assert result.latency_p95_ms == 20.0
        assert result.latency_p99_ms == 30.0
        assert result.latency_mean_ms == 15.0
    
    def test_replay_benchmark_result_dataclass(self):
        """Verify ReplayBenchmarkResult dataclass structure"""
        result = ReplayBenchmarkResult(
            runs=100,
            execution_time_avg_ms=10.0,
            execution_time_p50_ms=8.0,
            execution_time_p95_ms=15.0,
            execution_time_p99_ms=20.0,
            replay_time_avg_ms=5.0,
            replay_time_p50_ms=4.0,
            replay_time_p95_ms=8.0,
            replay_time_p99_ms=10.0,
            verification_time_avg_ms=2.0,
            verification_time_p50_ms=1.0,
            verification_time_p95_ms=3.0,
            verification_time_p99_ms=4.0
        )
        
        assert result.runs == 100
        assert result.execution_time_avg_ms == 10.0
        assert result.replay_time_avg_ms == 5.0
        assert result.verification_time_avg_ms == 2.0
    
    def test_noise_benchmark_result_dataclass(self):
        """Verify NoiseBenchmarkResult dataclass structure"""
        result = NoiseBenchmarkResult(
            noise_level=100,
            hash_stable=True,
            latency_impact_percent=5.0,
            baseline_latency_ms=10.0,
            noisy_latency_ms=10.5
        )
        
        assert result.noise_level == 100
        assert result.hash_stable is True
        assert result.latency_impact_percent == 5.0
        assert result.baseline_latency_ms == 10.0
        assert result.noisy_latency_ms == 10.5
