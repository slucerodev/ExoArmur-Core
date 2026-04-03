"""
Isolated Observability Adapters
Adapters for existing observability systems to work with isolated planes
"""

import json
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from .plane_manager import (
    ObservabilityPlane, IsolatedPlaneContext, SerializedEvent, 
    get_observability_plane_manager
)

# Import existing observability systems
try:
    from ..telemetry.v2_telemetry_handler import V2TelemetryHandler, V2TelemetryEvent
    from ..causal.causal_context_logger import CausalContextLogger, CausalContextRecord
except ImportError:
    # Handle case where modules aren't available
    V2TelemetryHandler = None
    V2TelemetryEvent = None
    CausalContextLogger = None
    CausalContextRecord = None

logger = logging.getLogger(__name__)


class IsolatedTelemetryAdapter:
    """Adapter for V2TelemetryHandler to work in isolated plane"""
    
    def __init__(self, plane_context: IsolatedPlaneContext):
        self.plane_context = plane_context
        self.telemetry_handler = None
        self._setup_handler()
        self._register_event_handlers()
    
    def _setup_handler(self):
        """Setup telemetry handler in isolated context"""
        if V2TelemetryHandler is not None:
            # Create memory sink for isolated operation
            from ..telemetry.v2_telemetry_handler import MemoryTelemetrySink
            
            memory_sink = MemoryTelemetrySink()
            self.telemetry_handler = V2TelemetryHandler(
                sinks=[memory_sink],
                enabled=True,
                high_performance_mode=True
            )
        else:
            # Fallback implementation
            self.telemetry_handler = None
    
    def _register_event_handlers(self):
        """Register event handlers for plane communication"""
        self.plane_context.register_event_handler('telemetry_entry', self._handle_entry_event)
        self.plane_context.register_event_handler('telemetry_exit', self._handle_exit_event)
    
    def _handle_entry_event(self, event: SerializedEvent):
        """Handle entry telemetry event"""
        if self.telemetry_handler is None:
            return
        
        try:
            payload = event.payload
            
            # Create telemetry event from serialized payload
            telemetry_event = V2TelemetryEvent(
                event_id=payload.get('event_id', 'unknown'),
                timestamp=datetime.fromisoformat(payload['timestamp']),
                correlation_id=payload.get('correlation_id'),
                trace_id=payload.get('trace_id'),
                entry_path=payload.get('entry_path'),
                module_id=payload.get('module_id'),
                execution_id=payload.get('execution_id'),
                feature_flags=payload.get('feature_flags', {}),
                routing_decision=payload.get('routing_decision'),
                routing_context=payload.get('routing_context', {}),
                v2_governance_active=payload.get('v2_governance_active', False),
                v2_validation_passed=payload.get('v2_validation_passed', False)
            )
            
            # Emit to isolated telemetry handler
            self.telemetry_handler.capture_entry_observation(
                entry_path=telemetry_event.entry_path,
                module_id=telemetry_event.module_id,
                execution_id=telemetry_event.execution_id,
                correlation_id=telemetry_event.correlation_id,
                trace_id=telemetry_event.trace_id,
                feature_flags=telemetry_event.feature_flags,
                routing_decision=telemetry_event.routing_decision,
                routing_context=telemetry_event.routing_context,
                v2_governance_active=telemetry_event.v2_governance_active,
                v2_validation_passed=telemetry_event.v2_validation_passed
            )
            
        except Exception as e:
            logger.error(f"Error handling telemetry entry event: {e}")
    
    def _handle_exit_event(self, event: SerializedEvent):
        """Handle exit telemetry event"""
        if self.telemetry_handler is None:
            return
        
        try:
            payload = event.payload
            
            # Emit to isolated telemetry handler
            self.telemetry_handler.capture_exit_observation(
                event_id=payload.get('event_id'),
                success=payload.get('success', False),
                result_summary=payload.get('result_summary', {}),
                processing_duration_ms=payload.get('processing_duration_ms')
            )
            
        except Exception as e:
            logger.error(f"Error handling telemetry exit event: {e}")
    
    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get telemetry events from isolated plane"""
        if self.telemetry_handler is None:
            return []
        
        try:
            # Get events from memory sink
            events = []
            sinks = self.telemetry_handler.sinks
            for sink in sinks:
                if hasattr(sink, 'get_events'):
                    sink_events = sink.get_events(limit)
                    events.extend([event.to_dict() for event in sink_events])
            
            return events
        except Exception as e:
            logger.error(f"Error getting telemetry events: {e}")
            return []


class IsolatedCausalAdapter:
    """Adapter for CausalContextLogger to work in isolated plane"""
    
    def __init__(self, plane_context: IsolatedPlaneContext):
        self.plane_context = plane_context
        self.causal_logger = None
        self._setup_logger()
        self._register_event_handlers()
    
    def _setup_logger(self):
        """Setup causal logger in isolated context"""
        if CausalContextLogger is not None:
            # Create memory sink for isolated operation
            from ..causal.causal_context_logger import MemoryCausalSink
            
            memory_sink = MemoryCausalSink()
            self.causal_logger = CausalContextLogger(
                sinks=[memory_sink],
                enabled=True,
                high_performance_mode=True
            )
        else:
            # Fallback implementation
            self.causal_logger = None
    
    def _register_event_handlers(self):
        """Register event handlers for plane communication"""
        self.plane_context.register_event_handler('causal_start', self._handle_start_event)
        self.plane_context.register_event_handler('causal_decision', self._handle_decision_event)
        self.plane_context.register_event_handler('causal_end', self._handle_end_event)
        self.plane_context.register_event_handler('causal_boundary', self._handle_boundary_event)
    
    def _handle_start_event(self, event: SerializedEvent):
        """Handle causal start event"""
        if self.causal_logger is None:
            return
        
        try:
            payload = event.payload
            
            self.causal_logger.capture_execution_start(
                module_id=payload.get('module_id'),
                execution_id=payload.get('execution_id'),
                correlation_id=payload.get('correlation_id'),
                trace_id=payload.get('trace_id'),
                parent_event_id=payload.get('parent_event_id'),
                boundary_type=payload.get('boundary_type'),
                metadata=payload.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error handling causal start event: {e}")
    
    def _handle_decision_event(self, event: SerializedEvent):
        """Handle causal decision event"""
        if self.causal_logger is None:
            return
        
        try:
            payload = event.payload
            
            self.causal_logger.capture_decision_point(
                decision_type=payload.get('decision_type'),
                module_id=payload.get('module_id'),
                execution_id=payload.get('execution_id'),
                correlation_id=payload.get('correlation_id'),
                trace_id=payload.get('trace_id'),
                parent_event_id=payload.get('parent_event_id'),
                boundary_type=payload.get('boundary_type'),
                decision_metadata=payload.get('decision_metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error handling causal decision event: {e}")
    
    def _handle_end_event(self, event: SerializedEvent):
        """Handle causal end event"""
        if self.causal_logger is None:
            return
        
        try:
            payload = event.payload
            
            self.causal_logger.capture_execution_end(
                execution_start_record_id=payload.get('execution_start_record_id'),
                module_id=payload.get('module_id'),
                execution_id=payload.get('execution_id'),
                correlation_id=payload.get('correlation_id'),
                trace_id=payload.get('trace_id'),
                boundary_type=payload.get('boundary_type'),
                success=payload.get('success', False),
                duration_ms=payload.get('duration_ms'),
                metadata=payload.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error handling causal end event: {e}")
    
    def _handle_boundary_event(self, event: SerializedEvent):
        """Handle causal boundary event"""
        if self.causal_logger is None:
            return
        
        try:
            payload = event.payload
            
            self.causal_logger.capture_boundary_crossing(
                from_boundary=payload.get('from_boundary'),
                to_boundary=payload.get('to_boundary'),
                module_id=payload.get('module_id'),
                execution_id=payload.get('execution_id'),
                correlation_id=payload.get('correlation_id'),
                trace_id=payload.get('trace_id'),
                parent_event_id=payload.get('parent_event_id'),
                crossing_metadata=payload.get('crossing_metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error handling causal boundary event: {e}")
    
    def get_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get causal records from isolated plane"""
        if self.causal_logger is None:
            return []
        
        try:
            # Get records from memory sink
            records = []
            sinks = self.causal_logger.sinks
            for sink in sinks:
                if hasattr(sink, 'get_records'):
                    sink_records = sink.get_records(limit)
                    records.extend([record.to_dict() for record in sink_records])
            
            return records
        except Exception as e:
            logger.error(f"Error getting causal records: {e}")
            return []
    
    def get_causal_chains(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get causal chains from isolated plane"""
        if self.causal_logger is None:
            return {}
        
        try:
            chains = {}
            sinks = self.causal_logger.sinks
            for sink in sinks:
                if hasattr(sink, 'get_causal_chains'):
                    sink_chains = sink.get_causal_chains()
                    for chain_id, chain_records in sink_chains.items():
                        chains[chain_id] = [record.to_dict() for record in chain_records]
            
            return chains
        except Exception as e:
            logger.error(f"Error getting causal chains: {e}")
            return {}


class IsolatedAuditAdapter:
    """Adapter for audit/replay systems to work in isolated plane"""
    
    def __init__(self, plane_context: IsolatedPlaneContext):
        self.plane_context = plane_context
        self.audit_records = []
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """Register event handlers for plane communication"""
        self.plane_context.register_event_handler('audit_record', self._handle_audit_record)
        self.plane_context.register_event_handler('replay_event', self._handle_replay_event)
    
    def _handle_audit_record(self, event: SerializedEvent):
        """Handle audit record event"""
        try:
            # Store audit record in isolated plane
            audit_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id
            }
            self.audit_records.append(audit_data)
            
        except Exception as e:
            logger.error(f"Error handling audit record: {e}")
    
    def _handle_replay_event(self, event: SerializedEvent):
        """Handle replay event"""
        try:
            # Store replay event in isolated plane
            replay_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id
            }
            self.audit_records.append(replay_data)
            
        except Exception as e:
            logger.error(f"Error handling replay event: {e}")
    
    def get_audit_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get audit records from isolated plane"""
        if limit:
            return self.audit_records[-limit:]
        return self.audit_records.copy()


class IsolatedSafetyAdapter:
    """Adapter for safety/decision systems to work in isolated plane"""
    
    def __init__(self, plane_context: IsolatedPlaneContext):
        self.plane_context = plane_context
        self.safety_decisions = []
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """Register event handlers for plane communication"""
        self.plane_context.register_event_handler('safety_decision', self._handle_safety_decision)
        self.plane_context.register_event_handler('trust_evaluation', self._handle_trust_evaluation)
        self.plane_context.register_event_handler('policy_evaluation', self._handle_policy_evaluation)
    
    def _handle_safety_decision(self, event: SerializedEvent):
        """Handle safety decision event"""
        try:
            # Store safety decision in isolated plane
            decision_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id
            }
            self.safety_decisions.append(decision_data)
            
        except Exception as e:
            logger.error(f"Error handling safety decision: {e}")
    
    def _handle_trust_evaluation(self, event: SerializedEvent):
        """Handle trust evaluation event"""
        try:
            # Store trust evaluation in isolated plane
            trust_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id
            }
            self.safety_decisions.append(trust_data)
            
        except Exception as e:
            logger.error(f"Error handling trust evaluation: {e}")
    
    def _handle_policy_evaluation(self, event: SerializedEvent):
        """Handle policy evaluation event"""
        try:
            # Store policy evaluation in isolated plane
            policy_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id
            }
            self.safety_decisions.append(policy_data)
            
        except Exception as e:
            logger.error(f"Error handling policy evaluation: {e}")
    
    def get_safety_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get safety decisions from isolated plane"""
        if limit:
            return self.safety_decisions[-limit:]
        return self.safety_decisions.copy()


class ObservabilityPlaneFactory:
    """Factory for creating isolated observability planes with adapters"""
    
    @staticmethod
    def create_telemetry_plane(config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """Create isolated telemetry plane"""
        manager = get_observability_plane_manager()
        
        # Create plane context
        context = manager.create_plane(ObservabilityPlane.TELEMETRY, config)
        
        # Create adapter
        adapter = IsolatedTelemetryAdapter(context)
        
        # Store adapter reference in context for access
        context.adapter = adapter
        
        return context
    
    @staticmethod
    def create_causal_plane(config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """Create isolated causal plane"""
        manager = get_observability_plane_manager()
        
        # Create plane context
        context = manager.create_plane(ObservabilityPlane.CAUSAL, config)
        
        # Create adapter
        adapter = IsolatedCausalAdapter(context)
        
        # Store adapter reference in context for access
        context.adapter = adapter
        
        return context
    
    @staticmethod
    def create_audit_replay_plane(config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """Create isolated audit/replay plane"""
        manager = get_observability_plane_manager()
        
        # Create plane context
        context = manager.create_plane(ObservabilityPlane.AUDIT_REPLAY, config)
        
        # Create adapter
        adapter = IsolatedAuditAdapter(context)
        
        # Store adapter reference in context for access
        context.adapter = adapter
        
        return context
    
    @staticmethod
    def create_safety_decision_plane(config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """Create isolated safety/decision plane"""
        manager = get_observability_plane_manager()
        
        # Create plane context
        context = manager.create_plane(ObservabilityPlane.SAFETY_DECISION, config)
        
        # Create adapter
        adapter = IsolatedSafetyAdapter(context)
        
        # Store adapter reference in context for access
        context.adapter = adapter
        
        return context
    
    @staticmethod
    def create_execution_plane(config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """Create isolated execution plane"""
        manager = get_observability_plane_manager()
        
        # Create plane context
        context = manager.create_plane(ObservabilityPlane.EXECUTION, config)
        
        # Execution plane doesn't need an adapter - it's the source of events
        
        return context
    
    @staticmethod
    def create_all_planes(config: Optional[Dict[str, Any]] = None) -> Dict[ObservabilityPlane, IsolatedPlaneContext]:
        """Create all observability planes"""
        planes = {}
        
        try:
            planes[ObservabilityPlane.EXECUTION] = ObservabilityPlaneFactory.create_execution_plane(config)
            planes[ObservabilityPlane.TELEMETRY] = ObservabilityPlaneFactory.create_telemetry_plane(config)
            planes[ObservabilityPlane.CAUSAL] = ObservabilityPlaneFactory.create_causal_plane(config)
            planes[ObservabilityPlane.AUDIT_REPLAY] = ObservabilityPlaneFactory.create_audit_replay_plane(config)
            planes[ObservabilityPlane.SAFETY_DECISION] = ObservabilityPlaneFactory.create_safety_decision_plane(config)
            
        except Exception as e:
            logger.error(f"Error creating planes: {e}")
            # Cleanup any created planes
            for context in planes.values():
                try:
                    manager = get_observability_plane_manager()
                    manager.destroy_plane(context)
                except:
                    pass
            raise
        
        return planes
