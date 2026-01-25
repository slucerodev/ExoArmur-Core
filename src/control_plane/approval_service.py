"""
ExoArmur ADMO V2 Approval Service
Human operator approval workflows - Phase 1 scaffolding only
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ApprovalConfig:
    """Approval service configuration"""
    enabled: bool = False
    approval_timeout_seconds: int = 3600
    dual_approval_required: bool = True
    business_hours_only: bool = False


@dataclass
class ApprovalRequest:
    """Approval request data structure"""
    approval_id: str
    correlation_id: str
    trace_id: str
    tenant_id: str
    cell_id: str
    idempotency_key: str
    requested_action_class: str
    payload_ref: Dict[str, Any]
    created_at: datetime
    status: Literal["PENDING", "APPROVED", "DENIED", "EXPIRED"] = "PENDING"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    denied_at: Optional[datetime] = None
    denial_reason: Optional[str] = None
    bound_intent_id: Optional[str] = None
    bound_idempotency_key: Optional[str] = None
    bound_intent_hash: Optional[str] = None


class ApprovalService:
    """Human operator approval service - Minimum viable implementation"""
    
    def __init__(self, config: Optional[ApprovalConfig] = None):
        self.config = config or ApprovalConfig()
        self._initialized = False
        self._approvals: Dict[str, ApprovalRequest] = {}
        
        if self.config.enabled:
            logger.warning("ApprovalService: enabled=True not yet implemented (Phase 2)")
        else:
            logger.info("ApprovalService initialized (minimum viable implementation)")
    
    def create_request(
        self,
        correlation_id: str,
        trace_id: str,
        tenant_id: str,
        cell_id: str,
        idempotency_key: str,
        requested_action_class: str,
        payload_ref: Dict[str, Any]
    ) -> str:
        """Create approval request and return approval_id"""
        approval_id = f"apr-{uuid.uuid4().hex[:12]}"
        
        approval = ApprovalRequest(
            approval_id=approval_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=idempotency_key,
            requested_action_class=requested_action_class,
            payload_ref=payload_ref,
            created_at=datetime.now(timezone.utc),
            status="PENDING"
        )
        
        self._approvals[approval_id] = approval
        logger.info(f"Created approval request {approval_id} for action {requested_action_class}")
        
        return approval_id
    
    def get_status(self, approval_id: str) -> Literal["PENDING", "APPROVED", "DENIED", "EXPIRED"]:
        """Get approval status"""
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        return approval.status
    
    def approve(self, approval_id: str, operator_id: str) -> Literal["PENDING", "APPROVED", "DENIED", "EXPIRED"]:
        """Approve a request"""
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "PENDING":
            return approval.status
        
        approval.status = "APPROVED"
        approval.approved_by = operator_id
        approval.approved_at = datetime.now(timezone.utc)
        
        logger.info(f"Approved request {approval_id} by operator {operator_id}")
        return "APPROVED"
    
    def deny(self, approval_id: str, operator_id: str, reason: str) -> Literal["PENDING", "APPROVED", "DENIED", "EXPIRED"]:
        """Deny a request"""
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "PENDING":
            return approval.status
        
        approval.status = "DENIED"
        approval.approved_by = operator_id
        approval.denied_at = datetime.now(timezone.utc)
        approval.denial_reason = reason
        
        logger.info(f"Denied request {approval_id} by operator {operator_id}: {reason}")
        return "DENIED"
    
    def get_approval_details(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get full approval details"""
        return self._approvals.get(approval_id)
    
    def bind_intent(self, approval_id: str, intent_id: str, idempotency_key: str, intent_hash: str) -> None:
        """Bind approval to a specific frozen intent"""
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        # Check if already bound
        if approval.bound_intent_id is not None:
            # Allow idempotent re-binding if same values
            if (approval.bound_intent_id == intent_id and 
                approval.bound_idempotency_key == idempotency_key and 
                approval.bound_intent_hash == intent_hash):
                logger.debug(f"Intent already bound to approval {approval_id} (idempotent)")
                return
            else:
                raise ValueError(f"Approval {approval_id} already bound to different intent")
        
        # Bind the intent
        approval.bound_intent_id = intent_id
        approval.bound_idempotency_key = idempotency_key
        approval.bound_intent_hash = intent_hash
        
        logger.info(f"Bound intent {intent_id} to approval {approval_id}")
    
    def get_bound_intent_hash(self, approval_id: str) -> Optional[str]:
        """Get the bound intent hash for an approval"""
        approval = self._approvals.get(approval_id)
        return approval.bound_intent_hash if approval else None
    
    # Legacy methods for compatibility (no-op)
    async def initialize(self) -> None:
        """Initialize approval service"""
        if not self.config.enabled:
            return  # No-op when disabled
        
        # Check V2 feature flags
        from feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        if not feature_flags.is_v2_operator_approval_required():
            raise NotImplementedError("V2 operator approval not yet implemented (Phase 2)")
        
        # V2 implementation would go here
        self._initialized = True
    
    async def submit_approval_request(self, request_data: Dict[str, Any]) -> str:
        """Submit approval request"""
        if not self.config.enabled:
            return f"legacy-{uuid.uuid4().hex[:8]}"
        
        # Check V2 feature flags
        from feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        if not feature_flags.is_v2_operator_approval_required():
            raise NotImplementedError("V2 operator approval not yet implemented (Phase 2)")
        
        # V2 implementation would go here
        return f"v2-{uuid.uuid4().hex[:8]}"
    
    async def get_approval_status(self, request_id: str) -> Dict[str, Any]:
        """Get approval request status (legacy - no-op)"""
        return {
            "request_id": request_id,
            "status": "legacy",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approval_required": False
        }
    
    async def approve_request(self, request_id: str, operator_id: str, reason: str) -> bool:
        """Approve a request (legacy - no-op)"""
        return True
    
    async def deny_request(self, request_id: str, operator_id: str, reason: str) -> bool:
        """Deny a request (legacy - no-op)"""
        return True
    
    async def get_pending_approvals(self, operator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending approvals"""
        if not self.config.enabled:
            return []
        
        # Check V2 feature flags
        from feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        if not feature_flags.is_v2_operator_approval_required():
            raise NotImplementedError("V2 operator approval not yet implemented (Phase 2)")
        
        # V2 implementation would go here
        return []
    
    async def check_authorization(self, operator_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check operator authorization for request"""
        if not self.config.enabled:
            return {
                "authorized": False,
                "reason": "V2 approval service disabled"
            }
        
        # Check V2 feature flags
        from feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        if not feature_flags.is_v2_operator_approval_required():
            raise NotImplementedError("V2 operator approval not yet implemented (Phase 2)")
        
        # V2 implementation would go here
        return {
            "authorized": True,
            "operator_id": operator_id,
            "clearance_level": "admin"
        }
    
    async def request_emergency_override(self, emergency_data: Dict[str, Any]) -> str:
        """Request emergency override"""
        if not self.config.enabled:
            return f"legacy-emergency-{uuid.uuid4().hex[:8]}"
        
        # Check V2 feature flags
        from feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
        if not feature_flags.is_v2_operator_approval_required():
            raise NotImplementedError("V2 operator approval not yet implemented (Phase 2)")
        
        # V2 implementation would go here
        return f"v2-emergency-{uuid.uuid4().hex[:8]}"
    
    def is_approval_required(self, request_type: str, risk_score: float) -> bool:
        """Check if approval is required for request (legacy - no-op)"""
        return False

    async def shutdown(self) -> None:
        """Shutdown approval service (no-op)"""
        pass
