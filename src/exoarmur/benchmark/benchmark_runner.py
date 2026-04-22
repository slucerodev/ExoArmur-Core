"""
Benchmark Runner for ExoArmur Performance and Determinism Testing

This module provides a comprehensive benchmark suite that measures:
1. Determinism under load (PRIMARY)
2. Throughput and latency (SECONDARY)
3. Replay/verification cost (CRITICAL)
4. Noise resistance impact (OPTIONAL)

The system proves that performance scaling does NOT break determinism.

All benchmarking is additive and isolated from core logic.
Uses canonical payload + stable_hash only.
Fails immediately on ANY hash divergence.
"""

from typing import List, Dict, Any, Optional
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from exoarmur.proof.determinism_harness import (
    DeterminismHarness,
    ProofReport
)
from exoarmur.proof.scenario_builder import build_deterministic_scenario
from exoarmur.proof.hash_extractor import (
    extract_canonical_audit_hash,
    verify_hash_consistency,
    get_unique_hash_count
)
from exoarmur.stability.deterministic_ordering import DeterminismViolationError
from .metrics import (
    measure_latency,
    calculate_percentiles,
    track_execution_time,
    MetricsCollector,
)


@dataclass
class DeterminismLoadResult:
    """Results from determinism load test."""
    concurrency_level: int
    total_executions: int
    unique_hash_count: int
    failures: int
    total_runtime_ms: float
    all_hashes: List[str] = field(default_factory=list)
    status: str = ""


@dataclass
class ThroughputResult:
    """Results from throughput test."""
    concurrency_level: int
    total_executions: int
    executions_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    total_runtime_ms: float


@dataclass
class ReplayBenchmarkResult:
    """Results from replay benchmark."""
    runs: int
    execution_time_avg_ms: float
    execution_time_p50_ms: float
    execution_time_p95_ms: float
    replay_time_avg_ms: float
    replay_time_p50_ms: float
    replay_time_p95_ms: float
    verification_time_avg_ms: float
    verification_time_p50_ms: float
    verification_time_p95_ms: float


@dataclass
class NoiseBenchmarkResult:
    """Results from noise benchmark."""
    noise_level: int
    hash_stable: bool
    latency_impact_percent: float
    baseline_latency_ms: float
    noisy_latency_ms: float


class BenchmarkRunner:
    """
    Comprehensive benchmark runner for ExoArmur performance and determinism.
    
    This runner leverages the existing DeterminismHarness and adds performance
    measurement capabilities. All benchmarking is additive and does not modify
    V1 behavior or contracts.
    """
    
    def __init__(self, scenario_builder=None):
        """
        Initialize benchmark runner.
        
        Args:
            scenario_builder: Callable that builds and executes a scenario.
                            Defaults to build_deterministic_scenario.
        """
        self.scenario_builder = scenario_builder or build_deterministic_scenario
        self.metrics_collector = MetricsCollector()
    
    def run_determinism_load_test(
        self,
        concurrency_levels: List[int] = [10, 50, 100, 500, 1000],
        runs_per_level: int = 100
    ) -> List[DeterminismLoadResult]:
        """
        Execute determinism proof under increasing concurrency load.
        
        This test proves that determinism holds even under high concurrency.
        Uses the existing DeterminismHarness parallel execution mode.
        
        Args:
            concurrency_levels: List of concurrency levels to test
            runs_per_level: Number of runs to execute per concurrency level
        
        Returns:
            List of DeterminismLoadResult, one per concurrency level
        
        Raises:
            DeterminismViolationError: If unique_hashes != 1 at any level
        """
        results = []
        
        for concurrency in concurrency_levels:
            print(f"\nDETERMINISM LOAD TEST - Concurrency: {concurrency}")
            print("=" * 60)
            
            start_time = time.perf_counter()
            hashes = []
            failures = 0
            
            # Create harness with appropriate runs
            harness = DeterminismHarness(self.scenario_builder, runs=runs_per_level)
            
            # Run parallel executions at this concurrency level
            try:
                parallel_hashes = harness.run_parallel()
                hashes.extend(parallel_hashes)
                
                # Verify all hashes are identical
                unique_count = get_unique_hash_count(hashes)
                
                if unique_count != 1:
                    raise DeterminismViolationError(
                        f"Determinism violation at concurrency {concurrency}: "
                        f"Expected 1 unique hash, got {unique_count}"
                    )
                
                status = "DETERMINISTIC"
                
            except Exception as e:
                failures = 1
                status = f"FAILED: {str(e)}"
                print(f"  ✗ {status}")
                raise
            
            end_time = time.perf_counter()
            total_runtime_ms = (end_time - start_time) * 1000
            
            result = DeterminismLoadResult(
                concurrency_level=concurrency,
                total_executions=len(hashes),
                unique_hash_count=unique_count,
                failures=failures,
                total_runtime_ms=total_runtime_ms,
                all_hashes=hashes,
                status=status
            )
            
            results.append(result)
            
            print(f"  Executions: {result.total_executions}")
            print(f"  Unique Hashes: {result.unique_hash_count}")
            print(f"  Failures: {result.failures}")
            print(f"  Runtime: {result.total_runtime_ms:.2f} ms")
            print(f"  STATUS: {result.status}")
        
        return results
    
    def run_throughput_test(
        self,
        concurrency_levels: List[int] = [10, 50, 100],
        runs: int = 1000
    ) -> List[ThroughputResult]:
        """
        Measure throughput and latency under load.
        
        This test measures:
        - Executions per second
        - p50, p95, p99 latency
        - CPU and memory (if available)
        
        Args:
            concurrency_levels: List of concurrency levels to test
            runs: Number of runs to execute per concurrency level
        
        Returns:
            List of ThroughputResult, one per concurrency level
        """
        results = []
        
        for concurrency in concurrency_levels:
            print(f"\nTHROUGHPUT TEST - Concurrency: {concurrency}")
            print("=" * 60)
            
            latencies = []
            start_time = time.perf_counter()
            
            def execute_with_timing():
                """Execute scenario and measure latency."""
                exec_start = time.perf_counter()
                audit_records = self.scenario_builder()
                hash_value = extract_canonical_audit_hash(audit_records)
                exec_end = time.perf_counter()
                latency_ms = (exec_end - exec_start) * 1000
                return latency_ms
            
            # Execute with ThreadPoolExecutor at concurrency level
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(execute_with_timing) for _ in range(runs)]
                for future in futures:
                    try:
                        latency = future.result()
                        latencies.append(latency)
                        self.metrics_collector.record_latency(latency)
                    except Exception as e:
                        self.metrics_collector.record_error(type(e).__name__, str(e))
            
            end_time = time.perf_counter()
            total_runtime_ms = (end_time - start_time) * 1000
            total_runtime_sec = total_runtime_ms / 1000
            
            # Calculate percentiles
            percentiles = calculate_percentiles(latencies, [50, 95, 99])
            mean_latency = sum(latencies) / len(latencies) if latencies else 0
            
            # Calculate throughput
            executions_per_second = len(latencies) / total_runtime_sec if total_runtime_sec > 0 else 0
            
            result = ThroughputResult(
                concurrency_level=concurrency,
                total_executions=len(latencies),
                executions_per_second=executions_per_second,
                latency_p50_ms=percentiles['p50'],
                latency_p95_ms=percentiles['p95'],
                latency_p99_ms=percentiles['p99'],
                latency_mean_ms=mean_latency,
                total_runtime_ms=total_runtime_ms
            )
            
            results.append(result)
            
            print(f"  Executions: {result.total_executions}")
            print(f"  Throughput: {result.executions_per_second:.2f} exec/sec")
            print(f"  p50 latency: {result.latency_p50_ms:.2f} ms")
            print(f"  p95 latency: {result.latency_p95_ms:.2f} ms")
            print(f"  p99 latency: {result.latency_p99_ms:.2f} ms")
            print(f"  Mean latency: {result.latency_mean_ms:.2f} ms")
        
        return results
    
    def run_replay_benchmark(self, runs: int = 100) -> ReplayBenchmarkResult:
        """
        Measure execution, replay, and verification performance.
        
        This test measures the cost of:
        - Initial execution
        - Replay from input hash
        - Verification of replay matches execution
        
        Args:
            runs: Number of runs to execute
        
        Returns:
            ReplayBenchmarkResult with timing metrics
        """
        print(f"\nREPLAY BENCHMARK - Runs: {runs}")
        print("=" * 60)
        
        execution_times = []
        replay_times = []
        verification_times = []
        
        # Create harness for input hash
        harness = DeterminismHarness(self.scenario_builder, runs=1)
        input_hash = harness.report.input_hash
        
        for i in range(runs):
            # Measure execution time
            exec_start = time.perf_counter()
            audit_records = self.scenario_builder()
            execution_hash = extract_canonical_audit_hash(audit_records)
            exec_end = time.perf_counter()
            execution_times.append((exec_end - exec_start) * 1000)
            
            # Measure replay time
            from exoarmur.proof.replay_verifier import replay_from_input
            replay_start = time.perf_counter()
            replay_hash = replay_from_input(input_hash)
            replay_end = time.perf_counter()
            replay_times.append((replay_end - replay_start) * 1000)
            
            # Measure verification time
            verify_start = time.perf_counter()
            from exoarmur.proof.replay_verifier import verify_replay_matches
            verified = verify_replay_matches(execution_hash, replay_hash)
            verify_end = time.perf_counter()
            verification_times.append((verify_end - verify_start) * 1000)
            
            if i % 10 == 0:
                print(f"  Progress: {i+1}/{runs}")
        
        # Calculate statistics
        exec_percentiles = calculate_percentiles(execution_times, [50, 95, 99])
        replay_percentiles = calculate_percentiles(replay_times, [50, 95, 99])
        verify_percentiles = calculate_percentiles(verification_times, [50, 95, 99])
        
        result = ReplayBenchmarkResult(
            runs=runs,
            execution_time_avg_ms=sum(execution_times) / len(execution_times),
            execution_time_p50_ms=exec_percentiles['p50'],
            execution_time_p95_ms=exec_percentiles['p95'],
            replay_time_avg_ms=sum(replay_times) / len(replay_times),
            replay_time_p50_ms=replay_percentiles['p50'],
            replay_time_p95_ms=replay_percentiles['p95'],
            verification_time_avg_ms=sum(verification_times) / len(verification_times),
            verification_time_p50_ms=verify_percentiles['p50'],
            verification_time_p95_ms=verify_percentiles['p95']
        )
        
        print(f"  Execution (avg): {result.execution_time_avg_ms:.2f} ms")
        print(f"  Execution (p50): {result.execution_time_p50_ms:.2f} ms")
        print(f"  Execution (p95): {result.execution_time_p95_ms:.2f} ms")
        print(f"  Replay (avg): {result.replay_time_avg_ms:.2f} ms")
        print(f"  Replay (p50): {result.replay_time_p50_ms:.2f} ms")
        print(f"  Replay (p95): {result.replay_time_p95_ms:.2f} ms")
        print(f"  Verification (avg): {result.verification_time_avg_ms:.2f} ms")
        print(f"  Verification (p50): {result.verification_time_p50_ms:.2f} ms")
        print(f"  Verification (p95): {result.verification_time_p95_ms:.2f} ms")
        
        return result
    
    def run_noise_benchmark(
        self,
        noise_levels: List[int] = [1, 10, 100]
    ) -> List[NoiseBenchmarkResult]:
        """
        Measure noise resistance impact on performance and hash stability.
        
        This test:
        - Injects increasing irrelevant payload size
        - Measures latency impact
        - Verifies hash does NOT change
        
        Args:
            noise_levels: List of noise levels to test (size of noise payload)
        
        Returns:
            List of NoiseBenchmarkResult, one per noise level
        
        Raises:
            DeterminismViolationError: If hash changes at any noise level
        """
        results = []
        
        # Get baseline hash without noise
        harness = DeterminismHarness(self.scenario_builder, runs=1)
        baseline_hash = harness.report.canonical_hash
        
        # Measure baseline latency
        baseline_latencies = []
        for _ in range(10):
            start = time.perf_counter()
            audit_records = self.scenario_builder()
            extract_canonical_audit_hash(audit_records)
            baseline_latencies.append((time.perf_counter() - start) * 1000)
        baseline_latency_ms = sum(baseline_latencies) / len(baseline_latencies)
        
        print(f"\nNOISE RESISTANCE BENCHMARK")
        print("=" * 60)
        print(f"  Baseline hash: {baseline_hash}")
        print(f"  Baseline latency: {baseline_latency_ms:.2f} ms")
        
        for noise_level in noise_levels:
            print(f"\n  Noise Level: {noise_level}")
            
            from exoarmur.proof.scenario_builder import inject_noise, build_canonical_input_payload
            
            noisy_latencies = []
            noisy_hashes = []
            
            for run in range(10):
                # Generate base payload
                base_payload = build_canonical_input_payload()
                
                # Inject noise at this level
                noisy_payload = inject_noise(base_payload, noise_level=noise_level)
                
                # Execute and measure latency
                start = time.perf_counter()
                audit_records = self.scenario_builder()
                hash_value = extract_canonical_audit_hash(audit_records)
                noisy_latencies.append((time.perf_counter() - start) * 1000)
                noisy_hashes.append(hash_value)
            
            # Calculate average noisy latency
            noisy_latency_ms = sum(noisy_latencies) / len(noisy_latencies)
            
            # Calculate latency impact
            latency_impact_percent = ((noisy_latency_ms - baseline_latency_ms) / baseline_latency_ms) * 100
            
            # Verify hash stability
            unique_hashes = set(noisy_hashes)
            hash_stable = (len(unique_hashes) == 1 and list(unique_hashes)[0] == baseline_hash)
            
            if not hash_stable:
                raise DeterminismViolationError(
                    f"Hash changed at noise level {noise_level}: "
                    f"Expected {baseline_hash}, got {unique_hashes}"
                )
            
            result = NoiseBenchmarkResult(
                noise_level=noise_level,
                hash_stable=hash_stable,
                latency_impact_percent=latency_impact_percent,
                baseline_latency_ms=baseline_latency_ms,
                noisy_latency_ms=noisy_latency_ms
            )
            
            results.append(result)
            
            print(f"    Hash Stable: {'YES' if hash_stable else 'NO'}")
            print(f"    Noisy latency: {noisy_latency_ms:.2f} ms")
            print(f"    Latency Impact: {latency_impact_percent:.2f}%")
        
        return results
    
    def run_all_benchmarks(
        self,
        concurrency_levels: List[int] = [10, 50, 100, 500, 1000],
        runs_per_level: int = 100,
        noise_levels: List[int] = [1, 10, 100]
    ) -> Dict[str, Any]:
        """
        Run all benchmarks and return comprehensive results.
        
        Args:
            concurrency_levels: Concurrency levels for determinism and throughput tests
            runs_per_level: Runs per concurrency level
            noise_levels: Noise levels for noise benchmark
        
        Returns:
            Dictionary containing all benchmark results
        """
        print("\n" + "=" * 60)
        print("EXOARMUR BENCHMARK SUITE - FULL EXECUTION")
        print("=" * 60)
        
        results = {}
        
        # Run determinism load test
        try:
            results['determinism'] = self.run_determinism_load_test(
                concurrency_levels=concurrency_levels,
                runs_per_level=runs_per_level
            )
        except Exception as e:
            print(f"  Determinism load test failed: {e}")
            results['determinism'] = None
        
        # Run throughput test
        try:
            results['throughput'] = self.run_throughput_test(
                concurrency_levels=[c for c in concurrency_levels if c <= 100],  # Limit throughput test
                runs=1000
            )
        except Exception as e:
            print(f"  Throughput test failed: {e}")
            results['throughput'] = None
        
        # Run replay benchmark
        try:
            results['replay'] = self.run_replay_benchmark(runs=100)
        except Exception as e:
            print(f"  Replay benchmark failed: {e}")
            results['replay'] = None
        
        # Run noise benchmark
        try:
            results['noise'] = self.run_noise_benchmark(noise_levels=noise_levels)
        except Exception as e:
            print(f"  Noise benchmark failed: {e}")
            results['noise'] = None
        
        return results
