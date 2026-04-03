"""
Regression tests for AuditNormalizer
Ensures strict derivative transformation with zero side effects and ordering preservation
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from exoarmur.audit.audit_normalizer import (
    AuditNormalizer, 
    CanonicalAuditEnvelope
)
from spec.contracts.models_v1 import AuditRecordV1


class TestAuditNormalizerDerivativeBehavior:
    """Test AuditNormalizer maintains strict derivative behavior with zero side effects"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.audit_normalizer = AuditNormalizer()
        
        # Sample V1 audit record
        self.sample_v1_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={
                "kind": "inline",
                "ref": "payload-data",
                "severity": "medium",
                "observed_at": "2024-01-01T12:00:00Z"
            },
            hashes={
                "sha256": "abc123...",
                "upstream_hashes": ["hash-1", "hash-2"]
            },
            correlation_id="corr-123",
            trace_id="trace-123"
        )
    
    def test_normalizer_preserves_v1_record_structure(self):
        """Test that normalizer preserves V1 record structure without modification"""
        # Normalize V1 record
        canonical_envelope = self.audit_normalizer.normalize_audit_record(self.sample_v1_record)
        
        # Verify core identity fields are preserved exactly
        assert canonical_envelope.audit_id == self.sample_v1_record.audit_id
        assert canonical_envelope.tenant_id == self.sample_v1_record.tenant_id
        assert canonical_envelope.cell_id == self.sample_v1_record.cell_id
        assert canonical_envelope.correlation_id == self.sample_v1_record.correlation_id
        assert canonical_envelope.trace_id == self.sample_v1_record.trace_id
        
        # Verify content is preserved
        assert canonical_envelope.payload_ref == self.sample_v1_record.payload_ref
        assert canonical_envelope.event_kind == self.sample_v1_record.event_kind
        assert canonical_envelope.recorded_at == self.sample_v1_record.recorded_at
        
        # Verify source format is tracked
        assert canonical_envelope.source_format == "v1"
        assert canonical_envelope.source_hashes == self.sample_v1_record.hashes
    
    def test_normalizer_deterministic_output(self):
        """Test that normalizer produces deterministic output across multiple calls"""
        # Normalize same record multiple times
        results = []
        for _ in range(100):
            canonical_envelope = self.audit_normalizer.normalize_audit_record(self.sample_v1_record)
            results.append(canonical_envelope)
        
        # All results should be identical (deterministic)
        first_result = results[0]
        for result in results[1:]:
            assert result.audit_id == first_result.audit_id
            assert result.ordering_key == first_result.ordering_key
            assert result.canonical_hashes == first_result.canonical_hashes
            assert result.normalized_at.isoformat() != first_result.normalized_at.isoformat()  # Timestamp changes
    
    def test_normalizer_ordering_preservation(self):
        """Test that normalizer preserves exact ordering semantics"""
        # Create multiple V1 records with different timestamps
        records = []
        for i in range(5):
            record = AuditRecordV1(
                schema_version="1.0.0",
                audit_id=f"01J4NR5X9Z8GABCDEF1234567{i}",
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                idempotency_key=f"abc{i}",
                recorded_at=datetime(2024, 1, 1, 12, 0, i, tzinfo=timezone.utc),
                event_kind="telemetry_ingested",
                payload_ref={"index": i},
                hashes={"sha256": f"hash{i}"},
                correlation_id="corr-123",
                trace_id="trace-123"
            )
            records.append(record)
        
        # Normalize records
        normalized_records = self.audit_normalizer.batch_normalize(records, preserve_ordering=True)
        
        # Verify ordering is preserved
        for i, record in enumerate(normalized_records):
            assert record.ordering_key == f"2024-01-01T12:00:0{i}+00:00_01J4NR5X9Z8GABCDEF1234567{i}"
        
        # Verify ordering keys are in correct sequence
        ordering_keys = [record.ordering_key for record in normalized_records]
        assert ordering_keys == sorted(ordering_keys)
    
    def test_normalizer_no_side_effects_on_input(self):
        """Test that normalizer does not modify input records"""
        # Create a copy of the original record
        original_record_dict = self.sample_v1_record.model_dump()
        
        # Normalize the record
        canonical_envelope = self.audit_normalizer.normalize_audit_record(self.sample_v1_record)
        
        # Verify original record is unchanged
        current_record_dict = self.sample_v1_record.model_dump()
        assert original_record_dict == current_record_dict
    
    def test_normalizer_canonical_passthrough(self):
        """Test that normalizer handles canonical envelope passthrough correctly"""
        from datetime import timezone
        
        # Create a canonical envelope
        canonical_input = CanonicalAuditEnvelope(
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            correlation_id="corr-123",
            trace_id="trace-123",
            recorded_at=datetime.now(timezone.utc),
            event_timestamp=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            event_category="ingestion",
            event_severity="medium",
            payload_ref={"test": "data"},
            source_format="canonical",
            source_hashes={"original": "hash"},
            canonical_hashes={"canonical": "hash"},
            normalized_at=datetime.now(timezone.utc),
            normalizer_version="1.0.0",
            ordering_key="test-key"
        )
        
        # Normalize canonical input
        normalized_output = self.audit_normalizer.normalize_audit_record(canonical_input)
        
        # Verify passthrough behavior (most fields preserved)
        assert normalized_output.audit_id == canonical_input.audit_id
        assert normalized_output.tenant_id == canonical_input.tenant_id
        assert normalized_output.event_kind == canonical_input.event_kind
        assert normalized_output.event_category == canonical_input.event_category
        assert normalized_output.event_severity == canonical_input.event_severity
        assert normalized_output.payload_ref == canonical_input.payload_ref
        assert normalized_output.source_format == "canonical"
        assert normalized_output.ordering_key == canonical_input.ordering_key
        
        # Verify normalization metadata is updated
        assert normalized_output.normalizer_version == "1.0.0"
        # Use timestamp comparison that works with timezone-aware datetimes
        assert normalized_output.normalized_at.replace(tzinfo=None) >= canonical_input.normalized_at.replace(tzinfo=None)
    
    def test_normalizer_event_category_normalization(self):
        """Test event category normalization logic"""
        # Test different event kinds
        test_cases = [
            ("telemetry_ingested", "ingestion"),
            ("local_decision_generated", "decision"),
            ("belief_generated", "reasoning"),
            ("collective_state_computed", "aggregation"),
            ("safety_gate_evaluated", "safety"),
            ("execution_intent_created", "execution"),
            ("action_executed", "execution"),
            ("approval_requested", "approval"),
            ("approval_granted", "approval"),
            ("approval_denied", "approval"),
            ("unknown_event", "other")
        ]
        
        for event_kind, expected_category in test_cases:
            record = AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345678",
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                idempotency_key="abc123",
                recorded_at=datetime.now(timezone.utc),
                event_kind=event_kind,
                payload_ref={},
                hashes={},
                correlation_id="corr-123",
                trace_id="trace-123"
            )
            
            canonical = self.audit_normalizer.normalize_audit_record(record)
            assert canonical.event_category == expected_category, f"Failed for {event_kind}"
    
    def test_normalizer_event_severity_normalization(self):
        """Test event severity normalization logic"""
        # Test severity extraction from payload
        record_with_severity = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={"severity": "high"},
            hashes={},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        canonical = self.audit_normalizer.normalize_audit_record(record_with_severity)
        assert canonical.event_severity == "high"
        
        # Test default severity based on event kind
        high_severity_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="action_executed",
            payload_ref={},
            hashes={},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        canonical = self.audit_normalizer.normalize_audit_record(high_severity_record)
        assert canonical.event_severity == "high"
    
    def test_normalizer_event_timestamp_extraction(self):
        """Test event timestamp extraction from payload"""
        record_with_timestamp = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={
                "observed_at": "2024-01-01T12:00:00Z",
                "other_field": "value"
            },
            hashes={},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        canonical = self.audit_normalizer.normalize_audit_record(record_with_timestamp)
        assert canonical.event_timestamp is not None
        assert canonical.event_timestamp.year == 2024
        assert canonical.event_timestamp.month == 1
        assert canonical.event_timestamp.day == 1
    
    def test_normalizer_safe_fallback_on_error(self):
        """Test that normalizer provides safe fallback on errors"""
        # Create a valid record but mock the internal normalization to fail
        valid_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={},
            hashes={},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        # Mock the internal normalization to fail
        with pytest.MonkeyPatch().context() as m:
            def mock_normalize(*args, **kwargs):
                raise Exception("Simulated failure")
            
            m.setattr(self.audit_normalizer, '_normalize_from_v1', mock_normalize)
            
            # Should still return a safe fallback envelope
            canonical = self.audit_normalizer.normalize_audit_record(valid_record)
            
            assert isinstance(canonical, CanonicalAuditEnvelope)
            assert canonical.audit_id == valid_record.audit_id
            assert canonical.event_category == 'unknown'
            assert canonical.event_severity == 'low'
            assert canonical.canonical_hashes == {'fallback': True}
    
    def test_normalizer_batch_normalization_preserves_ordering(self):
        """Test batch normalization preserves input ordering"""
        # Create mixed format records
        v1_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={},
            hashes={},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        canonical_record = CanonicalAuditEnvelope(
            audit_id="01J4NR5X9Z8GABCDEF12345679",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            correlation_id="corr-123",
            trace_id="trace-123",
            recorded_at=datetime(2024, 1, 1, 12, 0, 2, tzinfo=timezone.utc),
            event_timestamp=datetime(2024, 1, 1, 12, 0, 2, tzinfo=timezone.utc),
            event_kind="local_decision_generated",
            event_category="decision",
            event_severity="medium",
            payload_ref={},
            source_format="canonical",
            source_hashes={},
            canonical_hashes={},
            normalized_at=datetime.now(timezone.utc),
            normalizer_version="1.0.0",
            ordering_key="2024-01-01T12:00:02+00:00_01J4NR5X9Z8GABCDEF12345679"
        )
        
        # Batch normalize with mixed input
        input_records = [v1_record, canonical_record]
        normalized_records = self.audit_normalizer.batch_normalize(input_records, preserve_ordering=True)
        
        # Verify output ordering matches input ordering
        assert len(normalized_records) == 2
        assert normalized_records[0].audit_id == v1_record.audit_id
        assert normalized_records[1].audit_id == canonical_record.audit_id
        
        # Verify ordering keys are preserved
        assert normalized_records[0].ordering_key.startswith("2024-01-01T12:00:01")
        assert normalized_records[1].ordering_key.startswith("2024-01-01T12:00:02")
    
    def test_normalizer_format_detection(self):
        """Test format detection functionality"""
        # Test V1 format detection
        assert not self.audit_normalizer.is_canonical_format(self.sample_v1_record)
        
        # Test canonical format detection
        canonical_envelope = self.audit_normalizer.normalize_audit_record(self.sample_v1_record)
        assert self.audit_normalizer.is_canonical_format(canonical_envelope)
    
    def test_normalizer_no_mutation_of_stored_data(self):
        """Test that normalizer never mutates stored data structures"""
        # Create a record with complex nested data
        complex_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            idempotency_key="abc123",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={
                "nested": {
                    "deep": {
                        "value": "test",
                        "array": [1, 2, 3]
                    }
                }
            },
            hashes={"complex": "hash"},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        # Store original payload reference
        original_payload = complex_record.payload_ref.copy()
        
        # Normalize multiple times
        for _ in range(10):
            canonical = self.audit_normalizer.normalize_audit_record(complex_record)
            assert canonical.payload_ref == original_payload
        
        # Verify original record is unchanged
        assert complex_record.payload_ref == original_payload
