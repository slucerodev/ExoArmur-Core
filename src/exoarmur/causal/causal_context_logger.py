"""
Causal Context Logging System
Non-blocking observability layer for execution lineage tracking
"""

import logging
import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from queue import Queue, Empty
import time
import uuid

logger = logging.getLogger(__name__)


class CausalContextType(Enum):
    """Types of causal context events"""
    EXECUTION_START = "execution_start"
    EXECUTION_END = "execution_end"
    DECISION_POINT = "decision_point"
    MODULE_INVOCATION = "module_invocation"
    BOUNDARY_CROSSING = "boundary_crossing"
    ERROR_EVENT = "error_event"


@dataclass(frozen=True)
class CausalContextRecord:
    """Immutable causal context record for lineage tracking"""
    
    # Core identification
    record_id: str
    timestamp: datetime
    
    # Causal lineage information
    correlation_id: Optional[str]
    trace_id: Optional[str]
    parent_event_id: Optional[str]
    causal_chain_id: str
    
    # Event classification
    event_type: CausalContextType
    context_type: str
    
    # Execution context (minimal, non-decisional)
    module_id: Optional[str]
    execution_id: Optional[str]
    boundary_type: Optional[str]  # "v1" or "v2"
    
    # Metadata (observational only)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics (observational only)
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'record_id': self.record_id,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'trace_id': self.trace_id,
            'parent_event_id': self.parent_event_id,
            'causal_chain_id': self.causal_chain_id,
            'event_type': self.event_type.value,
            'context_type': self.context_type,
            'module_id': self.module_id,
            'execution_id': self.execution_id,
            'boundary_type': self.boundary_type,
            'metadata': self.metadata,
            'duration_ms': self.duration_ms
        }
    
    @property
    def causal_key(self) -> str:
        """Generate causal key for lineage tracking"""
        parts = [self.causal_chain_id]
        if self.correlation_id:
            parts.append(self.correlation_id)
        if self.trace_id:
            parts.append(self.trace_id)
        if self.parent_event_id:
            parts.append(self.parent_event_id)
        return "|".join(parts)


class CausalContextSink:
    """Abstract base for causal context sinks"""
    
    def emit(self, record: CausalContextRecord) -> bool:
        """Emit causal context record - must be non-blocking and failure-tolerant"""
        raise NotImplementedError
    
    def close(self):
        """Close sink and cleanup resources"""
        pass


class LogCausalSink(CausalContextSink):
    """Log-based causal context sink"""
    
    def __init__(self, logger_name: str = "causal_context"):
        self.logger = logging.getLogger(logger_name)
    
    def emit(self, record: CausalContextRecord) -> bool:
        """Emit to structured log - non-blocking"""
        try:
            self.logger.info(
                "CAUSAL_CONTEXT_EVENT",
                extra={
                    'causal_record': record.to_dict(),
                    'causal_key': record.causal_key,
                    'event_type': 'causal_lineage'
                }
            )
            return True
        except Exception as e:
            # Causal logging failure must never affect execution
            logger.debug(f"Causal log emission failed: {e}")
            return False


class MemoryCausalSink(CausalContextSink):
    """In-memory causal context sink for testing and debugging"""
    
    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self.records: List[CausalContextRecord] = []
        self._lock = threading.Lock()
        self._causal_chains: Dict[str, List[str]] = {}  # chain_id -> list of record_ids
    
    def emit(self, record: CausalContextRecord) -> bool:
        """Emit to memory buffer - non-blocking"""
        try:
            with self._lock:
                self.records.append(record)
                
                # Maintain size limit
                if len(self.records) > self.max_records:
                    # Remove oldest records and update chains
                    removed_count = len(self.records) - self.max_records
                    for i in range(removed_count):
                        old_record = self.records[i]
                        if old_record.causal_chain_id in self._causal_chains:
                            if old_record.record_id in self._causal_chains[old_record.causal_chain_id]:
                                self._causal_chains[old_record.causal_chain_id].remove(old_record.record_id)
                    self.records = self.records[-self.max_records:]
                
                # Update causal chain tracking
                if record.causal_chain_id not in self._causal_chains:
                    self._causal_chains[record.causal_chain_id] = []
                self._causal_chains[record.causal_chain_id].append(record.record_id)
            
            return True
        except Exception as e:
            logger.debug(f"Causal memory emission failed: {e}")
            return False
    
    def get_records(self, limit: Optional[int] = None) -> List[CausalContextRecord]:
        """Get stored records"""
        with self._lock:
            if limit:
                return self.records[-limit:]
            return self.records.copy()
    
    def get_causal_chain(self, chain_id: str) -> List[CausalContextRecord]:
        """Get records for a specific causal chain"""
        with self._lock:
            if chain_id not in self._causal_chains:
                return []
            
            record_ids = self._causal_chains[chain_id]
            return [record for record in self.records if record.record_id in record_ids]
    
    def clear(self):
        """Clear stored records"""
        with self._lock:
            self.records.clear()
            self._causal_chains.clear()
    
    def get_chain_statistics(self) -> Dict[str, Any]:
        """Get statistics about causal chains"""
        with self._lock:
            return {
                'total_records': len(self.records),
                'total_chains': len(self._causal_chains),
                'chain_lengths': {
                    chain_id: len(record_ids) 
                    for chain_id, record_ids in self._causal_chains.items()
                }
            }


class AsyncFileCausalSink(CausalContextSink):
    """Asynchronous file-based causal context sink"""
    
    def __init__(self, file_path: str, buffer_size: int = 200):
        self.file_path = file_path
        self.buffer_size = buffer_size
        self._buffer: List[CausalContextRecord] = []
        self._buffer_lock = threading.Lock()
        self._flush_thread = None
        self._stop_event = threading.Event()
        self._start_flush_thread()
    
    def _start_flush_thread(self):
        """Start background flush thread"""
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _flush_loop(self):
        """Background loop for flushing causal context to file"""
        while not self._stop_event.is_set():
            try:
                records_to_flush = []
                with self._buffer_lock:
                    if self._buffer:
                        records_to_flush = self._buffer.copy()
                        self._buffer.clear()
                
                if records_to_flush:
                    self._write_records_to_file(records_to_flush)
                
                # Wait before next flush
                self._stop_event.wait(2.0)
            except Exception as e:
                logger.debug(f"Causal file flush failed: {e}")
    
    def _write_records_to_file(self, records: List[CausalContextRecord]):
        """Write records to file"""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record.to_dict()) + '\n')
        except Exception as e:
            logger.debug(f"Failed to write causal records to file: {e}")
    
    def emit(self, record: CausalContextRecord) -> bool:
        """Add record to buffer for async writing - non-blocking"""
        try:
            with self._buffer_lock:
                self._buffer.append(record)
                if len(self._buffer) >= self.buffer_size:
                    # Trigger immediate flush if buffer is full
                    pass
            return True
        except Exception as e:
            logger.debug(f"Causal file emission failed: {e}")
            return False
    
    def close(self):
        """Close sink and flush remaining records"""
        self._stop_event.set()
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        
        # Flush any remaining records
        records_to_flush = []
        with self._buffer_lock:
            if self._buffer:
                records_to_flush = self._buffer.copy()
                self._buffer.clear()
        
        if records_to_flush:
            self._write_records_to_file(records_to_flush)


class CausalContextLogger:
    """
    Causal Context Logger - Non-blocking observability layer
    
    STRICTLY OBSERVATIONAL - ZERO INFLUENCE ON EXECUTION
    Captures execution lineage metadata without affecting any system behavior
    """
    
    def __init__(self, 
                 sinks: Optional[List[CausalContextSink]] = None,
                 enabled: bool = True,
                 high_performance_mode: bool = True):
        """
        Initialize causal context logger
        
        Args:
            sinks: List of causal context sinks (defaults to log sink)
            enabled: Whether causal logging is enabled
            high_performance_mode: Use non-blocking buffered emission
        """
        self.enabled = enabled
        self.high_performance_mode = high_performance_mode
        
        # Default to log sink if none provided
        if sinks is None:
            sinks = [LogCausalSink()]
        
        self.sinks = sinks
        
        # Performance optimization: async emission queue
        if high_performance_mode:
            self._emission_queue = Queue(maxsize=2000)
            self._emission_thread = None
            self._stop_event = threading.Event()
            self._start_emission_thread()
        
        logger.info("CausalContextLogger initialized - OBSERVATIONAL ONLY")
    
    def _start_emission_thread(self):
        """Start background emission thread for high performance"""
        self._emission_thread = threading.Thread(target=self._emission_loop, daemon=True)
        self._emission_thread.start()
    
    def _emission_loop(self):
        """Background loop for emitting causal context records"""
        while not self._stop_event.is_set():
            try:
                # Get record from queue with timeout
                record = self._emission_queue.get(timeout=1.0)
                
                # Emit to all sinks (non-blocking)
                for sink in self.sinks:
                    try:
                        sink.emit(record)
                    except Exception as e:
                        logger.debug(f"Causal sink emission failed: {e}")
                
                self._emission_queue.task_done()
            except Empty:
                # Queue empty, continue
                continue
            except Exception as e:
                logger.debug(f"Causal emission loop error: {e}")
    
    def _generate_causal_chain_id(self, correlation_id: Optional[str], trace_id: Optional[str]) -> str:
        """Generate deterministic causal chain ID"""
        if correlation_id:
            return f"chain_{correlation_id}"
        elif trace_id:
            return f"chain_{trace_id}"
        else:
            return f"chain_{uuid.uuid4().hex[:16]}"
    
    def capture_execution_start(
        self,
        module_id: str,
        execution_id: str,
        correlation_id: Optional[str],
        trace_id: Optional[str],
        parent_event_id: Optional[str],
        boundary_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Capture execution start causal context
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        """
        if not self.enabled:
            return None
        
        try:
            now = datetime.now(timezone.utc)
            causal_chain_id = self._generate_causal_chain_id(correlation_id, trace_id)
            
            record = CausalContextRecord(
                record_id=f"causal_{int(now.timestamp() * 1000000)}_{module_id}_{execution_id}",
                timestamp=now,
                correlation_id=correlation_id,
                trace_id=trace_id,
                parent_event_id=parent_event_id,
                causal_chain_id=causal_chain_id,
                event_type=CausalContextType.EXECUTION_START,
                context_type="execution_lifecycle",
                module_id=module_id,
                execution_id=execution_id,
                boundary_type=boundary_type,
                metadata=metadata or {}
            )
            
            # Emit record (non-blocking)
            if self.high_performance_mode:
                try:
                    self._emission_queue.put(record, block=False)
                except:
                    # Queue full, drop record (never block execution)
                    logger.debug("Causal queue full, dropping record")
                    return None
            else:
                # Synchronous emission (still non-blocking for sinks)
                for sink in self.sinks:
                    try:
                        sink.emit(record)
                    except Exception as e:
                        logger.debug(f"Causal emission failed: {e}")
            
            return record.record_id
            
        except Exception as e:
            # Causal logging failure must never affect execution
            logger.debug(f"Causal execution start capture failed: {e}")
            return None
    
    def capture_execution_end(
        self,
        execution_start_record_id: Optional[str],
        module_id: str,
        execution_id: str,
        correlation_id: Optional[str],
        trace_id: Optional[str],
        boundary_type: str,
        success: bool,
        duration_ms: Optional[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Capture execution end causal context
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        """
        if not self.enabled or not execution_start_record_id:
            return False
        
        try:
            now = datetime.now(timezone.utc)
            causal_chain_id = self._generate_causal_chain_id(correlation_id, trace_id)
            
            record = CausalContextRecord(
                record_id=f"causal_{int(now.timestamp() * 1000000)}_{module_id}_{execution_id}_end",
                timestamp=now,
                correlation_id=correlation_id,
                trace_id=trace_id,
                parent_event_id=execution_start_record_id,
                causal_chain_id=causal_chain_id,
                event_type=CausalContextType.EXECUTION_END,
                context_type="execution_lifecycle",
                module_id=module_id,
                execution_id=execution_id,
                boundary_type=boundary_type,
                metadata={
                    'success': success,
                    **(metadata or {})
                },
                duration_ms=duration_ms
            )
            
            # Emit record (non-blocking)
            if self.high_performance_mode:
                try:
                    self._emission_queue.put(record, block=False)
                except:
                    # Queue full, drop record (never block execution)
                    logger.debug("Causal queue full, dropping record")
                    return False
            else:
                # Synchronous emission (still non-blocking for sinks)
                for sink in self.sinks:
                    try:
                        sink.emit(record)
                    except Exception as e:
                        logger.debug(f"Causal emission failed: {e}")
            
            return True
            
        except Exception as e:
            logger.debug(f"Causal execution end capture failed: {e}")
            return False
    
    def capture_decision_point(
        self,
        decision_type: str,
        module_id: str,
        execution_id: str,
        correlation_id: Optional[str],
        trace_id: Optional[str],
        parent_event_id: Optional[str],
        boundary_type: str,
        decision_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Capture decision point causal context (observational only)
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        """
        if not self.enabled:
            return None
        
        try:
            now = datetime.now(timezone.utc)
            causal_chain_id = self._generate_causal_chain_id(correlation_id, trace_id)
            
            record = CausalContextRecord(
                record_id=f"causal_{int(now.timestamp() * 1000000)}_{module_id}_{execution_id}_decision",
                timestamp=now,
                correlation_id=correlation_id,
                trace_id=trace_id,
                parent_event_id=parent_event_id,
                causal_chain_id=causal_chain_id,
                event_type=CausalContextType.DECISION_POINT,
                context_type="decision_observation",
                module_id=module_id,
                execution_id=execution_id,
                boundary_type=boundary_type,
                metadata={
                    'decision_type': decision_type,
                    **decision_metadata
                }
            )
            
            # Emit record (non-blocking)
            if self.high_performance_mode:
                try:
                    self._emission_queue.put(record, block=False)
                except:
                    # Queue full, drop record (never block execution)
                    logger.debug("Causal queue full, dropping record")
                    return None
            else:
                # Synchronous emission (still non-blocking for sinks)
                for sink in self.sinks:
                    try:
                        sink.emit(record)
                    except Exception as e:
                        logger.debug(f"Causal emission failed: {e}")
            
            return record.record_id
            
        except Exception as e:
            logger.debug(f"Causal decision point capture failed: {e}")
            return None
    
    def capture_boundary_crossing(
        self,
        from_boundary: str,
        to_boundary: str,
        module_id: str,
        execution_id: str,
        correlation_id: Optional[str],
        trace_id: Optional[str],
        parent_event_id: Optional[str],
        crossing_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Capture boundary crossing causal context
        
        STRICTLY OBSERVATIONAL - NEVER AFFECTS EXECUTION
        """
        if not self.enabled:
            return None
        
        try:
            now = datetime.now(timezone.utc)
            causal_chain_id = self._generate_causal_chain_id(correlation_id, trace_id)
            
            record = CausalContextRecord(
                record_id=f"causal_{int(now.timestamp() * 1000000)}_{module_id}_{execution_id}_boundary",
                timestamp=now,
                correlation_id=correlation_id,
                trace_id=trace_id,
                parent_event_id=parent_event_id,
                causal_chain_id=causal_chain_id,
                event_type=CausalContextType.BOUNDARY_CROSSING,
                context_type="boundary_observation",
                module_id=module_id,
                execution_id=execution_id,
                boundary_type=to_boundary,
                metadata={
                    'from_boundary': from_boundary,
                    'to_boundary': to_boundary,
                    **(crossing_metadata or {})
                }
            )
            
            # Emit record (non-blocking)
            if self.high_performance_mode:
                try:
                    self._emission_queue.put(record, block=False)
                except:
                    # Queue full, drop record (never block execution)
                    logger.debug("Causal queue full, dropping record")
                    return None
            else:
                # Synchronous emission (still non-blocking for sinks)
                for sink in self.sinks:
                    try:
                        sink.emit(record)
                    except Exception as e:
                        logger.debug(f"Causal emission failed: {e}")
            
            return record.record_id
            
        except Exception as e:
            logger.debug(f"Causal boundary crossing capture failed: {e}")
            return None
    
    def get_memory_records(self, limit: Optional[int] = None) -> List[CausalContextRecord]:
        """Get records from memory sinks (for testing/debugging)"""
        records = []
        for sink in self.sinks:
            if isinstance(sink, MemoryCausalSink):
                records.extend(sink.get_records(limit))
        return records
    
    def get_causal_chains(self) -> Dict[str, List[CausalContextRecord]]:
        """Get causal chains from memory sinks"""
        chains = {}
        for sink in self.sinks:
            if isinstance(sink, MemoryCausalSink):
                # Get all unique chain IDs
                all_records = sink.get_records()
                chain_ids = set(record.causal_chain_id for record in all_records)
                
                for chain_id in chain_ids:
                    if chain_id not in chains:
                        chains[chain_id] = sink.get_causal_chain(chain_id)
        
        return chains
    
    def clear_memory_records(self):
        """Clear records from memory sinks"""
        for sink in self.sinks:
            if isinstance(sink, MemoryCausalSink):
                sink.clear()
    
    def close(self):
        """Close causal context logger and cleanup resources"""
        if self.high_performance_mode and self._emission_thread:
            self._stop_event.set()
            if self._emission_thread.is_alive():
                self._emission_thread.join(timeout=5.0)
        
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as e:
                logger.debug(f"Error closing causal sink: {e}")
        
        logger.info("CausalContextLogger closed")


# Global causal context logger instance (singleton pattern)
_causal_context_logger: Optional[CausalContextLogger] = None


def get_causal_context_logger() -> CausalContextLogger:
    """Get global causal context logger instance"""
    global _causal_context_logger
    if _causal_context_logger is None:
        _causal_context_logger = CausalContextLogger()
    return _causal_context_logger


def configure_causal_context(
    sinks: Optional[List[CausalContextSink]] = None,
    enabled: bool = True,
    high_performance_mode: bool = True
) -> CausalContextLogger:
    """Configure global causal context logger"""
    global _causal_context_logger
    if _causal_context_logger:
        _causal_context_logger.close()
    
    _causal_context_logger = CausalContextLogger(sinks, enabled, high_performance_mode)
    return _causal_context_logger
