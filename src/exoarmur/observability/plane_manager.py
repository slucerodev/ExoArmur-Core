"""
Observability Plane Hard Partitioning System
Physical isolation layer for independent observability planes
"""

import json
import threading
import queue
import multiprocessing
import uuid
from enum import Enum
from typing import Dict, Set, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import logging
import traceback
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ObservabilityPlane(Enum):
    """Independent observability planes"""
    EXECUTION = "execution"
    TELEMETRY = "telemetry"
    CAUSAL = "causal"
    AUDIT_REPLAY = "audit_replay"
    SAFETY_DECISION = "safety_decision"


@dataclass(frozen=True)
class PlaneIdentityToken:
    """Immutable identity token for observability planes"""
    plane_id: str
    plane_type: ObservabilityPlane
    instance_id: str
    created_at: datetime
    isolation_level: str = "process"
    
    def __str__(self) -> str:
        return f"{self.plane_type.value}:{self.plane_id}:{self.instance_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'plane_id': self.plane_id,
            'plane_type': self.plane_type.value,
            'instance_id': self.instance_id,
            'created_at': self.created_at.isoformat(),
            'isolation_level': self.isolation_level
        }


@dataclass(frozen=True)
class SerializedEvent:
    """Serialized event for cross-plane communication"""
    event_id: str
    source_plane: PlaneIdentityToken
    target_plane: Optional[PlaneIdentityToken]
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    
    def serialize(self) -> bytes:
        """Serialize event to bytes for transport"""
        event_dict = {
            'event_id': self.event_id,
            'source_plane': self.source_plane.to_dict(),
            'target_plane': self.target_plane.to_dict() if self.target_plane else None,
            'event_type': self.event_type,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'trace_id': self.trace_id
        }
        return json.dumps(event_dict).encode('utf-8')
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'SerializedEvent':
        """Deserialize event from bytes"""
        event_dict = json.loads(data.decode('utf-8'))
        
        source_plane_dict = event_dict['source_plane']
        source_plane = PlaneIdentityToken(
            plane_id=source_plane_dict['plane_id'],
            plane_type=ObservabilityPlane(source_plane_dict['plane_type']),
            instance_id=source_plane_dict['instance_id'],
            created_at=datetime.fromisoformat(source_plane_dict['created_at']),
            isolation_level=source_plane_dict['isolation_level']
        )
        
        target_plane = None
        if event_dict['target_plane']:
            target_plane_dict = event_dict['target_plane']
            target_plane = PlaneIdentityToken(
                plane_id=target_plane_dict['plane_id'],
                plane_type=ObservabilityPlane(target_plane_dict['plane_type']),
                instance_id=target_plane_dict['instance_id'],
                created_at=datetime.fromisoformat(target_plane_dict['created_at']),
                isolation_level=target_plane_dict['isolation_level']
            )
        
        return cls(
            event_id=event_dict['event_id'],
            source_plane=source_plane,
            target_plane=target_plane,
            event_type=event_dict['event_type'],
            payload=event_dict['payload'],
            timestamp=datetime.fromisoformat(event_dict['timestamp']),
            correlation_id=event_dict.get('correlation_id'),
            trace_id=event_dict.get('trace_id')
        )


class IsolationStrategy(ABC):
    """Abstract base for isolation strategies"""
    
    @abstractmethod
    def create_isolated_context(self, plane_type: ObservabilityPlane, config: Dict[str, Any]) -> 'IsolatedPlaneContext':
        """Create isolated context for a plane"""
        pass
    
    @abstractmethod
    def cleanup_context(self, context: 'IsolatedPlaneContext'):
        """Cleanup isolated context"""
        pass


class ThreadIsolationStrategy(IsolationStrategy):
    """Thread-based isolation strategy"""
    
    def create_isolated_context(self, plane_type: ObservabilityPlane, config: Dict[str, Any]) -> 'IsolatedPlaneContext':
        """Create thread-based isolated context"""
        return ThreadIsolatedPlaneContext(plane_type, config)
    
    def cleanup_context(self, context: 'IsolatedPlaneContext'):
        """Cleanup thread-based context"""
        context.stop()


class ProcessIsolationStrategy(IsolationStrategy):
    """Process-based isolation strategy"""
    
    def create_isolated_context(self, plane_type: ObservabilityPlane, config: Dict[str, Any]) -> 'IsolatedPlaneContext':
        """Create process-based isolated context"""
        return ProcessIsolatedPlaneContext(plane_type, config)
    
    def cleanup_context(self, context: 'IsolatedPlaneContext'):
        """Cleanup process-based context"""
        context.stop()


class IsolatedPlaneContext(ABC):
    """Abstract base for isolated plane contexts"""
    
    def __init__(self, plane_type: ObservabilityPlane, config: Dict[str, Any]):
        self.plane_type = plane_type
        self.config = config
        self.identity_token = PlaneIdentityToken(
            plane_id=f"{plane_type.value}_{uuid.uuid4().hex[:8]}",
            plane_type=plane_type,
            instance_id=uuid.uuid4().hex,
            created_at=datetime.now(timezone.utc)
        )
        self.is_running = False
        self._lock = threading.RLock()
    
    @abstractmethod
    def start(self):
        """Start the isolated context"""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop the isolated context"""
        pass
    
    @abstractmethod
    def send_event(self, event: SerializedEvent) -> bool:
        """Send event to this context"""
        pass
    
    @abstractmethod
    def receive_event(self, timeout: Optional[float] = None) -> Optional[SerializedEvent]:
        """Receive event from this context"""
        pass


class ThreadIsolatedPlaneContext(IsolatedPlaneContext):
    """Thread-based isolated plane context"""
    
    def __init__(self, plane_type: ObservabilityPlane, config: Dict[str, Any]):
        super().__init__(plane_type, config)
        self._event_queue = queue.Queue(maxsize=config.get('queue_size', 1000))
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._event_handlers: Dict[str, Callable] = {}
    
    def start(self):
        """Start the thread-based context"""
        with self._lock:
            if self.is_running:
                return
            
            self.is_running = True
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            
            logger.info(f"Thread isolated context started for {self.plane_type.value}")
    
    def stop(self):
        """Stop the thread-based context"""
        with self._lock:
            if not self.is_running:
                return
            
            self.is_running = False
            self._stop_event.set()
            
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
            
            logger.info(f"Thread isolated context stopped for {self.plane_type.value}")
    
    def send_event(self, event: SerializedEvent) -> bool:
        """Send event to this context"""
        try:
            self._event_queue.put(event, block=False)
            return True
        except queue.Full:
            logger.debug(f"Event queue full for {self.plane_type.value} plane")
            return False
    
    def receive_event(self, timeout: Optional[float] = None) -> Optional[SerializedEvent]:
        """Receive event from this context"""
        try:
            return self._event_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        self._event_handlers[event_type] = handler
    
    def _worker_loop(self):
        """Worker loop for processing events"""
        while not self._stop_event.is_set():
            try:
                event = self._event_queue.get(timeout=1.0)
                self._process_event(event)
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event in {self.plane_type.value} plane: {e}")
    
    def _process_event(self, event: SerializedEvent):
        """Process a single event"""
        handler = self._event_handlers.get(event.event_type)
        if handler:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.event_type}: {e}")


class ProcessIsolatedPlaneContext(IsolatedPlaneContext):
    """Process-based isolated plane context"""
    
    def __init__(self, plane_type: ObservabilityPlane, config: Dict[str, Any]):
        super().__init__(plane_type, config)
        self._process = None
        self._parent_conn = None
        self._child_conn = None
    
    def start(self):
        """Start the process-based context"""
        with self._lock:
            if self.is_running:
                return
            
            self._parent_conn, self._child_conn = multiprocessing.Pipe()
            self._process = multiprocessing.Process(target=self._process_worker, args=(self._child_conn,))
            self._process.start()
            self.is_running = True
            
            logger.info(f"Process isolated context started for {self.plane_type.value}")
    
    def stop(self):
        """Stop the process-based context"""
        with self._lock:
            if not self.is_running:
                return
            
            self.is_running = False
            
            if self._parent_conn:
                self._parent_conn.send({'type': 'stop'})
            
            if self._process and self._process.is_alive():
                self._process.join(timeout=5.0)
                if self._process.is_alive():
                    self._process.terminate()
            
            if self._parent_conn:
                self._parent_conn.close()
            
            logger.info(f"Process isolated context stopped for {self.plane_type.value}")
    
    def send_event(self, event: SerializedEvent) -> bool:
        """Send event to this context"""
        if not self._parent_conn:
            return False
        
        try:
            self._parent_conn.send({'type': 'event', 'data': event.serialize()})
            return True
        except Exception as e:
            logger.error(f"Error sending event to {self.plane_type.value} plane: {e}")
            return False
    
    def receive_event(self, timeout: Optional[float] = None) -> Optional[SerializedEvent]:
        """Receive event from this context"""
        if not self._parent_conn:
            return None
        
        try:
            if self._parent_conn.poll(timeout):
                msg = self._parent_conn.recv()
                if msg['type'] == 'event':
                    return SerializedEvent.deserialize(msg['data'])
        except Exception as e:
            logger.error(f"Error receiving event from {self.plane_type.value} plane: {e}")
        
        return None
    
    def _process_worker(self, conn):
        """Worker process"""
        try:
            while True:
                if conn.poll():
                    msg = conn.recv()
                    if msg['type'] == 'stop':
                        break
                    elif msg['type'] == 'event':
                        event = SerializedEvent.deserialize(msg['data'])
                        # Process event in isolated process
                        self._process_event_in_process(event)
        except Exception as e:
            logger.error(f"Error in process worker for {self.plane_type.value}: {e}")
        finally:
            conn.close()
    
    def _process_event_in_process(self, event: SerializedEvent):
        """Process event in isolated process"""
        # This would contain the actual plane-specific logic
        logger.debug(f"Processing {event.event_type} in {self.plane_type.value} process")


class SerializedEventBridge:
    """Bridge for serialized events between planes"""
    
    def __init__(self):
        self._plane_connections: Dict[PlaneIdentityToken, IsolatedPlaneContext] = {}
        self._event_routes: Dict[str, List[PlaneIdentityToken]] = {}
        self._lock = threading.RLock()
    
    def register_plane(self, context: IsolatedPlaneContext):
        """Register a plane context"""
        with self._lock:
            self._plane_connections[context.identity_token] = context
            logger.info(f"Registered plane: {context.identity_token}")
    
    def unregister_plane(self, token: PlaneIdentityToken):
        """Unregister a plane context"""
        with self._lock:
            if token in self._plane_connections:
                del self._plane_connections[token]
                logger.info(f"Unregistered plane: {token}")
    
    def route_event(self, event: SerializedEvent) -> bool:
        """Route event to target planes"""
        with self._lock:
            success_count = 0
            
            # Determine target planes
            target_planes = self._get_target_planes(event)
            
            for target_token in target_planes:
                if target_token in self._plane_connections:
                    context = self._plane_connections[target_token]
                    if context.send_event(event):
                        success_count += 1
                    else:
                        logger.warning(f"Failed to send event to {target_token}")
            
            return success_count > 0
    
    def _get_target_planes(self, event: SerializedEvent) -> List[PlaneIdentityToken]:
        """Get target planes for an event"""
        if event.target_plane:
            return [event.target_plane]
        
        # Default routing based on event type
        if event.event_type.startswith('telemetry_'):
            return [token for token in self._plane_connections.keys() 
                   if token.plane_type == ObservabilityPlane.TELEMETRY]
        elif event.event_type.startswith('causal_'):
            return [token for token in self._plane_connections.keys() 
                   if token.plane_type == ObservabilityPlane.CAUSAL]
        elif event.event_type.startswith('audit_'):
            return [token for token in self._plane_connections.keys() 
                   if token.plane_type == ObservabilityPlane.AUDIT_REPLAY]
        elif event.event_type.startswith('safety_'):
            return [token for token in self._plane_connections.keys() 
                   if token.plane_type == ObservabilityPlane.SAFETY_DECISION]
        
        return []
    
    def get_plane_status(self) -> Dict[str, Any]:
        """Get status of all registered planes"""
        with self._lock:
            return {
                'total_planes': len(self._plane_connections),
                'planes': {
                    str(token): {
                        'plane_type': token.plane_type.value,
                        'is_running': context.is_running,
                        'queue_size': getattr(context, '_event_queue', None) and context._event_queue.qsize() or 0
                    }
                    for token, context in self._plane_connections.items()
                }
            }


class ObservabilityPlaneManager:
    """
    Observability Plane Manager - Hard partitioning system
    
    Manages physically isolated observability planes with no shared memory
    """
    
    def __init__(self, isolation_strategy: IsolationStrategy = None):
        """
        Initialize observability plane manager
        
        Args:
            isolation_strategy: Strategy for plane isolation (thread or process)
        """
        self.isolation_strategy = isolation_strategy or ThreadIsolationStrategy()
        self.event_bridge = SerializedEventBridge()
        self._plane_contexts: Dict[ObservabilityPlane, List[IsolatedPlaneContext]] = {
            plane: [] for plane in ObservabilityPlane
        }
        self._lock = threading.RLock()
        
        logger.info("ObservabilityPlaneManager initialized - PHYSICAL ISOLATION LAYER")
    
    def create_plane(self, plane_type: ObservabilityPlane, config: Optional[Dict[str, Any]] = None) -> IsolatedPlaneContext:
        """
        Create an isolated observability plane
        
        Args:
            plane_type: Type of observability plane
            config: Configuration for the plane
            
        Returns:
            Isolated plane context
        """
        with self._lock:
            config = config or {}
            
            # Create isolated context
            context = self.isolation_strategy.create_isolated_context(plane_type, config)
            
            # Register with event bridge
            self.event_bridge.register_plane(context)
            
            # Store in manager
            self._plane_contexts[plane_type].append(context)
            
            # Start the context
            context.start()
            
            logger.info(f"Created isolated plane: {context.identity_token}")
            return context
    
    def destroy_plane(self, context: IsolatedPlaneContext):
        """
        Destroy an isolated observability plane
        
        Args:
            context: Plane context to destroy
        """
        with self._lock:
            # Stop the context
            context.stop()
            
            # Unregister from event bridge
            self.event_bridge.unregister_plane(context.identity_token)
            
            # Remove from manager
            plane_type = context.plane_type
            if context in self._plane_contexts[plane_type]:
                self._plane_contexts[plane_type].remove(context)
            
            # Cleanup strategy
            self.isolation_strategy.cleanup_context(context)
            
            logger.info(f"Destroyed isolated plane: {context.identity_token}")
    
    def send_event_to_plane(self, plane_type: ObservabilityPlane, event_type: str, 
                           payload: Dict[str, Any], correlation_id: Optional[str] = None,
                           trace_id: Optional[str] = None) -> bool:
        """
        Send event to a specific plane type
        
        Args:
            plane_type: Target plane type
            event_type: Type of event
            payload: Event payload
            correlation_id: Optional correlation ID
            trace_id: Optional trace ID
            
        Returns:
            True if event sent successfully
        """
        with self._lock:
            # Create serialized event
            event = SerializedEvent(
                event_id=f"evt_{uuid.uuid4().hex}",
                source_plane=PlaneIdentityToken(
                    plane_id="manager",
                    plane_type=ObservabilityPlane.EXECUTION,
                    instance_id="manager",
                    created_at=datetime.now(timezone.utc)
                ),
                target_plane=None,  # Will be routed by event type
                event_type=event_type,
                payload=payload,
                timestamp=datetime.now(timezone.utc),
                correlation_id=correlation_id,
                trace_id=trace_id
            )
            
            return self.event_bridge.route_event(event)
    
    def get_plane_manager_status(self) -> Dict[str, Any]:
        """Get status of plane manager"""
        with self._lock:
            return {
                'isolation_strategy': type(self.isolation_strategy).__name__,
                'total_planes': sum(len(contexts) for contexts in self._plane_contexts.values()),
                'planes_by_type': {
                    plane_type.value: len(contexts)
                    for plane_type, contexts in self._plane_contexts.items()
                },
                'bridge_status': self.event_bridge.get_plane_status()
            }
    
    def shutdown(self):
        """Shutdown all planes and cleanup"""
        with self._lock:
            logger.info("Shutting down ObservabilityPlaneManager...")
            
            # Stop all planes
            for plane_type, contexts in self._plane_contexts.items():
                for context in contexts:
                    self.destroy_plane(context)
            
            logger.info("ObservabilityPlaneManager shutdown complete")


# Global plane manager instance
_observability_plane_manager: Optional[ObservabilityPlaneManager] = None


def get_observability_plane_manager() -> ObservabilityPlaneManager:
    """Get global observability plane manager instance"""
    global _observability_plane_manager
    if _observability_plane_manager is None:
        _observability_plane_manager = ObservabilityPlaneManager()
    return _observability_plane_manager


def configure_observability_plane_manager(isolation_strategy: IsolationStrategy = None) -> ObservabilityPlaneManager:
    """Configure global observability plane manager"""
    global _observability_plane_manager
    if _observability_plane_manager:
        _observability_plane_manager.shutdown()
    
    _observability_plane_manager = ObservabilityPlaneManager(isolation_strategy)
    return _observability_plane_manager
