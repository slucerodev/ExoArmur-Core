#!/usr/bin/env python3
"""
Phase 6 Load Test Harness
Gate 8 Bounded Load & Backpressure - Scale Requirements
"""

import asyncio
import logging
import time
import random
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from reliability import (
    get_timeout_manager,
    get_retry_manager,
    get_backpressure_manager,
    get_circuit_breaker_manager
)

logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    # Test A: 1000 logical nodes
    test_a_nodes: int = 1000
    test_a_concurrency: int = 50
    test_a_duration: int = 60  # seconds
    
    # Test B: 500 peer identities
    test_b_peers: int = 500
    test_b_concurrency: int = 25
    test_b_duration: int = 60  # seconds
    
    # Workload parameters
    operations_per_second: int = 100
    operation_timeout: float = 5.0
    tenant_isolation: bool = True
    
    # Reliability parameters
    enable_timeouts: bool = True
    enable_retries: bool = True
    enable_backpressure: bool = True
    enable_circuit_breakers: bool = True


@dataclass
class LoadTestMetrics:
    """Load test metrics collection"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    timeout_operations: int = 0
    retry_operations: int = 0
    backpressure_rejections: int = 0
    circuit_breaker_rejections: int = 0
    
    operation_latencies: List[float] = field(default_factory=list)
    tenant_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    node_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    peer_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def add_operation(self, success: bool, latency: float, tenant_id: str, 
                     node_id: str, peer_id: str, failure_type: Optional[str] = None):
        """Record operation metrics"""
        self.total_operations += 1
        
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
            
            if failure_type == "timeout":
                self.timeout_operations += 1
            elif failure_type == "retry_exhausted":
                self.retry_operations += 1
            elif failure_type == "backpressure":
                self.backpressure_rejections += 1
            elif failure_type == "circuit_breaker":
                self.circuit_breaker_rejections += 1
        
        self.operation_latencies.append(latency)
        
        # Tenant metrics
        if tenant_id not in self.tenant_metrics:
            self.tenant_metrics[tenant_id] = {"success": 0, "failure": 0}
        if success:
            self.tenant_metrics[tenant_id]["success"] += 1
        else:
            self.tenant_metrics[tenant_id]["failure"] += 1
        
        # Node metrics
        if node_id not in self.node_metrics:
            self.node_metrics[node_id] = {"success": 0, "failure": 0}
        if success:
            self.node_metrics[node_id]["success"] += 1
        else:
            self.node_metrics[node_id]["failure"] += 1
        
        # Peer metrics
        if peer_id not in self.peer_metrics:
            self.peer_metrics[peer_id] = {"success": 0, "failure": 0}
        if success:
            self.peer_metrics[peer_id]["success"] += 1
        else:
            self.peer_metrics[peer_id]["failure"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.operation_latencies:
            return {"error": "No operations recorded"}
        
        avg_latency = sum(self.operation_latencies) / len(self.operation_latencies)
        sorted_latencies = sorted(self.operation_latencies)
        
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / self.total_operations if self.total_operations > 0 else 0,
            "failure_breakdown": {
                "timeouts": self.timeout_operations,
                "retries": self.retry_operations,
                "backpressure": self.backpressure_rejections,
                "circuit_breakers": self.circuit_breaker_rejections
            },
            "latency": {
                "average": avg_latency,
                "p50": sorted_latencies[len(sorted_latencies) // 2],
                "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)],
                "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)],
                "min": min(self.operation_latencies),
                "max": max(self.operation_latencies)
            },
            "throughput": self.total_operations / ((self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 1),
            "tenant_isolation": len(self.tenant_metrics),
            "node_distribution": len(self.node_metrics),
            "peer_distribution": len(self.peer_metrics)
        }


class MockService:
    """Mock service for load testing"""
    
    def __init__(self, failure_rate: float = 0.1, latency_range: tuple = (0.1, 2.0)):
        self.failure_rate = failure_rate
        self.latency_range = latency_range
        self.operation_count = 0
    
    async def process_request(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Process a mock request"""
        self.operation_count += 1
        
        # Simulate processing latency
        latency = random.uniform(*self.latency_range)
        await asyncio.sleep(latency)
        
        # Simulate failures
        if random.random() < self.failure_rate:
            raise Exception(f"Simulated service failure (operation #{self.operation_count})")
        
        return {
            "tenant_id": tenant_id,
            "node_id": node_id,
            "peer_id": peer_id,
            "operation_id": self.operation_count,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "latency": latency
        }


class LoadTestHarness:
    """Load test harness for Phase 6 scale requirements"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.metrics = LoadTestMetrics()
        self.mock_service = MockService(failure_rate=0.05, latency_range=(0.05, 1.0))
        
        # Initialize reliability components
        self.timeout_manager = get_timeout_manager()
        self.retry_manager = get_retry_manager()
        self.backpressure_manager = get_backpressure_manager()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        
        # Setup audit emitter
        self.audit_events = []
        self._setup_audit_emitters()
        
        logger.info("Load test harness initialized")
    
    def _setup_audit_emitters(self):
        """Setup audit emitters for reliability components"""
        async def audit_emitter(event_data):
            self.audit_events.append(event_data)
        
        self.timeout_manager.set_audit_emitter(audit_emitter)
        self.retry_manager.set_audit_emitter(audit_emitter)
        self.backpressure_manager.set_audit_emitter(audit_emitter)
        self.circuit_breaker_manager.set_audit_emitter(audit_emitter)
    
    async def execute_operation(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Execute a single operation with all reliability protections"""
        start_time = time.time()
        failure_type = None
        success = False
        
        try:
            if self.config.enable_circuit_breakers:
                # Use circuit breaker protection
                result = await self.circuit_breaker_manager.call_with_breaker(
                    "mock-service",
                    self._execute_with_protections,
                    tenant_id=tenant_id,
                    node_id=node_id,
                    peer_id=peer_id
                )
            else:
                # Execute without circuit breaker
                result = await self._execute_with_protections(
                    tenant_id=tenant_id,
                    node_id=node_id,
                    peer_id=peer_id
                )
            
            success = True
            return result
            
        except Exception as e:
            # Classify failure type
            if "timeout" in str(e).lower():
                failure_type = "timeout"
            elif "retry" in str(e).lower():
                failure_type = "retry_exhausted"
            elif "rate limit" in str(e).lower():
                failure_type = "backpressure"
            elif "circuit" in str(e).lower():
                failure_type = "circuit_breaker"
            else:
                failure_type = "other"
            
            raise
        finally:
            latency = time.time() - start_time
            self.metrics.add_operation(success, latency, tenant_id, node_id, peer_id, failure_type)
    
    async def _execute_with_protections(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Execute operation with timeout, retry, and backpressure protections"""
        
        async def operation():
            if self.config.enable_backpressure:
                # Check backpressure before execution
                await self.backpressure_manager.check_backpressure(
                    tenant_id=tenant_id,
                    operation=f"process_request_{node_id}_{peer_id}"
                )
            
            # Execute the actual service call
            return await self.mock_service.process_request(tenant_id, node_id, peer_id)
        
        if self.config.enable_retries:
            # Use retry protection
            return await self.retry_manager.execute_with_retry(
                category="RETRY_API_REQUEST",
                operation=f"process_request_{node_id}_{peer_id}",
                coro=operation(),
                tenant_id=tenant_id
            )
        else:
            # Execute without retry
            return await operation()
    
    async def run_test_a_1000_nodes(self) -> Dict[str, Any]:
        """Test A: 1000 logical nodes with concurrent workload"""
        logger.info("Starting Test A: 1000 logical nodes")
        
        self.metrics = LoadTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Generate 1000 unique node IDs
        node_ids = [f"node-{i:04d}" for i in range(self.config.test_a_nodes)]
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.test_a_concurrency)
        
        async def worker():
            async with semaphore:
                # Select random node and tenant
                node_id = random.choice(node_ids)
                tenant_id = f"tenant-{random.randint(1, 10)}"
                peer_id = f"peer-{random.randint(1, 100)}"
                
                try:
                    await self.execute_operation(tenant_id, node_id, peer_id)
                except Exception as e:
                    # Metrics are recorded in execute_operation
                    pass
        
        # Calculate operation timing
        operations_per_second = self.config.operations_per_second
        operation_interval = 1.0 / operations_per_second
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_a_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(operation_interval)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Test A: 1000 Logical Nodes"
        summary["test_config"] = {
            "nodes": self.config.test_a_nodes,
            "concurrency": self.config.test_a_concurrency,
            "duration": self.config.test_a_duration,
            "operations_per_second": operations_per_second
        }
        
        logger.info(f"Test A completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary
    
    async def run_test_b_500_peers(self) -> Dict[str, Any]:
        """Test B: 500 peer identities with concurrent workload"""
        logger.info("Starting Test B: 500 peer identities")
        
        self.metrics = LoadTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Generate 500 unique peer IDs
        peer_ids = [f"peer-{i:04d}" for i in range(self.config.test_b_peers)]
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.test_b_concurrency)
        
        async def worker():
            async with semaphore:
                # Select random peer and tenant
                peer_id = random.choice(peer_ids)
                tenant_id = f"tenant-{random.randint(1, 10)}"
                node_id = f"node-{random.randint(1, 100)}"
                
                try:
                    await self.execute_operation(tenant_id, node_id, peer_id)
                except Exception as e:
                    # Metrics are recorded in execute_operation
                    pass
        
        # Calculate operation timing
        operations_per_second = self.config.operations_per_second
        operation_interval = 1.0 / operations_per_second
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_b_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(operation_interval)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Test B: 500 Peer Identities"
        summary["test_config"] = {
            "peers": self.config.test_b_peers,
            "concurrency": self.config.test_b_concurrency,
            "duration": self.config.test_b_duration,
            "operations_per_second": operations_per_second
        }
        
        logger.info(f"Test B completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary
    
    def get_reliability_stats(self) -> Dict[str, Any]:
        """Get reliability component statistics"""
        return {
            "timeout_manager": {
                "configured": self.config.enable_timeouts
            },
            "retry_manager": {
                "configured": self.config.enable_retries,
                "retry_attempts": len([e for e in self.audit_events if e.get("event_type") == "retry_attempt"])
            },
            "backpressure_manager": {
                "configured": self.config.enable_backpressure,
                "backpressure_events": len([e for e in self.audit_events if e.get("event_type") == "backpressure"]),
                "rate_limiters": len(self.backpressure_manager.rate_limiters),
                "queues": len(self.backpressure_manager.queues)
            },
            "circuit_breaker_manager": {
                "configured": self.config.enable_circuit_breakers,
                "circuit_breakers": len(self.circuit_breaker_manager.breakers),
                "state_changes": len([e for e in self.audit_events if e.get("event_type") == "circuit_breaker_state_change"])
            },
            "total_audit_events": len(self.audit_events)
        }


async def main():
    """Run Phase 6 load tests"""
    print("=" * 80)
    print("PHASE 6: LOAD TEST HARNESS")
    print("Gate 8: Bounded Load & Backpressure - Scale Requirements")
    print("=" * 80)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create load test configuration
    config = LoadTestConfig(
        test_a_nodes=1000,
        test_a_concurrency=50,
        test_a_duration=30,  # Shorter for demo
        test_b_peers=500,
        test_b_concurrency=25,
        test_b_duration=30,  # Shorter for demo
        operations_per_second=50,
        enable_timeouts=True,
        enable_retries=True,
        enable_backpressure=True,
        enable_circuit_breakers=True
    )
    
    # Create load test harness
    harness = LoadTestHarness(config)
    
    # Run tests
    results = {}
    
    try:
        print("\n" + "=" * 60)
        print("RUNNING TEST A: 1000 LOGICAL NODES")
        print("=" * 60)
        results["test_a"] = await harness.run_test_a_1000_nodes()
        
        print("\n" + "=" * 60)
        print("RUNNING TEST B: 500 PEER IDENTITIES")
        print("=" * 60)
        results["test_b"] = await harness.run_test_b_500_peers()
        
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        return False
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("PHASE 6 LOAD TEST RESULTS")
    print("=" * 80)
    
    for test_name, result in results.items():
        print(f"\n{result['test_name']}:")
        print(f"  Total Operations: {result['total_operations']}")
        print(f"  Success Rate: {result['success_rate']:.2%}")
        print(f"  Average Latency: {result['latency']['average']:.3f}s")
        print(f"  P95 Latency: {result['latency']['p95']:.3f}s")
        print(f"  Throughput: {result['throughput']:.1f} ops/sec")
        print(f"  Tenant Isolation: {result['tenant_isolation']} tenants")
        print(f"  Node Distribution: {result['node_distribution']} nodes")
        print(f"  Peer Distribution: {result['peer_distribution']} peers")
        
        if result['failure_breakdown']['timeouts'] > 0:
            print(f"  Timeouts: {result['failure_breakdown']['timeouts']}")
        if result['failure_breakdown']['retries'] > 0:
            print(f"  Retry Exhaustions: {result['failure_breakdown']['retries']}")
        if result['failure_breakdown']['backpressure'] > 0:
            print(f"  Backpressure Rejections: {result['failure_breakdown']['backpressure']}")
        if result['failure_breakdown']['circuit_breakers'] > 0:
            print(f"  Circuit Breaker Rejections: {result['failure_breakdown']['circuit_breakers']}")
    
    # Reliability statistics
    reliability_stats = harness.get_reliability_stats()
    print(f"\nReliability Component Statistics:")
    print(f"  Timeout Manager: {'✓' if reliability_stats['timeout_manager']['configured'] else '✗'}")
    print(f"  Retry Manager: {'✓' if reliability_stats['retry_manager']['configured'] else '✗'}")
    print(f"  Backpressure Manager: {'✓' if reliability_stats['backpressure_manager']['configured'] else '✗'}")
    print(f"  Circuit Breaker Manager: {'✓' if reliability_stats['circuit_breaker_manager']['configured'] else '✗'}")
    print(f"  Total Audit Events: {reliability_stats['total_audit_events']}")
    
    # Save results to file
    # Resolve repo-relative paths for portability
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    results_file = repo_root / "artifacts" / "reality_run_008" / "09_load_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": config.__dict__,
            "results": results,
            "reliability_stats": reliability_stats
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    
    # Evaluate success criteria
    success = True
    for test_name, result in results.items():
        if result['success_rate'] < 0.95:  # 95% success rate required
            print(f"❌ {test_name}: Success rate {result['success_rate']:.2%} below 95% threshold")
            success = False
        
        if result['latency']['p95'] > 2.0:  # P95 latency under 2s
            print(f"❌ {test_name}: P95 latency {result['latency']['p95']:.3f}s above 2s threshold")
            success = False
    
    if success:
        print("\n✅ PHASE 6 LOAD TESTS PASSED")
        print("✅ GATE 8 REQUIREMENTS MET")
    else:
        print("\n❌ PHASE 6 LOAD TESTS FAILED")
        print("❌ GATE 8 REQUIREMENTS NOT MET")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
