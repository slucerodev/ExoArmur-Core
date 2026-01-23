"""
Audit logging components
"""

from .audit_logger import AuditLogger
from datetime import datetime
from typing import Dict, Any


class NoOpAuditInterface:
    """No-op audit interface for testing scenarios"""
    
    def emit_audit_record(self, event_kind: str, payload_ref: dict, correlation_id: str = None):
        """No-op audit record emission"""
        pass
    
    def get_audit_trail(self, correlation_id: str = None):
        """No-op audit trail retrieval"""
        return []
    
    def validate_audit_integrity(self, correlation_id: str = None):
        """No-op audit integrity validation"""
        return True, "No-op audit interface"
    
    def log_event(self, event_type: str, correlation_id: str, data: Dict[str, Any], recorded_at: datetime) -> bool:
        """No-op audit event logging for federation interface compatibility"""
        return True


class FederationAuditInterface:
    """Audit interface compatible with federation components"""
    
    def log_event(self, event_type: str, correlation_id: str, data: Dict[str, Any], recorded_at: datetime) -> bool:
        """Audit event logging for federation interface compatibility"""
        return True


__all__ = ['AuditLogger', 'NoOpAuditInterface', 'FederationAuditInterface']
