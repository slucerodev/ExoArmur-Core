"""
Forensic-grade replay verification engine for deterministic audit replay.

Provides comprehensive mismatch detection, deterministic diffing, and
structured replay reporting for execution governance boundary verification.
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum

from exoarmur.clock import utc_now
from exoarmur.ids import make_id
from ..models.execution_trace import ExecutionTrace, TraceEvent, TraceStage
from ..models.execution_proof_bundle import ExecutionProofBundle
from ..utils.canonicalization import to_canonical_dict, canonical_json
from ..utils.verdict_resolution import FinalVerdict

logger = logging.getLogger(__name__)


def _canonical_replay_timestamp() -> datetime:
    """Generate canonical timestamp for replay reports."""
    return utc_now()


class ReplayResult(Enum):
    """Replay outcome status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    MISMATCH = "mismatch"


class MismatchType(str, Enum):
    """Types of mismatches that can be detected during replay."""
    REPLAY_HASH_MISMATCH = "replay_hash_mismatch"
    BUNDLE_ID_MISMATCH = "bundle_id_mismatch"
    TRACE_ID_MISMATCH = "trace_id_mismatch"
    EVENT_ID_MISMATCH = "event_id_mismatch"
    TIMESTAMP_MISMATCH = "timestamp_mismatch"
    PDP_VERDICT_MISMATCH = "pdp_verdict_mismatch"
    SAFETY_VERDICT_MISMATCH = "safety_verdict_mismatch"
    FINAL_VERDICT_MISMATCH = "final_verdict_mismatch"
    EXECUTOR_OUTPUT_MISMATCH = "executor_output_mismatch"
    MISSING_TRACE_EVENTS = "missing_trace_events"
    MISSING_AUDIT_EVENTS = "missing_audit_events"
    CANONICALIZATION_MISMATCH = "canonicalization_mismatch"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"
    NONDETERMINISTIC_IDS = "nondeterministic_ids"
    NONDETERMINISTIC_TIMESTAMPS = "nondeterministic_timestamps"
    MISSING_FIELDS = "missing_fields"
    UNKNOWN_SCHEMA_VERSION = "unknown_schema_version"


@dataclass
class ReplayMismatch:
    """Individual replay mismatch with detailed context."""
    mismatch_type: MismatchType
    field_path: str
    expected_value: Any
    actual_value: Any
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "high"  # high, medium, low
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mismatch to deterministic dictionary."""
        return {
            "mismatch_type": self.mismatch_type.value,
            "field_path": self.field_path,
            "expected_value": self._serialize_value(self.expected_value),
            "actual_value": self._serialize_value(self.actual_value),
            "context": self.context,
            "severity": self.severity
        }
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for deterministic output."""
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        elif hasattr(value, "dict"):
            return value.dict()
        elif isinstance(value, (dict, list)):
            return value
        else:
            return str(value)


@dataclass
class ReplayDiff:
    """Deterministic diff structure for replay comparisons."""
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    modified: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to deterministic dictionary."""
        return {
            "added": sorted(self.added),
            "removed": sorted(self.removed),
            "modified": dict(sorted(self.modified.items()))
        }
    
    def has_changes(self) -> bool:
        """Check if diff has any changes."""
        return bool(self.added or self.removed or self.modified)


@dataclass
class ReplayReport:
    """Comprehensive forensic replay execution report."""
    
    correlation_id: str
    bundle_id: Optional[str] = None
    trace_id: Optional[str] = None
    replay_timestamp: datetime = field(default_factory=_canonical_replay_timestamp)
    result: ReplayResult = ReplayResult.SUCCESS
    
    # Replay verification metrics
    replay_hash_verified: bool = True
    bundle_id_verified: bool = True
    trace_id_verified: bool = True
    event_ids_verified: bool = True
    timestamps_verified: bool = True
    schema_version_verified: bool = True
    
    # Processing metrics
    total_events: int = 0
    processed_events: int = 0
    failed_events: int = 0
    
    # Mismatch detection
    mismatches: List[ReplayMismatch] = field(default_factory=list)
    mismatch_flags: Set[MismatchType] = field(default_factory=set)
    
    # Diff structures
    trace_diff: ReplayDiff = field(default_factory=ReplayDiff)
    bundle_diff: ReplayDiff = field(default_factory=ReplayDiff)
    evidence_diff: ReplayDiff = field(default_factory=ReplayDiff)
    verdict_diff: ReplayDiff = field(default_factory=ReplayDiff)
    executor_output_diff: ReplayDiff = field(default_factory=ReplayDiff)
    
    # Deterministic evidence summary
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Failure details
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_mismatch(self, mismatch_type: MismatchType, field_path: str,
                    expected_value: Any, actual_value: Any,
                    context: Optional[Dict[str, Any]] = None,
                    severity: str = "high"):
        """Add a mismatch to the report."""
        mismatch = ReplayMismatch(
            mismatch_type=mismatch_type,
            field_path=field_path,
            expected_value=expected_value,
            actual_value=actual_value,
            context=context or {},
            severity=severity
        )
        self.mismatches.append(mismatch)
        self.mismatch_flags.add(mismatch_type)
        
        # Update result based on severity
        if severity == "high":
            self.result = ReplayResult.FAILURE
        elif self.result == ReplayResult.SUCCESS:
            self.result = ReplayResult.MISMATCH
    
    def add_failure(self, message: str):
        """Add failure to report."""
        self.failures.append(message)
        self.result = ReplayResult.FAILURE
        self.failed_events += 1
    
    def add_warning(self, message: str):
        """Add warning to report."""
        self.warnings.append(message)
        if self.result == ReplayResult.SUCCESS:
            self.result = ReplayResult.PARTIAL
    
    def has_mismatches(self) -> bool:
        """Check if report has any mismatches."""
        return bool(self.mismatches)
    
    def get_mismatch_count(self, mismatch_type: MismatchType) -> int:
        """Get count of specific mismatch type."""
        return sum(1 for m in self.mismatches if m.mismatch_type == mismatch_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize report deterministically for replay comparisons."""
        return {
            "correlation_id": self.correlation_id,
            "bundle_id": self.bundle_id,
            "trace_id": self.trace_id,
            "replay_timestamp": self.replay_timestamp.isoformat().replace("+00:00", "Z"),
            "result": self.result.value,
            "replay_hash_verified": self.replay_hash_verified,
            "bundle_id_verified": self.bundle_id_verified,
            "trace_id_verified": self.trace_id_verified,
            "event_ids_verified": self.event_ids_verified,
            "timestamps_verified": self.timestamps_verified,
            "schema_version_verified": self.schema_version_verified,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
            "failed_events": self.failed_events,
            "mismatches": [m.to_dict() for m in sorted(self.mismatches, key=lambda x: x.field_path)],
            "mismatch_flags": sorted([m.value for m in self.mismatch_flags]),
            "trace_diff": self.trace_diff.to_dict(),
            "bundle_diff": self.bundle_diff.to_dict(),
            "evidence_diff": self.evidence_diff.to_dict(),
            "verdict_diff": self.verdict_diff.to_dict(),
            "executor_output_diff": self.executor_output_diff.to_dict(),
            "evidence_summary": self.evidence_summary,
            "failures": sorted(self.failures),
            "warnings": sorted(self.warnings),
        }


class ReplayEngine:
    """Forensic-grade deterministic audit replay engine."""
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize replay engine with forensic verification capabilities.
        
        Args:
            strict_mode: If True, rejects any nondeterministic behavior
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
    
    def replay_bundle(self, bundle: ExecutionProofBundle) -> ReplayReport:
        """
        Replay execution proof bundle with forensic verification.
        
        Args:
            bundle: Execution proof bundle to replay
            
        Returns:
            Comprehensive forensic replay report
        """
        report = ReplayReport(
            correlation_id=bundle.intent.get("correlation_id", "unknown"),
            bundle_id=bundle.bundle_id,
            trace_id=bundle.execution_trace.get("trace_id", "unknown")
        )
        
        try:
            # Step 1: Verify bundle integrity
            self._verify_bundle_integrity(bundle, report)
            
            # Step 2: Verify replay hash
            self._verify_replay_hash(bundle, report)
            
            # Step 3: Verify schema version
            self._verify_schema_version(bundle, report)
            
            # Step 4: Verify deterministic IDs
            self._verify_deterministic_ids(bundle, report)
            
            # Step 5: Verify timestamps
            self._verify_timestamps(bundle, report)
            
            # Step 6: Verify trace events
            self._verify_trace_events(bundle, report)
            
            # Step 7: Verify verdicts
            self._verify_verdicts(bundle, report)
            
            # Step 8: Verify executor output
            self._verify_executor_output(bundle, report)
            
            # Step 9: Generate evidence summary
            self._generate_evidence_summary(bundle, report)
            
            # Step 10: Final verification status
            self._finalize_verification_status(report)
            
        except Exception as e:
            report.add_failure(f"Replay failed with unexpected error: {e}")
            self.logger.error(f"Replay failed for bundle {bundle.bundle_id}: {e}")
        
        return report
    
    def compare_bundles(self, original_bundle: ExecutionProofBundle,
                        replay_bundle: ExecutionProofBundle) -> ReplayReport:
        """
        Compare two execution proof bundles and generate forensic diff report.
        
        Args:
            original_bundle: Original execution bundle
            replay_bundle: Replay execution bundle
            
        Returns:
            Comprehensive comparison report with diffs
        """
        report = ReplayReport(
            correlation_id=original_bundle.intent.get("correlation_id", "unknown"),
            bundle_id=original_bundle.bundle_id,
            trace_id=original_bundle.execution_trace.get("trace_id", "unknown")
        )
        
        try:
            # Compare bundle structure
            self._compare_bundle_structure(original_bundle, replay_bundle, report)
            
            # Compare execution traces
            self._compare_execution_traces(original_bundle, replay_bundle, report)
            
            # Compare verdicts
            self._compare_verdicts(original_bundle, replay_bundle, report)
            
            # Compare evidence
            self._compare_evidence(original_bundle, replay_bundle, report)
            
            # Compare executor outputs
            self._compare_executor_outputs(original_bundle, replay_bundle, report)
            
        except Exception as e:
            report.add_failure(f"Bundle comparison failed: {e}")
        
        return report
    
    def _verify_bundle_integrity(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify basic bundle integrity and required fields."""
        required_fields = ["bundle_id", "intent", "policy_decision", "safety_verdict", 
                          "final_verdict", "execution_trace", "replay_hash"]
        
        for field in required_fields:
            if not hasattr(bundle, field) or getattr(bundle, field) is None:
                report.add_mismatch(
                    MismatchType.MISSING_FIELDS,
                    field,
                    f"field present and non-null",
                    f"field missing or null",
                    {"bundle_id": bundle.bundle_id}
                )
    
    def _verify_replay_hash(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify replay hash matches canonical bundle data."""
        try:
            # Create canonical representation
            canonical_data = {
                "bundle_version": bundle.bundle_version,
                "intent": to_canonical_dict(bundle.intent),
                "policy_decision": to_canonical_dict(bundle.policy_decision),
                "safety_verdict": to_canonical_dict(bundle.safety_verdict),
                "final_verdict": bundle.final_verdict.value,
                "approval_records": [to_canonical_dict(r) for r in bundle.approval_records],
                "execution_trace": to_canonical_dict(bundle.execution_trace),
                "executor_result": to_canonical_dict(bundle.executor_result),
                "governance_evidence": to_canonical_dict(bundle.governance_evidence),
                "resolution_evidence": to_canonical_dict(bundle.resolution_evidence),
                "executor_capabilities": to_canonical_dict(bundle.executor_capabilities),
                "validation_evidence": to_canonical_dict(bundle.validation_evidence),
                "executor_failure_evidence": to_canonical_dict(bundle.executor_failure_evidence),
            }
            
            # Generate canonical hash
            canonical_json_bytes = canonical_json(canonical_data)
            computed_hash = hashlib.sha256(canonical_json_bytes).hexdigest()
            
            if computed_hash != bundle.replay_hash:
                report.add_mismatch(
                    MismatchType.REPLAY_HASH_MISMATCH,
                    "replay_hash",
                    bundle.replay_hash,
                    computed_hash,
                    {"bundle_id": bundle.bundle_id}
                )
                report.replay_hash_verified = False
            else:
                report.replay_hash_verified = True
                
        except Exception as e:
            report.add_failure(f"Replay hash verification failed: {e}")
            report.replay_hash_verified = False
    
    def _verify_schema_version(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify bundle schema version is supported."""
        supported_versions = ["v1"]
        
        if bundle.bundle_version not in supported_versions:
            report.add_mismatch(
                MismatchType.UNKNOWN_SCHEMA_VERSION,
                "bundle_version",
                supported_versions,
                bundle.bundle_version,
                {"bundle_id": bundle.bundle_id}
            )
            report.schema_version_verified = False
        else:
            report.schema_version_verified = True
    
    def _verify_deterministic_ids(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify IDs follow deterministic patterns."""
        # Verify bundle_id format
        if not self._is_valid_ulid(bundle.bundle_id):
            report.add_mismatch(
                MismatchType.NONDETERMINISTIC_IDS,
                "bundle_id",
                "valid ULID",
                bundle.bundle_id,
                {"bundle_id": bundle.bundle_id}
            )
            report.bundle_id_verified = False
        else:
            report.bundle_id_verified = True
        
        # Verify trace events have valid IDs
        trace_events = bundle.execution_trace.get("events", [])
        for event in trace_events:
            event_id = event.get("event_id")
            if not event_id or not self._is_valid_ulid(event_id):
                report.add_mismatch(
                    MismatchType.EVENT_ID_MISMATCH,
                    f"events.{event.get('stage', 'unknown')}.event_id",
                    "valid ULID",
                    event_id,
                    {"trace_id": bundle.execution_trace.get("trace_id")}
                )
                report.event_ids_verified = False
        
        if report.event_ids_verified is False:
            report.event_ids_verified = len(trace_events) > 0 and all(
                self._is_valid_ulid(event.get("event_id")) for event in trace_events
            )
    
    def _verify_timestamps(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify timestamps are deterministic or properly handled."""
        # Check if timestamps are present but should be None for determinism
        if bundle.bundle_created_at is not None:
            if self.strict_mode:
                report.add_mismatch(
                    MismatchType.NONDETERMINISTIC_TIMESTAMPS,
                    "bundle_created_at",
                    "None (for determinism)",
                    bundle.bundle_created_at.isoformat(),
                    {"bundle_id": bundle.bundle_id}
                )
                report.timestamps_verified = False
        
        # Check trace event timestamps
        trace_events = bundle.execution_trace.get("events", [])
        for event in trace_events:
            timestamp = event.get("timestamp")
            if timestamp is not None and self.strict_mode:
                report.add_mismatch(
                    MismatchType.NONDETERMINISTIC_TIMESTAMPS,
                    f"events.{event.get('stage', 'unknown')}.timestamp",
                    "None (for determinism)",
                    timestamp,
                    {"trace_id": bundle.execution_trace.get("trace_id")}
                )
                report.timestamps_verified = False
        
        if report.timestamps_verified is False:
            report.timestamps_verified = len(trace_events) > 0 and all(
                event.get("timestamp") is None for event in trace_events
            ) and bundle.bundle_created_at is None
    
    def _verify_trace_events(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify trace events are complete and properly ordered."""
        trace_events = bundle.execution_trace.get("events", [])
        required_stages = [stage.value for stage in TraceStage]
        
        # Check for missing stages
        present_stages = {event.get("stage") for event in trace_events}
        missing_stages = set(required_stages) - present_stages
        
        if missing_stages:
            report.add_mismatch(
                MismatchType.MISSING_TRACE_EVENTS,
                "execution_trace.events",
                required_stages,
                list(present_stages),
                {"missing_stages": list(missing_stages)}
            )
        
        report.total_events = len(trace_events)
        report.processed_events = len([e for e in trace_events if e.get("ok", False)])
    
    def _verify_verdicts(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify verdict consistency and validity."""
        # Verify final verdict is valid
        valid_final_verdicts = [v.value for v in FinalVerdict]
        if bundle.final_verdict.value not in valid_final_verdicts:
            report.add_mismatch(
                MismatchType.FINAL_VERDICT_MISMATCH,
                "final_verdict",
                valid_final_verdicts,
                bundle.final_verdict.value,
                {"bundle_id": bundle.bundle_id}
            )
        
        # Verify safety verdict structure
        safety_verdict = bundle.safety_verdict
        if not isinstance(safety_verdict, dict):
            report.add_mismatch(
                MismatchType.SAFETY_VERDICT_MISMATCH,
                "safety_verdict",
                "dict with verdict field",
                type(safety_verdict).__name__,
                {"bundle_id": bundle.bundle_id}
            )
        
        # Verify policy decision structure
        policy_decision = bundle.policy_decision
        if not isinstance(policy_decision, dict):
            report.add_mismatch(
                MismatchType.PDP_VERDICT_MISMATCH,
                "policy_decision",
                "dict with verdict field",
                type(policy_decision).__name__,
                {"bundle_id": bundle.bundle_id}
            )
    
    def _verify_executor_output(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Verify executor output structure and consistency."""
        executor_result = bundle.executor_result
        
        if not isinstance(executor_result, dict):
            report.add_mismatch(
                MismatchType.EXECUTOR_OUTPUT_MISMATCH,
                "executor_result",
                "dict with success, output, error fields",
                type(executor_result).__name__,
                {"bundle_id": bundle.bundle_id}
            )
            return
        
        # Check required fields
        required_fields = ["success", "output", "error"]
        for field in required_fields:
            if field not in executor_result:
                report.add_mismatch(
                    MismatchType.EXECUTOR_OUTPUT_MISMATCH,
                    f"executor_result.{field}",
                    f"field present",
                    f"field missing",
                    {"bundle_id": bundle.bundle_id}
                )
    
    def _generate_evidence_summary(self, bundle: ExecutionProofBundle, report: ReplayReport):
        """Generate deterministic evidence summary."""
        report.evidence_summary = {
            "bundle_id": bundle.bundle_id,
            "trace_id": bundle.execution_trace.get("trace_id"),
            "correlation_id": bundle.intent.get("correlation_id"),
            "final_verdict": bundle.final_verdict.value,
            "total_events": len(bundle.execution_trace.get("events", [])),
            "successful_events": len([e for e in bundle.execution_trace.get("events", []) if e.get("ok", False)]),
            "has_governance_evidence": bool(bundle.governance_evidence),
            "has_resolution_evidence": bool(bundle.resolution_evidence),
            "has_executor_capabilities": bool(bundle.executor_capabilities),
            "has_validation_evidence": bool(bundle.validation_evidence),
            "schema_version": bundle.bundle_version,
        }
    
    def _finalize_verification_status(self, report: ReplayReport):
        """Finalize verification status based on all checks."""
        if report.has_mismatches():
            if any(m.severity == "high" for m in report.mismatches):
                report.result = ReplayResult.FAILURE
            else:
                report.result = ReplayResult.MISMATCH
        elif report.failures:
            report.result = ReplayResult.FAILURE
        elif report.warnings:
            report.result = ReplayResult.PARTIAL
        else:
            report.result = ReplayResult.SUCCESS
    
    def _compare_bundle_structure(self, original: ExecutionProofBundle,
                                 replay: ExecutionProofBundle, report: ReplayReport):
        """Compare bundle structure and generate diff."""
        # Compare basic fields
        if original.bundle_id != replay.bundle_id:
            report.bundle_diff.modified["bundle_id"] = {
                "original": original.bundle_id,
                "replay": replay.bundle_id
            }
        
        if original.bundle_version != replay.bundle_version:
            report.bundle_diff.modified["bundle_version"] = {
                "original": original.bundle_version,
                "replay": replay.bundle_version
            }
        
        # Compare replay hashes
        if original.replay_hash != replay.replay_hash:
            report.bundle_diff.modified["replay_hash"] = {
                "original": original.replay_hash,
                "replay": replay.replay_hash
            }
            report.add_mismatch(
                MismatchType.REPLAY_HASH_MISMATCH,
                "replay_hash",
                original.replay_hash,
                replay.replay_hash
            )
    
    def _compare_execution_traces(self, original: ExecutionProofBundle,
                                  replay: ExecutionProofBundle, report: ReplayReport):
        """Compare execution traces and generate diff."""
        original_trace = original.execution_trace
        replay_trace = replay.execution_trace
        
        # Compare trace IDs
        if original_trace.get("trace_id") != replay_trace.get("trace_id"):
            report.trace_diff.modified["trace_id"] = {
                "original": original_trace.get("trace_id"),
                "replay": replay_trace.get("trace_id")
            }
            report.add_mismatch(
                MismatchType.TRACE_ID_MISMATCH,
                "execution_trace.trace_id",
                original_trace.get("trace_id"),
                replay_trace.get("trace_id")
            )
        
        # Compare events
        original_events = original_trace.get("events", [])
        replay_events = replay_trace.get("events", [])
        
        if len(original_events) != len(replay_events):
            report.trace_diff.modified["event_count"] = {
                "original": len(original_events),
                "replay": len(replay_events)
            }
            report.add_mismatch(
                MismatchType.MISSING_TRACE_EVENTS,
                "execution_trace.events",
                len(original_events),
                len(replay_events)
            )
        
        # Compare individual events
        for i, (orig_event, replay_event) in enumerate(zip(original_events, replay_events)):
            if orig_event != replay_event:
                report.trace_diff.modified[f"event_{i}"] = {
                    "original": orig_event,
                    "replay": replay_event
                }
    
    def _compare_verdicts(self, original: ExecutionProofBundle,
                         replay: ExecutionProofBundle, report: ReplayReport):
        """Compare verdicts and generate diff."""
        # Compare final verdicts
        if original.final_verdict != replay.final_verdict:
            report.verdict_diff.modified["final_verdict"] = {
                "original": original.final_verdict.value,
                "replay": replay.final_verdict.value
            }
            report.add_mismatch(
                MismatchType.FINAL_VERDICT_MISMATCH,
                "final_verdict",
                original.final_verdict.value,
                replay.final_verdict.value
            )
        
        # Compare safety verdicts
        if original.safety_verdict != replay.safety_verdict:
            report.verdict_diff.modified["safety_verdict"] = {
                "original": original.safety_verdict,
                "replay": replay.safety_verdict
            }
            report.add_mismatch(
                MismatchType.SAFETY_VERDICT_MISMATCH,
                "safety_verdict",
                original.safety_verdict,
                replay.safety_verdict
            )
        
        # Compare policy decisions
        if original.policy_decision != replay.policy_decision:
            report.verdict_diff.modified["policy_decision"] = {
                "original": original.policy_decision,
                "replay": replay.policy_decision
            }
            report.add_mismatch(
                MismatchType.PDP_VERDICT_MISMATCH,
                "policy_decision",
                original.policy_decision,
                replay.policy_decision
            )
    
    def _compare_evidence(self, original: ExecutionProofBundle,
                         replay: ExecutionProofBundle, report: ReplayReport):
        """Compare evidence structures and generate diff."""
        evidence_fields = [
            "governance_evidence",
            "resolution_evidence", 
            "executor_capabilities",
            "validation_evidence",
            "executor_failure_evidence"
        ]
        
        for field in evidence_fields:
            orig_value = getattr(original, field)
            replay_value = getattr(replay, field)
            
            if orig_value != replay_value:
                report.evidence_diff.modified[field] = {
                    "original": orig_value,
                    "replay": replay_value
                }
    
    def _compare_executor_outputs(self, original: ExecutionProofBundle,
                                 replay: ExecutionProofBundle, report: ReplayReport):
        """Compare executor outputs and generate diff."""
        if original.executor_result != replay.executor_result:
            report.executor_output_diff.modified["executor_result"] = {
                "original": original.executor_result,
                "replay": replay.executor_result
            }
            report.add_mismatch(
                MismatchType.EXECUTOR_OUTPUT_MISMATCH,
                "executor_result",
                original.executor_result,
                replay.executor_result
            )
    
    def _is_valid_ulid(self, ulid_string: str) -> bool:
        """Check if string is a valid ULID format."""
        if not isinstance(ulid_string, str):
            return False
        
        # Basic ULID format check: 26 characters, base32
        if len(ulid_string) != 26:
            return False
        
        # Check if all characters are valid base32
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        return all(c in valid_chars for c in ulid_string.upper())


class ReplayEngineError(Exception):
    """Raised when replay engine operations fail."""
    pass
