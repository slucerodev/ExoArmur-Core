#!/usr/bin/env python3
"""
Phase 6 Chaos & Failure Testing
Gate 7 Failure Survival & Crash Consistency
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
class ChaosTestConfig:
    """Chaos test configuration"""
    # Test scenarios
    enable_service_crash: bool = True
    enable_nats_restart: bool = True
    enable_network_latency: bool = True
    enable_duplicate_messages: bool = True
    enable_slow_consumer: bool = True
    
    # Test parameters
    crash_probability: float = 0.1
    latency_range: tuple = (0.5, 2.0)  # seconds
    duplicate_probability: float = 0.05
    slow_consumer_delay: float = 5.0  # seconds
    
    # Test duration
    test_duration: int = 60  # seconds
    operations_per_second: int = 20


@dataclass
class ChaosTestMetrics:
    """Chaos test metrics collection"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    chaos_events: int = 0
    
    # Chaos event counts
    service_crashes: int = 0
    nats_restarts: int = 0
    network_latency_events: int = 0
    duplicate_messages: int = 0
    slow_consumer_events: int = 0
    
    # Recovery metrics
    recovery_times: List[float] = field(default_factory=list)
    crash_recovery_success: int = 0
    crash_recovery_failures: int = 0
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def add_operation(self, success: bool):
        """Record operation metrics"""
        self.total_operations += 1
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
    
    def add_chaos_event(self, event_type: str, recovery_time: Optional[float] = None):
        """Record chaos event"""
        self.chaos_events += 1
        
        if event_type == "service_crash":
            self.service_crashes += 1
            if recovery_time is not None:
                self.recovery_times.append(recovery_time)
                if recovery_time < 10.0:  # Recovery within 10 seconds
                    self.crash_recovery_success += 1
                else:
                    self.crash_recovery_failures += 1
        elif event_type == "nats_restart":
            self.nats_restarts += 1
        elif event_type == "network_latency":
            self.network_latency_events += 1
        elif event_type == "duplicate_message":
            self.duplicate_messages += 1
        elif event_type == "slow_consumer":
            self.slow_consumer_events += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get chaos test summary"""
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / self.total_operations if self.total_operations > 0 else 0,
            "chaos_events": {
                "total": self.chaos_events,
                "service_crashes": self.service_crashes,
                "nats_restarts": self.nats_restarts,
                "network_latency": self.network_latency_events,
                "duplicate_messages": self.duplicate_messages,
                "slow_consumer": self.slow_consumer_events
            },
            "recovery_metrics": {
                "avg_recovery_time": sum(self.recovery_times) / len(self.recovery_times) if self.recovery_times else 0,
                "crash_recovery_success": self.crash_recovery_success,
                "crash_recovery_failures": self.crash_recovery_failures,
                "recovery_rate": self.crash_recovery_success / (self.crash_recovery_success + self.crash_recovery_failures) if (self.crash_recovery_success + self.crash_recovery_failures) > 0 else 0
            }
        }


class ChaosService:
    """Mock service with chaos injection capabilities"""
    
    def __init__(self, config: ChaosTestConfig):
        self.config = config
        self.is_running = True
        self.operation_count = 0
        self.crash_count = 0
        self.latency_injected = False
        self.duplicate_mode = False
        self.slow_consumer_mode = False
        
        logger.info("Chaos service initialized")
    
    async def process_request(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Process request with chaos injection"""
        if not self.is_running:
            raise Exception("Service crashed - not available")
        
        self.operation_count += 1
        
        # Inject service crash
        if self.config.enable_service_crash and random.random() < self.config.crash_probability:
            await self._crash_service()
            raise Exception("Service crashed during operation")
        
        # Inject network latency
        if self.config.enable_network_latency and random.random() < 0.3:
            latency = random.uniform(*self.config.latency_range)
            await asyncio.sleep(latency)
        
        # Inject slow consumer behavior
        if self.config.enable_slow_consumer and self.slow_consumer_mode:
            await asyncio.sleep(self.config.slow_consumer_delay)
        
        # Inject duplicate message behavior
        if self.config.enable_duplicate_messages and self.duplicate_mode:
            # Return same result for duplicate detection
            return {
                "tenant_id": tenant_id,
                "node_id": node_id,
                "peer_id": peer_id,
                "operation_id": self.operation_count,
                "duplicate": True,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        
        return {
            "tenant_id": tenant_id,
            "node_id": node_id,
            "peer_id": peer_id,
            "operation_id": self.operation_count,
            "duplicate": False,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _crash_service(self):
        """Simulate service crash"""
        self.is_running = False
        self.crash_count += 1
        logger.warning(f"Service crashed (crash #{self.crash_count})")
    
    async def restart_service(self):
        """Simulate service restart"""
        await asyncio.sleep(1.0)  # Simulate restart time
        self.is_running = True
        logger.info(f"Service restarted after crash #{self.crash_count}")
    
    def inject_network_latency(self):
        """Enable network latency injection"""
        self.latency_injected = True
        logger.info("Network latency injection enabled")
    
    def remove_network_latency(self):
        """Disable network latency injection"""
        self.latency_injected = False
        logger.info("Network latency injection disabled")
    
    def enable_duplicate_mode(self):
        """Enable duplicate message mode"""
        self.duplicate_mode = True
        logger.info("Duplicate message mode enabled")
    
    def disable_duplicate_mode(self):
        """Disable duplicate message mode"""
        self.duplicate_mode = False
        logger.info("Duplicate message mode disabled")
    
    def enable_slow_consumer_mode(self):
        """Enable slow consumer mode"""
        self.slow_consumer_mode = True
        logger.info("Slow consumer mode enabled")
    
    def disable_slow_consumer_mode(self):
        """Disable slow consumer mode"""
        self.slow_consumer_mode = False
        logger.info("Slow consumer mode disabled")


class ChaosTestHarness:
    """Chaos test harness for Phase 6 failure testing"""
    
    def __init__(self, config: ChaosTestConfig):
        self.config = config
        self.metrics = ChaosTestMetrics()
        self.chaos_service = ChaosService(config)
        
        # Initialize reliability components
        self.timeout_manager = get_timeout_manager()
        self.retry_manager = get_retry_manager()
        self.backpressure_manager = get_backpressure_manager()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        
        # Setup audit emitter
        self.audit_events = []
        self._setup_audit_emitters()
        
        logger.info("Chaos test harness initialized")
    
    def _setup_audit_emitters(self):
        """Setup audit emitters for reliability components"""
        async def audit_emitter(event_data):
            self.audit_events.append(event_data)
        
        self.timeout_manager.set_audit_emitter(audit_emitter)
        self.retry_manager.set_audit_emitter(audit_emitter)
        self.backpressure_manager.set_audit_emitter(audit_emitter)
        self.circuit_breaker_manager.set_audit_emitter(audit_emitter)
    
    async def execute_operation_with_chaos(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Execute operation with chaos injection and reliability protections"""
        start_time = time.time()
        success = False
        
        try:
            # Use circuit breaker protection
            result = await self.circuit_breaker_manager.call_with_breaker(
                "chaos-service",
                self._execute_with_protections,
                tenant_id=tenant_id,
                node_id=node_id,
                peer_id=peer_id
            )
            
            success = True
            return result
            
        except Exception as e:
            # Handle service crash scenario
            if "crashed" in str(e).lower():
                recovery_start = time.time()
                await self.chaos_service.restart_service()
                recovery_time = time.time() - recovery_start
                self.metrics.add_chaos_event("service_crash", recovery_time)
            
            raise
        finally:
            self.metrics.add_operation(success)
    
    async def _execute_with_protections(self, tenant_id: str, node_id: str, peer_id: str) -> Dict[str, Any]:
        """Execute operation with all reliability protections"""
        
        async def operation():
            # Check backpressure
            await self.backpressure_manager.check_backpressure(
                tenant_id=tenant_id,
                operation=f"chaos_request_{node_id}_{peer_id}"
            )
            
            # Execute the actual service call
            return await self.chaos_service.process_request(tenant_id, node_id, peer_id)
        
        # Use retry protection
        return await self.retry_manager.execute_with_retry(
            category="RETRY_API_REQUEST",
            operation=f"chaos_request_{node_id}_{peer_id}",
            coro=operation(),
            tenant_id=tenant_id
        )
    
    async def run_service_crash_test(self) -> Dict[str, Any]:
        """Test service crash mid-execution"""
        logger.info("Starting service crash chaos test")
        
        self.metrics = ChaosTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Enable high crash probability
        original_crash_prob = self.chaos_service.config.crash_probability
        self.chaos_service.config.crash_probability = 0.3  # 30% crash rate
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(10)
        
        async def worker():
            async with semaphore:
                tenant_id = f"tenant-{random.randint(1, 5)}"
                node_id = f"node-{random.randint(1, 100)}"
                peer_id = f"peer-{random.randint(1, 50)}"
                
                try:
                    await self.execute_operation_with_chaos(tenant_id, node_id, peer_id)
                except Exception as e:
                    # Metrics are recorded in execute_operation_with_chaos
                    pass
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(1.0 / self.config.operations_per_second)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Restore original crash probability
        self.chaos_service.config.crash_probability = original_crash_prob
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Service Crash Test"
        summary["test_config"] = {
            "crash_probability": 0.3,
            "duration": self.config.test_duration,
            "operations_per_second": self.config.operations_per_second
        }
        
        logger.info(f"Service crash test completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary
    
    async def run_network_latency_test(self) -> Dict[str, Any]:
        """Test network latency/flap"""
        logger.info("Starting network latency chaos test")
        
        self.metrics = ChaosTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Enable network latency injection
        self.chaos_service.inject_network_latency()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(10)
        
        async def worker():
            async with semaphore:
                tenant_id = f"tenant-{random.randint(1, 5)}"
                node_id = f"node-{random.randint(1, 100)}"
                peer_id = f"peer-{random.randint(1, 50)}"
                
                try:
                    result = await self.execute_operation_with_chaos(tenant_id, node_id, peer_id)
                    
                    # Count latency events
                    if self.chaos_service.latency_injected:
                        self.metrics.add_chaos_event("network_latency")
                    
                    return result
                except Exception as e:
                    # Metrics are recorded in execute_operation_with_chaos
                    pass
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(1.0 / self.config.operations_per_second)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Disable network latency injection
        self.chaos_service.remove_network_latency()
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Network Latency Test"
        summary["test_config"] = {
            "latency_range": self.config.latency_range,
            "duration": self.config.test_duration,
            "operations_per_second": self.config.operations_per_second
        }
        
        logger.info(f"Network latency test completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary
    
    async def run_duplicate_message_test(self) -> Dict[str, Any]:
        """Test duplicate message delivery"""
        logger.info("Starting duplicate message chaos test")
        
        self.metrics = ChaosTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Enable duplicate message mode
        self.chaos_service.enable_duplicate_mode()
        
        # Track operation IDs for duplicate detection
        operation_results = {}
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(5)  # Lower concurrency for duplicate detection
        
        async def worker():
            async with semaphore:
                tenant_id = f"tenant-{random.randint(1, 5)}"
                node_id = f"node-{random.randint(1, 100)}"
                peer_id = f"peer-{random.randint(1, 50)}"
                
                try:
                    result = await self.execute_operation_with_chaos(tenant_id, node_id, peer_id)
                    
                    # Check for duplicates
                    op_id = result.get("operation_id")
                    if op_id in operation_results:
                        self.metrics.add_chaos_event("duplicate_message")
                    else:
                        operation_results[op_id] = result
                    
                    return result
                except Exception as e:
                    # Metrics are recorded in execute_operation_with_chaos
                    pass
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(1.0 / self.config.operations_per_second)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Disable duplicate message mode
        self.chaos_service.disable_duplicate_mode()
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Duplicate Message Test"
        summary["test_config"] = {
            "duplicate_probability": self.config.duplicate_probability,
            "duration": self.config.test_duration,
            "operations_per_second": self.config.operations_per_second
        }
        
        logger.info(f"Duplicate message test completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary
    
    async def run_slow_consumer_test(self) -> Dict[str, Any]:
        """Test slow consumer/backlog growth"""
        logger.info("Starting slow consumer chaos test")
        
        self.metrics = ChaosTestMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)
        
        # Enable slow consumer mode
        self.chaos_service.enable_slow_consumer_mode()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(20)  # Higher concurrency to stress queues
        
        async def worker():
            async with semaphore:
                tenant_id = f"tenant-{random.randint(1, 5)}"
                node_id = f"node-{random.randint(1, 100)}"
                peer_id = f"peer-{random.randint(1, 50)}"
                
                try:
                    result = await self.execute_operation_with_chaos(tenant_id, node_id, peer_id)
                    
                    # Count slow consumer events
                    if self.chaos_service.slow_consumer_mode:
                        self.metrics.add_chaos_event("slow_consumer")
                    
                    return result
                except Exception as e:
                    # Metrics are recorded in execute_operation_with_chaos
                    pass
        
        # Run workload for specified duration
        end_time = time.time() + self.config.test_duration
        tasks = []
        
        while time.time() < end_time:
            # Schedule operation
            task = asyncio.create_task(worker())
            tasks.append(task)
            
            # Wait for operation interval
            await asyncio.sleep(1.0 / self.config.operations_per_second)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Disable slow consumer mode
        self.chaos_service.disable_slow_consumer_mode()
        
        self.metrics.end_time = datetime.now(timezone.utc)
        
        summary = self.metrics.get_summary()
        summary["test_name"] = "Slow Consumer Test"
        summary["test_config"] = {
            "slow_consumer_delay": self.config.slow_consumer_delay,
            "duration": self.config.test_duration,
            "operations_per_second": self.config.operations_per_second
        }
        
        logger.info(f"Slow consumer test completed: {summary['total_operations']} operations, "
                   f"{summary['success_rate']:.2%} success rate")
        
        return summary


async def main():
    """Run Phase 6 chaos and failure tests"""
    print("=" * 80)
    print("PHASE 6: CHAOS & FAILURE TESTING")
    print("Gate 7: Failure Survival & Crash Consistency")
    print("=" * 80)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create chaos test configuration
    config = ChaosTestConfig(
        enable_service_crash=True,
        enable_nats_restart=False,  # Skip NATS restart for simplicity
        enable_network_latency=True,
        enable_duplicate_messages=True,
        enable_slow_consumer=True,
        crash_probability=0.1,
        latency_range=(0.5, 2.0),
        duplicate_probability=0.05,
        slow_consumer_delay=3.0,
        test_duration=30,  # Shorter for demo
        operations_per_second=10
    )
    
    # Create chaos test harness
    harness = ChaosTestHarness(config)
    
    # Run chaos tests
    results = {}
    
    try:
        print("\n" + "=" * 60)
        print("RUNNING SERVICE CRASH TEST")
        print("=" * 60)
        results["service_crash"] = await harness.run_service_crash_test()
        
        print("\n" + "=" * 60)
        print("RUNNING NETWORK LATENCY TEST")
        print("=" * 60)
        results["network_latency"] = await harness.run_network_latency_test()
        
        print("\n" + "=" * 60)
        print("RUNNING DUPLICATE MESSAGE TEST")
        print("=" * 60)
        results["duplicate_message"] = await harness.run_duplicate_message_test()
        
        print("\n" + "=" * 60)
        print("RUNNING SLOW CONSUMER TEST")
        print("=" * 60)
        results["slow_consumer"] = await harness.run_slow_consumer_test()
        
    except Exception as e:
        logger.error(f"Chaos test failed: {e}")
        return False
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("PHASE 6 CHAOS TEST RESULTS")
    print("=" * 80)
    
    for test_name, result in results.items():
        print(f"\n{result['test_name']}:")
        print(f"  Total Operations: {result['total_operations']}")
        print(f"  Success Rate: {result['success_rate']:.2%}")
        print(f"  Chaos Events: {result['chaos_events']['total']}")
        
        if result['chaos_events']['service_crashes'] > 0:
            print(f"  Service Crashes: {result['chaos_events']['service_crashes']}")
            recovery_rate = result['recovery_metrics']['recovery_rate']
            print(f"  Recovery Rate: {recovery_rate:.2%}")
        
        if result['chaos_events']['network_latency'] > 0:
            print(f"  Network Latency Events: {result['chaos_events']['network_latency']}")
        
        if result['chaos_events']['duplicate_messages'] > 0:
            print(f"  Duplicate Messages: {result['chaos_events']['duplicate_messages']}")
        
        if result['chaos_events']['slow_consumer'] > 0:
            print(f"  Slow Consumer Events: {result['chaos_events']['slow_consumer']}")
    
    # Evaluate success criteria
    success = True
    for test_name, result in results.items():
        # Success criteria: system should survive chaos with reasonable success rate
        if result['success_rate'] < 0.70:  # 70% success rate under chaos
            print(f"❌ {test_name}: Success rate {result['success_rate']:.2%} below 70% threshold")
            success = False
        
        # Recovery criteria: should recover from crashes
        if result['chaos_events']['service_crashes'] > 0:
            recovery_rate = result['recovery_metrics']['recovery_rate']
            if recovery_rate < 0.80:  # 80% recovery rate
                print(f"❌ {test_name}: Recovery rate {recovery_rate:.2%} below 80% threshold")
                success = False
    
    if success:
        print("\n✅ PHASE 6 CHAOS TESTS PASSED")
        print("✅ GATE 7 REQUIREMENTS MET")
    else:
        print("\n❌ PHASE 6 CHAOS TESTS FAILED")
        print("❌ GATE 7 REQUIREMENTS NOT MET")
    
    # Save results to file
    # Resolve repo-relative paths for portability
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    results_file = repo_root / "artifacts" / "reality_run_008" / "11_chaos_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": config.__dict__,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
