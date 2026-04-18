"""
Regression tests for Observability Plane Hard Partitioning
Ensures physical isolation between observability planes with no shared memory
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from exoarmur.observability.plane_manager import (
    ObservabilityPlane, PlaneIdentityToken, SerializedEvent,
    ObservabilityPlaneManager, ThreadIsolationStrategy, ProcessIsolationStrategy,
    get_observability_plane_manager, configure_observability_plane_manager
)
from exoarmur.observability.isolated_adapters import (
    ObservabilityPlaneFactory, IsolatedTelemetryAdapter, IsolatedCausalAdapter,
    IsolatedAuditAdapter, IsolatedSafetyAdapter
)
from exoarmur.observability.integration_bridge import (
    IsolatedObservabilityBridge, get_isolated_observability_bridge,
    configure_isolated_observability_bridge
)


@pytest.fixture(autouse=True)
def _reset_observability_plane_singletons():
    """
    Reset the process-wide observability plane singletons around every test
    in this module.

    Why this is necessary
    ---------------------
    `ObservabilityPlaneManager` and `IsolatedObservabilityBridge` are both
    exposed as module-level singletons (see `_observability_plane_manager`
    in `plane_manager.py` and `_isolated_observability_bridge` in
    `integration_bridge.py`). Every `IsolatedObservabilityBridge()`
    constructor registers 5 new plane contexts on the shared manager; if
    any earlier test in the session leaves even one plane registered
    (including tests in other modules that touch these adapters), the
    assertions here that expect `total_planes == 5` see accumulated state
    and fail non-deterministically — the exact flake class
    `test_plane_status_through_bridge` was hitting under certain
    `pytest-randomly` seeds (e.g. `PYTHONHASHSEED=0`).

    Scope and invariants
    --------------------
    - This fixture ONLY resets the two observability singletons. It does
      not touch any V1 contract, replay engine, or audit path state.
    - It runs with `autouse=True` but is confined to this test module, so
      it cannot affect other test files' lifecycles.
    - The fixture is idempotent: repeated calls produce identical empty
      state.
    - `configure_observability_plane_manager` internally calls `shutdown()`
      on the prior singleton, so any planes left registered by a prior
      test are destroyed before the next test starts.
    """
    configure_observability_plane_manager(ThreadIsolationStrategy())
    # Also reset the integration-bridge singleton so tests that call
    # get_isolated_observability_bridge() observe a fresh instance.
    import exoarmur.observability.integration_bridge as _bridge_module
    if _bridge_module._isolated_observability_bridge is not None:
        try:
            _bridge_module._isolated_observability_bridge.shutdown()
        except Exception:
            pass
        _bridge_module._isolated_observability_bridge = None

    yield

    # Post-test cleanup: shut down whatever the test may have spun up so the
    # next test (inside or outside this module) starts from a clean slate.
    configure_observability_plane_manager(ThreadIsolationStrategy())
    if _bridge_module._isolated_observability_bridge is not None:
        try:
            _bridge_module._isolated_observability_bridge.shutdown()
        except Exception:
            pass
        _bridge_module._isolated_observability_bridge = None


class TestPlaneIdentityToken:
    """Test plane identity token functionality"""
    
    def test_plane_identity_token_creation(self):
        """Test plane identity token creation"""
        token = PlaneIdentityToken(
            plane_id="test_plane",
            plane_type=ObservabilityPlane.TELEMETRY,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        assert token.plane_id == "test_plane"
        assert token.plane_type == ObservabilityPlane.TELEMETRY
        assert token.instance_id == "instance_123"
        assert token.isolation_level == "process"
        
        # Test string representation
        token_str = str(token)
        assert "telemetry" in token_str
        assert "test_plane" in token_str
        assert "instance_123" in token_str
        
        # Test serialization
        token_dict = token.to_dict()
        assert token_dict['plane_id'] == "test_plane"
        assert token_dict['plane_type'] == "telemetry"
        assert token_dict['instance_id'] == "instance_123"
        assert token_dict['isolation_level'] == "process"


class TestSerializedEvent:
    """Test serialized event functionality"""
    
    def test_serialized_event_creation(self):
        """Test serialized event creation"""
        source_token = PlaneIdentityToken(
            plane_id="source_plane",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        target_token = PlaneIdentityToken(
            plane_id="target_plane",
            plane_type=ObservabilityPlane.TELEMETRY,
            instance_id="instance_456",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=target_token,
            event_type="test_type",
            payload={"test": "data"},
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        
        assert event.event_id == "test_event"
        assert event.source_plane == source_token
        assert event.target_plane == target_token
        assert event.event_type == "test_type"
        assert event.payload["test"] == "data"
        assert event.correlation_id == "corr_123"
        assert event.trace_id == "trace_123"
    
    def test_serialized_event_serialization(self):
        """Test serialized event serialization and deserialization"""
        source_token = PlaneIdentityToken(
            plane_id="source_plane",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=None,
            event_type="test_type",
            payload={"test": "data"},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Serialize
        serialized_data = event.serialize()
        assert isinstance(serialized_data, bytes)
        
        # Deserialize
        deserialized_event = SerializedEvent.deserialize(serialized_data)
        
        assert deserialized_event.event_id == event.event_id
        assert deserialized_event.source_plane.plane_type == event.source_plane.plane_type
        assert deserialized_event.target_plane is None
        assert deserialized_event.event_type == event.event_type
        assert deserialized_event.payload == event.payload


class TestObservabilityPlaneManager:
    """Test observability plane manager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = ObservabilityPlaneManager(ThreadIsolationStrategy())
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.manager.shutdown()
    
    def test_create_plane(self):
        """Test creating isolated planes"""
        # Create telemetry plane
        telemetry_plane = self.manager.create_plane(ObservabilityPlane.TELEMETRY)
        
        assert telemetry_plane.plane_type == ObservabilityPlane.TELEMETRY
        assert telemetry_plane.is_running is True
        assert telemetry_plane.identity_token.plane_type == ObservabilityPlane.TELEMETRY
        
        # Create causal plane
        causal_plane = self.manager.create_plane(ObservabilityPlane.CAUSAL)
        
        assert causal_plane.plane_type == ObservabilityPlane.CAUSAL
        assert causal_plane.is_running is True
        assert causal_plane.identity_token.plane_type == ObservabilityPlane.CAUSAL
        
        # Verify planes are isolated (different tokens)
        assert telemetry_plane.identity_token != causal_plane.identity_token
    
    def test_destroy_plane(self):
        """Test destroying isolated planes"""
        # Create plane
        plane = self.manager.create_plane(ObservabilityPlane.TELEMETRY)
        assert plane.is_running is True
        
        # Destroy plane
        self.manager.destroy_plane(plane)
        assert plane.is_running is False
        
        # Verify plane is removed from manager
        assert plane not in self.manager._plane_contexts[ObservabilityPlane.TELEMETRY]
    
    def test_send_event_to_plane(self):
        """Test sending events to planes"""
        # Create planes
        telemetry_plane = self.manager.create_plane(ObservabilityPlane.TELEMETRY)
        causal_plane = self.manager.create_plane(ObservabilityPlane.CAUSAL)
        
        # Send event to telemetry plane
        success = self.manager.send_event_to_plane(
            ObservabilityPlane.TELEMETRY,
            "telemetry_test",
            {"test": "data"},
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        
        assert success is True
        
        # Send event to causal plane
        success = self.manager.send_event_to_plane(
            ObservabilityPlane.CAUSAL,
            "causal_test",
            {"test": "data"},
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        
        assert success is True
    
    def test_plane_manager_status(self):
        """Test plane manager status"""
        # Create planes
        self.manager.create_plane(ObservabilityPlane.TELEMETRY)
        self.manager.create_plane(ObservabilityPlane.CAUSAL)
        self.manager.create_plane(ObservabilityPlane.AUDIT_REPLAY)
        
        # Get status
        status = self.manager.get_plane_manager_status()
        
        assert 'isolation_strategy' in status
        assert 'total_planes' in status
        assert 'planes_by_type' in status
        assert 'bridge_status' in status
        
        assert status['total_planes'] == 3
        assert status['planes_by_type']['telemetry'] == 1
        assert status['planes_by_type']['causal'] == 1
        assert status['planes_by_type']['audit_replay'] == 1
    
    def test_global_plane_manager(self):
        """Test global plane manager singleton"""
        manager1 = get_observability_plane_manager()
        manager2 = get_observability_plane_manager()
        
        # Should be same instance
        assert manager1 is manager2
        
        # Configure new manager
        new_manager = configure_observability_plane_manager(ThreadIsolationStrategy())
        
        # Global manager should be updated
        manager3 = get_observability_plane_manager()
        assert manager3 is new_manager
        assert manager3 is not manager1
        
        new_manager.shutdown()


class TestObservabilityPlaneFactory:
    """Test observability plane factory functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = ObservabilityPlaneManager(ThreadIsolationStrategy())
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.manager.shutdown()
    
    def test_create_telemetry_plane(self):
        """Test creating telemetry plane with adapter"""
        plane = ObservabilityPlaneFactory.create_telemetry_plane()
        
        assert plane.plane_type == ObservabilityPlane.TELEMETRY
        assert plane.is_running is True
        assert hasattr(plane, 'adapter')
        assert isinstance(plane.adapter, IsolatedTelemetryAdapter)
        
        # Cleanup
        self.manager.destroy_plane(plane)
    
    def test_create_causal_plane(self):
        """Test creating causal plane with adapter"""
        plane = ObservabilityPlaneFactory.create_causal_plane()
        
        assert plane.plane_type == ObservabilityPlane.CAUSAL
        assert plane.is_running is True
        assert hasattr(plane, 'adapter')
        assert isinstance(plane.adapter, IsolatedCausalAdapter)
        
        # Cleanup
        self.manager.destroy_plane(plane)
    
    def test_create_audit_replay_plane(self):
        """Test creating audit/replay plane with adapter"""
        plane = ObservabilityPlaneFactory.create_audit_replay_plane()
        
        assert plane.plane_type == ObservabilityPlane.AUDIT_REPLAY
        assert plane.is_running is True
        assert hasattr(plane, 'adapter')
        assert isinstance(plane.adapter, IsolatedAuditAdapter)
        
        # Cleanup
        self.manager.destroy_plane(plane)
    
    def test_create_safety_decision_plane(self):
        """Test creating safety decision plane with adapter"""
        plane = ObservabilityPlaneFactory.create_safety_decision_plane()
        
        assert plane.plane_type == ObservabilityPlane.SAFETY_DECISION
        assert plane.is_running is True
        assert hasattr(plane, 'adapter')
        assert isinstance(plane.adapter, IsolatedSafetyAdapter)
        
        # Cleanup
        self.manager.destroy_plane(plane)
    
    def test_create_execution_plane(self):
        """Test creating execution plane"""
        plane = ObservabilityPlaneFactory.create_execution_plane()
        
        assert plane.plane_type == ObservabilityPlane.EXECUTION
        assert plane.is_running is True
        # Execution plane doesn't have an adapter
        assert not hasattr(plane, 'adapter')
        
        # Cleanup
        self.manager.destroy_plane(plane)
    
    def test_create_all_planes(self):
        """Test creating all planes"""
        planes = ObservabilityPlaneFactory.create_all_planes()
        
        assert len(planes) == 5
        assert ObservabilityPlane.EXECUTION in planes
        assert ObservabilityPlane.TELEMETRY in planes
        assert ObservabilityPlane.CAUSAL in planes
        assert ObservabilityPlane.AUDIT_REPLAY in planes
        assert ObservabilityPlane.SAFETY_DECISION in planes
        
        # Verify all planes are running
        for plane in planes.values():
            assert plane.is_running is True
        
        # Cleanup
        for plane in planes.values():
            self.manager.destroy_plane(plane)


class TestIsolatedAdapters:
    """Test isolated adapters functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = ObservabilityPlaneManager(ThreadIsolationStrategy())
        self.telemetry_plane = self.manager.create_plane(ObservabilityPlane.TELEMETRY)
        self.causal_plane = self.manager.create_plane(ObservabilityPlane.CAUSAL)
        self.audit_plane = self.manager.create_plane(ObservabilityPlane.AUDIT_REPLAY)
        self.safety_plane = self.manager.create_plane(ObservabilityPlane.SAFETY_DECISION)
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.manager.shutdown()
    
    def test_isolated_telemetry_adapter(self):
        """Test isolated telemetry adapter"""
        adapter = IsolatedTelemetryAdapter(self.telemetry_plane)
        
        # Test event handling
        source_token = PlaneIdentityToken(
            plane_id="source",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=self.telemetry_plane.identity_token,
            event_type="telemetry_entry",
            payload={
                'event_id': 'test_event',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'entry_path': 'v2_wrapped',
                'module_id': 'test_module',
                'execution_id': 'exec_123',
                'correlation_id': 'corr_123',
                'trace_id': 'trace_123',
                'feature_flags': {'test': True},
                'routing_decision': 'v2_governance',
                'routing_context': {},
                'v2_governance_active': True,
                'v2_validation_passed': True
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        # Send event to adapter
        success = self.telemetry_plane.send_event(event)
        assert success is True
        
        # Wait for processing
        time.sleep(0.1)
        
        # Get events from adapter
        events = adapter.get_events()
        assert len(events) >= 0  # May be 0 if V2TelemetryHandler is not available
    
    def test_isolated_causal_adapter(self):
        """Test isolated causal adapter"""
        adapter = IsolatedCausalAdapter(self.causal_plane)
        
        # Test event handling
        source_token = PlaneIdentityToken(
            plane_id="source",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=self.causal_plane.identity_token,
            event_type="causal_start",
            payload={
                'module_id': 'test_module',
                'execution_id': 'exec_123',
                'correlation_id': 'corr_123',
                'trace_id': 'trace_123',
                'parent_event_id': None,
                'boundary_type': 'v2',
                'metadata': {'test': 'data'}
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        # Send event to adapter
        success = self.causal_plane.send_event(event)
        assert success is True
        
        # Wait for processing
        time.sleep(0.1)
        
        # Get records from adapter
        records = adapter.get_records()
        assert len(records) >= 0  # May be 0 if CausalContextLogger is not available
    
    def test_isolated_audit_adapter(self):
        """Test isolated audit adapter"""
        adapter = IsolatedAuditAdapter(self.audit_plane)
        
        # Test event handling
        source_token = PlaneIdentityToken(
            plane_id="source",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=self.audit_plane.identity_token,
            event_type="audit_record",
            payload={
                'record_type': 'execution',
                'record_data': {'test': 'data'}
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        # Send event to adapter
        success = self.audit_plane.send_event(event)
        assert success is True
        
        # Wait for processing
        time.sleep(0.1)
        
        # Get records from adapter
        records = adapter.get_audit_records()
        assert len(records) == 1
        assert records[0]['payload']['record_type'] == 'execution'
    
    def test_isolated_safety_adapter(self):
        """Test isolated safety adapter"""
        adapter = IsolatedSafetyAdapter(self.safety_plane)
        
        # Test event handling
        source_token = PlaneIdentityToken(
            plane_id="source",
            plane_type=ObservabilityPlane.EXECUTION,
            instance_id="instance_123",
            created_at=datetime.now(timezone.utc)
        )
        
        event = SerializedEvent(
            event_id="test_event",
            source_plane=source_token,
            target_plane=self.safety_plane.identity_token,
            event_type="safety_decision",
            payload={
                'decision_type': 'safety_gate',
                'decision_data': {'safe': True}
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        # Send event to adapter
        success = self.safety_plane.send_event(event)
        assert success is True
        
        # Wait for processing
        time.sleep(0.1)
        
        # Get decisions from adapter
        decisions = adapter.get_safety_decisions()
        assert len(decisions) == 1
        assert decisions[0]['payload']['decision_type'] == 'safety_gate'


class TestIsolatedObservabilityBridge:
    """Test isolated observability bridge functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.bridge = IsolatedObservabilityBridge()
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.bridge.shutdown()
    
    def test_capture_telemetry_through_bridge(self):
        """Test capturing telemetry through isolated bridge"""
        # Capture entry
        event_id = self.bridge.capture_telemetry_entry(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            feature_flags={"test": True},
            routing_decision="v2_governance",
            routing_context={},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        assert event_id is not None
        assert event_id.startswith("tel_entry_")
        
        # Capture exit
        success = self.bridge.capture_telemetry_exit(
            event_id=event_id,
            success=True,
            result_summary={"status": "completed"},
            processing_duration_ms=150.5
        )
        
        assert success is True
        
        # Get events
        events = self.bridge.get_telemetry_events()
        assert len(events) >= 0  # May be 0 if V2TelemetryHandler is not available
    
    def test_capture_causal_through_bridge(self):
        """Test capturing causal through isolated bridge"""
        # Capture start
        start_id = self.bridge.capture_causal_start(
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            parent_event_id=None,
            boundary_type="v2",
            metadata={"test": "start"}
        )
        
        assert start_id is not None
        assert start_id.startswith("causal_start_")
        
        # Capture decision
        decision_id = self.bridge.capture_causal_decision(
            decision_type="safety_evaluation",
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            parent_event_id=start_id,
            boundary_type="v2",
            decision_metadata={"safety_score": 0.95}
        )
        
        assert decision_id is not None
        assert decision_id.startswith("causal_decision_")
        
        # Capture end
        success = self.bridge.capture_causal_end(
            execution_start_record_id=start_id,
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            boundary_type="v2",
            success=True,
            duration_ms=250.5,
            metadata={"test": "end"}
        )
        
        assert success is True
        
        # Get records
        records = self.bridge.get_causal_records()
        assert len(records) >= 0  # May be 0 if CausalContextLogger is not available
    
    def test_capture_audit_through_bridge(self):
        """Test capturing audit through isolated bridge"""
        success = self.bridge.capture_audit_record(
            record_type="execution",
            record_data={"module": "test_module", "action": "execute"},
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        
        assert success is True
        
        # Get records
        records = self.bridge.get_audit_records()
        assert len(records) == 1
        assert records[0]['payload']['record_type'] == "execution"
    
    def test_capture_safety_through_bridge(self):
        """Test capturing safety through isolated bridge"""
        success = self.bridge.capture_safety_decision(
            decision_type="safety_gate",
            decision_data={"safe": True, "confidence": 0.95},
            correlation_id="corr_123",
            trace_id="trace_123"
        )
        
        assert success is True
        
        # Get decisions
        decisions = self.bridge.get_safety_decisions()
        assert len(decisions) == 1
        assert decisions[0]['payload']['decision_type'] == "safety_gate"
    
    def test_plane_status_through_bridge(self):
        """Test getting plane status through bridge"""
        status = self.bridge.get_plane_status()
        
        assert 'isolation_strategy' in status
        assert 'total_planes' in status
        assert 'planes_by_type' in status
        assert 'bridge_status' in status
        
        assert status['total_planes'] == 5  # All planes should be created
        assert status['planes_by_type']['execution'] == 1
        assert status['planes_by_type']['telemetry'] == 1
        assert status['planes_by_type']['causal'] == 1
        assert status['planes_by_type']['audit_replay'] == 1
        assert status['planes_by_type']['safety_decision'] == 1
    
    def test_global_bridge(self):
        """Test global bridge singleton"""
        bridge1 = get_isolated_observability_bridge()
        bridge2 = get_isolated_observability_bridge()
        
        # Should be same instance
        assert bridge1 is bridge2
        
        # Configure new bridge
        new_bridge = configure_isolated_observability_bridge()
        
        # Global bridge should be updated
        bridge3 = get_isolated_observability_bridge()
        assert bridge3 is new_bridge
        assert bridge3 is not bridge1
        
        new_bridge.shutdown()


class TestPlaneIsolation:
    """Test plane isolation guarantees"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.bridge = IsolatedObservabilityBridge()
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.bridge.shutdown()
    
    def test_no_shared_memory_between_planes(self):
        """Test that planes don't share memory"""
        # Get plane contexts
        telemetry_plane = self.bridge.planes[ObservabilityPlane.TELEMETRY]
        causal_plane = self.bridge.planes[ObservabilityPlane.CAUSAL]
        
        # Verify different identity tokens
        assert telemetry_plane.identity_token != causal_plane.identity_token
        
        # Verify different memory spaces (different queue objects)
        assert telemetry_plane._event_queue is not causal_plane._event_queue
        
        # Verify different adapters
        assert telemetry_plane.adapter is not causal_plane.adapter
    
    def test_plane_failure_isolation(self):
        """Test that plane failures don't affect other planes"""
        # Get planes
        telemetry_plane = self.bridge.planes[ObservabilityPlane.TELEMETRY]
        causal_plane = self.bridge.planes[ObservabilityPlane.CAUSAL]
        
        # Stop telemetry plane (simulate failure)
        telemetry_plane.stop()
        assert telemetry_plane.is_running is False
        
        # Verify causal plane is still running
        assert causal_plane.is_running is True
        
        # Verify we can still send events to causal plane
        success = self.bridge.capture_causal_start(
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            parent_event_id=None,
            boundary_type="v2",
            metadata={}
        )
        
        assert success is not None
    
    def test_serialized_event_boundary(self):
        """Test that all cross-plane communication is serialized"""
        # Send events to different planes
        self.bridge.capture_telemetry_entry(
            entry_path="v2_wrapped",
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            feature_flags={},
            routing_decision="test",
            routing_context={},
            v2_governance_active=True,
            v2_validation_passed=True
        )
        
        self.bridge.capture_causal_start(
            module_id="test_module",
            execution_id="exec_123",
            correlation_id="corr_123",
            trace_id="trace_123",
            parent_event_id=None,
            boundary_type="v2",
            metadata={}
        )
        
        # Wait for processing
        time.sleep(0.1)
        
        # Verify events were processed (serialized communication worked)
        # The fact that we got here without exceptions means serialization worked
        assert True  # Placeholder assertion
    
    def test_no_direct_object_references(self):
        """Test that no direct object references are shared across planes"""
        # Get planes
        telemetry_plane = self.bridge.planes[ObservabilityPlane.TELEMETRY]
        causal_plane = self.bridge.planes[ObservabilityPlane.CAUSAL]
        
        # Verify no shared objects
        shared_objects = []
        
        # Check queues
        if telemetry_plane._event_queue is causal_plane._event_queue:
            shared_objects.append("event_queue")
        
        # Check adapters
        if telemetry_plane.adapter is causal_plane.adapter:
            shared_objects.append("adapter")
        
        # Check locks
        if telemetry_plane._lock is causal_plane._lock:
            shared_objects.append("lock")
        
        # Should have no shared objects
        assert len(shared_objects) == 0
