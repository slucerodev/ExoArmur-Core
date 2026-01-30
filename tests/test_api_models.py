"""
Contract-first tests for API response models

Tests validate that API models conform to contracts and handle edge cases properly.
"""

import pytest
import sys
import os
from datetime import datetime
from pydantic import ValidationError

# Add paths for imports

from exoarmur.clock import utc_now

from exoarmur.api_models import (
    TelemetryIngestResponseV1,
    AuditResponseV1,
    ErrorResponseV1
)
from spec.contracts.models_v1 import AuditRecordV1


class TestTelemetryIngestResponseV1:
    """Test TelemetryIngestResponseV1 contract compliance"""
    
    def test_minimal_valid_response(self):
        """Test minimal valid response"""
        response = TelemetryIngestResponseV1(
            accepted=True,
            correlation_id="corr-123",
            event_id="01J4NR5X9Z8GABCDEF12345678",
            processed_at=utc_now(),
            trace_id="trace-123"
        )
        
        assert response.accepted is True
        assert response.correlation_id == "corr-123"
        assert response.event_id == "01J4NR5X9Z8GABCDEF12345678"
        assert response.belief_id is None
        assert response.trace_id == "trace-123"
    
    def test_full_response_with_belief_id(self):
        """Test full response including belief_id"""
        response = TelemetryIngestResponseV1(
            accepted=True,
            correlation_id="corr-123",
            event_id="01J4NR5X9Z8GABCDEF12345678",
            belief_id="01J4NR5X9Z8GABCDEF12345679",
            processed_at=utc_now(),
            trace_id="trace-123"
        )
        
        assert response.belief_id == "01J4NR5X9Z8GABCDEF12345679"
    
    def test_reject_extra_fields(self):
        """Test that extra fields are rejected"""
        with pytest.raises(ValidationError):
            TelemetryIngestResponseV1(
                accepted=True,
                correlation_id="corr-123",
                event_id="01J4NR5X9Z8GABCDEF12345678",
                processed_at=utc_now(),
                trace_id="trace-123",
                extra_field="not_allowed"
            )
    
    def test_required_fields(self):
        """Test that required fields cannot be omitted"""
        with pytest.raises(ValidationError):
            TelemetryIngestResponseV1(
                accepted=True,
                correlation_id="corr-123"
                # Missing event_id, processed_at, trace_id
            )


class TestAuditResponseV1:
    """Test AuditResponseV1 contract compliance"""
    
    def test_minimal_valid_response(self):
        """Test minimal valid response with empty audit list"""
        response = AuditResponseV1(
            correlation_id="corr-123",
            audit_records=[],
            total_count=0,
            retrieved_at=utc_now()
        )
        
        assert response.correlation_id == "corr-123"
        assert response.audit_records == []
        assert response.total_count == 0
    
    def test_response_with_audit_records(self):
        """Test response with actual audit records"""
        audit_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="idemp-123",
            recorded_at=utc_now(),
            event_kind="telemetry_ingested",
            payload_ref={"kind": "inline", "ref": "payload-data"},
            hashes={"sha256": "abc123"},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        response = AuditResponseV1(
            correlation_id="corr-123",
            audit_records=[audit_record.model_dump()],
            total_count=1,
            retrieved_at=utc_now()
        )
        
        assert len(response.audit_records) == 1
        assert response.total_count == 1
        assert response.audit_records[0]["audit_id"] == "01J4NR5X9Z8GABCDEF12345678"
    
    def test_reject_extra_fields(self):
        """Test that extra fields are rejected"""
        with pytest.raises(ValidationError):
            AuditResponseV1(
                correlation_id="corr-123",
                audit_records=[],
                total_count=0,
                retrieved_at=utc_now(),
                extra_field="not_allowed"
            )


class TestErrorResponseV1:
    """Test ErrorResponseV1 contract compliance"""
    
    def test_minimal_error_response(self):
        """Test minimal error response"""
        error = ErrorResponseV1(
            error="ValidationError",
            message="Invalid input data",
            timestamp=utc_now()
        )
        
        assert error.error == "ValidationError"
        assert error.message == "Invalid input data"
        assert error.correlation_id is None
    
    def test_error_response_with_correlation(self):
        """Test error response with correlation ID"""
        error = ErrorResponseV1(
            error="ProcessingError",
            message="Failed to process telemetry",
            correlation_id="corr-123",
            timestamp=utc_now()
        )
        
        assert error.correlation_id == "corr-123"
    
    def test_reject_extra_fields(self):
        """Test that extra fields are rejected"""
        with pytest.raises(ValidationError):
            ErrorResponseV1(
                error="ValidationError",
                message="Invalid input data",
                timestamp=utc_now(),
                extra_field="not_allowed"
            )
