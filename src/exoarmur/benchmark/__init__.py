"""
ExoArmur Benchmark Suite

Performance and determinism benchmarking utilities for ExoArmur Core.
This module is additive and isolated from core logic - it does not modify
V1 behavior or contracts.

All benchmarking uses canonical payloads and stable_hash to ensure
determinism verification is not compromised.
"""

from exoarmur.benchmark.benchmark_runner import BenchmarkRunner
from exoarmur.benchmark.metrics import (
    measure_latency,
    calculate_percentiles,
    track_execution_time,
)

__all__ = [
    "BenchmarkRunner",
    "measure_latency",
    "calculate_percentiles",
    "track_execution_time",
]
