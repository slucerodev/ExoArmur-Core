"""
Arbitration Service

Manages arbitration of conflicts with human approval requirements.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from spec.contracts.models_v1 import (
    ArbitrationV1,
    ArbitrationStatus,
    ArbitrationConflictType
)
from exoarmur.federation.arbitration_store import ArbitrationStore
from exoarmur.federation.audit import AuditService, AuditEventEnvelope, AuditEventType
from exoarmur.federation.clock import Clock
from exoarmur.federation.observation_store import ObservationStore

logger = logging.getLogger(__name__)


class ArbitrationService:
    """Service for managing arbitration of conflicts"""
    
    def __init__(
        self,
        arbitration_store: ArbitrationStore,
        audit_service: AuditService,
        clock: Clock,
        observation_store: Optional[ObservationStore] = None,
        feature_flag_enabled: bool = False
    ):
        self.arbitration_store = arbitration_store
        self.audit_service = audit_service
        self.clock = clock
        self.observation_store = observation_store
        self.feature_flag_enabled = feature_flag_enabled
    
    def create_arbitration(self, arbitration: ArbitrationV1) -> bool:
        """
        Create a new arbitration requiring human approval
        
        Args:
            arbitration: Arbitration object to create
            
        Returns:
            True if created successfully, False otherwise
        """
        if not self.feature_flag_enabled:
            logger.warning("Arbitration feature is disabled")
            return False
        
        # Store arbitration
        success = self.arbitration_store.store_arbitration(arbitration)
        if not success:
            return False
        
        # Create human approval request (A3 default)
        approval_id = self._create_approval_request(arbitration)
        arbitration.approval_id = approval_id
        
        # Update arbitration with approval ID
        self.arbitration_store.update_arbitration(arbitration)
        
        # Emit audit event
        self._emit_arbitration_created_event(arbitration)
        
        logger.info(f"Created arbitration {arbitration.arbitration_id} with approval {approval_id}")
        return True
    
    def propose_resolution(self, arbitration_id: str, resolution: Dict[str, Any]) -> bool:
        """
        Propose a resolution for an arbitration
        
        Args:
            arbitration_id: Arbitration identifier
            resolution: Proposed resolution
            
        Returns:
            True if proposal stored successfully, False otherwise
        """
        if not self.feature_flag_enabled:
            return False
        
        arbitration = self.arbitration_store.get_arbitration(arbitration_id)
        if not arbitration:
            logger.warning(f"Arbitration {arbitration_id} not found")
            return False
        
        if arbitration.status != ArbitrationStatus.OPEN:
            logger.warning(f"Arbitration {arbitration_id} is not open for resolution")
            return False
        
        # Store proposed resolution
        arbitration.proposed_resolution = resolution
        
        # Update arbitration
        success = self.arbitration_store.update_arbitration(arbitration)
        if not success:
            return False
        
        # Emit audit event
        self._emit_resolution_proposed_event(arbitration)
        
        logger.info(f"Proposed resolution for arbitration {arbitration_id}")
        return True
    
    def apply_resolution(self, arbitration_id: str, resolver_federate_id: str) -> bool:
        """
        Apply resolution after approval
        
        Args:
            arbitration_id: Arbitration identifier
            resolver_federate_id: Federate applying the resolution
            
        Returns:
            True if resolution applied successfully, False otherwise
        """
        if not self.feature_flag_enabled:
            return False
        
        arbitration = self.arbitration_store.get_arbitration(arbitration_id)
        if not arbitration:
            logger.warning(f"Arbitration {arbitration_id} not found")
            return False
        
        if arbitration.status != ArbitrationStatus.OPEN:
            logger.warning(f"Arbitration {arbitration_id} is not open")
            return False
        
        if not arbitration.proposed_resolution:
            logger.warning(f"Arbitration {arbitration_id} has no proposed resolution")
            return False
        
        # Check approval status (mock for now - would integrate with ApprovalService)
        if not self._check_approval_status(arbitration.approval_id):
            logger.warning(f"Arbitration {arbitration_id} approval not granted")
            return False
        
        # Apply resolution to beliefs
        success = self._apply_resolution_to_beliefs(arbitration)
        if not success:
            return False
        
        # Update arbitration status
        arbitration.status = ArbitrationStatus.RESOLVED
        arbitration.decision = arbitration.proposed_resolution
        arbitration.resolved_at_utc = self.clock.now()
        arbitration.resolver_federate_id = resolver_federate_id
        arbitration.resolution_applied_at_utc = self.clock.now()
        
        # Update arbitration
        self.arbitration_store.update_arbitration(arbitration)
        
        # Emit audit event
        self._emit_arbitration_resolved_event(arbitration)
        
        logger.info(f"Applied resolution for arbitration {arbitration_id}")
        return True
    
    def reject_arbitration(self, arbitration_id: str, resolver_federate_id: str, reason: str) -> bool:
        """
        Reject an arbitration
        
        Args:
            arbitration_id: Arbitration identifier
            resolver_federate_id: Federate rejecting the arbitration
            reason: Reason for rejection
            
        Returns:
            True if rejected successfully, False otherwise
        """
        if not self.feature_flag_enabled:
            return False
        
        arbitration = self.arbitration_store.get_arbitration(arbitration_id)
        if not arbitration:
            logger.warning(f"Arbitration {arbitration_id} not found")
            return False
        
        if arbitration.status != ArbitrationStatus.OPEN:
            logger.warning(f"Arbitration {arbitration_id} is not open")
            return False
        
        # Update arbitration status
        arbitration.status = ArbitrationStatus.REJECTED
        arbitration.resolved_at_utc = self.clock.now()
        arbitration.resolver_federate_id = resolver_federate_id
        arbitration.decision = {"rejected": True, "reason": reason}
        
        # Update arbitration
        self.arbitration_store.update_arbitration(arbitration)
        
        # Emit audit event
        self._emit_arbitration_rejected_event(arbitration)
        
        logger.info(f"Rejected arbitration {arbitration_id}: {reason}")
        return True
    
    def get_arbitration(self, arbitration_id: str) -> Optional[ArbitrationV1]:
        """Get arbitration by ID"""
        return self.arbitration_store.get_arbitration(arbitration_id)
    
    def list_arbitrations(
        self,
        status: Optional[ArbitrationStatus] = None,
        conflict_type: Optional[ArbitrationConflictType] = None,
        correlation_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ArbitrationV1]:
        """List arbitrations with optional filters"""
        arbitrations = self.arbitration_store.list_arbitrations(
            status=status,
            correlation_id=correlation_id,
            limit=limit
        )
        
        # Filter by conflict type if specified
        if conflict_type:
            arbitrations = [a for a in arbitrations if a.conflict_type == conflict_type]
        
        return arbitrations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get arbitration service statistics"""
        store_stats = self.arbitration_store.get_statistics()
        
        return {
            "feature_enabled": self.feature_flag_enabled,
            "store_statistics": store_stats,
            "pending_approvals": len(self.arbitration_store.get_open_arbitrations())
        }
    
    def _create_approval_request(self, arbitration: ArbitrationV1) -> str:
        """
        Create approval request for arbitration
        
        Args:
            arbitration: Arbitration requiring approval
            
        Returns:
            Approval request ID
        """
        # Mock approval request creation
        # In real implementation, this would integrate with ApprovalService
        approval_id = f"approval_{arbitration.arbitration_id}_{self.clock.now().strftime('%Y%m%d%H%M%S')}"
        
        # TODO: Integrate with ApprovalService
        # approval = self.approval_service.create_approval(
        #     request_type="A3",
        #     scope=f"arbitration:{arbitration.arbitration_id}",
        #     rationale=f"Human approval required for {arbitration.conflict_type.value} conflict",
        #     correlation_id=arbitration.correlation_id
        # )
        
        return approval_id
    
    def _check_approval_status(self, approval_id: str) -> bool:
        """
        Check if approval is granted
        
        Args:
            approval_id: Approval request ID
            
        Returns:
            True if approved, False otherwise
        """
        # Mock approval check
        # In real implementation, this would check with ApprovalService
        # approval = self.approval_service.get_approval(approval_id)
        # return approval.status == "approved"
        
        # For now, assume all approvals are granted for testing
        return True
    
    def _apply_resolution_to_beliefs(self, arbitration: ArbitrationV1) -> bool:
        """
        Apply resolution to related beliefs
        
        Args:
            arbitration: Arbitration with resolution to apply
            
        Returns:
            True if applied successfully, False otherwise
        """
        if not self.observation_store:
            logger.warning("No observation store available for belief updates")
            return False
        
        resolution = arbitration.proposed_resolution
        
        # Apply resolution based on conflict type
        if arbitration.conflict_type == ArbitrationConflictType.THREAT_CLASSIFICATION:
            return self._apply_threat_classification_resolution(arbitration, resolution)
        elif arbitration.conflict_type == ArbitrationConflictType.SYSTEM_HEALTH:
            return self._apply_system_health_resolution(arbitration, resolution)
        elif arbitration.conflict_type == ArbitrationConflictType.CONFIDENCE_DISPUTE:
            return self._apply_confidence_dispute_resolution(arbitration, resolution)
        else:
            logger.warning(f"Unknown conflict type: {arbitration.conflict_type}")
            return False
    
    def _apply_threat_classification_resolution(self, arbitration: ArbitrationV1, resolution: Dict[str, Any]) -> bool:
        """Apply threat classification resolution"""
        # Update beliefs with resolved threat type
        if "resolved_threat_type" in resolution:
            for claim in arbitration.claims:
                belief_id = claim.get("belief_id")
                if belief_id:
                    belief = self.observation_store.get_belief(belief_id)
                    if belief:
                        # Update belief metadata with resolution
                        belief.metadata["resolved_threat_type"] = resolution["resolved_threat_type"]
                        belief.metadata["arbitration_id"] = arbitration.arbitration_id
                        self.observation_store.store_belief(belief)
        
        return True
    
    def _apply_system_health_resolution(self, arbitration: ArbitrationV1, resolution: Dict[str, Any]) -> bool:
        """Apply system health resolution"""
        # Update beliefs with resolved health score
        if "resolved_health_score" in resolution:
            for claim in arbitration.claims:
                belief_id = claim.get("belief_id")
                if belief_id:
                    belief = self.observation_store.get_belief(belief_id)
                    if belief:
                        # Update belief metadata with resolution
                        belief.metadata["resolved_health_score"] = resolution["resolved_health_score"]
                        belief.metadata["arbitration_id"] = arbitration.arbitration_id
                        self.observation_store.store_belief(belief)
        
        return True
    
    def _apply_confidence_dispute_resolution(self, arbitration: ArbitrationV1, resolution: Dict[str, Any]) -> bool:
        """Apply confidence dispute resolution"""
        # Update beliefs with resolved confidence
        if "resolved_confidence" in resolution:
            for claim in arbitration.claims:
                belief_id = claim.get("belief_id")
                if belief_id:
                    belief = self.observation_store.get_belief(belief_id)
                    if belief:
                        # Update belief confidence with resolution
                        belief.confidence = resolution["resolved_confidence"]
                        belief.metadata["arbitration_id"] = arbitration.arbitration_id
                        self.observation_store.store_belief(belief)
        
        return True
    
    def _emit_arbitration_created_event(self, arbitration: ArbitrationV1):
        """Emit audit event for arbitration creation"""
        try:
            audit_event = AuditEventEnvelope(
                event_type=AuditEventType.ARBITRATION_CREATED,
                timestamp_utc=self.clock.now(),
                correlation_id=arbitration.correlation_id,
                source_federate_id="arbitration_service",
                event_data={
                    "arbitration_id": arbitration.arbitration_id,
                    "conflict_type": arbitration.conflict_type.value,
                    "subject_key": arbitration.subject_key,
                    "conflict_key": arbitration.conflict_key,
                    "approval_id": arbitration.approval_id,
                    "num_claims": len(arbitration.claims)
                }
            )
            
            self.audit_service.emit_audit_event(audit_event)
            
        except Exception as e:
            logger.error(f"Failed to emit arbitration created audit event: {e}")
    
    def _emit_resolution_proposed_event(self, arbitration: ArbitrationV1):
        """Emit audit event for resolution proposal"""
        try:
            audit_event = AuditEventEnvelope(
                event_type=AuditEventType.ARBITRATION_RESOLUTION_PROPOSED,
                timestamp_utc=self.clock.now(),
                correlation_id=arbitration.correlation_id,
                source_federate_id="arbitration_service",
                event_data={
                    "arbitration_id": arbitration.arbitration_id,
                    "resolution_type": arbitration.proposed_resolution.get("type", "unknown"),
                    "proposed_by": arbitration.proposed_resolution.get("proposed_by", "unknown")
                }
            )
            
            self.audit_service.emit_audit_event(audit_event)
            
        except Exception as e:
            logger.error(f"Failed to emit resolution proposed audit event: {e}")
    
    def _emit_arbitration_resolved_event(self, arbitration: ArbitrationV1):
        """Emit audit event for arbitration resolution"""
        try:
            audit_event = AuditEventEnvelope(
                event_type=AuditEventType.ARBITRATION_RESOLVED,
                timestamp_utc=self.clock.now(),
                correlation_id=arbitration.correlation_id,
                source_federate_id=arbitration.resolver_federate_id,
                event_data={
                    "arbitration_id": arbitration.arbitration_id,
                    "resolver_federate_id": arbitration.resolver_federate_id,
                    "resolution_applied_at": arbitration.resolution_applied_at_utc.isoformat().replace('+00:00', 'Z'),
                    "decision_summary": arbitration.decision.get("summary", "No summary")
                }
            )
            
            self.audit_service.emit_audit_event(audit_event)
            
        except Exception as e:
            logger.error(f"Failed to emit arbitration resolved audit event: {e}")
    
    def _emit_arbitration_rejected_event(self, arbitration: ArbitrationV1):
        """Emit audit event for arbitration rejection"""
        try:
            audit_event = AuditEventEnvelope(
                event_type=AuditEventType.ARBITRATION_REJECTED,
                timestamp_utc=self.clock.now(),
                correlation_id=arbitration.correlation_id,
                source_federate_id=arbitration.resolver_federate_id,
                event_data={
                    "arbitration_id": arbitration.arbitration_id,
                    "resolver_federate_id": arbitration.resolver_federate_id,
                    "rejection_reason": arbitration.decision.get("reason", "No reason provided")
                }
            )
            
            self.audit_service.emit_audit_event(audit_event)
            
        except Exception as e:
            logger.error(f"Failed to emit arbitration rejected audit event: {e}")
