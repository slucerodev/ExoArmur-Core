"""
ExoArmur ADMO V2 Approval Service
Human operator approval workflows
"""

import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timezone
from exoarmur.feature_flags import get_feature_flags
from exoarmur.clock import deterministic_timestamp

logger = logging.getLogger(__name__)


def _deterministic_approval_created_at(approval_id: str) -> datetime:
    digest = hashlib.sha256(approval_id.encode("utf-8")).digest()
    seconds = int.from_bytes(digest[:4], "big")
    microseconds = int.from_bytes(digest[4:7], "big") % 1_000_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=microseconds)


def _deterministic_approval_transition_at(approval_id: str, operator_id: str, status: str) -> datetime:
    digest = hashlib.sha256(f"{approval_id}:{operator_id}:{status}".encode("utf-8")).digest()
    seconds = int.from_bytes(digest[:4], "big")
    microseconds = int.from_bytes(digest[4:7], "big") % 1_000_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=microseconds)


def _deterministic_approval_id(
    correlation_id: str,
    trace_id: str,
    tenant_id: str,
    cell_id: str,
    idempotency_key: str,
    requested_action_class: str,
    payload_ref: Dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "cell_id": cell_id,
            "idempotency_key": idempotency_key,
            "requested_action_class": requested_action_class,
            "payload_ref": payload_ref,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"apr-{digest[:12]}"


def _deterministic_legacy_token(prefix: str, *seed_parts: Any) -> str:
    canonical = json.dumps(seed_parts, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:8]}"


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


# Risk thresholds for clearance levels
_RISK_CLEARANCE_MAP = {
    'supervisor': 0.7,   # can approve up to 0.7 risk
    'admin': 0.9,        # can approve up to 0.9 risk
    'superuser': 1.0,    # can approve anything
}


class ApprovalService:
    """Human operator approval service with authorization and emergency override"""
    
    def __init__(self, config: Optional[ApprovalConfig] = None):
        self.config = config or ApprovalConfig()
        self._initialized = False
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._operator_interface = None
        self._audit_log: List[Dict[str, Any]] = []
        
        if self.config.enabled:
            logger.info("ApprovalService: Phase 2 enabled")
        else:
            logger.info("ApprovalService initialized (minimum viable implementation)")
    
    def set_operator_interface(self, operator_interface) -> None:
        """Wire the operator interface for authorization checks"""
        self._operator_interface = operator_interface
    
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
        approval_id = _deterministic_approval_id(
            correlation_id,
            trace_id,
            tenant_id,
            cell_id,
            idempotency_key,
            requested_action_class,
            payload_ref,
        )
        
        approval = ApprovalRequest(
            approval_id=approval_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            cell_id=cell_id,
            idempotency_key=idempotency_key,
            requested_action_class=requested_action_class,
            payload_ref=payload_ref,
            created_at=_deterministic_approval_created_at(approval_id),
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
        approval.approved_at = _deterministic_approval_transition_at(approval_id, operator_id, "APPROVED")
        
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
        approval.denied_at = _deterministic_approval_transition_at(approval_id, operator_id, "DENIED")
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
    
    async def initialize(self) -> None:
        """Initialize approval service"""
        if not self.config.enabled:
            return
        from exoarmur.core.phase_gate import PhaseGate
        PhaseGate.check_phase_2_eligibility("ApprovalService")
        self._initialized = True
        logger.info("ApprovalService initialized (Phase 2)")
    
    async def submit_approval_request(self, request_data: Dict[str, Any]) -> str:
        """Submit approval request and return approval ID"""
        if not self.config.enabled:
            return _deterministic_legacy_token("legacy", "submit_approval_request", request_data)
        
        # Extract fields from request_data, using deterministic defaults
        request_id = request_data.get("request_id", "unknown")
        intent_type = request_data.get("intent_type", "unknown")
        risk_score = request_data.get("risk_score", 0.0)
        clearance_required = request_data.get("clearance_required", "supervisor")
        target = request_data.get("target_entity", {})
        
        approval_id = _deterministic_approval_id(
            correlation_id=request_id,
            trace_id=request_id,
            tenant_id="default",
            cell_id="local",
            idempotency_key=request_id,
            requested_action_class=intent_type,
            payload_ref=target,
        )
        
        approval = ApprovalRequest(
            approval_id=approval_id,
            correlation_id=request_id,
            trace_id=request_id,
            tenant_id="default",
            cell_id="local",
            idempotency_key=request_id,
            requested_action_class=intent_type,
            payload_ref={"target": target, "risk_score": risk_score,
                         "clearance_required": clearance_required},
            created_at=_deterministic_approval_created_at(approval_id),
            status="PENDING",
        )
        self._approvals[approval_id] = approval
        self._emit_audit("approval_submitted", {"approval_id": approval_id,
                                                  "intent_type": intent_type,
                                                  "risk_score": risk_score})
        
        logger.info(f"Submitted approval request {approval_id} for {intent_type} (risk={risk_score})")
        return approval_id
    
    async def get_approval_status(self, request_id: str) -> Dict[str, Any]:
        """Get approval request status"""
        approval = self._approvals.get(request_id)
        if approval:
            return {
                "request_id": request_id,
                "status": approval.status,
                "created_at": approval.created_at.isoformat(),
                "approval_required": True,
            }
        return {
            "request_id": request_id,
            "status": "NOT_FOUND",
            "created_at": deterministic_timestamp(request_id, "legacy_status").isoformat(),
            "approval_required": False,
        }
    
    async def approve_request(self, request_id: str, operator_id: str, reason: str) -> bool:
        """Approve a request by operator"""
        if not self.config.enabled:
            return True
        approval = self._approvals.get(request_id)
        if approval is None:
            return False
        if approval.status != "PENDING":
            return False
        self.approve(request_id, operator_id)
        self._emit_audit("approval_granted", {"approval_id": request_id,
                                                "operator_id": operator_id,
                                                "reason": reason})
        return True
    
    async def deny_request(self, request_id: str, operator_id: str, reason: str) -> bool:
        """Deny a request by operator"""
        if not self.config.enabled:
            return True
        approval = self._approvals.get(request_id)
        if approval is None:
            return False
        if approval.status != "PENDING":
            return False
        self.deny(request_id, operator_id, reason)
        self._emit_audit("approval_denied", {"approval_id": request_id,
                                               "operator_id": operator_id,
                                               "reason": reason})
        return True
    
    async def get_pending_approvals(self, operator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending approvals"""
        if not self.config.enabled:
            return []
        
        results = []
        for approval in self._approvals.values():
            if approval.status != "PENDING":
                continue
            results.append({
                "approval_id": approval.approval_id,
                "requested_action_class": approval.requested_action_class,
                "payload_ref": approval.payload_ref,
                "created_at": approval.created_at.isoformat(),
                "status": approval.status,
            })
        return results
    
    async def check_authorization(self, operator_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check operator authorization for request"""
        if not self.config.enabled:
            return {"authorized": False, "reason": "V2 approval service disabled"}
        
        risk_score = request_data.get("risk_score", 0.0)
        clearance_required = request_data.get("clearance_required", "supervisor")
        
        # Check via operator interface if wired
        if self._operator_interface is not None:
            if not self._operator_interface.clearance_at_least(operator_id, clearance_required):
                return {
                    "authorized": False,
                    "operator_id": operator_id,
                    "reason": f"Insufficient clearance (requires {clearance_required})",
                }
            # Check risk threshold for clearance level
            registered = self._operator_interface._registered_operators.get(operator_id)
            if registered:
                max_risk = _RISK_CLEARANCE_MAP.get(registered.clearance_level, 0.0)
                if risk_score > max_risk:
                    return {
                        "authorized": False,
                        "operator_id": operator_id,
                        "reason": f"Risk {risk_score} exceeds clearance threshold {max_risk}",
                    }
        
        self._emit_audit("authorization_check", {"operator_id": operator_id,
                                                   "authorized": True,
                                                   "risk_score": risk_score})
        return {
            "authorized": True,
            "operator_id": operator_id,
            "clearance_required": clearance_required,
        }
    
    async def request_emergency_override(self, emergency_data: Dict[str, Any]) -> str:
        """Request emergency override — creates high-priority approval"""
        if not self.config.enabled:
            return _deterministic_legacy_token("legacy-emergency", "request_emergency_override", emergency_data)
        
        emergency_type = emergency_data.get("emergency_type", "unknown")
        override_id = _deterministic_legacy_token("emergency", emergency_type, emergency_data)
        
        approval = ApprovalRequest(
            approval_id=override_id,
            correlation_id=f"emergency-{emergency_type}",
            trace_id=f"emergency-{emergency_type}",
            tenant_id="default",
            cell_id="local",
            idempotency_key=override_id,
            requested_action_class=f"emergency_override:{emergency_type}",
            payload_ref=emergency_data,
            created_at=_deterministic_approval_created_at(override_id),
            status="PENDING",
        )
        self._approvals[override_id] = approval
        self._emit_audit("emergency_override_requested", {
            "override_id": override_id,
            "emergency_type": emergency_type,
        })
        
        logger.warning(f"Emergency override requested: {override_id} ({emergency_type})")
        return override_id
    
    def is_approval_required(self, request_type: str, risk_score: float) -> bool:
        """Check if approval is required for request"""
        if not self.config.enabled:
            return False
        # Any action with risk > 0.5 requires approval
        return risk_score > 0.5
    
    async def shutdown(self) -> None:
        """Shutdown approval service"""
        self._approvals.clear()
        self._audit_log.clear()
        self._operator_interface = None
    
    def _emit_audit(self, event_type: str, details: Dict[str, Any]) -> None:
        """Emit audit event"""
        entry = {
            "event_type": event_type,
            "timestamp": deterministic_timestamp(event_type, "approval_audit").isoformat(),
            "details": details,
        }
        self._audit_log.append(entry)
        logger.debug(f"Approval audit: {event_type}")
