"""
Replay Engine for deterministic audit replay
Reconstructs and verifies organism behavior from audit logs
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .event_envelope import AuditEventEnvelope, EnvelopeValidationError
from .canonical_utils import canonical_json, stable_hash, verify_canonical_hash

# Import system components for reconstruction
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
from models_v1 import TelemetryEventV1, LocalDecisionV1, BeliefV1, ExecutionIntentV1, AuditRecordV1

logger = logging.getLogger(__name__)


class ReplayResult(Enum):
    """Replay outcome status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class ReplayReport:
    """Comprehensive replay execution report"""
    
    correlation_id: str
    replay_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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


class ReplayEngine:
    """Deterministic audit replay engine"""
    
    def __init__(self, 
                 audit_store: Dict[str, List[AuditRecordV1]],
                 intent_store: Optional['IntentStore'] = None,
                 approval_service: Optional['ApprovalService'] = None):
        """
        Initialize replay engine
        
        Args:
            audit_store: Audit record storage by correlation_id
            intent_store: Intent store for verification
            approval_service: Approval service for verification
        """
        self.audit_store = audit_store
        self.intent_store = intent_store
        self.approval_service = approval_service
        self.logger = logging.getLogger(__name__)
    
    def replay_correlation(self, correlation_id: str) -> ReplayReport:
        """
        Replay all events for a correlation ID deterministically
        
        Args:
            correlation_id: Correlation ID to replay
            
        Returns:
            Comprehensive replay report
        """
        report = ReplayReport(correlation_id=correlation_id)
        
        try:
            # Step 1: Retrieve and validate audit events
            audit_records = self.audit_store.get(correlation_id, [])
            if not audit_records:
                report.add_failure(f"No audit records found for correlation_id: {correlation_id}")
                return report
            
            # Step 2: Convert to envelopes and sort deterministically
            envelopes = self._create_envelopes(audit_records, report)
            if not envelopes:
                report.add_failure("No valid envelopes created from audit records")
                return report
            
            # Step 3: Sort by deterministic ordering
            envelopes.sort(key=lambda e: e.ordering_key)
            report.total_events = len(envelopes)
            
            # Step 4: Process events in order
            for envelope in envelopes:
                try:
                    self._process_envelope(envelope, report)
                    report.processed_events += 1
                except Exception as e:
                    report.add_failure(f"Failed to process envelope {envelope.event_id}: {e}")
            
            # Step 5: Verify final state integrity
            self._verify_final_state(report)
            
        except Exception as e:
            report.add_failure(f"Replay failed with unexpected error: {e}")
            self.logger.error(f"Replay failed for {correlation_id}: {e}")
        
        return report
    
    def _create_envelopes(self, 
                         audit_records: List[AuditRecordV1], 
                         report: ReplayReport) -> List[AuditEventEnvelope]:
        """Convert audit records to envelopes with validation"""
        envelopes = []
        
        for i, record in enumerate(audit_records):
            try:
                envelope = AuditEventEnvelope.from_audit_record(record, sequence_number=i)
                
                # Verify payload integrity
                if not envelope.verify_payload_integrity():
                    report.add_failure(f"Payload integrity check failed for event {record.event_id}")
                    continue
                
                envelopes.append(envelope)
                
            except Exception as e:
                report.add_failure(f"Failed to create envelope for record {record.event_id}: {e}")
        
        return envelopes
    
    def _process_envelope(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process individual envelope based on event type"""
        event_type = envelope.event_type
        
        if event_type == "telemetry_ingested":
            self._process_telemetry_ingested(envelope, report)
        elif event_type == "safety_gate_evaluated":
            self._process_safety_gate_evaluated(envelope, report)
        elif event_type == "approval_requested":
            self._process_approval_requested(envelope, report)
        elif event_type == "approval_bound_to_intent":
            self._process_approval_bound_to_intent(envelope, report)
        elif event_type == "intent_executed":
            self._process_intent_executed(envelope, report)
        elif event_type == "intent_denied":
            self._process_intent_denied(envelope, report)
        else:
            report.add_warning(f"Unknown event type: {event_type}")
    
    def _process_telemetry_ingested(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process telemetry ingestion event"""
        # Reconstruct telemetry event from payload
        try:
            telemetry_data = envelope.payload.get("kind", {}).get("ref", {})
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
    
    def _process_safety_gate_evaluated(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process safety gate evaluation event"""
        try:
            verdict_data = envelope.payload.get("kind", {}).get("ref", {})
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
    
    def _process_approval_requested(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process approval request event"""
        try:
            approval_data = envelope.payload.get("kind", {}).get("ref", {})
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
    
    def _process_approval_bound_to_intent(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process approval-intent binding event"""
        try:
            binding_data = envelope.payload.get("kind", {}).get("ref", {})
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
    
    def _process_intent_executed(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process intent execution event"""
        try:
            execution_data = envelope.payload.get("kind", {}).get("ref", {})
            if not execution_data:
                report.add_failure("Intent execution payload missing data")
                return
            
            intent_data = execution_data.get("intent")
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
    
    def _process_intent_denied(self, envelope: AuditEventEnvelope, report: ReplayReport):
        """Process intent denial event"""
        try:
            denial_data = envelope.payload.get("kind", {}).get("ref", {})
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


class ReplayEngineError(Exception):
    """Raised when replay engine operations fail"""
    pass
