"""
Integration test for thin vertical slice
Tests the complete ADMO loop: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

# Import the main app
from src.main import app, initialize_components
from models_v1 import TelemetryEventV1, BeliefV1, ExecutionIntentV1, AuditRecordV1


@pytest.fixture(autouse=True)
def setup_test_components():
    """Initialize components for testing"""
    initialize_components()


class TestThinVerticalSlice:
    """Integration test for thin vertical slice"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        
        # Create test telemetry event
        self.telemetry_event = TelemetryEventV1(
            schema_version="1.0.0",
            event_id="3EDW0S2AFBGFZ0T10NPVFXFT77",  # Valid ULID
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            source={
                "kind": "edr",
                "name": "crowdstrike",
                "host": "sensor-01",
                "sensor_id": "sensor-123"
            },
            event_type="process_start",
            severity="high",
            attributes={
                "process_name": "suspicious.exe",
                "process_path": "C:\\\\temp\\suspicious.exe",
                "command_line": "suspicious.exe -malicious"
            },
            entity_refs=None,
            correlation_id="test-correlation-123",
            trace_id="test-trace-123"
        )
    
    def test_health_endpoint(self):
        """Test that /health endpoint works"""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_telemetry_ingest_endpoint(self):
        """Test POST /v1/telemetry/ingest endpoint"""
        response = self.client.post(
            "/v1/telemetry/ingest",
            json=self.telemetry_event.model_dump()
        )
        
        # Should accept the telemetry
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["accepted"] is True
        assert response_data["correlation_id"] == self.telemetry_event.correlation_id
        assert response_data["event_id"] == self.telemetry_event.event_id
        assert "belief_id" in response_data
        assert "processed_at" in response_data
        assert response_data["trace_id"] == self.telemetry_event.trace_id
    
    def test_audit_retrieval_endpoint(self):
        """Test GET /v1/audit/{correlation_id} endpoint"""
        # First ingest telemetry to generate audit records
        ingest_response = self.client.post(
            "/v1/telemetry/ingest",
            json=self.telemetry_event.model_dump()
        )
        assert ingest_response.status_code == 200
        
        # Then retrieve audit records
        audit_response = self.client.get(
            f"/v1/audit/{self.telemetry_event.correlation_id}"
        )
        
        assert audit_response.status_code == 200
        
        audit_data = audit_response.json()
        assert audit_data["correlation_id"] == self.telemetry_event.correlation_id
        assert "audit_records" in audit_data
        assert "total_count" in audit_data
        assert "retrieved_at" in audit_data
        
        # Should have multiple audit records for the complete flow
        assert audit_data["total_count"] >= 3  # telemetry_ingested, safety_gate_evaluated, intent_executed/denied
        
        # Verify audit record structure
        audit_records = audit_data["audit_records"]
        for record in audit_records:
            assert "audit_id" in record
            assert "tenant_id" in record
            assert "cell_id" in record
            assert "event_kind" in record
            assert "payload_ref" in record
            assert "hashes" in record
            assert record["correlation_id"] == self.telemetry_event.correlation_id
    
    def test_admo_flow_audit_chain(self):
        """Test that complete ADMO flow creates proper audit chain"""
        # Ingest telemetry
        ingest_response = self.client.post(
            "/v1/telemetry/ingest",
            json=self.telemetry_event.model_dump()
        )
        assert ingest_response.status_code == 200
        
        # Get audit records
        audit_response = self.client.get(
            f"/v1/audit/{self.telemetry_event.correlation_id}"
        )
        assert audit_response.status_code == 200
        
        audit_records = audit_response.json()["audit_records"]
        event_kinds = [record["event_kind"] for record in audit_records]
        
        # Verify expected audit events in the flow
        assert "telemetry_ingested" in event_kinds
        assert "safety_gate_evaluated" in event_kinds
        assert "intent_executed" in event_kinds or "intent_denied" in event_kinds
        
        # Verify audit record linking through correlation_id and trace_id
        for record in audit_records:
            assert record["correlation_id"] == self.telemetry_event.correlation_id
            assert record["trace_id"] == self.telemetry_event.trace_id
            assert record["tenant_id"] == self.telemetry_event.tenant_id
            assert record["cell_id"] == self.telemetry_event.cell_id
    
    def test_telemetry_validation_error_handling(self):
        """Test that invalid telemetry events are properly rejected"""
        invalid_event = {
            # Missing required fields
            "event_id": "01J4NR5X9Z8GABCDEF12345678",
            "tenant_id": "tenant-acme"
        }
        
        response = self.client.post(
            "/v1/telemetry/ingest",
            json=invalid_event
        )
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_different_severity_levels(self):
        """Test telemetry events with different severity levels"""
        severities = ["low", "medium", "high", "critical"]
        
        for severity in severities:
            event = TelemetryEventV1(
                schema_version="1.0.0",
                event_id=f"01J4NR5X9Z8GABCDEF1234567{severities.index(severity)}",
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                observed_at=datetime.utcnow(),
                received_at=datetime.utcnow(),
                source={"kind": "edr", "name": "test"},
                event_type="process_start",
                severity=severity,
                attributes={},
                entity_refs=None,
                correlation_id=f"test-correlation-{severity}",
                trace_id=f"test-trace-{severity}"
            )
            
            response = self.client.post(
                "/v1/telemetry/ingest",
                json=event.model_dump()
            )
            
            assert response.status_code == 200
            assert response.json()["accepted"] is True
    
    def test_idempotency_in_integration(self):
        """Test idempotency behavior in integration"""
        # Send the same event twice
        response1 = self.client.post(
            "/v1/telemetry/ingest",
            json=self.telemetry_event.model_dump()
        )
        assert response1.status_code == 200
        
        response2 = self.client.post(
            "/v1/telemetry/ingest",
            json=self.telemetry_event.model_dump()
        )
        assert response2.status_code == 200
        
        # Both should succeed, but we can verify idempotency through audit records
        audit_response = self.client.get(
            f"/v1/audit/{self.telemetry_event.correlation_id}"
        )
        assert audit_response.status_code == 200
        
        # Should have audit records for both processing attempts
        audit_records = audit_response.json()["audit_records"]
        telemetry_ingested_records = [
            r for r in audit_records if r["event_kind"] == "telemetry_ingested"
        ]
        
        # Should have at least one telemetry_ingested record
        assert len(telemetry_ingested_records) >= 1
    
    def test_audit_for_nonexistent_correlation(self):
        """Test audit retrieval for non-existent correlation ID"""
        response = self.client.get("/v1/audit/nonexistent-correlation")
        
        assert response.status_code == 200
        audit_data = response.json()
        assert audit_data["correlation_id"] == "nonexistent-correlation"
        assert audit_data["total_count"] == 0
        assert audit_data["audit_records"] == []


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Async integration tests"""
    
    async def test_async_client_integration(self):
        """Test with async client"""
        from httpx import ASGITransport
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            event = TelemetryEventV1(
                schema_version="1.0.0",
                event_id="3EDW0S2AFBGFZ0T10NPVFXFT77",  # Valid ULID
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                observed_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                source={"kind": "edr", "name": "test"},
                event_type="process_start",
                severity="medium",
                attributes={},
                entity_refs=None,
                correlation_id="async-test-123",
                trace_id="async-trace-123"
            )
            
            response = await client.post(
                "/v1/telemetry/ingest",
                json=event.model_dump()
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["accepted"] is True
