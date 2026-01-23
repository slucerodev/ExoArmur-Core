"""
API Response Models for ExoArmur ADMO

Contract-first response models for FastAPI endpoints using Pydantic v2.
All models reference the core contract models from spec/contracts/models_v1.py.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_serializer

# Import core contract models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))
from models_v1 import TelemetryEventV1, AuditRecordV1


class TelemetryIngestResponseV1(BaseModel):
    """Response model for POST /v1/telemetry/ingest"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    accepted: bool = Field(description="Whether the telemetry was accepted for processing")
    correlation_id: str = Field(description="Correlation identifier from request")
    event_id: str = Field(description="Event ID from request")
    belief_id: Optional[str] = Field(default=None, description="Generated belief ID if available")
    processed_at: datetime = Field(description="When the request was processed")
    trace_id: str = Field(description="Trace identifier from request")
    approval_id: Optional[str] = Field(default=None, description="Approval ID if approval required")
    approval_status: Optional[str] = Field(default=None, description="Approval status (PENDING/APPROVED/DENIED)")
    safety_verdict: Optional[str] = Field(default=None, description="Safety verdict (require_human/require_quorum)")
    
    @field_serializer('processed_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ApprovalActionRequestV1(BaseModel):
    """Request model for approval actions (approve/deny)"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    operator_id: str = Field(description="ID of the operator performing the action")
    reason: Optional[str] = Field(default=None, description="Reason for denial (required for deny)")


class ApprovalResponseV1(BaseModel):
    """Response model for approval actions"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    approval_id: str = Field(description="Approval request ID")
    status: str = Field(description="Approval status (PENDING/APPROVED/DENIED)")
    created_at: datetime = Field(description="When the approval was created")
    
    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ApprovalStatusResponseV1(BaseModel):
    """Response model for GET /v1/approvals/{approval_id}"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    approval_id: str = Field(description="Approval request ID")
    status: str = Field(description="Approval status (PENDING/APPROVED/DENIED)")
    created_at: datetime = Field(description="When the approval was created")
    requested_action_class: str = Field(description="Action class requiring approval")
    correlation_id: str = Field(description="Correlation ID from original request")
    
    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class AuditResponseV1(BaseModel):
    """Response model for GET /v1/audit/{correlation_id}"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    correlation_id: str = Field(description="Correlation identifier")
    audit_records: List[AuditRecordV1] = Field(description="List of audit records for this correlation")
    total_count: int = Field(description="Total number of audit records found")
    retrieved_at: datetime = Field(description="When the audit records were retrieved")
    
    @field_serializer('retrieved_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ErrorResponseV1(BaseModel):
    """Standard error response model"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID if available")
    timestamp: datetime = Field(description="When the error occurred")
    
    @field_serializer('timestamp')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


# Export all models
__all__ = [
    'TelemetryIngestResponseV1',
    'ApprovalActionRequestV1',
    'ApprovalResponseV1',
    'ApprovalStatusResponseV1',
    'AuditResponseV1', 
    'ErrorResponseV1'
]
