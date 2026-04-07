"""
Execution trace models for deterministic governance tracking.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

Provides comprehensive execution event tracking with forensic-grade replay
verification and deterministic ID generation for complete audit trails.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from exoarmur.clock import utc_now
from exoarmur.ids import make_trace_id, make_event_id
from ..utils.verdict_resolution import FinalVerdict


class TraceStage(str, Enum):
    """Execution trace stage enumeration with governance semantics."""
    INTENT_RECEIVED = "intent_received"
    POLICY_EVALUATED = "policy_evaluated"
    SAFETY_EVALUATED = "safety_evaluated"
    VERDICT_RESOLVED = "verdict_resolved"
    APPROVAL_CHECKED = "approval_checked"
    TARGET_VALIDATED = "target_validated"
    EXECUTOR_DISPATCHED = "executor_dispatched"
    COMPLETED = "completed"


class TraceEvent(BaseModel):
    """Single event in execution trace with governance context."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(description="Event identifier (deterministic ULID)")
    stage: TraceStage = Field(description="Trace stage identifier")
    ok: bool = Field(description="Whether the stage succeeded")
    code: str = Field(description="Stage-specific status code")
    details: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific details")
    timestamp: Optional[str] = Field(default=None, description="Event timestamp (optional for determinism)")
    sequence: int = Field(default=0, description="Event sequence number for ordering")
    
    # Enhanced replay verification fields
    checksum: Optional[str] = Field(default=None, description="SHA-256 checksum of event data for integrity verification")
    parent_event_id: Optional[str] = Field(default=None, description="Parent event ID for dependency tracking")
    event_hash: Optional[str] = Field(default=None, description="Hash of event for replay verification")

    @classmethod
    def create(cls, trace_id: str, stage: TraceStage, ok: bool, code: str,
               details: Optional[Dict[str, Any]] = None, sequence: int = 0,
               parent_event_id: Optional[str] = None) -> "TraceEvent":
        """Create TraceEvent with deterministic ID and enhanced verification."""
        if details is None:
            details = {}
        
        event_id = make_event_id(trace_id, stage.value, sequence)
        
        # Generate event hash for replay verification
        event_data = {
            "event_id": event_id,
            "stage": stage.value,
            "ok": ok,
            "code": code,
            "details": details,
            "sequence": sequence,
            "parent_event_id": parent_event_id
        }
        event_hash = __import__('hashlib').sha256(
            __import__('json').dumps(event_data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        
        return cls(
            event_id=event_id,
            stage=stage,
            ok=ok,
            code=code,
            details=details,
            sequence=sequence,
            parent_event_id=parent_event_id,
            event_hash=event_hash
        )
    
    def verify_integrity(self) -> bool:
        """Verify event integrity using stored hash."""
        if not self.event_hash:
            return False
        
        event_data = {
            "event_id": self.event_id,
            "stage": self.stage.value,
            "ok": self.ok,
            "code": self.code,
            "details": self.details,
            "sequence": self.sequence,
            "parent_event_id": self.parent_event_id
        }
        
        computed_hash = __import__('hashlib').sha256(
            __import__('json').dumps(event_data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        
        return computed_hash == self.event_hash


class ExecutorTrace(BaseModel):
    """Executor-specific trace information for sandbox verification."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    executor_name: str = Field(description="Executor plugin name")
    executor_version: str = Field(description="Executor plugin version")
    capabilities: Dict[str, Any] = Field(description="Executor capabilities used")
    validation_result: Dict[str, Any] = Field(description="Target validation result")
    execution_start: Optional[str] = Field(default=None, description="Execution start timestamp")
    execution_end: Optional[str] = Field(default=None, description="Execution end timestamp")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage metrics")
    
    def verify_determinism(self) -> bool:
        """Verify executor trace follows deterministic patterns."""
        # Check that timestamps are None for determinism
        if self.execution_start is not None or self.execution_end is not None:
            return False
        
        # Check that resource usage is deterministic (or empty)
        if self.resource_usage and not all(
            isinstance(v, (int, float, str, bool)) for v in self.resource_usage.values()
        ):
            return False
        
        return True


class VerdictTrace(BaseModel):
    """Comprehensive verdict tracking for governance audit trail."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    policy_verdict: str = Field(description="Policy decision verdict")
    policy_decision_id: str = Field(description="Policy decision identifier")
    policy_rationale: str = Field(description="Policy decision rationale")
    policy_evidence: Dict[str, Any] = Field(default_factory=dict, description="Policy decision evidence")
    
    safety_verdict: str = Field(description="Safety gate verdict")
    safety_rule_ids: List[str] = Field(default_factory=list, description="Safety gate rule identifiers")
    safety_rationale: str = Field(description="Safety gate rationale")
    
    final_verdict: FinalVerdict = Field(description="Final resolved verdict")
    resolution_evidence: Dict[str, Any] = Field(default_factory=dict, description="Verdict resolution evidence")
    resolution_rules_applied: List[str] = Field(default_factory=list, description="Precedence rules applied")


class ExecutionTrace(BaseModel):
    """Complete execution trace with comprehensive governance context.
    
    Enhanced with forensic-grade replay verification and integrity checking.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    trace_id: str = Field(description="Trace identifier (deterministic ULID)")
    correlation_id: str = Field(description="Correlation identifier for audit linking")
    intent_id: str = Field(description="Associated intent identifier")
    bundle_id: Optional[str] = Field(default=None, description="Associated bundle identifier")
    
    # Trace events and ordering
    events: List[TraceEvent] = Field(description="Ordered trace events")
    event_sequence: List[str] = Field(description="Event ID sequence for verification")
    
    # Governance context
    final_verdict: FinalVerdict = Field(description="Final resolved verdict")
    policy_decision_id: Optional[str] = Field(default=None, description="Policy decision identifier")
    safety_verdict_id: Optional[str] = Field(default=None, description="Safety verdict identifier")
    
    # Verdict tracking
    verdict_trace: Optional[VerdictTrace] = Field(default=None, description="Comprehensive verdict tracking")
    
    # Executor information
    executor_trace: Optional[ExecutorTrace] = Field(default=None, description="Executor execution trace")
    
    # Enhanced verification fields
    trace_hash: Optional[str] = Field(default=None, description="SHA-256 hash of entire trace")
    integrity_checksum: Optional[str] = Field(default=None, description="Checksum for integrity verification")
    replay_timestamp: Optional[str] = Field(default=None, description="Replay verification timestamp")
    
    # Audit linking
    audit_stream_id: Optional[str] = Field(default=None, description="Audit stream identifier")
    audit_event_count: int = Field(default=0, description="Number of audit events generated")
    
    trace_created_at: Optional[str] = Field(default=None, description="Trace creation timestamp (optional for determinism)")

    @classmethod
    def create(cls, correlation_id: str, intent_id: str, final_verdict: FinalVerdict) -> "ExecutionTrace":
        """Create execution trace with deterministic ID."""
        from exoarmur.clock import utc_now
        trace_id = make_trace_id(intent_id)
        
        return cls(
            trace_id=trace_id,
            correlation_id=correlation_id,
            intent_id=intent_id,
            events=[],
            event_sequence=[],
            final_verdict=final_verdict,
            audit_event_count=0,
            trace_created_at=utc_now().isoformat(),  # Populated for audit trail; excluded from hash by canonicalization
            replay_timestamp=None   # Set during replay, not at creation
        )
    
    def add_event(self, stage: TraceStage, ok: bool, code: str,
                  details: Optional[Dict[str, Any]] = None,
                  parent_event_id: Optional[str] = None) -> TraceEvent:
        """Add event to trace with automatic sequencing."""
        sequence = len(self.events)
        
        event = TraceEvent.create(
            trace_id=self.trace_id,
            stage=stage,
            ok=ok,
            code=code,
            details=details or {},
            sequence=sequence,
            parent_event_id=parent_event_id
        )
        
        self.events.append(event)
        self.event_sequence.append(event.event_id)
        
        # Update trace hash
        self._update_trace_hash()
        
        return event
    
    def get_event_by_stage(self, stage: TraceStage) -> Optional[TraceEvent]:
        """Get event by stage."""
        for event in self.events:
            if event.stage == stage:
                return event
        return None
    
    def get_events_by_code(self, code: str) -> List[TraceEvent]:
        """Get all events with specific code."""
        return [event for event in self.events if event.code == code]
    
    def verify_event_sequence(self) -> bool:
        """Verify event sequence is complete and ordered."""
        if len(self.events) != len(self.event_sequence):
            return False
        
        # Check sequence matches events
        for i, event in enumerate(self.events):
            if self.event_sequence[i] != event.event_id:
                return False
            
            # Verify event integrity
            if not event.verify_integrity():
                return False
        
        return True
    
    def verify_stage_completeness(self) -> List[str]:
        """Verify all required stages are present."""
        required_stages = set(TraceStage)
        present_stages = {event.stage for event in self.events}
        missing_stages = required_stages - present_stages
        
        return [stage.value for stage in missing_stages]
    
    def _update_trace_hash(self):
        """Update trace hash for integrity verification."""
        trace_data = {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "intent_id": self.intent_id,
            "final_verdict": self.final_verdict.value,
            "events": [event.model_dump() for event in self.events],
            "event_sequence": self.event_sequence
        }
        
        self.trace_hash = __import__('hashlib').sha256(
            __import__('json').dumps(trace_data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify complete trace integrity."""
        # Verify event sequence
        if not self.verify_event_sequence():
            return False
        
        # Verify trace hash
        if self.trace_hash:
            trace_data = {
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "intent_id": self.intent_id,
                "final_verdict": self.final_verdict.value,
                "events": [event.model_dump() for event in self.events],
                "event_sequence": self.event_sequence
            }
            
            computed_hash = __import__('hashlib').sha256(
                __import__('json').dumps(trace_data, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            
            if computed_hash != self.trace_hash:
                return False
        
        # Verify executor trace determinism if present
        if self.executor_trace and not self.executor_trace.verify_determinism():
            return False
        
        return True
    
    def get_replay_summary(self) -> Dict[str, Any]:
        """Get summary for replay verification."""
        successful_events = len([e for e in self.events if e.ok])
        failed_events = len(self.events) - successful_events
        
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "intent_id": self.intent_id,
            "final_verdict": self.final_verdict.value,
            "total_events": len(self.events),
            "successful_events": successful_events,
            "failed_events": failed_events,
            "event_stages": [event.stage.value for event in self.events],
            "has_executor_trace": self.executor_trace is not None,
            "trace_hash_verified": self.verify_integrity(),
            "missing_stages": self.verify_stage_completeness()
        }
    
    def record_verdicts(self, policy_decision, safety_verdict, final_verdict, resolution_evidence) -> None:
        """Record comprehensive verdict information for governance audit trail."""
        self.verdict_trace = VerdictTrace(
            policy_verdict=policy_decision.verdict.value,
            policy_decision_id=policy_decision.decision_id,
            policy_rationale=policy_decision.rationale,
            policy_evidence=policy_decision.evidence or {},
            safety_verdict=safety_verdict.verdict,
            safety_rule_ids=safety_verdict.rule_ids,
            safety_rationale=safety_verdict.rationale,
            final_verdict=final_verdict,
            resolution_evidence=resolution_evidence,
            resolution_rules_applied=resolution_evidence.get("resolution_rules_applied", [])
        )
    
    def record_executor_info(self, executor_name: str, executor_version: str, 
                            executor_capabilities: Dict[str, Any], 
                            validation_result: Dict[str, Any],
                            validation_evidence: Dict[str, Any], 
                            executor_failure_evidence: Dict[str, Any]) -> None:
        """Record executor sandboxing and capability enforcement information."""
        self.executor_trace = ExecutorTrace(
            executor_name=executor_name,
            executor_version=executor_version,
            capabilities=executor_capabilities,
            validation_result=validation_result,
            resource_usage=executor_failure_evidence
        )
