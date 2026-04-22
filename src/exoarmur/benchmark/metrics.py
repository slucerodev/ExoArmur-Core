"""
Metrics Collection Utilities for ExoArmur Benchmarks

Provides measurement utilities for performance and determinism benchmarking.
All measurements are non-invasive and do not modify core behavior.
"""

import time
import statistics
from typing import Callable, List, Dict, Any, Optional, ContextManager
from contextlib import contextmanager
from functools import wraps
import psutil
import os


def measure_latency(func: Callable) -> Callable:
    """
    Decorator to measure function execution latency.
    
    Returns a wrapped function that records execution time in milliseconds.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        return result, latency_ms
    return wrapper


def calculate_percentiles(values: List[float], percentiles: List[float] = [50, 95, 99]) -> Dict[str, float]:
    """
    Calculate percentile values from a list of measurements.
    
    Args:
        values: List of numeric values (e.g., latencies in ms)
        percentiles: List of percentiles to calculate (default: [50, 95, 99])
    
    Returns:
        Dictionary mapping percentile names to values (e.g., {'p50': 10.5, 'p95': 25.3, 'p99': 45.2})
    """
    if not values:
        return {f"p{p}": 0.0 for p in percentiles}
    
    sorted_values = sorted(values)
    result = {}
    for p in percentiles:
        index = int((p / 100) * len(sorted_values))
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        result[f"p{p}"] = sorted_values[index]
    
    return result


@contextmanager
def track_execution_time() -> ContextManager[Dict[str, float]]:
    """
    Context manager to track execution time of a code block.
    
    Yields a dictionary that will be populated with timing metrics:
        - duration_ms: Total execution time in milliseconds
        - start_time: Start timestamp (perf_counter)
        - end_time: End timestamp (perf_counter)
    
    Usage:
        with track_execution_time() as metrics:
            # do work
        print(f"Execution took {metrics['duration_ms']} ms")
    """
    metrics: Dict[str, float] = {}
    start_time = time.perf_counter()
    try:
        yield metrics
    finally:
        end_time = time.perf_counter()
        metrics['start_time'] = start_time
        metrics['end_time'] = end_time
        metrics['duration_ms'] = (end_time - start_time) * 1000


def capture_cpu_memory() -> Dict[str, float]:
    """
    Capture current CPU and memory usage metrics.
    
    Returns:
        Dictionary with:
            - cpu_percent: Current CPU usage percentage
            - memory_mb: Current memory usage in MB
            - memory_percent: Current memory usage percentage
    """
    process = psutil.Process(os.getpid())
    
    try:
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        memory_percent = process.memory_percent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        # Fallback if psutil fails
        cpu_percent = 0.0
        memory_mb = 0.0
        memory_percent = 0.0
    
    return {
        'cpu_percent': cpu_percent,
        'memory_mb': memory_mb,
        'memory_percent': memory_percent,
    }


class MetricsCollector:
    """
    Collects and aggregates benchmark metrics across multiple runs.
    """
    
    def __init__(self):
        self.latencies: List[float] = []
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []
        self.errors: List[Dict[str, Any]] = []
    
    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement in milliseconds."""
        self.latencies.append(latency_ms)
    
    def record_resource_usage(self, cpu_percent: float, memory_mb: float) -> None:
        """Record CPU and memory usage samples."""
        self.cpu_samples.append(cpu_percent)
        self.memory_samples.append(memory_mb)
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """Record an error occurrence."""
        self.errors.append({
            'type': error_type,
            'message': error_message,
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of collected metrics.
        
        Returns:
            Dictionary with:
                - latency_stats: p50, p95, p99, mean, min, max latencies
                - resource_stats: avg CPU, avg memory
                - error_count: Number of errors recorded
                - total_samples: Total number of samples
        """
        summary = {
            'latency_stats': {},
            'resource_stats': {},
            'error_count': len(self.errors),
            'total_samples': len(self.latencies),
        }
        
        if self.latencies:
            percentiles = calculate_percentiles(self.latencies)
            summary['latency_stats'] = {
                **percentiles,
                'mean': statistics.mean(self.latencies),
                'min': min(self.latencies),
                'max': max(self.latencies),
            }
        
        if self.cpu_samples:
            summary['resource_stats']['avg_cpu_percent'] = statistics.mean(self.cpu_samples)
        
        if self.memory_samples:
            summary['resource_stats']['avg_memory_mb'] = statistics.mean(self.memory_samples)
        
        return summary
    
    def reset(self) -> None:
        """Reset all collected metrics."""
        self.latencies.clear()
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self.errors.clear()
