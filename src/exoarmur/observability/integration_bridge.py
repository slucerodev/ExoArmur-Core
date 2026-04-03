"""
Observability Integration Layer
Integration of existing systems with isolated observability planes
"""

import json
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from .plane_manager import (
    ObservabilityPlane, SerializedEvent, get_observability_plane_manager
)
from .isolated_adapters import ObservabilityPlaneFactory

logger = logging.getLogger(__name__)


class IsolatedObservabilityBridge:
    """
    Bridge for integrating existing observability systems with isolated planes
    
    Provides the same interface as existing systems but routes through isolated planes
    """
    
    def __init__(self, isolation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize isolated observability bridge
        
        Args:
            isolation_config: Configuration for plane isolation
        """
        self.isolation_config = isolation_config or {}
        self.plane_manager = get_observability_plane_manager()
        self.planes: Dict[ObservabilityPlane, Any] = {}
        self._lock = threading.RLock()
        self._initialize_planes()
    
    def _initialize_planes(self):
        """Initialize all observability planes"""
        try:
            # Create all planes
            self.planes = ObservabilityPlaneFactory.create_all_planes(self.isolation_config)
            logger.info("All observability planes initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize observability planes: {e}")
            raise
    
    def capture_telemetry_entry(self, entry_path: str, module_id: str, execution_id: str,
                               correlation_id: Optional[str], trace_id: Optional[str],
                               feature_flags: Dict[str, Any], routing_decision: str,
                               routing_context: Dict[str, Any], v2_governance_active: bool,
                               v2_validation_passed: bool) -> Optional[str]:
        """
        Capture telemetry entry through isolated plane
        
        Args:
            entry_path: Entry path
            module_id: Module ID
            execution_id: Execution ID
            correlation_id: Correlation ID
            trace_id: Trace ID
            feature_flags: Feature flags
            routing_decision: Routing decision
            routing_context: Routing context
            v2_governance_active: V2 governance active flag
            v2_validation_passed: V2 validation passed flag
            
        Returns:
            Event ID if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"tel_entry_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.TELEMETRY].identity_token,
                event_type="telemetry_entry",
                payload={
                    'event_id': f"tel_entry_{datetime.now(timezone.utc).timestamp()}",
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'entry_path': entry_path,
                    'module_id': module_id,
                    'execution_id': execution_id,
                    'correlation_id': correlation_id,
                    'trace_id': trace_id,
                    'feature_flags': feature_flags,
                    'routing_decision': routing_decision,
                    'routing_context': routing_context,
                    'v2_governance_active': v2_governance_active,
                    'v2_validation_passed': v2_validation_passed
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to telemetry plane
            success = self.plane_manager.event_bridge.route_event(event)
            
            return event.event_id if success else None
            
        except Exception as e:
            logger.error(f"Error capturing telemetry entry: {e}")
            return None
    
    def capture_telemetry_exit(self, event_id: str, success: bool, result_summary: Dict[str, Any],
                             processing_duration_ms: Optional[float]) -> bool:
        """
        Capture telemetry exit through isolated plane
        
        Args:
            event_id: Event ID
            success: Success flag
            result_summary: Result summary
            processing_duration_ms: Processing duration in milliseconds
            
        Returns:
            True if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"tel_exit_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.TELEMETRY].identity_token,
                event_type="telemetry_exit",
                payload={
                    'event_id': event_id,
                    'success': success,
                    'result_summary': result_summary,
                    'processing_duration_ms': processing_duration_ms
                },
                timestamp=datetime.now(timezone.utc)
            )
            
            # Route to telemetry plane
            return self.plane_manager.event_bridge.route_event(event)
            
        except Exception as e:
            logger.error(f"Error capturing telemetry exit: {e}")
            return False
    
    def capture_causal_start(self, module_id: str, execution_id: str, correlation_id: Optional[str],
                           trace_id: Optional[str], parent_event_id: Optional[str],
                           boundary_type: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Capture causal start through isolated plane
        
        Args:
            module_id: Module ID
            execution_id: Execution ID
            correlation_id: Correlation ID
            trace_id: Trace ID
            parent_event_id: Parent event ID
            boundary_type: Boundary type
            metadata: Metadata
            
        Returns:
            Event ID if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"causal_start_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.CAUSAL].identity_token,
                event_type="causal_start",
                payload={
                    'module_id': module_id,
                    'execution_id': execution_id,
                    'correlation_id': correlation_id,
                    'trace_id': trace_id,
                    'parent_event_id': parent_event_id,
                    'boundary_type': boundary_type,
                    'metadata': metadata
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to causal plane
            success = self.plane_manager.event_bridge.route_event(event)
            
            return event.event_id if success else None
            
        except Exception as e:
            logger.error(f"Error capturing causal start: {e}")
            return None
    
    def capture_causal_decision(self, decision_type: str, module_id: str, execution_id: str,
                              correlation_id: Optional[str], trace_id: Optional[str],
                              parent_event_id: Optional[str], boundary_type: str,
                              decision_metadata: Dict[str, Any]) -> Optional[str]:
        """
        Capture causal decision through isolated plane
        
        Args:
            decision_type: Decision type
            module_id: Module ID
            execution_id: Execution ID
            correlation_id: Correlation ID
            trace_id: Trace ID
            parent_event_id: Parent event ID
            boundary_type: Boundary type
            decision_metadata: Decision metadata
            
        Returns:
            Event ID if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"causal_decision_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.CAUSAL].identity_token,
                event_type="causal_decision",
                payload={
                    'decision_type': decision_type,
                    'module_id': module_id,
                    'execution_id': execution_id,
                    'correlation_id': correlation_id,
                    'trace_id': trace_id,
                    'parent_event_id': parent_event_id,
                    'boundary_type': boundary_type,
                    'decision_metadata': decision_metadata
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to causal plane
            success = self.plane_manager.event_bridge.route_event(event)
            
            return event.event_id if success else None
            
        except Exception as e:
            logger.error(f"Error capturing causal decision: {e}")
            return None
    
    def capture_causal_end(self, execution_start_record_id: str, module_id: str, execution_id: str,
                          correlation_id: Optional[str], trace_id: Optional[str],
                          boundary_type: str, success: bool, duration_ms: Optional[float],
                          metadata: Dict[str, Any]) -> bool:
        """
        Capture causal end through isolated plane
        
        Args:
            execution_start_record_id: Execution start record ID
            module_id: Module ID
            execution_id: Execution ID
            correlation_id: Correlation ID
            trace_id: Trace ID
            boundary_type: Boundary type
            success: Success flag
            duration_ms: Duration in milliseconds
            metadata: Metadata
            
        Returns:
            True if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"causal_end_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.CAUSAL].identity_token,
                event_type="causal_end",
                payload={
                    'execution_start_record_id': execution_start_record_id,
                    'module_id': module_id,
                    'execution_id': execution_id,
                    'correlation_id': correlation_id,
                    'trace_id': trace_id,
                    'boundary_type': boundary_type,
                    'success': success,
                    'duration_ms': duration_ms,
                    'metadata': metadata
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to causal plane
            return self.plane_manager.event_bridge.route_event(event)
            
        except Exception as e:
            logger.error(f"Error capturing causal end: {e}")
            return False
    
    def capture_audit_record(self, record_type: str, record_data: Dict[str, Any],
                           correlation_id: Optional[str], trace_id: Optional[str]) -> bool:
        """
        Capture audit record through isolated plane
        
        Args:
            record_type: Record type
            record_data: Record data
            correlation_id: Correlation ID
            trace_id: Trace ID
            
        Returns:
            True if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"audit_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.AUDIT_REPLAY].identity_token,
                event_type="audit_record",
                payload={
                    'record_type': record_type,
                    'record_data': record_data
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to audit/replay plane
            return self.plane_manager.event_bridge.route_event(event)
            
        except Exception as e:
            logger.error(f"Error capturing audit record: {e}")
            return False
    
    def capture_safety_decision(self, decision_type: str, decision_data: Dict[str, Any],
                               correlation_id: Optional[str], trace_id: Optional[str]) -> bool:
        """
        Capture safety decision through isolated plane
        
        Args:
            decision_type: Decision type
            decision_data: Decision data
            correlation_id: Correlation ID
            trace_id: Trace ID
            
        Returns:
            True if successful
        """
        try:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"safety_{datetime.now(timezone.utc).timestamp()}",
                source_plane=self.planes[ObservabilityPlane.EXECUTION].identity_token,
                target_plane=self.planes[ObservabilityPlane.SAFETY_DECISION].identity_token,
                event_type="safety_decision",
                payload={
                    'decision_type': decision_type,
                    'decision_data': decision_data
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            # Route to safety decision plane
            return self.plane_manager.event_bridge.route_event(event)
            
        except Exception as e:
            logger.error(f"Error capturing safety decision: {e}")
            return False
    
    def get_telemetry_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get telemetry events from isolated plane"""
        try:
            telemetry_plane = self.planes[ObservabilityPlane.TELEMETRY]
            if hasattr(telemetry_plane, 'adapter'):
                return telemetry_plane.adapter.get_events(limit)
            return []
        except Exception as e:
            logger.error(f"Error getting telemetry events: {e}")
            return []
    
    def get_causal_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get causal records from isolated plane"""
        try:
            causal_plane = self.planes[ObservabilityPlane.CAUSAL]
            if hasattr(causal_plane, 'adapter'):
                return causal_plane.adapter.get_records(limit)
            return []
        except Exception as e:
            logger.error(f"Error getting causal records: {e}")
            return []
    
    def get_causal_chains(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get causal chains from isolated plane"""
        try:
            causal_plane = self.planes[ObservabilityPlane.CAUSAL]
            if hasattr(causal_plane, 'adapter'):
                return causal_plane.adapter.get_causal_chains()
            return {}
        except Exception as e:
            logger.error(f"Error getting causal chains: {e}")
            return {}
    
    def get_audit_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get audit records from isolated plane"""
        try:
            audit_plane = self.planes[ObservabilityPlane.AUDIT_REPLAY]
            if hasattr(audit_plane, 'adapter'):
                return audit_plane.adapter.get_audit_records(limit)
            return []
        except Exception as e:
            logger.error(f"Error getting audit records: {e}")
            return []
    
    def get_safety_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get safety decisions from isolated plane"""
        try:
            safety_plane = self.planes[ObservabilityPlane.SAFETY_DECISION]
            if hasattr(safety_plane, 'adapter'):
                return safety_plane.adapter.get_safety_decisions(limit)
            return []
        except Exception as e:
            logger.error(f"Error getting safety decisions: {e}")
            return []
    
    def get_plane_status(self) -> Dict[str, Any]:
        """Get status of all observability planes"""
        return self.plane_manager.get_plane_manager_status()
    
    def shutdown(self):
        """Shutdown all observability planes"""
        with self._lock:
            try:
                self.plane_manager.shutdown()
                logger.info("Isolated observability bridge shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down observability bridge: {e}")


# Global isolated observability bridge instance
_isolated_observability_bridge: Optional[IsolatedObservabilityBridge] = None


def get_isolated_observability_bridge() -> IsolatedObservabilityBridge:
    """Get global isolated observability bridge instance"""
    global _isolated_observability_bridge
    if _isolated_observability_bridge is None:
        _isolated_observability_bridge = IsolatedObservabilityBridge()
    return _isolated_observability_bridge


def configure_isolated_observability_bridge(isolation_config: Optional[Dict[str, Any]] = None) -> IsolatedObservabilityBridge:
    """Configure global isolated observability bridge"""
    global _isolated_observability_bridge
    if _isolated_observability_bridge:
        _isolated_observability_bridge.shutdown()
    
    _isolated_observability_bridge = IsolatedObservabilityBridge(isolation_config)
    return _isolated_observability_bridge
