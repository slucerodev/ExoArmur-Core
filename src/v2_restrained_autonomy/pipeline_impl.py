"""
ExoArmur ADMO V2 Restrained Autonomy Pipeline
Minimal belief->policy->action pipeline with operator approval
"""

import logging
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid

from federation.clock import Clock, FixedClock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_flags.feature_flags import get_feature_flags, FeatureFlagContext
from control_plane.approval_service import ApprovalService, ApprovalRequest
from audit.audit_logger import AuditLogger
try:
    from spec.contracts.models_v1 import (
        TelemetryEventV1, BeliefV1 as BeliefV1Original, ExecutionIntentV1, AuditRecordV1
    )
    BeliefV1 = BeliefV1Original  # Use the first BeliefV1 definition
except ImportError:
    # Fallback for running without package installation
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
    from models_v1 import (
        TelemetryEventV1, BeliefV1 as BeliefV1Original, ExecutionIntentV1, AuditRecordV1
    )
    BeliefV1 = BeliefV1Original  # Use the first BeliefV1 definition
from .mock_executor import MockActionExecutor

logger = logging.getLogger(__name__)


@dataclass
class RestrainedAutonomyConfig:
    """Configuration for restrained autonomy pipeline"""
    enabled: bool = False
    require_approval_for_A3: bool = True
    approval_timeout_seconds: int = 3600
    max_belief_ttl_seconds: int = 86400
    deterministic_seed: Optional[str] = None


@dataclass
class ActionOutcome:
    """Result of an action execution attempt"""
    action_taken: bool
    refusal_reason: Optional[str]
    execution_id: Optional[str]
    approval_id: Optional[str]
    audit_stream_id: str
    timestamp: datetime


class RestrainedAutonomyPipeline:
    """Minimal restrained autonomy pipeline for V2"""
    
    def __init__(
        self,
        config: Optional[RestrainedAutonomyConfig] = None,
        approval_service: Optional[ApprovalService] = None,
        audit_logger: Optional[AuditLogger] = None,
        action_executor: Optional['MockActionExecutor'] = None,
        clock: Optional[Clock] = None
    ):
        self.config = config or RestrainedAutonomyConfig()
        self.approval_service = approval_service or ApprovalService()
        self.audit_logger = audit_logger or AuditLogger()
        self.action_executor = action_executor or MockActionExecutor()
        self.clock = clock or FixedClock()
        self.feature_flags = get_feature_flags()
        
        self._pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
        logger.info(f"RestrainedAutonomyPipeline initialized: {self._pipeline_id}")
    
    def is_enabled(self, context: Optional[FeatureFlagContext] = None) -> bool:
        """Check if V2 restrained autonomy is enabled"""
        return (
            self.feature_flags.is_v2_control_plane_enabled(context) and
            self.feature_flags.is_v2_operator_approval_required(context) and
            self.config.enabled
        )
    
    def create_deterministic_id(self, seed_data: Dict[str, Any]) -> str:
        """Create deterministic ID from seed data"""
        if self.config.deterministic_seed:
            seed_data["pipeline_seed"] = self.config.deterministic_seed
        
        seed_string = json.dumps(seed_data, sort_keys=True, separators=(',', ':'))
        hash_digest = hashlib.sha256(seed_string.encode()).hexdigest()
        
        # Create a ULID-like ID from hash (26 chars, Crockford's base32)
        import ulid
        # Use hash to seed deterministic ULID generation
        hash_int = int(hash_digest[:16], 16)
        
        # Create proper 16-byte ULID from hash
        ulid_bytes = hash_int.to_bytes(16, 'big')[:16]  # Ensure exactly 16 bytes
        if len(ulid_bytes) < 16:
            ulid_bytes = ulid_bytes + b'\x00' * (16 - len(ulid_bytes))
        
        return f"det-{str(ulid.ULID.from_bytes(ulid_bytes))}"
    
    def create_deterministic_ulid(self, seed_data: Dict[str, Any]) -> str:
        """Create deterministic ULID from seed data (for ExecutionIntentV1)"""
        if self.config.deterministic_seed:
            seed_data["pipeline_seed"] = self.config.deterministic_seed
        
        seed_string = json.dumps(seed_data, sort_keys=True, separators=(',', ':'))
        hash_digest = hashlib.sha256(seed_string.encode()).hexdigest()
        
        # Create a ULID-like ID from hash (26 chars, Crockford's base32)
        import ulid
        # Use hash to seed deterministic ULID generation
        hash_int = int(hash_digest[:16], 16)
        
        # Create proper 16-byte ULID from hash
        ulid_bytes = hash_int.to_bytes(16, 'big')[:16]  # Ensure exactly 16 bytes
        if len(ulid_bytes) < 16:
            ulid_bytes = ulid_bytes + b'\x00' * (16 - len(ulid_bytes))
        
        return str(ulid.ULID.from_bytes(ulid_bytes))
    
    def emit_audit_event(
        self,
        correlation_id: str,
        trace_id: str,
        tenant_id: str,
        cell_id: str,
        event_kind: str,
        payload_ref: Dict[str, Any],
        audit_stream_id: str = None
    ) -> str:
        """Emit structured audit event"""
        audit_id = self.create_deterministic_id({
            "correlation_id": correlation_id,
            "event_kind": event_kind,
            "timestamp": self.clock.now().isoformat(),
            "pipeline_id": self._pipeline_id
        })
        
        # Use provided audit_stream_id or generate one for storage
        storage_correlation_id = audit_stream_id or correlation_id
        
        audit_record = self.audit_logger.record_audit(
            event_kind=event_kind,
            payload_ref={"kind": "inline", "ref": json.dumps(payload_ref)},
            correlation_id=storage_correlation_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=f"{correlation_id}-{event_kind}"
        )
        
        return audit_record.audit_id
    
    def create_belief_from_event(self, event: TelemetryEventV1) -> BeliefV1:
        """Create a belief from telemetry event"""
        belief_id = self.create_deterministic_id({
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "claim_type": "suspicious_endpoint_activity"
        })
        
        return BeliefV1(
            schema_version="2.0.0",
            belief_id=belief_id,
            belief_type="suspicious_endpoint_activity",
            confidence=0.8,
            source_observations=[event.event_id],
            derived_at=self.clock.now(),
            correlation_id=event.correlation_id,
            evidence_summary=f"Suspicious activity detected from endpoint {event.attributes.get('endpoint_id', 'unknown')}",
            metadata={
                "tenant_id": event.tenant_id,
                "emitter_node_id": event.cell_id,
                "subject": {
                    "subject_type": "endpoint",
                    "subject_id": event.attributes.get("endpoint_id", "unknown")
                },
                "claim_type": "suspicious_endpoint_activity",
                "severity": "high",
                "evidence_refs": {
                    "event_ids": [event.event_id],
                    "feature_hashes": [hashlib.sha256(str(event.attributes).encode()).hexdigest()[:16]]
                },
                "policy_context": {
                    "bundle_hash_sha256": "demo_bundle_v1",
                    "rule_ids": ["rule_suspicious_activity"],
                    "trust_score_at_emit": 0.9
                },
                "ttl_seconds": 3600,
                "first_seen": self.clock.now().isoformat(),
                "last_seen": self.clock.now().isoformat(),
                "trace_id": event.trace_id
            }
        )
    
    def create_execution_intent(
        self,
        belief: BeliefV1,
        action_type: str = "isolate_endpoint",
        action_class: Literal["A0_observe", "A1_soft_containment", "A2_hard_containment", "A3_irreversible"] = "A2_hard_containment"
    ) -> ExecutionIntentV1:
        """Create execution intent from belief"""
        intent_id = self.create_deterministic_ulid({
            "belief_id": belief.belief_id,
            "action_type": action_type,
            "correlation_id": belief.correlation_id
        })
        
        return ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id=intent_id,
            tenant_id=belief.metadata.get("tenant_id"),
            cell_id=belief.metadata.get("emitter_node_id"),
            idempotency_key=f"{belief.correlation_id}-{action_type}",
            subject=belief.metadata.get("subject"),
            intent_type=action_type,
            action_class=action_class,
            requested_at=self.clock.now(),
            ttl_seconds=3600,
            parameters={"endpoint_id": belief.metadata.get("subject", {}).get("subject_id", "unknown")},
            policy_context=belief.metadata.get("policy_context"),
            safety_context={
                "safety_verdict": "require_approval",
                "rationale": "A2 action requires operator approval in V2",
                "quorum_status": "pending",
                "human_approval_id": None
            },
            correlation_id=belief.correlation_id,
            trace_id=belief.metadata.get("trace_id")
        )
    
    async def process_event_to_action(
        self,
        event: TelemetryEventV1,
        operator_decision: Optional[Literal["approve", "deny"]] = None,
        operator_id: Optional[str] = None
    ) -> ActionOutcome:
        """Process event through belief->policy->action pipeline"""
        correlation_id = event.correlation_id
        trace_id = event.trace_id
        tenant_id = event.tenant_id
        cell_id = event.cell_id
        
        # Generate audit stream ID for this processing
        audit_stream_id = self.create_deterministic_id({
            "correlation_id": correlation_id,
            "pipeline_id": self._pipeline_id,
            "session_start": self.clock.now().isoformat()
        })
        
        # Check if pipeline is enabled
        if not self.is_enabled():
            refusal_reason = "V2 restrained autonomy pipeline is disabled"
            self.emit_audit_event(
                correlation_id, trace_id, tenant_id, cell_id,
                "pipeline_disabled", {"reason": refusal_reason}, audit_stream_id
            )
            return ActionOutcome(
                action_taken=False,
                refusal_reason=refusal_reason,
                execution_id=None,
                approval_id=None,
                audit_stream_id=audit_stream_id,
                timestamp=self.clock.now()
            )
        
        # Step 1: Create belief from event
        self.emit_audit_event(
            correlation_id, trace_id, tenant_id, cell_id,
            "belief_creation_started", {"event_id": event.event_id}, audit_stream_id
        )
        
        belief = self.create_belief_from_event(event)
        
        self.emit_audit_event(
            correlation_id, trace_id, tenant_id, cell_id,
            "belief_created", {
                "belief_id": belief.belief_id,
                "claim_type": belief.metadata.get("claim_type"),
                "confidence": belief.confidence
            }, audit_stream_id
        )
        
        # Step 2: Create execution intent
        intent = self.create_execution_intent(belief, "isolate_endpoint", "A2_hard_containment")
        
        self.emit_audit_event(
            correlation_id, trace_id, tenant_id, cell_id,
            "intent_created", {
                "intent_id": intent.intent_id,
                "intent_type": intent.intent_type,
                "action_class": intent.action_class
            }, audit_stream_id
        )
        
        # Step 3: Request operator approval
        approval_id = self.approval_service.create_request(
            correlation_id=correlation_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=intent.idempotency_key,
            requested_action_class=intent.action_class,
            payload_ref={
                "intent_id": intent.intent_id,
                "description": f"A2 containment action for endpoint {intent.subject['subject_id']}"
            }
        )
            
        # Bind intent to approval
        intent_hash = hashlib.sha256(json.dumps(intent.model_dump(), sort_keys=True).encode()).hexdigest()
        self.approval_service.bind_intent(
            approval_id, intent.intent_id, intent.idempotency_key, intent_hash
        )
            
        self.emit_audit_event(
            correlation_id, trace_id, tenant_id, cell_id,
            "approval_requested", {
                "approval_id": approval_id,
                "intent_id": intent.intent_id,
                "action_class": intent.action_class
            }, audit_stream_id
        )
            
        # Apply operator decision if provided
        if operator_decision is not None and operator_id is not None:
            if operator_decision == "approve":
                self.approval_service.approve(approval_id, operator_id)
                self.emit_audit_event(
                    correlation_id, trace_id, tenant_id, cell_id,
                    "approval_granted", {
                        "approval_id": approval_id,
                        "operator_id": operator_id
                    }, audit_stream_id
                )
            else:
                self.approval_service.deny(approval_id, operator_id, "Operator denied in demo")
                self.emit_audit_event(
                    correlation_id, trace_id, tenant_id, cell_id,
                    "approval_denied", {
                        "approval_id": approval_id,
                        "operator_id": operator_id,
                        "reason": "Operator denied in demo"
                    }, audit_stream_id
                )
                    
                return ActionOutcome(
                    action_taken=False,
                    refusal_reason="Operator approval denied",
                    execution_id=None,
                    approval_id=approval_id,
                    audit_stream_id=audit_stream_id,
                    timestamp=self.clock.now()
                )
        else:
            # No operator decision provided, refuse action
            return ActionOutcome(
                action_taken=False,
                refusal_reason="Operator approval required but not provided",
                execution_id=None,
                approval_id=approval_id,
                audit_stream_id=audit_stream_id,
                timestamp=self.clock.now()
            )
        
        # Step 4: Execute action (if approved)
        endpoint_id = intent.subject["subject_id"]
        
        # Check idempotency
        if self.action_executor.has_executed_recently(endpoint_id, correlation_id):
            refusal_reason = "Action already executed recently (idempotency check)"
            self.emit_audit_event(
                correlation_id, trace_id, tenant_id, cell_id,
                "action_refused_idempotent", {"endpoint_id": endpoint_id}, audit_stream_id
            )
            return ActionOutcome(
                action_taken=False,
                refusal_reason=refusal_reason,
                execution_id=None,
                approval_id=approval_id,
                audit_stream_id=audit_stream_id,
                timestamp=self.clock.now()
            )
        
        # Execute action
        execution_record = self.action_executor.execute_isolate_endpoint(endpoint_id, correlation_id, approval_id)
        
        self.emit_audit_event(
            correlation_id, trace_id, tenant_id, cell_id,
            "action_executed", {
                "execution_id": execution_record["execution_id"],
                "action_type": execution_record["action_type"],
                "endpoint_id": execution_record["endpoint_id"]
            }, audit_stream_id
        )
        
        return ActionOutcome(
            action_taken=True,
            refusal_reason=None,
            execution_id=execution_record["execution_id"],
            approval_id=approval_id,
            audit_stream_id=audit_stream_id,
            timestamp=self.clock.now()
        )
    
    def replay_audit_stream(self, audit_stream_id: str) -> Dict[str, Any]:
        """Replay audit stream to verify deterministic outcome"""
        # Get all audit records - try both correlation_id and audit_stream_id
        audit_records = self.audit_logger.get_audit_records(audit_stream_id)
        
        # If no records found, try to find by any field containing the stream ID
        if not audit_records:
            # Get all records from the audit logger and search for our stream ID
            all_records = []
            for correlation_id, records in self.audit_logger.audit_records.items():
                for record in records:
                    if audit_stream_id in str(record.audit_id) or audit_stream_id in correlation_id:
                        all_records.append(record)
            audit_records = all_records
        
        replay_timeline = []
        final_outcome = None
        
        for record in audit_records:
            replay_timeline.append({
                "timestamp": record.recorded_at.isoformat(),
                "event_kind": record.event_kind,
                "payload": json.loads(record.payload_ref["ref"])
            })
            
            if record.event_kind == "action_executed":
                final_outcome = "action_taken"
            elif record.event_kind in ["approval_denied", "action_refused_idempotent", "pipeline_disabled"]:
                final_outcome = record.event_kind
        
        return {
            "audit_stream_id": audit_stream_id,
            "replay_timeline": replay_timeline,
            "final_outcome": final_outcome,
            "total_events": len(audit_records),
            "deterministic_hash": self.create_deterministic_id({
                "stream_id": audit_stream_id,
                "timeline": replay_timeline
            })
        }
