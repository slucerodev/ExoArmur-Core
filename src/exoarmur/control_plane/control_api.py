"""
ExoArmur ADMO V2 Control Plane API
Operator control plane for governed execution visibility
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from exoarmur.core.phase_gate import PhaseGate
from exoarmur.clock import deterministic_timestamp

logger = logging.getLogger(__name__)


@dataclass
class ControlAPIConfig:
    """Control API configuration"""
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8080
    require_authentication: bool = True
    rate_limit_enabled: bool = True


class ControlAPI:
    """Control plane API for governed execution visibility and operator workflows"""
    
    def __init__(self, config: Optional[ControlAPIConfig] = None):
        self.config = config or ControlAPIConfig()
        self._running = False
        self._approval_service = None
        self._operator_interface = None
        self._federation_cells: List[Dict[str, Any]] = []
        self._audit_log: List[Dict[str, Any]] = []
        
        if self.config.enabled:
            logger.info("ControlAPI: Phase 2 enabled")
        else:
            logger.debug("ControlAPI: scaffolding mode (enabled=False)")
    
    def wire_services(self, approval_service=None, operator_interface=None) -> None:
        """Wire backing services for the control plane"""
        self._approval_service = approval_service
        self._operator_interface = operator_interface
    
    def register_federation_cell(self, cell_id: str, cell_info: Dict[str, Any]) -> None:
        """Register a federation cell for status tracking"""
        self._federation_cells.append({
            "cell_id": cell_id,
            "status": "healthy",
            **cell_info,
        })
    
    async def startup(self) -> None:
        """Start control API server"""
        if not self.config.enabled:
            logger.debug("ControlAPI.startup() - no-op (scaffolding)")
            self._running = False
            return
        PhaseGate.check_phase_2_eligibility("ControlAPI")
        self._running = True
        self._emit_audit("control_api_started", {})
        logger.info(f"ControlAPI started (host={self.config.host}, port={self.config.port})")
    
    async def shutdown(self) -> None:
        """Shutdown control API server"""
        if not self.config.enabled:
            logger.debug("ControlAPI.shutdown() - no-op (scaffolding)")
            self._running = False
            return
        self._running = False
        self._emit_audit("control_api_stopped", {})
        self._federation_cells.clear()
        self._audit_log.clear()
        logger.info("ControlAPI shutdown")
    
    def is_running(self) -> bool:
        """Check if API server is running"""
        return self._running
    
    async def get_federation_status(self) -> Dict[str, Any]:
        """Get federation status"""
        if not self.config.enabled:
            return {
                "federation_id": "scaffold-federation",
                "member_count": 0,
                "healthy_cells": [],
                "degraded_cells": [],
                "last_coordination": None,
            }
        
        healthy = [c for c in self._federation_cells if c.get("status") == "healthy"]
        degraded = [c for c in self._federation_cells if c.get("status") != "healthy"]
        
        return {
            "federation_id": "exoarmur-federation",
            "member_count": len(self._federation_cells),
            "healthy_cells": [c["cell_id"] for c in healthy],
            "degraded_cells": [c["cell_id"] for c in degraded],
            "last_coordination": deterministic_timestamp(
                "federation-status", "coordination").isoformat(),
            "api_running": self._running,
        }
    
    async def get_federation_members(self) -> Dict[str, Any]:
        """Get federation members"""
        if not self.config.enabled:
            return {"members": [], "total_count": 0,
                    "page_info": {"page": 1, "per_page": 50, "total_pages": 0}}
        
        return {
            "members": self._federation_cells,
            "total_count": len(self._federation_cells),
            "page_info": {"page": 1, "per_page": 50,
                          "total_pages": max(1, len(self._federation_cells) // 50)},
        }
    
    async def join_federation(self, join_data: Dict[str, Any]) -> Dict[str, Any]:
        """Join federation"""
        if not self.config.enabled:
            return {"request_id": "scaffold-join-request", "status": "scaffolding",
                    "estimated_approval_time": None}
        
        cell_id = join_data.get("cell_id", "unknown")
        self.register_federation_cell(cell_id, join_data)
        self._emit_audit("federation_join", {"cell_id": cell_id})
        
        return {
            "request_id": f"join-{cell_id}",
            "status": "accepted",
            "cell_id": cell_id,
        }
    
    async def get_pending_approvals(self) -> Dict[str, Any]:
        """Get pending approvals"""
        if not self.config.enabled:
            return {"pending_approvals": [], "total_pending": 0, "priority_queue": False}
        
        pending = []
        if self._approval_service is not None:
            pending = await self._approval_service.get_pending_approvals()
        
        return {
            "pending_approvals": pending,
            "total_pending": len(pending),
            "priority_queue": True,
        }
    
    async def get_approval_details(self, approval_id: str) -> Dict[str, Any]:
        """Get approval details"""
        if not self.config.enabled:
            return {"approval_request": None, "related_events": [],
                    "risk_assessment": None}
        
        details = None
        if self._approval_service is not None:
            details = self._approval_service.get_approval_details(approval_id)
        
        return {
            "approval_request": details,
            "related_events": [],
            "risk_assessment": None,
        }
    
    async def approve_request(self, approval_id: str, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """Approve request"""
        if not self.config.enabled:
            return {"approval_id": approval_id, "status": "scaffolding",
                    "approval_token": None}
        
        operator_id = approval_data.get("operator_id", "unknown")
        reason = approval_data.get("reason", "")
        
        success = False
        if self._approval_service is not None:
            success = await self._approval_service.approve_request(
                approval_id, operator_id, reason)
        
        self._emit_audit("approval_granted", {"approval_id": approval_id,
                                                "operator_id": operator_id})
        return {
            "approval_id": approval_id,
            "status": "APPROVED" if success else "FAILED",
            "operator_id": operator_id,
        }
    
    async def deny_request(self, approval_id: str, denial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deny request"""
        if not self.config.enabled:
            return {"approval_id": approval_id, "status": "scaffolding",
                    "denial_reason": "scaffolding_mode"}
        
        operator_id = denial_data.get("operator_id", "unknown")
        reason = denial_data.get("reason", "denied")
        
        success = False
        if self._approval_service is not None:
            success = await self._approval_service.deny_request(
                approval_id, operator_id, reason)
        
        self._emit_audit("approval_denied", {"approval_id": approval_id,
                                               "operator_id": operator_id})
        return {
            "approval_id": approval_id,
            "status": "DENIED" if success else "FAILED",
            "denial_reason": reason,
        }
    
    async def get_audit_events(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get audit events"""
        if not self.config.enabled:
            return {"audit_events": [], "total_count": 0, "has_more": False}
        
        limit = query_params.get("limit", 50)
        events = self._audit_log[-limit:]
        
        return {
            "audit_events": events,
            "total_count": len(self._audit_log),
            "has_more": len(self._audit_log) > limit,
        }
    
    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics"""
        if not self.config.enabled:
            return {"overall_health": "scaffolding", "cell_health": {},
                    "network_status": {}, "performance_metrics": {}}
        
        healthy_count = sum(1 for c in self._federation_cells
                           if c.get("status") == "healthy")
        total = len(self._federation_cells)
        
        return {
            "overall_health": "healthy" if healthy_count == total else "degraded",
            "cell_health": {c["cell_id"]: c["status"] for c in self._federation_cells},
            "network_status": {"connected_cells": total, "healthy": healthy_count},
            "performance_metrics": {"api_running": self._running,
                                     "audit_events": len(self._audit_log)},
        }
    
    def get_available_endpoints(self) -> List[str]:
        """Get list of available endpoints"""
        return [
            "/api/v2/federation/status",
            "/api/v2/federation/members",
            "/api/v2/federation/join",
            "/api/v2/approvals/pending",
            "/api/v2/approvals/{approval_id}",
            "/api/v2/audit/federation",
            "/api/v2/monitoring/health",
        ]
    
    def _emit_audit(self, event_type: str, details: Dict[str, Any]) -> None:
        """Emit audit event"""
        entry = {
            "event_type": event_type,
            "timestamp": deterministic_timestamp(event_type, "control_api_audit").isoformat(),
            "details": details,
        }
        self._audit_log.append(entry)
        logger.debug(f"ControlAPI audit: {event_type}")
