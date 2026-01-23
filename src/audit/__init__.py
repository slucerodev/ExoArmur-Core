"""
Audit Module - Audit Record Generation

Emits AuditRecordV1 at each major step with linking IDs.
"""

from .audit_logger import AuditLogger

# No-op audit interface for testing
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

__all__ = ['AuditLogger', 'NoOpAuditInterface']
