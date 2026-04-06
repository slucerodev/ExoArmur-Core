"""
Replay Engine for deterministic audit replay
Reconstructs and verifies organism behavior from audit logs
Enhanced with dual-format support for V1 and CanonicalAuditEnvelope
Now includes schema versioning and migration support for proof bundles.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .event_envelope import CanonicalEvent, EnvelopeValidationError
from .replay_envelope_builder import ReplayEnvelopeBuilder, ReplayEnvelope
from spec.contracts.models_v1 import AuditRecordV1
from exoarmur.audit.audit_normalizer import CanonicalAuditEnvelope
from exoarmur.clock import utc_now
from exoarmur.execution_boundary_v2.schema_migrations import SchemaMigrations, MigrationError
from exoarmur.execution_boundary_v2.utils.canonicalization import compute_replay_hash_with_migration

# Import system components for reconstruction
import sys
import os
from spec.contracts.models_v1 import TelemetryEventV1, LocalDecisionV1, BeliefV1, ExecutionIntentV1

logger = logging.getLogger(__name__)


def _canonical_replay_timestamp() -> datetime:
    """Generate canonical timestamp for replay reports."""
    return utc_now()


class ReplayResult(Enum):
    """Replay outcome status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    HASH_MISMATCH = "hash_mismatch"
    NO_AUDIT_RECORDS = "no_audit_records"
    MIGRATION_FAILED = "migration_failed"
    REPLAY_FAILED = "replay_failed"


@dataclass
class ReplayReport:
    """Comprehensive replay execution report"""
    
    correlation_id: str
    replay_timestamp: datetime = field(default_factory=_canonical_replay_timestamp)
    result: ReplayResult = ReplayResult.SUCCESS
    
    # Event processing metrics
    total_events: int = 0
    processed_events: int = 0
    failed_events: int = 0
    
    # Verification results
    intent_hash_verified: bool = True
    safety_gate_verified: bool = True
    audit_integrity_verified: bool = True
    
    # Reconstructed state
    reconstructed_intents: Dict[str, ExecutionIntentV1] = field(default_factory=dict)
    reconstructed_decisions: Dict[str, LocalDecisionV1] = field(default_factory=dict)
    safety_gate_verdicts: Dict[str, str] = field(default_factory=dict)
    
    # Failure details
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_failure(self, message: str):
        """Add failure to report"""
        self.failures.append(message)
        self.result = ReplayResult.FAILURE
        self.failed_events += 1
    
    def add_warning(self, message: str):
        """Add warning to report"""
        self.warnings.append(message)
        if self.result == ReplayResult.SUCCESS:
            self.result = ReplayResult.PARTIAL
    
    def add_info(self, message: str):
        """Add informational message to report"""
        # For now, add info as warnings since ReplayReport doesn't have an info field
        # In a future enhancement, we could add an info_messages field
        self.warnings.append(f"INFO: {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report deterministically for replay comparisons."""

        def _serialize_value(value: Any) -> Any:
            if hasattr(value, "model_dump"):
                return value.model_dump(mode="json")
            if hasattr(value, "dict"):
                return value.dict()
            return value

        return {
            "correlation_id": self.correlation_id,
            "replay_timestamp": self.replay_timestamp.isoformat().replace("+00:00", "Z"),
            "result": self.result.value,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
            "failed_events": self.failed_events,
            "intent_hash_verified": self.intent_hash_verified,
            "safety_gate_verified": self.safety_gate_verified,
            "audit_integrity_verified": self.audit_integrity_verified,
            "reconstructed_intents": {
                key: _serialize_value(value)
                for key, value in self.reconstructed_intents.items()
            },
            "reconstructed_decisions": {
                key: _serialize_value(value)
                for key, value in self.reconstructed_decisions.items()
            },
            "safety_gate_verdicts": dict(self.safety_gate_verdicts),
            "failures": list(self.failures),
            "warnings": list(self.warnings),
        }


class ReplayEngine:
    """Deterministic audit replay engine with dual-format support"""
    
    def __init__(self, 
                 audit_store: Dict[str, List[Union[CanonicalEvent, AuditRecordV1, CanonicalAuditEnvelope]]],
                 intent_store: Optional['IntentStore'] = None,
                 approval_service: Optional['ApprovalService'] = None):
        """
        Initialize replay engine with dual-format support
        
        Args:
            audit_store: Mixed format audit storage by correlation_id (V1, CanonicalEvent, or CanonicalAuditEnvelope)
            intent_store: Intent store for verification
            approval_service: Approval service for verification
        """
        self.audit_store = audit_store
        self.intent_store = intent_store
        self.approval_service = approval_service
        self.envelope_builder = ReplayEnvelopeBuilder()
        self.logger = logging.getLogger(__name__)
    
    def replay_correlation(self, correlation_id: str) -> ReplayReport:
        """
        Replay all events for a correlation ID deterministically with dual-format support
        
        Args:
            correlation_id: Correlation ID to replay
            
        Returns:
            Comprehensive replay report
        """
        report = ReplayReport(correlation_id=correlation_id)
        
        # Step 1: Retrieve mixed format audit records
        audit_records = self.audit_store.get(correlation_id, [])
        if not audit_records:
            report.add_failure(f"No audit records found for correlation_id: {correlation_id}")
            return report

        # Step 2: Build unified replay envelopes from mixed formats
        replay_envelopes = self.envelope_builder.build_envelopes(audit_records, preserve_ordering=True)
        if not replay_envelopes:
            report.add_failure("No valid replay envelopes created from audit records")
            return report
        
        # Step 3: Validate envelope sequence
        validation_issues = self.envelope_builder.validate_envelope_sequence(replay_envelopes)
        for issue in validation_issues:
            report.add_warning(f"Envelope validation issue: {issue}")

        try:
            # Step 4: Convert to CanonicalEvent for compatibility with existing replay logic
            canonical_events = self.envelope_builder.convert_to_canonical_events(replay_envelopes)
            if not canonical_events:
                report.add_failure("No valid canonical events created from replay envelopes")
                return report
            
            # Step 5: Sort by deterministic ordering (preserves original sequence)
            canonical_events.sort(key=lambda e: e.ordering_key)
            report.total_events = len(canonical_events)
            
            # Step 6: Process events in order
            for event in canonical_events:
                try:
                    self._process_envelope(event, report)
                    report.processed_events += 1
                except Exception as e:
                    report.add_failure(f"Failed to process envelope {event.event_id}: {e}")
            
            # Step 7: Verify final state integrity
            self._verify_final_state(report)
            
        except Exception as e:
            report.add_failure(f"Replay failed with unexpected error: {e}")
            self.logger.error(f"Replay failed for {correlation_id}: {e}")
        
        return report
    
    def _validate_dual_format_inputs(self, audit_records: List[Any], correlation_id: str) -> None:
        """Validate dual-format audit records before replay begins."""
        supported_types = (AuditRecordV1, CanonicalAuditEnvelope, CanonicalEvent)
        
        for index, record in enumerate(audit_records):
            if not isinstance(record, supported_types):
                raise EnvelopeValidationError(
                    f"ReplayEngine requires AuditRecordV1, CanonicalAuditEnvelope, or CanonicalEvent inputs only; "
                    f"got {type(record).__name__} at index {index} for correlation_id {correlation_id}"
                )
    
    def _create_envelopes(self, 
                         audit_records: List[CanonicalEvent], 
                         report: ReplayReport) -> List[CanonicalEvent]:
        """Validate canonical replay events and preserve deterministic ordering."""
        envelopes = []
        
        for record in audit_records:
            # Verify payload integrity
            if not record.verify_payload_integrity():
                report.add_failure(f"Payload integrity check failed for event {record.event_id}")
                continue

            envelopes.append(record)
        
        return envelopes

    def replay_dual_format_validation(
        self,
        correlation_id: str,
        test_format_mixing: bool = False
    ) -> Dict[str, ReplayReport]:
        """
        Validate dual-format replay by testing different format combinations
        
        Args:
            correlation_id: Correlation ID to test
            test_format_mixing: Whether to test mixed format scenarios
            
        Returns:
            Dictionary of replay reports for different format scenarios
        """
        reports = {}
        
        # Get original audit records
        original_records = self.audit_store.get(correlation_id, [])
        if not original_records:
            return {"error": ReplayReport(correlation_id=correlation_id, result=ReplayResult.FAILURE)}
        
        # Test 1: Pure V1 format (if available)
        v1_records = [r for r in original_records if isinstance(r, AuditRecordV1)]
        if v1_records:
            v1_store = {correlation_id: v1_records}
            v1_engine = ReplayEngine(v1_store, self.intent_store, self.approval_service)
            reports["pure_v1"] = v1_engine.replay_correlation(correlation_id)
        
        # Test 2: Pure CanonicalAuditEnvelope format (if available)
        canonical_records = [r for r in original_records if isinstance(r, CanonicalAuditEnvelope)]
        if canonical_records:
            canonical_store = {correlation_id: canonical_records}
            canonical_engine = ReplayEngine(canonical_store, self.intent_store, self.approval_service)
            reports["pure_canonical"] = canonical_engine.replay_correlation(correlation_id)
        
        # Test 3: Mixed format (original mixed records)
        mixed_store = {correlation_id: original_records}
        mixed_engine = ReplayEngine(mixed_store, self.intent_store, self.approval_service)
        reports["mixed_format"] = mixed_engine.replay_correlation(correlation_id)
        
        # Test 4: Deterministic format mixing (if requested)
        if test_format_mixing and len(original_records) > 1:
            # Use deterministic ordering instead of random shuffle
            mixed_records = original_records.copy()
            # Simple deterministic shuffle: reverse order for testing
            mixed_records.reverse()
            mixed_store = {correlation_id: mixed_records}
            mixed_engine = ReplayEngine(mixed_store, self.intent_store, self.approval_service)
            reports["deterministic_mixed"] = mixed_engine.replay_correlation(correlation_id)
        
        return reports
    
    def verify_dual_format_equivalence(self, reports: Dict[str, ReplayReport]) -> List[str]:
        """
        Verify that all dual-format replay reports produce identical results
        
        Args:
            reports: Dictionary of replay reports from different format scenarios
            
        Returns:
            List of equivalence issues found
        """
        issues = []
        
        if len(reports) < 2:
            issues.append("Insufficient reports for equivalence verification")
            return issues
        
        # Get the first successful report as baseline
        baseline_report = None
        for report in reports.values():
            if report.result == ReplayResult.SUCCESS:
                baseline_report = report
                break
        
        if not baseline_report:
            issues.append("No successful replay report found for baseline")
            return issues
        
        # Compare all reports against baseline
        for scenario, report in reports.items():
            if report.result != ReplayResult.SUCCESS:
                issues.append(f"Replay failed for scenario {scenario}: {report.result}")
                continue
            
            # Compare key metrics
            if report.total_events != baseline_report.total_events:
                issues.append(f"Event count mismatch in {scenario}: {report.total_events} vs {baseline_report.total_events}")
            
            if report.processed_events != baseline_report.processed_events:
                issues.append(f"Processed events mismatch in {scenario}: {report.processed_events} vs {baseline_report.processed_events}")
            
            # Compare reconstructed state
            if report.reconstructed_intents != baseline_report.reconstructed_intents:
                issues.append(f"Reconstructed intents mismatch in {scenario}")
            
            if report.reconstructed_decisions != baseline_report.reconstructed_decisions:
                issues.append(f"Reconstructed decisions mismatch in {scenario}")
            
            if report.safety_gate_verdicts != baseline_report.safety_gate_verdicts:
                issues.append(f"Safety gate verdicts mismatch in {scenario}")
        
        return issues
    
    def _extract_payload_ref(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        kind = payload.get("kind")
        if kind == "inline":
            ref = payload.get("ref", {})
            if isinstance(ref, dict):
                return ref
            if isinstance(ref, str):
                try:
                    parsed = json.loads(ref)
                except json.JSONDecodeError:
                    return {}
                return parsed if isinstance(parsed, dict) else {}
            return {}

        legacy_kind = payload.get("kind", {})
        if isinstance(legacy_kind, dict):
            ref = legacy_kind.get("ref", {})
            return ref if isinstance(ref, dict) else {}

        ref = payload.get("ref", {})
        return ref if isinstance(ref, dict) else {}

    def _process_envelope(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process individual envelope based on event type"""
        event_type = envelope.event_type
        
        if event_type == "telemetry_ingested":
            self._process_telemetry_ingested(envelope, report)
        elif event_type == "belief_creation_started":
            self._process_belief_creation_started(envelope, report)
        elif event_type == "belief_created":
            self._process_belief_created(envelope, report)
        elif event_type == "intent_created":
            self._process_intent_created(envelope, report)
        elif event_type == "safety_gate_evaluated":
            self._process_safety_gate_evaluated(envelope, report)
        elif event_type == "approval_requested":
            self._process_approval_requested(envelope, report)
        elif event_type == "approval_bound_to_intent":
            self._process_approval_bound_to_intent(envelope, report)
        elif event_type == "approval_denied":
            self._process_approval_denied(envelope, report)
        elif event_type == "intent_executed":
            self._process_intent_executed(envelope, report)
        elif event_type == "intent_denied":
            self._process_intent_denied(envelope, report)
        else:
            report.add_warning(f"Unknown event type: {event_type}")

    def _process_telemetry_ingested(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process telemetry ingestion event"""
        # Reconstruct telemetry event from payload
        try:
            telemetry_data = self._extract_payload_ref(envelope.payload)
            if not telemetry_data:
                report.add_failure("Telemetry payload missing reference data")
                return
            
            # Validate telemetry structure (basic checks)
            required_fields = ["event_id", "correlation_id", "trace_id"]
            for field in required_fields:
                if field not in telemetry_data:
                    report.add_failure(f"Telemetry missing required field: {field}")
                    return
            
            self.logger.debug(f"Reconstructed telemetry event: {telemetry_data.get('event_id')}")
            
        except Exception as e:
            report.add_failure(f"Failed to process telemetry ingestion: {e}")

    def _process_belief_creation_started(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process belief creation start event"""
        try:
            belief_data = self._extract_payload_ref(envelope.payload)
            if not belief_data:
                report.add_failure("Belief creation start payload missing data")
                return

            if "event_id" not in belief_data:
                report.add_failure("Belief creation start missing event_id")
                return

            self.logger.debug(f"Reconstructed belief creation start: {belief_data.get('event_id')}")

        except Exception as e:
            report.add_failure(f"Failed to process belief creation start: {e}")

    def _process_belief_created(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process belief creation event"""
        try:
            belief_data = self._extract_payload_ref(envelope.payload)
            if not belief_data:
                report.add_failure("Belief creation payload missing data")
                return

            belief_id = belief_data.get("belief_id")
            if not belief_id:
                report.add_failure("Belief creation missing belief_id")
                return

            self.logger.debug(f"Reconstructed belief creation: {belief_id}")

        except Exception as e:
            report.add_failure(f"Failed to process belief creation: {e}")

    def _process_intent_created(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process intent creation event"""
        try:
            intent_data = self._extract_payload_ref(envelope.payload)
            if not intent_data:
                report.add_failure("Intent creation payload missing data")
                return

            intent_id = intent_data.get("intent_id")
            if not intent_id:
                report.add_failure("Intent creation missing intent_id")
                return

            self.logger.debug(f"Reconstructed intent creation: {intent_id}")

        except Exception as e:
            report.add_failure(f"Failed to process intent creation: {e}")

    def _process_safety_gate_evaluated(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process safety gate evaluation event"""
        try:
            verdict_data = self._extract_payload_ref(envelope.payload)
            if not verdict_data:
                report.add_failure("Safety gate payload missing verdict data")
                return
            
            verdict = verdict_data.get("verdict")
            rationale = verdict_data.get("rationale")
            
            if not verdict:
                report.add_failure("Safety gate verdict missing")
                return
            
            # Store verdict for verification
            report.safety_gate_verdicts[envelope.event_id] = verdict
            
            self.logger.debug(f"Reconstructed safety verdict: {verdict} - {rationale}")
            
        except Exception as e:
            report.add_failure(f"Failed to process safety gate evaluation: {e}")

    def _process_approval_requested(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process approval request event"""
        try:
            approval_data = self._extract_payload_ref(envelope.payload)
            if not approval_data:
                report.add_failure("Approval request payload missing data")
                return
            
            approval_id = approval_data.get("approval_id")
            if not approval_id:
                report.add_failure("Approval request missing approval_id")
                return
            
            self.logger.debug(f"Reconstructed approval request: {approval_id}")
            
        except Exception as e:
            report.add_failure(f"Failed to process approval request: {e}")

    def _process_approval_denied(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process approval denial event"""
        try:
            approval_data = self._extract_payload_ref(envelope.payload)
            if not approval_data:
                report.add_failure("Approval denial payload missing data")
                return

            approval_id = approval_data.get("approval_id")
            if not approval_id:
                report.add_failure("Approval denial missing approval_id")
                return

            self.logger.debug(f"Reconstructed approval denial: {approval_id}")

        except Exception as e:
            report.add_failure(f"Failed to process approval denial: {e}")

    def _process_approval_bound_to_intent(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process approval-intent binding event"""
        try:
            binding_data = self._extract_payload_ref(envelope.payload)
            if not binding_data:
                report.add_failure("Intent binding payload missing data")
                return
            
            # Reconstruct intent hash from binding
            intent_hash = binding_data.get("intent_hash")
            approval_id = binding_data.get("approval_id")
            
            if not intent_hash or not approval_id:
                report.add_failure("Intent binding missing hash or approval_id")
                return
            
            # Verify intent exists in store if available
            if self.intent_store:
                try:
                    stored_intent = self.intent_store.get_intent_by_approval_id(approval_id)
                    if stored_intent:
                        computed_hash = self.intent_store.compute_intent_hash(stored_intent)
                        if computed_hash != intent_hash:
                            report.add_failure(f"Intent hash mismatch: expected {intent_hash}, got {computed_hash}")
                            report.intent_hash_verified = False
                        else:
                            report.reconstructed_intents[approval_id] = stored_intent
                except Exception as e:
                    report.add_warning(f"Could not verify intent binding: {e}")
            
            self.logger.debug(f"Reconstructed intent binding: {approval_id} -> {intent_hash[:8]}...")
            
        except Exception as e:
            report.add_failure(f"Failed to process intent binding: {e}")
    
    def _process_intent_executed(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process intent execution event"""
        try:
            execution_data = self._extract_payload_ref(envelope.payload)
            if not execution_data:
                report.add_failure("Intent execution payload missing data")
                return
            
            intent_data = execution_data.get("intent", execution_data)
            if not intent_data:
                report.add_failure("Intent execution missing intent data")
                return
            
            # Reconstruct intent for verification
            try:
                reconstructed_intent = ExecutionIntentV1(**intent_data)
                report.reconstructed_intents[envelope.event_id] = reconstructed_intent
                
                # Verify intent hash if we have the original
                if self.intent_store:
                    approval_id = intent_data.get("safety_context", {}).get("human_approval_id")
                    if approval_id:
                        stored_intent = self.intent_store.get_intent_by_approval_id(approval_id)
                        if stored_intent:
                            stored_hash = self.intent_store.compute_intent_hash(stored_intent)
                            reconstructed_hash = self.intent_store.compute_intent_hash(reconstructed_intent)
                            if stored_hash != reconstructed_hash:
                                report.add_failure(f"Executed intent hash differs from stored intent")
                                report.intent_hash_verified = False
                
            except Exception as e:
                report.add_failure(f"Failed to reconstruct executed intent: {e}")
            
            self.logger.debug(f"Reconstructed intent execution: {intent_data.get('intent_id')}")
            
        except Exception as e:
            report.add_failure(f"Failed to process intent execution: {e}")
    
    def _process_intent_denied(self, envelope: CanonicalEvent, report: ReplayReport):
        """Process intent denial event"""
        try:
            denial_data = self._extract_payload_ref(envelope.payload)
            if not denial_data:
                report.add_failure("Intent denial payload missing data")
                return
            
            verdict = denial_data.get("verdict")
            rationale = denial_data.get("rationale")
            
            self.logger.debug(f"Reconstructed intent denial: {verdict} - {rationale}")
            
        except Exception as e:
            report.add_failure(f"Failed to process intent denial: {e}")
    
    def _verify_final_state(self, report: ReplayReport):
        """Verify final state consistency"""
        try:
            # Verify audit integrity
            report.audit_integrity_verified = len(report.failures) == 0
            
            # Verify safety gate consistency
            if report.safety_gate_verdicts:
                report.safety_gate_verified = True
                for event_id, verdict in report.safety_gate_verdicts.items():
                    if verdict not in ["allow", "deny", "require_human", "require_quorum"]:
                        report.add_warning(f"Unexpected safety verdict: {verdict}")
                        report.safety_gate_verified = False
            
            self.logger.info(f"Replay verification complete for {report.correlation_id}: "
                           f"Result={report.result.value}, Events={report.processed_events}/{report.total_events}")
            
        except Exception as e:
            report.add_failure(f"Final state verification failed: {e}")
    
    def replay_bundle_with_migration(self, bundle_dict: Dict[str, Any]) -> ReplayReport:
        """Replay execution proof bundle with automatic schema migration.
        
        Args:
            bundle_dict: Bundle dictionary to replay (may be older schema version)
            
        Returns:
            Replay report with migration information
            
        Raises:
            MigrationError: If bundle migration fails
        """
        report = ReplayReport(correlation_id=bundle_dict.get("bundle_id", "unknown"))
        
        try:
            # Detect schema version
            original_schema_version = SchemaMigrations.detect_schema_version(bundle_dict)
            report.add_info(f"Original schema version: {original_schema_version}")
            
            # Migrate bundle if needed
            migrated_bundle = SchemaMigrations.migrate_bundle(bundle_dict)
            current_schema_version = migrated_bundle.get("schema_version", "2.0")
            
            if original_schema_version != current_schema_version:
                report.add_info(f"Migrated from schema {original_schema_version} to {current_schema_version}")
            
            # Verify replay hash matches migrated bundle
            computed_hash = compute_replay_hash_with_migration(migrated_bundle)
            original_hash = migrated_bundle.get("replay_hash")
            
            if original_hash and computed_hash != original_hash:
                report.add_failure(f"Replay hash mismatch after migration: computed={computed_hash}, original={original_hash}")
                report.result = ReplayResult.HASH_MISMATCH
            else:
                report.add_info("Replay hash verification passed")
            
            # Extract correlation ID for replay
            intent_data = migrated_bundle.get("intent", {})
            correlation_id = intent_data.get("intent_id", migrated_bundle.get("bundle_id", "unknown"))
            
            # Perform standard replay
            if correlation_id in self.audit_store:
                return self.replay_correlation(correlation_id)
            else:
                report.add_warning(f"No audit records found for migrated bundle correlation_id: {correlation_id}")
                report.result = ReplayResult.NO_AUDIT_RECORDS
            
        except MigrationError as e:
            report.add_failure(f"Bundle migration failed: {e.message} (from {e.from_version} to {e.to_version})")
            report.result = ReplayResult.MIGRATION_FAILED
        except Exception as e:
            report.add_failure(f"Bundle replay failed: {e}")
            report.result = ReplayResult.REPLAY_FAILED
        
        return report
    
    def detect_bundle_schema_version(self, bundle_dict: Dict[str, Any]) -> str:
        """Detect schema version of bundle dictionary.
        
        Args:
            bundle_dict: Bundle dictionary to analyze
            
        Returns:
            Detected schema version
        """
        return SchemaMigrations.detect_schema_version(bundle_dict)
    
    def validate_bundle_schema(self, bundle_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bundle schema compliance.
        
        Args:
            bundle_dict: Bundle dictionary to validate
            
        Returns:
            Validation report
        """
        return SchemaMigrations.validate_schema_compliance(bundle_dict)


class ReplayEngineError(Exception):
    """Raised when replay engine operations fail"""
    pass
