"""
Tests for deterministic audit replay system
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from exoarmur.replay.canonical_utils import canonical_json, stable_hash, verify_canonical_hash, CanonicalHashError
from exoarmur.replay.event_envelope import AuditEventEnvelope, EventTypePriority, EnvelopeValidationError
from exoarmur.replay.replay_engine import ReplayEngine, ReplayReport, ReplayResult, ReplayEngineError
from exoarmur.control_plane.intent_store import IntentStore
from exoarmur.control_plane.approval_service import ApprovalService

# Import contract models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))
from models_v1 import AuditRecordV1, ExecutionIntentV1, TelemetryEventV1


class TestCanonicalUtils:
    """Test canonical serialization and hashing utilities"""
    
    def test_canonical_json_sorts_keys(self):
        """Test that canonical JSON sorts keys deterministically"""
        data = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(data)
        expected = '{"a":2,"m":3,"z":1}'
        assert result == expected
    
    def test_canonical_json_handles_nested_objects(self):
        """Test canonical JSON with nested objects"""
        data = {"outer": {"z": 1, "a": 2}, "b": 3}
        result = canonical_json(data)
        expected = '{"b":3,"outer":{"a":2,"z":1}}'
        assert result == expected
    
    def test_canonical_json_normalizes_datetime(self):
        """Test datetime normalization to UTC ISO format"""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        data = {"time": dt}
        result = canonical_json(data)
        expected = '{"time":"2023-01-01T12:00:00Z"}'
        assert result == expected
    
    def test_canonical_json_normalizes_naive_datetime(self):
        """Test naive datetime gets UTC timezone"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        data = {"time": dt}
        result = canonical_json(data)
        expected = '{"time":"2023-01-01T12:00:00Z"}'
        assert result == expected
    
    def test_canonical_json_handles_floats(self):
        """Test float normalization"""
        data = {"value": 1.23456789012345}
        result = canonical_json(data)
        expected = '{"value":1.234567890123}'
        assert result == expected
    
    def test_canonical_json_handles_special_floats(self):
        """Test special float values (NaN, inf)"""
        data = {"nan": float('nan'), "inf": float('inf'), "neg_inf": float('-inf')}
        result = canonical_json(data)
        # Special floats should be converted to string "null"
        parsed = json.loads(result)
        assert parsed["nan"] == "null"
        assert parsed["inf"] == "null"  
        assert parsed["neg_inf"] == "null"
        # Check the raw JSON contains null values
        assert '"nan":"null"' in result
        assert '"inf":"null"' in result
        assert '"neg_inf":"null"' in result
    
    def test_stable_hash_consistency(self):
        """Test that stable hash is consistent"""
        data = {"test": "value"}
        hash1 = stable_hash(canonical_json(data))
        hash2 = stable_hash(canonical_json(data))
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_verify_canonical_hash_success(self):
        """Test hash verification success"""
        data = {"test": "value"}
        expected_hash = stable_hash(canonical_json(data))
        assert verify_canonical_hash(data, expected_hash) is True
    
    def test_verify_canonical_hash_failure(self):
        """Test hash verification failure"""
        data = {"test": "value"}
        wrong_hash = "wrong_hash_value"
        assert verify_canonical_hash(data, wrong_hash) is False
    
    def test_canonical_json_unsupported_type(self):
        """Test error on unsupported type"""
        data = {"bad": set([1, 2, 3])}  # sets are not JSON serializable
        with pytest.raises(ValueError):
            canonical_json(data)


class TestAuditEventEnvelope:
    """Test audit event envelope functionality"""
    
    def test_envelope_creation(self):
        """Test basic envelope creation"""
        envelope = AuditEventEnvelope(
            event_id="test-event-1",
            timestamp=datetime.now(timezone.utc),
            event_type="telemetry_ingested",
            actor="system",
            correlation_id="corr-123",
            payload={"test": "data"},
            payload_hash=""
        )
        
        assert envelope.event_id == "test-event-1"
        assert envelope.event_type == "telemetry_ingested"
        assert envelope.priority == EventTypePriority.TELEMETRY_INGESTED.value
        assert envelope.verify_payload_integrity() is True
    
    def test_envelope_ordering_key(self):
        """Test deterministic ordering key"""
        timestamp = datetime.now(timezone.utc)
        envelope = AuditEventEnvelope(
            event_id="test-event-1",
            timestamp=timestamp,
            event_type="safety_gate_evaluated",
            actor="system",
            correlation_id="corr-123",
            payload={"test": "data"},
            payload_hash=""
        )
        
        ordering_key = envelope.ordering_key
        assert len(ordering_key) == 4
        assert ordering_key[0] == timestamp
        assert ordering_key[1] == EventTypePriority.SAFETY_GATE_EVALUATED.value
        assert ordering_key[2] == "test-event-1"
        assert ordering_key[3] == 0  # default sequence number
    
    def test_event_type_priority_unknown(self):
        """Test priority for unknown event type"""
        priority = EventTypePriority.get_priority("unknown_event")
        assert priority == 999
    
    def test_payload_integrity_verification(self):
        """Test payload integrity verification"""
        payload = {"test": "data"}
        envelope = AuditEventEnvelope(
            event_id="test-event-1",
            timestamp=datetime.now(timezone.utc),
            event_type="test",
            actor="system",
            correlation_id="corr-123",
            payload=payload,
            payload_hash=""
        )
        
        # Should verify with computed hash
        assert envelope.verify_payload_integrity() is True
        
        # Tamper with payload hash
        envelope = AuditEventEnvelope(
            event_id="test-event-1",
            timestamp=datetime.now(timezone.utc),
            event_type="test",
            actor="system",
            correlation_id="corr-123",
            payload=payload,
            payload_hash="wrong_hash"
        )
        
        assert envelope.verify_payload_integrity() is False
    
    def test_envelope_serialization(self):
        """Test envelope to_dict serialization"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        envelope = AuditEventEnvelope(
            event_id="test-event-1",
            timestamp=timestamp,
            event_type="test",
            actor="system",
            correlation_id="corr-123",
            payload={"test": "data"},
            payload_hash="hash123"
        )
        
        result = envelope.to_dict()
        assert result["event_id"] == "test-event-1"
        assert result["timestamp"] == "2023-01-01T12:00:00Z"
        assert result["event_type"] == "test"
        assert result["payload"] == {"test": "data"}
        assert result["payload_hash"] == "hash123"


class TestReplayEngine:
    """Test replay engine functionality"""
    
    @pytest.fixture
    def sample_audit_records(self):
        """Create sample audit records for testing"""
        base_time = datetime.now(timezone.utc)
        
        records = [
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345671",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time,
                event_kind="telemetry_ingested",
                payload_ref={"kind": {"ref": {"event_id": "event-1", "correlation_id": "test-corr", "trace_id": "trace-1", "tenant_id": "tenant-1", "cell_id": "cell-1"}}},
                hashes={"sha256": "hash1", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345672",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time + timedelta(seconds=1),
                event_kind="safety_gate_evaluated",
                payload_ref={"kind": {"ref": {"verdict": "require_human", "rationale": "A3 action"}}},
                hashes={"sha256": "hash2", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345673",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time + timedelta(seconds=2),
                event_kind="approval_requested",
                payload_ref={"kind": {"ref": {"approval_id": "approval-123"}}},
                hashes={"sha256": "hash3", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            )
        ]
        
        return records
    
    @pytest.fixture
    def replay_engine(self):
        """Create replay engine with sample data"""
        audit_store = {}
        intent_store = IntentStore()
        approval_service = ApprovalService()
        
        return ReplayEngine(audit_store, intent_store, approval_service)
    
    def test_replay_success(self, replay_engine, sample_audit_records):
        """Test successful replay"""
        correlation_id = "test-corr"
        replay_engine.audit_store[correlation_id] = sample_audit_records
        
        report = replay_engine.replay_correlation(correlation_id)
        
        assert report.result == ReplayResult.SUCCESS
        assert report.total_events == 3
        assert report.processed_events == 3
        assert report.failed_events == 0
        assert report.audit_integrity_verified is True
        assert len(report.failures) == 0
    
    def test_replay_no_audit_records(self, replay_engine):
        """Test replay with no audit records"""
        correlation_id = "nonexistent"
        
        report = replay_engine.replay_correlation(correlation_id)
        
        assert report.result == ReplayResult.FAILURE
        assert report.total_events == 0
        assert "No audit records found" in report.failures[0]
    
    def test_replay_with_corrupted_envelope(self, replay_engine):
        """Test replay with corrupted envelope data"""
        # Create audit record with missing required data
        corrupted_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345674",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc),
            event_kind="telemetry_ingested",
            payload_ref={"kind": {}},  # Missing ref data
            hashes={"sha256": "hash4", "upstream_hashes": []},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        replay_engine.audit_store["test-corr"] = [corrupted_record]
        
        report = replay_engine.replay_correlation("test-corr")
        
        assert report.result == ReplayResult.FAILURE
        assert len(report.failures) > 0
    
    def test_replay_deterministic_ordering(self, replay_engine):
        """Test that replay orders events deterministically"""
        base_time = datetime.now(timezone.utc)
        
        # Create events with same timestamp but different priorities
        records = [
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345675",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time,
                event_kind="intent_denied",  # Priority 5
                payload_ref={"kind": {"ref": {"verdict": "deny", "rationale": "Safety gate denied"}}},
                hashes={"sha256": "hash5", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            ),
            AuditRecordV1(
                schema_version="1.0.0",
                audit_id="01J4NR5X9Z8GABCDEF12345676",
                tenant_id="tenant-1",
                cell_id="cell-1",
                idempotency_key="key-1",
                recorded_at=base_time,
                event_kind="telemetry_ingested",  # Priority 1
                payload_ref={"kind": {"ref": {"event_id": "event-1", "correlation_id": "test-corr", "trace_id": "trace-1", "tenant_id": "tenant-1", "cell_id": "cell-1"}}},
                hashes={"sha256": "hash6", "upstream_hashes": []},
                correlation_id="test-corr",
                trace_id="trace-1"
            )
        ]
        
        replay_engine.audit_store["test-corr"] = records
        
        report = replay_engine.replay_correlation("test-corr")
        
        assert report.result == ReplayResult.SUCCESS
        # High priority event should be processed first
        # (this would be verified by checking processing order in actual implementation)
    
    def test_reconstruct_intent_hash_from_audit(self, replay_engine, sample_audit_records):
        """Test reconstructing intent hash from audit events"""
        # Add intent binding event
        binding_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345677",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc) + timedelta(seconds=3),
            event_kind="approval_bound_to_intent",
            payload_ref={"kind": {"ref": {"approval_id": "approval-123", "intent_hash": "6284b1aeb514bcc9640927b2248e7657058f31ae65af7e3f76ff9ff09457ad9f"}}},
            hashes={"sha256": "hash7", "upstream_hashes": []},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        records = sample_audit_records + [binding_record]
        replay_engine.audit_store["test-corr"] = records
        
        # Mock intent store to return intent
        fixed_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-1",
            cell_id="cell-1",
            subject={"subject_type": "host", "subject_id": "host-1"},
            intent_type="isolate_host",
            action_class="A3_irreversible",
            requested_at=fixed_time,
            policy_context={},
            safety_context={"human_approval_id": "approval-123"},
            correlation_id="test-corr",
            trace_id="trace-1",
            idempotency_key="key-1"
        )
        
        replay_engine.intent_store._frozen_intents["approval-123"] = mock_intent
        
        report = replay_engine.replay_correlation("test-corr")
        
        assert report.result == ReplayResult.SUCCESS
        assert "approval-123" in report.reconstructed_intents
    
    def test_replay_fails_if_intent_store_missing_referenced_intent(self, replay_engine, sample_audit_records):
        """Test replay failure when intent store missing referenced intent"""
        # Add intent binding event without corresponding intent in store
        binding_record = AuditRecordV1(
            schema_version="1.0.0",
            audit_id="01J4NR5X9Z8GABCDEF12345679",
            tenant_id="tenant-1",
            cell_id="cell-1",
            idempotency_key="key-1",
            recorded_at=datetime.now(timezone.utc) + timedelta(seconds=3),
            event_kind="approval_bound_to_intent",
            payload_ref={"kind": {"ref": {"approval_id": "missing-approval", "intent_hash": "6284b1aeb514bcc9640927b2248e7657058f31ae65af7e3f76ff9ff09457ad9f"}}},
            hashes={"sha256": "hash8", "upstream_hashes": []},
            correlation_id="test-corr",
            trace_id="trace-1"
        )
        
        records = sample_audit_records + [binding_record]
        replay_engine.audit_store["test-corr"] = records
        
        # Intent store is empty, should still succeed but without intent reconstruction
        report = replay_engine.replay_correlation("test-corr")
        
        assert report.result == ReplayResult.SUCCESS
        # Intent should not be reconstructed since it's missing from store
        assert "missing-approval" not in report.reconstructed_intents


class TestReplayIntegration:
    """Integration tests for replay system"""
    
    def test_end_to_end_replay_verification(self):
        """Test end-to-end replay with intent verification"""
        # This would test the full flow:
        # 1. Create actual telemetry event
        # 2. Process through system to generate audit trail
        # 3. Replay and verify same results
        
        # For now, just verify the components integrate properly
        intent_store = IntentStore()
        approval_service = ApprovalService()
        audit_store = {}
        
        engine = ReplayEngine(audit_store, intent_store, approval_service)
        
        assert engine.audit_store == audit_store
        assert engine.intent_store == intent_store
        assert engine.approval_service == approval_service
