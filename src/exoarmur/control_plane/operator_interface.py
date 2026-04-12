"""
ExoArmur ADMO V2 Operator Interface
Human operator interaction and session management
"""

import logging
import hashlib
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from exoarmur.core.phase_gate import PhaseGate
from exoarmur.clock import deterministic_timestamp

logger = logging.getLogger(__name__)


@dataclass
class OperatorConfig:
    """Operator interface configuration"""
    enabled: bool = False
    session_timeout_minutes: int = 480
    require_mfa: bool = True
    max_concurrent_sessions: int = 3


@dataclass
class OperatorCredentials:
    """Validated operator credential set"""
    operator_id: str
    clearance_level: str  # 'supervisor', 'admin', 'superuser'
    permissions: List[str] = field(default_factory=list)
    certificate_fingerprint: Optional[str] = None
    mfa_verified: bool = False


@dataclass
class OperatorSession:
    """Operator session data"""
    session_id: str
    operator_id: str
    clearance_level: str
    permissions: List[str]
    login_time: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    authenticated: bool = False


# Clearance level hierarchy — higher index = more authority
_CLEARANCE_HIERARCHY = ['supervisor', 'admin', 'superuser']


def _deterministic_session_id(operator_id: str, credential_fingerprint: str) -> str:
    """Generate deterministic session ID from operator and credential data"""
    canonical = json.dumps(
        {"operator_id": operator_id, "fingerprint": credential_fingerprint},
        sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"session-{digest[:16]}"


def _credential_fingerprint(credentials: Dict[str, Any]) -> str:
    """Compute deterministic fingerprint from credentials"""
    canonical = json.dumps(credentials, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class OperatorInterface:
    """Human operator interface with authentication, session management, and permissions"""
    
    def __init__(self, config: Optional[OperatorConfig] = None):
        self.config = config or OperatorConfig()
        self._sessions: Dict[str, OperatorSession] = {}
        self._registered_operators: Dict[str, OperatorCredentials] = {}
        self._audit_log: List[Dict[str, Any]] = []
        
        if self.config.enabled:
            logger.info("OperatorInterface: Phase 2 enabled")
        else:
            logger.debug("OperatorInterface: scaffolding mode (enabled=False)")
    
    async def initialize(self) -> None:
        """Initialize operator interface"""
        if not self.config.enabled:
            logger.debug("OperatorInterface.initialize() - no-op (scaffolding)")
            return
        PhaseGate.check_phase_2_eligibility("OperatorInterface")
        logger.info("OperatorInterface initialized (Phase 2)")
    
    def register_operator(self, operator_id: str, clearance_level: str,
                          permissions: List[str],
                          certificate_fingerprint: Optional[str] = None) -> None:
        """Register an operator in the local credential store"""
        if clearance_level not in _CLEARANCE_HIERARCHY:
            raise ValueError(f"Invalid clearance_level '{clearance_level}'. "
                             f"Must be one of {_CLEARANCE_HIERARCHY}")
        self._registered_operators[operator_id] = OperatorCredentials(
            operator_id=operator_id,
            clearance_level=clearance_level,
            permissions=list(permissions),
            certificate_fingerprint=certificate_fingerprint,
        )
        logger.info(f"Registered operator {operator_id} (clearance={clearance_level})")
    
    async def authenticate_operator(self, operator_id: str, credentials: Dict[str, Any]) -> str:
        """Authenticate operator and return session ID"""
        if not self.config.enabled:
            logger.debug("OperatorInterface.authenticate_operator() - no-op (scaffolding)")
            return f"scaffold-session-{operator_id}"
        
        PhaseGate.check_phase_2_eligibility("OperatorInterface")
        
        # Validate operator is registered
        registered = self._registered_operators.get(operator_id)
        if registered is None:
            self._emit_audit("auth_failed", operator_id, {"reason": "unknown_operator"})
            raise PermissionError(f"Operator '{operator_id}' is not registered")
        
        # Validate certificate if required
        if "certificate" in credentials:
            fingerprint = _credential_fingerprint(credentials)
            if registered.certificate_fingerprint and fingerprint != registered.certificate_fingerprint:
                self._emit_audit("auth_failed", operator_id, {"reason": "certificate_mismatch"})
                raise PermissionError(f"Certificate mismatch for operator '{operator_id}'")
        
        # Enforce max concurrent sessions
        active_count = sum(
            1 for s in self._sessions.values()
            if s.operator_id == operator_id and s.authenticated
        )
        if active_count >= self.config.max_concurrent_sessions:
            self._emit_audit("auth_failed", operator_id, {"reason": "max_sessions_exceeded"})
            raise PermissionError(
                f"Operator '{operator_id}' has reached max concurrent sessions "
                f"({self.config.max_concurrent_sessions})"
            )
        
        # Create deterministic session
        fingerprint = _credential_fingerprint(credentials)
        session_id = _deterministic_session_id(operator_id, fingerprint)
        now = deterministic_timestamp(session_id, "operator_login")
        
        session = OperatorSession(
            session_id=session_id,
            operator_id=operator_id,
            clearance_level=registered.clearance_level,
            permissions=list(registered.permissions),
            login_time=now,
            last_activity=now,
            ip_address=credentials.get("ip_address", "127.0.0.1"),
            user_agent=credentials.get("user_agent", "exoarmur-cli"),
            authenticated=True,
        )
        self._sessions[session_id] = session
        self._emit_audit("auth_success", operator_id, {"session_id": session_id})
        
        logger.info(f"Authenticated operator {operator_id} → session {session_id}")
        return session_id
    
    async def logout_operator(self, session_id: str) -> bool:
        """Logout operator"""
        if not self.config.enabled:
            logger.debug("OperatorInterface.logout_operator() - no-op (scaffolding)")
            return True
        
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        self._emit_audit("logout", session.operator_id, {"session_id": session_id})
        logger.info(f"Logged out session {session_id}")
        return True
    
    async def validate_session(self, session_id: str) -> Dict[str, Any]:
        """Validate operator session"""
        if not self.config.enabled:
            return {"session_id": session_id, "valid": False, "reason": "scaffolding_mode"}
        
        session = self._sessions.get(session_id)
        if session is None or not session.authenticated:
            return {"session_id": session_id, "valid": False, "reason": "no_session"}
        
        return {
            "session_id": session_id,
            "valid": True,
            "operator_id": session.operator_id,
            "clearance_level": session.clearance_level,
            "permissions": session.permissions,
        }
    
    async def get_operator_info(self, operator_id: str) -> Dict[str, Any]:
        """Get operator information"""
        if not self.config.enabled:
            return {"operator_id": operator_id, "clearance_level": "scaffolding",
                    "permissions": [], "status": "scaffolding"}
        
        registered = self._registered_operators.get(operator_id)
        if registered is None:
            return {"operator_id": operator_id, "clearance_level": None,
                    "permissions": [], "status": "unregistered"}
        
        active_sessions = [
            s.session_id for s in self._sessions.values()
            if s.operator_id == operator_id and s.authenticated
        ]
        return {
            "operator_id": operator_id,
            "clearance_level": registered.clearance_level,
            "permissions": registered.permissions,
            "status": "active" if active_sessions else "registered",
            "active_sessions": active_sessions,
        }
    
    async def check_permissions(self, operator_id: str, required_permission: str) -> bool:
        """Check operator permissions"""
        if not self.config.enabled:
            return False
        
        registered = self._registered_operators.get(operator_id)
        if registered is None:
            return False
        
        # Superuser can do everything
        if registered.clearance_level == "superuser":
            return True
        # Check explicit permission grant
        if required_permission in registered.permissions:
            return True
        # Check wildcard permissions
        if "approve_any_risk_level" in registered.permissions:
            return True
        
        return False
    
    def clearance_at_least(self, operator_id: str, required_level: str) -> bool:
        """Check if operator clearance meets or exceeds required level"""
        registered = self._registered_operators.get(operator_id)
        if registered is None:
            return False
        try:
            op_idx = _CLEARANCE_HIERARCHY.index(registered.clearance_level)
            req_idx = _CLEARANCE_HIERARCHY.index(required_level)
            return op_idx >= req_idx
        except ValueError:
            return False
    
    async def get_active_sessions(self, operator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active operator sessions"""
        if not self.config.enabled:
            return []
        
        results = []
        for s in self._sessions.values():
            if not s.authenticated:
                continue
            if operator_id and s.operator_id != operator_id:
                continue
            results.append({
                "session_id": s.session_id,
                "operator_id": s.operator_id,
                "clearance_level": s.clearance_level,
                "login_time": s.login_time.isoformat(),
                "last_activity": s.last_activity.isoformat(),
            })
        return results
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity"""
        if not self.config.enabled:
            return True
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.last_activity = deterministic_timestamp(session_id, "activity_update")
        return True
    
    async def terminate_session(self, session_id: str, reason: str) -> bool:
        """Terminate operator session"""
        if not self.config.enabled:
            return True
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        self._emit_audit("session_terminated", session.operator_id,
                         {"session_id": session_id, "reason": reason})
        return True
    
    async def request_emergency_access(self, operator_id: str, emergency_data: Dict[str, Any]) -> str:
        """Request emergency access — grants temporary superuser session"""
        if not self.config.enabled:
            return f"scaffold-emergency-{operator_id}"
        
        PhaseGate.check_phase_2_eligibility("OperatorInterface")
        
        registered = self._registered_operators.get(operator_id)
        if registered is None:
            raise PermissionError(f"Operator '{operator_id}' is not registered")
        
        # Emergency access requires at least admin clearance
        if not self.clearance_at_least(operator_id, "admin"):
            raise PermissionError(
                f"Operator '{operator_id}' lacks clearance for emergency access "
                f"(requires admin, has {registered.clearance_level})"
            )
        
        fingerprint = _credential_fingerprint(emergency_data)
        session_id = _deterministic_session_id(operator_id, f"emergency-{fingerprint}")
        now = deterministic_timestamp(session_id, "emergency_access")
        
        session = OperatorSession(
            session_id=session_id,
            operator_id=operator_id,
            clearance_level="superuser",  # emergency escalation
            permissions=["emergency_override_level_1", "emergency_override_level_2",
                         "approve_any_risk_level"],
            login_time=now,
            last_activity=now,
            ip_address="emergency",
            user_agent="emergency-protocol",
            authenticated=True,
        )
        self._sessions[session_id] = session
        self._emit_audit("emergency_access_granted", operator_id,
                         {"session_id": session_id, "emergency_data": emergency_data})
        
        logger.warning(f"Emergency access granted to {operator_id} → session {session_id}")
        return session_id
    
    def is_operator_authenticated(self, session_id: str) -> bool:
        """Check if operator is authenticated"""
        if not self.config.enabled:
            return False
        session = self._sessions.get(session_id)
        return session is not None and session.authenticated
    
    async def get_audit_trail(self, operator_id: str, start_time: datetime,
                              end_time: datetime) -> List[Dict[str, Any]]:
        """Get operator audit trail"""
        if not self.config.enabled:
            return []
        return [
            entry for entry in self._audit_log
            if entry["operator_id"] == operator_id
        ]
    
    async def shutdown(self) -> None:
        """Shutdown operator interface"""
        if not self.config.enabled:
            logger.debug("OperatorInterface.shutdown() - no-op (scaffolding)")
        self._sessions.clear()
        self._registered_operators.clear()
        self._audit_log.clear()
    
    def _emit_audit(self, event_type: str, operator_id: str, details: Dict[str, Any]) -> None:
        """Emit audit event for operator actions"""
        entry = {
            "event_type": event_type,
            "operator_id": operator_id,
            "timestamp": deterministic_timestamp(f"{event_type}-{operator_id}", "audit").isoformat(),
            "details": details,
        }
        self._audit_log.append(entry)
        logger.debug(f"Operator audit: {event_type} for {operator_id}")
