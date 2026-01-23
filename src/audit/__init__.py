"""
Audit Module - Audit Record Generation

Emits AuditRecordV1 at each major step with linking IDs.
"""

from .audit_logger import AuditLogger

__all__ = ['AuditLogger']
