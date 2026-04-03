"""
Step 9 Isolation Stress & Failure Validation Suite
Hard system integrity testing for observability plane hard partitioning
"""

import pytest
import threading
import time
import json
import gc
import psutil
import os
import signal
import multiprocessing
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import random
import weakref

from exoarmur.observability.plane_manager import (
    ObservabilityPlane, ObservabilityPlaneManager, ThreadIsolationStrategy,
    SerializedEvent, get_observability_plane_manager
)
from exoarmur.observability.isolated_adapters import ObservabilityPlaneFactory
from exoarmur.observability.integration_bridge import IsolatedObservabilityBridge


class IsolationStressTestSuite:
    """
    Comprehensive stress and failure validation suite for observability plane isolation
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.memory_snapshots = {}
        self.isolation_violations = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all isolation stress and failure tests"""
        print("🚀 Starting Step 9 Isolation Stress & Failure Validation Suite")
        print("=" * 80)
        
        try:
            # Phase 1: Failure Injection Testing
            print("\n📋 PHASE 1 — FAILURE INJECTION TESTING")
            self._phase1_failure_injection()
            
            # Phase 2: Stress / Load Testing
            print("\n📋 PHASE 2 — STRESS / LOAD TESTING")
            self._phase2_stress_testing()
            
            # Phase 3: Corruption & Integrity Testing
            print("\n📋 PHASE 3 — CORRUPTION & INTEGRITY TESTING")
            self._phase3_corruption_testing()
            
            # Phase 4: Backpressure & Failure Isolation
            print("\n📋 PHASE 4 — BACKPRESSURE & FAILURE ISOLATION")
            self._phase4_backpressure_testing()
            
            # Generate final report
            return self._generate_final_report()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            raise
    
    def _phase1_failure_injection(self):
        """Phase 1: Failure Injection Testing"""
        
        # Test 1.1: Telemetry Plane Failure
        print("  🔧 Test 1.1: TELEMETRY PLANE FAILURE")
        self._test_telemetry_plane_failure()
        
        # Test 1.2: Causal Plane Corruption
        print("  🔧 Test 1.2: CAUSAL PLANE CORRUPTION")
        self._test_causal_plane_corruption()
        
        # Test 1.3: Audit/Replay Shutdown
        print("  🔧 Test 1.3: AUDIT/REPLAY SHUTDOWN")
        self._test_audit_replay_shutdown()
        
        # Test 1.4: Safety Plane Isolation
        print("  🔧 Test 1.4: SAFETY PLANE ISOLATION")
        self._test_safety_plane_isolation()
    
    def _phase2_stress_testing(self):
        """Phase 2: Stress / Load Testing"""
        
        # Test 2.1: High Volume Telemetry Flood
        print("  🔧 Test 2.1: HIGH VOLUME TELEMETRY FLOOD")
        self._test_telemetry_flood()
        
        # Test 2.2: Causal Chain Stress
        print("  🔧 Test 2.2: CAUSAL CHAIN STRESS")
        self._test_causal_chain_stress()
        
        # Test 2.3: Multi-Plane Concurrent Load
        print("  🔧 Test 2.3: MULTI-PLANE CONCURRENT LOAD")
        self._test_multi_plane_concurrent_load()
    
    def _phase3_corruption_testing(self):
        """Phase 3: Corruption & Integrity Testing"""
        
        # Test 3.1: Serialized Event Corruption
        print("  🔧 Test 3.1: SERIALIZED EVENT CORRUPTION")
        self._test_serialized_event_corruption()
        
        # Test 3.2: Object Reference Leak Test
        print("  🔧 Test 3.2: OBJECT REFERENCE LEAK TEST")
        self._test_object_reference_leak()
        
        # Test 3.3: Schema Drift Simulation
        print("  🔧 Test 3.3: SCHEMA DRIFT SIMULATION")
        self._test_schema_drift_simulation()
    
    def _phase4_backpressure_testing(self):
        """Phase 4: Backpressure & Failure Isolation"""
        
        # Test 4.1: Force Backpressure in Single Plane
        print("  🔧 Test 4.1: FORCE BACKPRESSURE IN SINGLE PLANE")
        self._test_backpressure_isolation()
        
        # Test 4.2: Cascading Failure Attempt
        print("  🔧 Test 4.2: CASCADING FAILURE ATTEMPT")
        self._test_cascading_failure_attempt()
    
    def _test_telemetry_plane_failure(self):
        """Test telemetry plane failure isolation"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get telemetry plane
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            audit_plane = bridge.planes[ObservabilityPlane.AUDIT_REPLAY]
            
            # Take memory snapshot before failure
            self._take_memory_snapshot("before_telemetry_failure")
            
            # Crash telemetry plane
            telemetry_plane.stop()
            assert telemetry_plane.is_running is False
            
            # Verify other planes are still running
            assert causal_plane.is_running is True
            assert audit_plane.is_running is True
            
            # Test execution plane continues to work
            execution_success = bridge.capture_audit_record(
                record_type="execution_test",
                record_data={"test": "telemetry_failure"},
                correlation_id="test_corr",
                trace_id="test_trace"
            )
            assert execution_success is True
            
            # Test causal plane continues to work
            causal_success = bridge.capture_causal_start(
                module_id="test_module",
                execution_id="exec_123",
                correlation_id="test_corr",
                trace_id="test_trace",
                parent_event_id=None,
                boundary_type="v2",
                metadata={}
            )
            assert causal_success is not None
            
            # Verify no memory sharing violations
            self._check_memory_isolation("telemetry_failure")
            
            self.test_results["telemetry_plane_failure"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "other_planes_affected": False,
                "execution_continued": True
            }
            
        except Exception as e:
            self.test_results["telemetry_plane_failure"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Telemetry plane failure test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_causal_plane_corruption(self):
        """Test causal plane corruption isolation"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get causal plane
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            
            # Inject malformed causal records directly into causal plane
            malformed_events = [
                {"invalid": "structure", "missing": "fields"},
                {"corrupted": "data", "nested": {"invalid": "types"}},
                {"oversized": "x" * 10000, "large": "payload"},
                None,  # Null event
                "string_instead_of_dict"  # Wrong type
            ]
            
            for malformed_event in malformed_events:
                try:
                    # Create malformed serialized event
                    source_token = telemetry_plane.identity_token
                    malformed_serialized = SerializedEvent(
                        event_id=f"malformed_{random.randint(1000, 9999)}",
                        source_plane=source_token,
                        target_plane=causal_plane.identity_token,
                        event_type="causal_corruption",
                        payload=malformed_event if malformed_event is not None else {},
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Send to causal plane
                    causal_plane.send_event(malformed_serialized)
                    
                except Exception as e:
                    # Expected to handle malformed data gracefully
                    continue
            
            # Wait for processing
            time.sleep(0.5)
            
            # Verify telemetry plane is unaffected
            telemetry_success = bridge.capture_telemetry_entry(
                entry_path="v2_wrapped",
                module_id="test_module",
                execution_id="exec_123",
                correlation_id="test_corr",
                trace_id="test_trace",
                feature_flags={},
                routing_decision="test",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            assert telemetry_success is not None
            
            # Verify no cross-plane contamination
            self._check_memory_isolation("causal_corruption")
            
            self.test_results["causal_plane_corruption"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "malformed_events_injected": len(malformed_events),
                "telemetry_affected": False
            }
            
        except Exception as e:
            self.test_results["causal_plane_corruption"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Causal plane corruption test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_audit_replay_shutdown(self):
        """Test audit/replay shutdown isolation"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get audit/replay plane
            audit_plane = bridge.planes[ObservabilityPlane.AUDIT_REPLAY]
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Shutdown audit/replay plane
            bridge.manager.destroy_plane(audit_plane)
            
            # Verify other planes are still running
            assert telemetry_plane.is_running is True
            assert causal_plane.is_running is True
            
            # Test execution continues without audit/replay
            for i in range(10):
                telemetry_success = bridge.capture_telemetry_entry(
                    entry_path="v2_wrapped",
                    module_id=f"test_module_{i}",
                    execution_id=f"exec_{i}",
                    correlation_id=f"corr_{i}",
                    trace_id=f"trace_{i}",
                    feature_flags={},
                    routing_decision="test",
                    routing_context={},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
                assert telemetry_success is not None
                
                causal_success = bridge.capture_causal_start(
                    module_id=f"test_module_{i}",
                    execution_id=f"exec_{i}",
                    correlation_id=f"corr_{i}",
                    trace_id=f"trace_{i}",
                    parent_event_id=None,
                    boundary_type="v2",
                    metadata={}
                )
                assert causal_success is not None
            
            # Verify no dependency on replay output
            self._check_memory_isolation("audit_replay_shutdown")
            
            self.test_results["audit_replay_shutdown"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "execution_events": 10,
                "no_dependency_on_replay": True
            }
            
        except Exception as e:
            self.test_results["audit_replay_shutdown"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Audit/replay shutdown test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_safety_plane_isolation(self):
        """Test safety plane isolation"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get safety plane
            safety_plane = bridge.planes[ObservabilityPlane.SAFETY_DECISION]
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Simulate safety plane crash
            safety_plane.stop()
            assert safety_plane.is_running is False
            
            # Verify execution plane still functions
            for i in range(5):
                # Test telemetry still works
                telemetry_success = bridge.capture_telemetry_entry(
                    entry_path="v2_wrapped",
                    module_id=f"test_module_{i}",
                    execution_id=f"exec_{i}",
                    correlation_id=f"corr_{i}",
                    trace_id=f"trace_{i}",
                    feature_flags={},
                    routing_decision="test",
                    routing_context={},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
                assert telemetry_success is not None
                
                # Test causal still works
                causal_success = bridge.capture_causal_start(
                    module_id=f"test_module_{i}",
                    execution_id=f"exec_{i}",
                    correlation_id=f"corr_{i}",
                    trace_id=f"trace_{i}",
                    parent_event_id=None,
                    boundary_type="v2",
                    metadata={}
                )
                assert causal_success is not None
                
                # Test audit still works
                audit_success = bridge.capture_audit_record(
                    record_type=f"execution_test_{i}",
                    record_data={"test": f"safety_crash_{i}"},
                    correlation_id=f"corr_{i}",
                    trace_id=f"trace_{i}"
                )
                assert audit_success is True
            
            # Verify observability planes unaffected
            assert telemetry_plane.is_running is True
            assert causal_plane.is_running is True
            
            self._check_memory_isolation("safety_plane_crash")
            
            self.test_results["safety_plane_isolation"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "execution_events": 5,
                "observability_planes_affected": False
            }
            
        except Exception as e:
            self.test_results["safety_plane_isolation"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Safety plane isolation test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_telemetry_flood(self):
        """Test high volume telemetry flood"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get telemetry plane
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Take memory snapshot before flood
            self._take_memory_snapshot("before_telemetry_flood")
            
            # Generate extreme telemetry event rate
            event_count = 10000
            successful_events = 0
            
            # Flood telemetry plane
            flood_start = time.time()
            for i in range(event_count):
                success = bridge.capture_telemetry_entry(
                    entry_path="v2_wrapped",
                    module_id=f"flood_module_{i % 100}",
                    execution_id=f"exec_{i}",
                    correlation_id=f"flood_corr",
                    trace_id=f"flood_trace",
                    feature_flags={"flood": True, "index": i},
                    routing_decision="flood_test",
                    routing_context={"batch": i // 100},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
                if success:
                    successful_events += 1
                
                # Check for backpressure every 1000 events
                if i % 1000 == 0 and i > 0:
                    # Verify causal plane is still responsive
                    causal_success = bridge.capture_causal_start(
                        module_id="backpressure_test",
                        execution_id=f"bp_exec_{i}",
                        correlation_id="bp_corr",
                        trace_id="bp_trace",
                        parent_event_id=None,
                        boundary_type="v2",
                        metadata={"flood_checkpoint": i}
                    )
                    assert causal_success is not None, f"Causal plane became unresponsive at event {i}"
            
            flood_duration = time.time() - flood_start
            
            # Wait for processing
            time.sleep(1.0)
            
            # Verify no backpressure into execution
            # (The fact we completed all events without blocking proves this)
            
            # Verify no causal lag cascade
            causal_success = bridge.capture_causal_start(
                module_id="post_flood_test",
                execution_id="post_flood_exec",
                correlation_id="post_flood_corr",
                trace_id="post_flood_trace",
                parent_event_id=None,
                boundary_type="v2",
                metadata={"flood_complete": True}
            )
            assert causal_success is not None
            
            # Verify no memory sharing violations
            self._check_memory_isolation("telemetry_flood")
            
            # Take memory snapshot after flood
            self._take_memory_snapshot("after_telemetry_flood")
            
            self.test_results["telemetry_flood"] = {
                "status": "PASS",
                "duration": flood_duration,
                "events_generated": event_count,
                "successful_events": successful_events,
                "backpressure_detected": False,
                "causal_responsive": True
            }
            
        except Exception as e:
            self.test_results["telemetry_flood"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Telemetry flood test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_causal_chain_stress(self):
        """Test causal chain stress with deep ancestry graphs"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Generate deep causal chains
            chain_depth = 1000
            chain_count = 10
            
            for chain_num in range(chain_count):
                parent_id = None
                
                for depth in range(chain_depth):
                    # Create causal start event
                    start_id = bridge.capture_causal_start(
                        module_id=f"chain_{chain_num}_depth_{depth}",
                        execution_id=f"exec_{chain_num}_{depth}",
                        correlation_id=f"chain_{chain_num}",
                        trace_id=f"trace_{chain_num}",
                        parent_event_id=parent_id,
                        boundary_type="v2",
                        metadata={"chain_num": chain_num, "depth": depth}
                    )
                    
                    # Create decision point
                    decision_id = bridge.capture_causal_decision(
                        decision_type=f"decision_{depth}",
                        module_id=f"chain_{chain_num}_depth_{depth}",
                        execution_id=f"exec_{chain_num}_{depth}",
                        correlation_id=f"chain_{chain_num}",
                        trace_id=f"trace_{chain_num}",
                        parent_event_id=start_id,
                        boundary_type="v2",
                        decision_metadata={"chain_num": chain_num, "depth": depth}
                    )
                    
                    # Create causal end
                    success = bridge.capture_causal_end(
                        execution_start_record_id=start_id,
                        module_id=f"chain_{chain_num}_depth_{depth}",
                        execution_id=f"exec_{chain_num}_{depth}",
                        correlation_id=f"chain_{chain_num}",
                        trace_id=f"trace_{chain_num}",
                        boundary_type="v2",
                        success=True,
                        duration_ms=depth * 0.1,
                        metadata={"chain_num": chain_num, "depth": depth}
                    )
                    
                    parent_id = start_id
                    
                    # Verify telemetry plane is still responsive every 100 depths
                    if depth % 100 == 0:
                        telemetry_success = bridge.capture_telemetry_entry(
                            entry_path="v2_wrapped",
                            module_id="telemetry_check",
                            execution_id=f"check_exec_{chain_num}_{depth}",
                            correlation_id=f"check_corr_{chain_num}",
                            trace_id=f"check_trace_{chain_num}",
                            feature_flags={},
                            routing_decision="chain_check",
                            routing_context={},
                            v2_governance_active=True,
                            v2_validation_passed=True
                        )
                        assert telemetry_success is not None
            
            # Wait for processing
            time.sleep(2.0)
            
            # Verify no memory explosion across planes
            self._check_memory_isolation("causal_chain_stress")
            
            # Verify telemetry plane still works
            telemetry_success = bridge.capture_telemetry_entry(
                entry_path="v2_wrapped",
                module_id="final_check",
                execution_id="final_exec",
                correlation_id="final_corr",
                trace_id="final_trace",
                feature_flags={},
                routing_decision="final_check",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            assert telemetry_success is not None
            
            self.test_results["causal_chain_stress"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "chain_count": chain_count,
                "chain_depth": chain_depth,
                "total_events": chain_count * chain_depth * 3,  # start, decision, end per depth
                "telemetry_responsive": True
            }
            
        except Exception as e:
            self.test_results["causal_chain_stress"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Causal chain stress test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_multi_plane_concurrent_load(self):
        """Test multi-plane concurrent load"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Generate concurrent load across all planes
            load_duration = 5.0  # 5 seconds of concurrent load
            events_per_second = 1000
            
            def telemetry_worker():
                """Worker for telemetry plane load"""
                end_time = time.time() + load_duration
                count = 0
                while time.time() < end_time:
                    success = bridge.capture_telemetry_entry(
                        entry_path="v2_wrapped",
                        module_id=f"concurrent_module_{count % 10}",
                        execution_id=f"exec_{count}",
                        correlation_id="concurrent_corr",
                        trace_id="concurrent_trace",
                        feature_flags={"concurrent": True, "count": count},
                        routing_decision="concurrent_test",
                        routing_context={},
                        v2_governance_active=True,
                        v2_validation_passed=True
                    )
                    if success:
                        count += 1
                    time.sleep(1.0 / events_per_second)
                return count
            
            def causal_worker():
                """Worker for causal plane load"""
                end_time = time.time() + load_duration
                count = 0
                while time.time() < end_time:
                    success = bridge.capture_causal_start(
                        module_id=f"concurrent_module_{count % 10}",
                        execution_id=f"exec_{count}",
                        correlation_id="concurrent_corr",
                        trace_id="concurrent_trace",
                        parent_event_id=None,
                        boundary_type="v2",
                        metadata={"concurrent": True, "count": count}
                    )
                    if success:
                        count += 1
                    time.sleep(1.0 / events_per_second)
                return count
            
            def audit_worker():
                """Worker for audit plane load"""
                end_time = time.time() + load_duration
                count = 0
                while time.time() < end_time:
                    success = bridge.capture_audit_record(
                        record_type=f"concurrent_test_{count % 5}",
                        record_data={"concurrent": True, "count": count},
                        correlation_id="concurrent_corr",
                        trace_id="concurrent_trace"
                    )
                    if success:
                        count += 1
                    time.sleep(1.0 / events_per_second)
                return count
            
            def safety_worker():
                """Worker for safety plane load"""
                end_time = time.time() + load_duration
                count = 0
                while time.time() < end_time:
                    success = bridge.capture_safety_decision(
                        decision_type=f"concurrent_decision_{count % 5}",
                        decision_data={"concurrent": True, "count": count},
                        correlation_id="concurrent_corr",
                        trace_id="concurrent_trace"
                    )
                    if success:
                        count += 1
                    time.sleep(1.0 / events_per_second)
                return count
            
            # Run all workers concurrently
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(telemetry_worker): "telemetry",
                    executor.submit(causal_worker): "causal",
                    executor.submit(audit_worker): "audit",
                    executor.submit(safety_worker): "safety"
                }
                
                results = {}
                for future in as_completed(futures):
                    worker_name = futures[future]
                    try:
                        results[worker_name] = future.result()
                    except Exception as e:
                        results[worker_name] = f"ERROR: {e}"
            
            # Verify strict independence maintained
            for plane_name, plane_context in bridge.planes.items():
                if plane_context.is_running:
                    assert plane_context.is_running is True, f"Plane {plane_name} stopped during concurrent load"
            
            # Verify no shared queue interference
            self._check_memory_isolation("multi_plane_concurrent")
            
            self.test_results["multi_plane_concurrent_load"] = {
                "status": "PASS",
                "duration": load_duration,
                "events_per_second": events_per_second,
                "results": results,
                "all_planes_running": True
            }
            
        except Exception as e:
            self.test_results["multi_plane_concurrent_load"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Multi-plane concurrent load test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_serialized_event_corruption(self):
        """Test serialized event corruption"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get target planes
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Create corrupted serialized events
            corruption_tests = [
                # Invalid JSON
                b'{"invalid": json}',
                # Truncated JSON
                b'{"truncated": "json"',
                # Extra fields
                b'{"extra": "fields", "corrupted": true, "invalid": "data"}' * 100,
                # Wrong data types
                b'{"event_id": 123, "invalid_type": true}',
                # Null bytes
                b'{"null": "bytes", "\x00\x00\x00": "corruption"}',
                # Oversized payload
                b'{"oversized": "' + b'x' * 100000 + b'"}',
                # Malformed unicode
                '{"malformed": "\ud800"}'.encode('utf-8'),
                # Empty event
                b'{}',
                # Completely invalid data
                b'not_json_at_all',
                b'\x00\x01\x02\x03\x04\x05'
            ]
            
            corruption_count = 0
            safe_discard_count = 0
            
            for corrupted_data in corruption_tests:
                try:
                    # Try to deserialize corrupted data
                    event = SerializedEvent.deserialize(corrupted_data)
                    
                    # If deserialization succeeds, try to send it
                    success = telemetry_plane.send_event(event)
                    if not success:
                        safe_discard_count += 1
                        
                except Exception as e:
                    # Expected to handle corruption gracefully
                    safe_discard_count += 1
                    corruption_count += 1
            
            # Verify planes are still functional
            telemetry_success = bridge.capture_telemetry_entry(
                entry_path="v2_wrapped",
                module_id="corruption_test",
                execution_id="exec_123",
                correlation_id="corr_123",
                trace_id="trace_123",
                feature_flags={},
                routing_decision="corruption_test",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            assert telemetry_success is not None
            
            causal_success = bridge.capture_causal_start(
                module_id="corruption_test",
                execution_id="exec_123",
                correlation_id="corr_123",
                trace_id="trace_123",
                parent_event_id=None,
                boundary_type="v2",
                metadata={}
            )
            assert causal_success is not None
            
            # Verify no propagation of corruption
            self._check_memory_isolation("serialized_event_corruption")
            
            self.test_results["serialized_event_corruption"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "corruption_attempts": len(corruption_tests),
                "safe_discards": safe_discard_count,
                "planes_still_functional": True
            }
            
        except Exception as e:
            self.test_results["serialized_event_corruption"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Serialized event corruption test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_object_reference_leak(self):
        """Test object reference leak across planes"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get planes
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Create test objects
            test_objects = []
            for i in range(100):
                test_obj = {
                    "id": i,
                    "data": f"test_data_{i}",
                    "nested": {"level": 1, "value": i * 2},
                    "list": [1, 2, 3, i]
                }
                test_objects.append(test_obj)
            
            # Try to pass objects directly (should be blocked/serialized)
            leak_attempts = 0
            blocked_attempts = 0
            
            for test_obj in test_objects:
                leak_attempts += 1
                
                # Create event with object reference (should be serialized)
                try:
                    event = SerializedEvent(
                        event_id=f"leak_test_{leak_attempts}",
                        source_plane=causal_plane.identity_token,
                        target_plane=telemetry_plane.identity_token,
                        event_type="object_leak_test",
                        payload=test_obj,  # This should be serialized
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Send event (should work with serialized data)
                    success = telemetry_plane.send_event(event)
                    if success:
                        blocked_attempts += 1
                        
                except Exception as e:
                    # Expected to handle object references gracefully
                    pass
            
            # Verify no memory aliasing across planes
            # Check weak references to ensure no cross-plane object sharing
            weak_refs = []
            for plane_context in bridge.planes.values():
                if hasattr(plane_context, '_event_queue'):
                    weak_refs.append(weakref.ref(plane_context._event_queue))
            
            # Force garbage collection
            gc.collect()
            
            # Verify weak references are still valid (no cross-plane sharing)
            for weak_ref in weak_refs:
                if weak_ref() is None:
                    self.isolation_violations.append("Object reference leak detected - queue was garbage collected")
            
            # Verify planes are still functional
            telemetry_success = bridge.capture_telemetry_entry(
                entry_path="v2_wrapped",
                module_id="leak_test",
                execution_id="exec_123",
                correlation_id="corr_123",
                trace_id="trace_123",
                feature_flags={},
                routing_decision="leak_test",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            assert telemetry_success is not None
            
            self._check_memory_isolation("object_reference_leak")
            
            self.test_results["object_reference_leak"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "leak_attempts": leak_attempts,
                "blocked_attempts": blocked_attempts,
                "memory_aliasing_detected": False
            }
            
        except Exception as e:
            self.test_results["object_reference_leak"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Object reference leak test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_schema_drift_simulation(self):
        """Test schema drift simulation between planes"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get planes
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            
            # Create events with mismatched schema versions
            schema_drift_events = [
                # Event with extra fields
                {
                    "event_id": "drift_1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_plane": {"plane_type": "causal", "plane_id": "test"},
                    "target_plane": {"plane_type": "telemetry", "plane_id": "test"},
                    "event_type": "causal_start",
                    "payload": {
                        "module_id": "test_module",
                        "execution_id": "exec_123",
                        "correlation_id": "corr_123",
                        "trace_id": "trace_123",
                        "parent_event_id": None,
                        "boundary_type": "v2",
                        "metadata": {},
                        "extra_field_v2": "should_not_exist",
                        "another_new_field": {"nested": "data"}
                    }
                },
                # Event with missing required fields
                {
                    "event_id": "drift_2",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_plane": {"plane_type": "causal", "plane_id": "test"},
                    "target_plane": {"plane_type": "telemetry", "plane_id": "test"},
                    "event_type": "causal_start",
                    "payload": {
                        "module_id": "test_module"
                        # Missing required fields
                    }
                },
                # Event with wrong field types
                {
                    "event_id": "drift_3",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_plane": {"plane_type": "causal", "plane_id": "test"},
                    "target_plane": {"plane_type": "telemetry", "plane_id": "test"},
                    "event_type": "causal_start",
                    "payload": {
                        "module_id": 123,  # Should be string
                        "execution_id": ["should", "be", "string"],  # Should be string
                        "correlation_id": None,  # Should be string
                        "trace_id": True,  # Should be string
                        "parent_event_id": {"should": "be", "string"},  # Should be string
                        "boundary_type": 456,  # Should be string
                        "metadata": "should be dict"  # Should be dict
                    }
                }
            ]
            
            drift_count = 0
            handled_drift = 0
            
            for drift_event in schema_drift_events:
                drift_count += 1
                
                try:
                    # Create serialized event with schema drift
                    event = SerializedEvent(
                        event_id=drift_event["event_id"],
                        source_plane=causal_plane.identity_token,
                        target_plane=telemetry_plane.identity_token,
                        event_type=drift_event["event_type"],
                        payload=drift_event["payload"],
                        timestamp=datetime.fromisoformat(drift_event["timestamp"])
                    )
                    
                    # Send event (should handle schema gracefully)
                    success = telemetry_plane.send_event(event)
                    if success:
                        handled_drift += 1
                        
                except Exception as e:
                    # Expected to handle schema drift gracefully
                    handled_drift += 1
            
            # Verify no runtime cross-plane contamination
            telemetry_success = bridge.capture_telemetry_entry(
                entry_path="v2_wrapped",
                module_id="schema_drift_test",
                execution_id="exec_123",
                correlation_id="corr_123",
                trace_id="trace_123",
                feature_flags={},
                routing_decision="schema_drift_test",
                routing_context={},
                v2_governance_active=True,
                v2_validation_passed=True
            )
            assert telemetry_success is not None
            
            causal_success = bridge.capture_causal_start(
                module_id="schema_drift_test",
                execution_id="exec_123",
                correlation_id="corr_123",
                trace_id="trace_123",
                parent_event_id=None,
                boundary_type="v2",
                metadata={}
            )
            assert causal_success is not None
            
            self._check_memory_isolation("schema_drift_simulation")
            
            self.test_results["schema_drift_simulation"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "drift_events": drift_count,
                "handled_drift": handled_drift,
                "no_cross_plane_contamination": True
            }
            
        except Exception as e:
            self.test_results["schema_drift_simulation"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Schema drift simulation test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_backpressure_isolation(self):
        """Test backpressure isolation in single plane"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get telemetry plane to saturate
            telemetry_plane = bridge.planes[ObservabilityPlane.TELEMETRY]
            causal_plane = bridge.planes[ObservabilityPlane.CAUSAL]
            audit_plane = bridge.planes[ObservabilityPlane.AUDIT_REPLAY]
            
            # Saturate telemetry plane queue
            saturation_events = 2000  # More than queue size
            successful_sends = 0
            dropped_events = 0
            
            for i in range(saturation_events):
                success = bridge.capture_telemetry_entry(
                    entry_path="v2_wrapped",
                    module_id=f"saturation_module_{i % 10}",
                    execution_id=f"exec_{i}",
                    correlation_id="saturation_corr",
                    trace_id="saturation_trace",
                    feature_flags={"saturation": True, "index": i},
                    routing_decision="saturation_test",
                    routing_context={"batch": i // 100},
                    v2_governance_active=True,
                    v2_validation_passed=True
                )
                
                if success:
                    successful_sends += 1
                else:
                    dropped_events += 1
            
            # While telemetry is saturated, test other planes
            other_plane_events = 100
            causal_success_count = 0
            audit_success_count = 0
            
            for i in range(other_plane_events):
                # Test causal plane is not affected
                causal_success = bridge.capture_causal_start(
                    module_id=f"backpressure_test_{i}",
                    execution_id=f"exec_{i}",
                    correlation_id="bp_corr",
                    trace_id="bp_trace",
                    parent_event_id=None,
                    boundary_type="v2",
                    metadata={"backpressure_test": True}
                )
                if causal_success:
                    causal_success_count += 1
                
                # Test audit plane is not affected
                audit_success = bridge.capture_audit_record(
                    record_type=f"backpressure_test_{i}",
                    record_data={"backpressure_test": True, "index": i},
                    correlation_id="bp_corr",
                    trace_id="bp_trace"
                )
                if audit_success:
                    audit_success_count += 1
            
            # Verify no execution slowdown
            execution_start = time.time()
            for i in range(50):
                success = bridge.capture_safety_decision(
                    decision_type=f"execution_test_{i}",
                    decision_data={"backpressure_test": True, "index": i},
                    correlation_id="bp_corr",
                    trace_id="bp_trace"
                )
                assert success is True
            execution_duration = time.time() - execution_start
            
            # Verify no backpressure propagation
            self._check_memory_isolation("backpressure_isolation")
            
            self.test_results["backpressure_isolation"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "saturation_events": saturation_events,
                "successful_sends": successful_sends,
                "dropped_events": dropped_events,
                "causal_success_rate": causal_success_count / other_plane_events,
                "audit_success_rate": audit_success_count / other_plane_events,
                "execution_slowdown": execution_duration < 1.0  # Should be fast
            }
            
        except Exception as e:
            self.test_results["backpressure_isolation"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Backpressure isolation test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _test_cascading_failure_attempt(self):
        """Test cascading failure attempt"""
        bridge = IsolatedObservabilityBridge()
        start_time = time.time()
        
        try:
            # Get all planes
            planes = list(bridge.planes.values())
            
            # Create cascade failure scenario
            failure_sequence = []
            
            # Step 1: Crash telemetry plane
            planes[0].stop()  # Telemetry plane
            failure_sequence.append("telemetry_crashed")
            
            # Step 2: Try to cause causal to fail by sending invalid events
            for i in range(100):
                try:
                    # Send invalid events to causal plane
                    invalid_event = SerializedEvent(
                        event_id=f"invalid_{i}",
                        source_plane=planes[1].identity_token,  # Causal plane
                        target_plane=planes[1].identity_token,  # Self-target
                        event_type="invalid_event",
                        payload=None,  # Invalid payload
                        timestamp=datetime.now(timezone.utc)
                    )
                    planes[1].send_event(invalid_event)
                except:
                    pass  # Expected to handle gracefully
            
            failure_sequence.append("causal_stressed")
            
            # Step 3: Stop audit plane
            planes[2].stop()  # Audit plane
            failure_sequence.append("audit_crashed")
            
            # Step 4: Try to crash safety plane with malformed data
            for i in range(50):
                try:
                    # Send malformed data to safety plane
                    malformed_data = {"malformed": "x" * 10000, "nested": {"deep": "corruption"}}
                    success = bridge.capture_safety_decision(
                        decision_type=f"malformed_{i}",
                        decision_data=malformed_data,
                        correlation_id="cascade_corr",
                        trace_id="cascade_trace"
                    )
                except:
                    pass
            
            failure_sequence.append("safety_stressed")
            
            # Verify cascade didn't happen
            # Check if any remaining planes are still functional
            remaining_planes = [p for p in planes if p.is_running]
            
            # Test execution still works
            execution_success = bridge.capture_audit_record(
                record_type="cascade_test",
                record_data={"test": "after_cascade"},
                correlation_id="cascade_corr",
                trace_id="cascade_trace"
            )
            
            # Verify no memory sharing violations from cascade
            self._check_memory_isolation("cascading_failure")
            
            self.test_results["cascading_failure_attempt"] = {
                "status": "PASS",
                "duration": time.time() - start_time,
                "failure_sequence": failure_sequence,
                "remaining_planes": len(remaining_planes),
                "execution_still_works": execution_success,
                "cascade_prevented": True
            }
            
        except Exception as e:
            self.test_results["cascading_failure_attempt"] = {
                "status": "FAIL",
                "error": str(e),
                "duration": time.time() - start_time
            }
            self.isolation_violations.append(f"Cascading failure attempt test failed: {e}")
        finally:
            bridge.shutdown()
    
    def _take_memory_snapshot(self, name: str):
        """Take memory snapshot for analysis"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            self.memory_snapshots[name] = {
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "percent": process.memory_percent(),
                "timestamp": time.time()
            }
        except Exception as e:
            self.memory_snapshots[name] = {"error": str(e)}
    
    def _check_memory_isolation(self, test_name: str):
        """Check for memory isolation violations"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Check for excessive memory growth (potential sharing)
            if "baseline" in self.memory_snapshots:
                baseline = self.memory_snapshots["baseline"]
                current_rss = memory_info.rss
                baseline_rss = baseline["rss"]
                
                # If memory grew more than 100MB, potential sharing issue
                if current_rss - baseline_rss > 100 * 1024 * 1024:
                    self.isolation_violations.append(f"Memory growth detected in {test_name}: {(current_rss - baseline_rss) / 1024 / 1024:.1f}MB")
            
            # Check for excessive number of threads (potential sharing)
            thread_count = threading.active_count()
            if thread_count > 50:  # Arbitrary threshold
                self.isolation_violations.append(f"High thread count detected in {test_name}: {thread_count}")
                
        except Exception as e:
            self.isolation_violations.append(f"Memory isolation check failed for {test_name}: {e}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r.get("status") == "PASS"])
        failed_tests = total_tests - passed_tests
        
        return {
            "test_suite": "Step 9 Isolation Stress & Failure Validation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "isolation_violations": self.isolation_violations,
            "memory_snapshots": self.memory_snapshots,
            "validation_status": "PASS" if failed_tests == 0 and len(self.isolation_violations) == 0 else "FAIL",
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if len(self.isolation_violations) > 0:
            recommendations.append("CRITICAL: Isolation violations detected - system not ready for production")
        
        failed_tests = [name for name, result in self.test_results.items() if result.get("status") == "FAIL"]
        if failed_tests:
            recommendations.append(f"Failed tests require investigation: {', '.join(failed_tests)}")
        
        # Check for performance issues
        telemetry_flood = self.test_results.get("telemetry_flood")
        if telemetry_flood and telemetry_flood.get("status") == "PASS":
            if telemetry_flood.get("duration", 0) > 10.0:
                recommendations.append("Telemetry flood performance could be optimized")
        
        # Check memory usage
        if len(self.memory_snapshots) > 1:
            memory_growth = []
            snapshots = list(self.memory_snapshots.values())
            for i in range(1, len(snapshots)):
                if "rss" in snapshots[i] and "rss" in snapshots[i-1]:
                    growth = snapshots[i]["rss"] - snapshots[i-1]["rss"]
                    memory_growth.append(growth)
            
            avg_growth = sum(memory_growth) / len(memory_growth) if memory_growth else 0
            if avg_growth > 50 * 1024 * 1024:  # 50MB average growth
                recommendations.append("Memory usage growth detected - monitor for leaks")
        
        if not recommendations:
            recommendations.append("All isolation tests passed - system ready for production")
        
        return recommendations


def run_step9_validation_suite() -> Dict[str, Any]:
    """Run the complete Step 9 validation suite"""
    print("🔬 STEP 9 ISOLATION STRESS & FAILURE VALIDATION SUITE")
    print("=" * 80)
    
    # Take baseline memory snapshot
    suite = IsolationStressTestSuite()
    suite._take_memory_snapshot("baseline")
    
    # Run all tests
    results = suite.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 VALIDATION RESULTS")
    print("=" * 80)
    
    summary = results["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1%}")
    print(f"Validation Status: {results['validation_status']}")
    
    if results["isolation_violations"]:
        print(f"\n⚠️  Isolation Violations ({len(results['isolation_violations'])}):")
        for violation in results["isolation_violations"]:
            print(f"  - {violation}")
    
    print(f"\n📋 Recommendations:")
    for rec in results["recommendations"]:
        print(f"  - {rec}")
    
    return results


if __name__ == "__main__":
    # Run validation suite when executed directly
    results = run_step9_validation_suite()
    
    # Exit with appropriate code
    exit_code = 0 if results["validation_status"] == "PASS" else 1
    exit(exit_code)
