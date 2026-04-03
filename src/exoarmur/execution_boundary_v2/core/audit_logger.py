"""
Deterministic Audit Logger implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import hashlib
import json
import time

from .core_types import *

# === AUDIT LOG STRUCTURES ===

@dataclass(frozen=True)
class AuditLogEntry:
    """Single audit log entry with hash chaining"""
    entry_id: str
    execution_id: ExecutionID
    module_id: ModuleID
    event_type: str
    event_data: Dict[str, Any]
    timestamp: int
    previous_hash: str
    current_hash: str
    
    def verify_hash_chain(self, previous_entry: Optional['AuditLogEntry']) -> bool:
        """Verify hash chain integrity"""
        if previous_entry is None:
            return self.previous_hash == ""
        
        expected_previous = previous_entry.current_hash
        return self.previous_hash == expected_previous
    
    def compute_entry_hash(self) -> str:
        """Compute deterministic entry hash"""
        entry_data = {
            'entry_id': self.entry_id,
            'execution_id': self.execution_id.value,
            'module_id': self.module_id.value,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash
        }
        return hashlib.sha256(json.dumps(entry_data, sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class AuditLog:
    """Append-only audit log with hash chaining"""
    execution_id: ExecutionID
    entries: List[AuditLogEntry] = field(default_factory=list)
    final_hash: Optional[str] = None
    
    def add_entry(self, module_id: ModuleID, event_type: str, 
                  event_data: Dict[str, Any], timestamp: int) -> AuditLogEntry:
        """Add entry to audit log"""
        
        previous_hash = ""
        if self.entries:
            previous_hash = self.entries[-1].current_hash
        
        entry_id = f"entry_{len(self.entries)}"
        
        entry = AuditLogEntry(
            entry_id=entry_id,
            execution_id=self.execution_id,
            module_id=module_id,
            event_type=event_type,
            event_data=event_data,
            timestamp=timestamp,
            previous_hash=previous_hash,
            current_hash=""
        )
        
        entry.current_hash = entry.compute_entry_hash()
        
        self.entries.append(entry)
        
        return entry
    
    def verify_integrity(self) -> bool:
        """Verify complete audit log integrity"""
        for i, entry in enumerate(self.entries):
            previous_entry = self.entries[i-1] if i > 0 else None
            if not entry.verify_hash_chain(previous_entry):
                return False
        
        # Verify timestamps are in order
        timestamps = [entry.timestamp for entry in self.entries]
        if timestamps != sorted(timestamps):
            return False
        
        return True
    
    def compute_final_hash(self) -> str:
        """Compute final hash of entire audit log"""
        if not self.entries:
            return hashlib.sha256(b"").hexdigest()
        
        return self.entries[-1].current_hash
    
    def get_entries_by_type(self, event_type: str) -> List[AuditLogEntry]:
        """Get entries by event type"""
        return [entry for entry in self.entries if entry.event_type == event_type]
    
    def get_entries_by_module(self, module_id: ModuleID) -> List[AuditLogEntry]:
        """Get entries by module ID"""
        return [entry for entry in self.entries if entry.module_id == module_id]

# === AUDIT LOGGER ===

class DeterministicAuditLogger:
    """Deterministic audit logger with append-only semantics"""
    
    def __init__(self, execution_id: ExecutionID):
        self.execution_id = execution_id
        self.audit_log = AuditLog(execution_id=execution_id)
        self.is_finalized = False
    
    def log_state_transition(self, module_id: ModuleID, from_state: StateEnum, 
                           to_state: StateEnum, event: str, timestamp: int) -> AuditLogEntry:
        """Log state transition"""
        event_data = {
            'from_state': from_state.value,
            'to_state': to_state.value,
            'trigger_event': event
        }
        
        return self.audit_log.add_entry(
            module_id=module_id,
            event_type="state_transition",
            event_data=event_data,
            timestamp=timestamp
        )
    
    def log_module_input(self, module_id: ModuleID, input_data: Dict[str, Any], 
                        input_hash: str, timestamp: int) -> AuditLogEntry:
        """Log module input"""
        event_data = {
            'input_data': input_data,
            'input_hash': input_hash
        }
        
        return self.audit_log.add_entry(
            module_id=module_id,
            event_type="module_input",
            event_data=event_data,
            timestamp=timestamp
        )
    
    def log_module_output(self, module_id: ModuleID, output_data: Dict[str, Any], 
                         output_hash: str, success: bool, timestamp: int) -> AuditLogEntry:
        """Log module output"""
        event_data = {
            'output_data': output_data,
            'output_hash': output_hash,
            'success': success
        }
        
        return self.audit_log.add_entry(
            module_id=module_id,
            event_type="module_output",
            event_data=event_data,
            timestamp=timestamp
        )
    
    def log_failure(self, module_id: ModuleID, failure_code: FailureCode, 
                   failure_message: str, timestamp: int) -> AuditLogEntry:
        """Log failure event"""
        event_data = {
            'failure_code': failure_code.value,
            'failure_message': failure_message
        }
        
        return self.audit_log.add_entry(
            module_id=module_id,
            event_type="failure",
            event_data=event_data,
            timestamp=timestamp
        )
    
    def log_validation_result(self, module_id: ModuleID, validation_type: str, 
                            result: bool, details: Dict[str, Any], timestamp: int) -> AuditLogEntry:
        """Log validation result"""
        event_data = {
            'validation_type': validation_type,
            'result': result,
            'details': details
        }
        
        return self.audit_log.add_entry(
            module_id=module_id,
            event_type="validation_result",
            event_data=event_data,
            timestamp=timestamp
        )
    
    def finalize_log(self) -> str:
        """Finalize audit log and return final hash"""
        if self.is_finalized:
            raise RuntimeError("Audit log already finalized")
        
        self.audit_log.final_hash = self.audit_log.compute_final_hash()
        self.is_finalized = True
        
        return self.audit_log.final_hash
    
    def get_audit_log(self) -> AuditLog:
        """Get complete audit log"""
        return self.audit_log
    
    def verify_log_integrity(self) -> bool:
        """Verify audit log integrity"""
        return self.audit_log.verify_integrity()
    
    def get_entry_count(self) -> int:
        """Get total entry count"""
        return len(self.audit_log.entries)
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get audit log summary"""
        if not self.audit_log.entries:
            return {
                'execution_id': self.execution_id.value,
                'entry_count': 0,
                'first_timestamp': None,
                'last_timestamp': None,
                'event_types': [],
                'final_hash': self.audit_log.final_hash
            }
        
        event_types = list(set(entry.event_type for entry in self.audit_log.entries))
        
        return {
            'execution_id': self.execution_id.value,
            'entry_count': len(self.audit_log.entries),
            'first_timestamp': self.audit_log.entries[0].timestamp,
            'last_timestamp': self.audit_log.entries[-1].timestamp,
            'event_types': event_types,
            'final_hash': self.audit_log.final_hash
        }