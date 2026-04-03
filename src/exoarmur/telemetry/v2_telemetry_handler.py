"""
V2 Entry Gate Telemetry Handler
Strictly observational instrumentation at V2 boundary with zero influence on execution
"""

import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)


class TelemetrySinkType(Enum):
    """Types of telemetry sinks"""
    LOG = "log"
    FILE = "file"
    MEMORY = "memory"
    EXTERNAL = "external"


@dataclass(frozen=True)
class V2TelemetryEvent:
    """Immutable V2 telemetry event for boundary observation"""
    
    # Event metadata
    event_id: str
    timestamp: datetime
    correlation_id: Optional[str]
    trace_id: Optional[str]
    
    # V2 boundary context
    entry_path: str  # "v1_direct" or "v2_wrapped"
    module_id: str
    execution_id: str
    
    # Feature flag state (observational only)
    feature_flags: Dict[str, bool]
    
    # Routing decision context (observational only)
    routing_decision: str
    routing_context: Dict[str, Any]
    
    # Performance metrics (observational only)
    entry_timestamp: datetime
    processing_start: datetime
    
    # System state snapshot (observational only)
    v2_governance_active: bool
    v2_validation_passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'trace_id': self.trace_id,
            'entry_path': self.entry_path,
            'module_id': self.module_id,
            'execution_id': self.execution_id,
            'feature_flags': self.feature_flags,
            'routing_decision': self.routing_decision,
            'routing_context': self.routing_context,
            'entry_timestamp': self.entry_timestamp.isoformat(),
            'processing_start': self.processing_start.isoformat(),
            'v2_governance_active': self.v2_governance_active,
            'v2_validation_passed': self.v2_validation_passed
        }


class TelemetrySink:
    """Abstract base for telemetry sinks"""
    
    def emit(self, event: V2TelemetryEvent) -> bool:
        """Emit telemetry event - must be non-blocking and failure-tolerant"""
        raise NotImplementedError
    
    def close(self):
        """Close sink and cleanup resources"""
        pass


class LogTelemetrySink(TelemetrySink):
    """Log-based telemetry sink"""
    
    def __init__(self, logger_name: str = "v2_telemetry"):
        self.logger = logging.getLogger(logger_name)
    
    def emit(self, event: V2TelemetryEvent) -> bool:
        """Emit to structured log - non-blocking"""
        try:
            self.logger.info(
                "V2_TELEMETRY_EVENT",
                extra={
                    'telemetry_event': event.to_dict(),
                    'event_type': 'v2_boundary_observation'
                }
            )
            return True
        except Exception as e:
            # Telemetry failure must never affect execution
            logger.debug(f"Telemetry log emission failed: {e}")
            return False


class MemoryTelemetrySink(TelemetrySink):
    """In-memory telemetry sink for testing and debugging"""
    
    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self.events: List[V2TelemetryEvent] = []
        self._lock = threading.Lock()
    
    def emit(self, event: V2TelemetryEvent) -> bool:
        """Emit to memory buffer - non-blocking"""
        try:
            with self._lock:
                self.events.append(event)
                # Maintain size limit
                if len(self.events) > self.max_events:
                    self.events = self.events[-self.max_events:]
            return True
        except Exception as e:
            logger.debug(f"Telemetry memory emission failed: {e}")
            return False
    
    def get_events(self, limit: Optional[int] = None) -> List[V2TelemetryEvent]:
        """Get stored events"""
        with self._lock:
            if limit:
                return self.events[-limit:]
            return self.events.copy()
    
    def clear(self):
        """Clear stored events"""
        with self._lock:
            self.events.clear()


class AsyncFileTelemetrySink(TelemetrySink):
    """Asynchronous file-based telemetry sink"""
    
    def __init__(self, file_path: str, buffer_size: int = 100):
        self.file_path = file_path
        self.buffer_size = buffer_size
        self._buffer: List[V2TelemetryEvent] = []
        self._buffer_lock = threading.Lock()
        self._flush_thread = None
        self._stop_event = threading.Event()
        self._start_flush_thread()
    
    def _start_flush_thread(self):
        """Start background flush thread"""
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _flush_loop(self):
        """Background loop for flushing telemetry to file"""
        while not self._stop_event.is_set():
            try:
                events_to_flush = []
                with self._buffer_lock:
                    if self._buffer:
                        events_to_flush = self._buffer.copy()
                        self._buffer.clear()
                
                if events_to_flush:
                    self._write_events_to_file(events_to_flush)
                
                # Wait before next flush
                self._stop_event.wait(1.0)
            except Exception as e:
                logger.debug(f"Telemetry file flush failed: {e}")
    
    def _write_events_to_file(self, events: List[V2TelemetryEvent]):
        """Write events to file"""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event.to_dict()) + '\n')
        except Exception as e:
            logger.debug(f"Failed to write telemetry events to file: {e}")
    
    def emit(self, event: V2TelemetryEvent) -> bool:
        """Add event to buffer for async writing - non-blocking"""
        try:
            with self._buffer_lock:
                self._buffer.append(event)
                if len(self._buffer) >= self.buffer_size:
                    # Trigger immediate flush if buffer is full
                    pass
            return True
        except Exception as e:
            logger.debug(f"Telemetry file emission failed: {e}")
            return False
    
    def close(self):
        """Close sink and flush remaining events"""
        self._stop_event.set()
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        
        # Flush any remaining events
        events_to_flush = []
        with self._buffer_lock:
            if self._buffer:
                events_to_flush = self._buffer.copy()
                self._buffer.clear()
        
        if events_to_flush:
            self._write_events_to_file(events_to_flush)


class V2TelemetryHandler:
    """
    V2 Entry Gate Telemetry Handler
    
    STRICTLY OBSERVATIONAL - ZERO INFLUENCE ON EXECUTION
    Captures metadata at V2 boundary without affecting routing, decisions, or behavior
    """
    
    def __init__(self, 
                 sinks: Optional[List[TelemetrySink]] = None,
                 enabled: bool = True,
                 high_performance_mode: bool = True):
        """
        Initialize V2 telemetry handler
        
        Args:
            sinks: List of telemetry sinks (defaults to log sink)
            enabled: Whether telemetry is enabled
            high_performance_mode: Use non-blocking buffered emission
        """
        self.enabled = enabled
        self.high_performance_mode = high_performance_mode
        
        # Default to log sink if none provided
        if sinks is None:
            sinks = [LogTelemetrySink()]
        
        self.sinks = sinks
        
        # Performance optimization: async emission queue
        if high_performance_mode:
            self._emission_queue = Queue(maxsize=1000)
            self._emission_thread = None
            self._stop_event = threading.Event()
            self._start_emission_thread()
        
        logger.info("V2TelemetryHandler initialized - OBSERVATIONAL ONLY")
    
    def _start_emission_thread(self):
        """Start background emission thread for high performance"""
        self._emission_thread = threading.Thread(target=self._emission_loop, daemon=True)
        self._emission_thread.start()
    
    def _emission_loop(self):
        """Background loop for emitting telemetry events"""
        while not self._stop_event.is_set():
            try:
                # Get event from queue with timeout
                event = self._emission_queue.get(timeout=1.0)
                
                # Emit to all sinks (non-blocking)
                for sink in self.sinks:
                    try:
                        sink.emit(event)
                    except Exception as e:
                        logger.debug(f"Telemetry sink emission failed: {e}")
                
                self._emission_queue.task_done()
            except Empty:
                # Queue empty, continue
                continue
            except Exception as e:
                logger.debug(f"Telemetry emission loop error: {e}")
    
    def capture_entry_observation(
        self,
        entry_path: str,
        module_id: str,
        execution_id: str,
        correlation_id: Optional[str],
        trace_id: Optional[str],
        feature_flags: Dict[str, bool],
        routing_decision: str,
        routing_context: Dict[str, Any],
        v2_governance_active: bool,
        v2_validation_passed: bool
    ) -> Optional[str]:
        """
        Capture V2 entry boundary observation
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        Returns event ID for reference (or None if disabled/failed)
        """
        if not self.enabled:
            return None
        
        try:
            # Create telemetry event
            now = datetime.now(timezone.utc)
            event = V2TelemetryEvent(
                event_id=f"v2_telemetry_{int(now.timestamp() * 1000000)}_{module_id}_{execution_id}",
                timestamp=now,
                correlation_id=correlation_id,
                trace_id=trace_id,
                entry_path=entry_path,
                module_id=module_id,
                execution_id=execution_id,
                feature_flags=feature_flags.copy(),
                routing_decision=routing_decision,
                routing_context=routing_context.copy(),
                entry_timestamp=now,
                processing_start=now,
                v2_governance_active=v2_governance_active,
                v2_validation_passed=v2_validation_passed
            )
            
            # Emit event (non-blocking)
            if self.high_performance_mode:
                try:
                    self._emission_queue.put(event, block=False)
                except:
                    # Queue full, drop event (never block execution)
                    logger.debug("Telemetry queue full, dropping event")
                    return None
            else:
                # Synchronous emission (still non-blocking for sinks)
                for sink in self.sinks:
                    try:
                        sink.emit(event)
                    except Exception as e:
                        logger.debug(f"Telemetry emission failed: {e}")
            
            return event.event_id
            
        except Exception as e:
            # Telemetry failure must never affect execution
            logger.debug(f"V2 telemetry capture failed: {e}")
            return None
    
    def capture_exit_observation(
        self,
        event_id: str,
        success: bool,
        result_summary: Dict[str, Any],
        processing_duration_ms: Optional[float] = None
    ) -> bool:
        """
        Capture V2 exit boundary observation
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        Returns True if captured, False if failed/disabled
        """
        if not self.enabled or not event_id:
            return False
        
        try:
            # Create exit telemetry event (extend entry event)
            now = datetime.now(timezone.utc)
            exit_event_data = {
                'event_id': f"{event_id}_exit",
                'timestamp': now.isoformat(),
                'exit_success': success,
                'result_summary': result_summary,
                'processing_duration_ms': processing_duration_ms,
                'event_type': 'v2_exit_observation'
            }
            
            # Emit exit event (non-blocking)
            if self.high_performance_mode:
                # For simplicity, treat as log event
                logger.info("V2_TELEMETRY_EXIT", extra={'exit_event': exit_event_data})
            else:
                for sink in self.sinks:
                    try:
                        # Emit as structured log for simplicity
                        logger.info("V2_TELEMETRY_EXIT", extra={'exit_event': exit_event_data})
                    except Exception as e:
                        logger.debug(f"Telemetry exit emission failed: {e}")
            
            return True
            
        except Exception as e:
            logger.debug(f"V2 telemetry exit capture failed: {e}")
            return False
    
    def get_memory_events(self, limit: Optional[int] = None) -> List[V2TelemetryEvent]:
        """Get events from memory sinks (for testing/debugging)"""
        events = []
        for sink in self.sinks:
            if isinstance(sink, MemoryTelemetrySink):
                events.extend(sink.get_events(limit))
        return events
    
    def clear_memory_events(self):
        """Clear events from memory sinks"""
        for sink in self.sinks:
            if isinstance(sink, MemoryTelemetrySink):
                sink.clear()
    
    def close(self):
        """Close telemetry handler and cleanup resources"""
        if self.high_performance_mode and self._emission_thread:
            self._stop_event.set()
            if self._emission_thread.is_alive():
                self._emission_thread.join(timeout=5.0)
        
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as e:
                logger.debug(f"Error closing telemetry sink: {e}")
        
        logger.info("V2TelemetryHandler closed")


# Global telemetry handler instance (singleton pattern)
_telemetry_handler: Optional[V2TelemetryHandler] = None


def get_v2_telemetry_handler() -> V2TelemetryHandler:
    """Get global V2 telemetry handler instance"""
    global _telemetry_handler
    if _telemetry_handler is None:
        _telemetry_handler = V2TelemetryHandler()
    return _telemetry_handler


def configure_v2_telemetry(
    sinks: Optional[List[TelemetrySink]] = None,
    enabled: bool = True,
    high_performance_mode: bool = True
) -> V2TelemetryHandler:
    """Configure global V2 telemetry handler"""
    global _telemetry_handler
    if _telemetry_handler:
        _telemetry_handler.close()
    
    _telemetry_handler = V2TelemetryHandler(sinks, enabled, high_performance_mode)
    return _telemetry_handler
