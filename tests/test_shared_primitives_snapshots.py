"""
Schema Snapshot Tests for Shared Primitives
Ensures contract stability for ExoArmur expansions
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import ulid
from pydantic import ValidationError

from spec.contracts.shared_primitives_v1 import (
    BeliefDeltaV1,
    ConflictV1,
    EvidenceRefV1,
    FindingV1,
    HypothesisV1,
    NarrativeV1,
    TimelineEventV1,
    TimelineV1,
)


class TestSharedPrimitivesSnapshots:
    """Test schema snapshots for shared primitives"""
    
    def test_evidence_ref_v1_schema_snapshot(self):
        """EvidenceRefV1 schema should be stable"""
        schema = EvidenceRefV1.model_json_schema()
        
        # Critical schema assertions
        assert schema['type'] == 'object'
        assert schema['properties']['schema_version']['default'] == '1.0.0'
        assert schema['properties']['evidence_type']['enum'] == ['telemetry', 'belief', 'external', 'derived']
        assert 'evidence_id' in schema['required']
        assert 'evidence_type' in schema['required']
        assert 'source_id' in schema['required']
        assert 'hash_sha256' in schema['required']
        
        # Test with valid data
        evidence = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        # Verify serialization is deterministic
        serialized = evidence.model_dump_json()
        parsed = json.loads(serialized)
        assert parsed['schema_version'] == '1.0.0'
        assert parsed['evidence_type'] == 'telemetry'
    
    def test_belief_delta_v1_schema_snapshot(self):
        """BeliefDeltaV1 schema should be stable"""
        schema = BeliefDeltaV1.model_json_schema()
        
        assert schema['properties']['delta_type']['enum'] == ['create', 'reinforce', 'decay', 'contradict']
        assert schema['properties']['confidence_delta']['type'] == 'number'
        assert schema['properties']['new_confidence']['minimum'] == 0.0
        assert schema['properties']['new_confidence']['maximum'] == 1.0
        assert 'evidence_refs' in schema['required']
        
        # Test with valid evidence refs
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        delta = BeliefDeltaV1(
            delta_id=str(ulid.ULID()),
            belief_id=str(ulid.ULID()),
            delta_type="reinforce",
            confidence_delta=0.1,
            new_confidence=0.8,
            evidence_refs=[evidence_ref],
            reason="Additional evidence supports belief",
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        assert delta.confidence_delta == 0.1
        assert delta.new_confidence == 0.8
        assert len(delta.evidence_refs) == 1
    
    def test_hypothesis_v1_schema_snapshot(self):
        """HypothesisV1 schema should be stable"""
        schema = HypothesisV1.model_json_schema()
        
        assert schema['properties']['hypothesis_type']['enum'] == ['threat', 'pattern', 'causal', 'correlation']
        assert schema['properties']['confidence_score']['minimum'] == 0.0
        assert schema['properties']['confidence_score']['maximum'] == 1.0
        assert 'supporting_evidence' in schema['required']
        assert 'testable_prediction' in schema['required']
        assert 'falsifiable_criteria' in schema['required']
        
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        hypothesis = HypothesisV1(
            hypothesis_id=str(ulid.ULID()),
            title="Lateral Movement Detection",
            description="System detects potential lateral movement",
            hypothesis_type="threat",
            confidence_score=0.75,
            supporting_evidence=[evidence_ref],
            testable_prediction="Additional auth failures will occur",
            falsifiable_criteria=["No further auth failures", "Benign activity confirmed"],
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        assert hypothesis.confidence_score == 0.75
        assert len(hypothesis.supporting_evidence) == 1
    
    def test_narrative_v1_schema_snapshot(self):
        """NarrativeV1 schema should be stable"""
        schema = NarrativeV1.model_json_schema()
        
        assert schema['properties']['narrative_type']['enum'] == ['threat_assessment', 'incident_timeline', 'pattern_analysis', 'conclusion']
        assert schema['properties']['confidence_level']['enum'] == ['low', 'medium', 'high']
        assert 'supporting_hypotheses' in schema['required']
        assert 'evidence_citations' in schema['required']
        
        # Test narrative requires hypotheses and evidence
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        hypothesis = HypothesisV1(
            hypothesis_id=str(ulid.ULID()),
            title="Test Hypothesis",
            description="Test description",
            hypothesis_type="threat",
            confidence_score=0.8,
            supporting_evidence=[evidence_ref],
            testable_prediction="Test prediction",
            falsifiable_criteria=["Test criteria"],
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        narrative = NarrativeV1(
            narrative_id=str(ulid.ULID()),
            title="Security Incident Analysis",
            summary="Analysis of potential security incident",
            detailed_analysis="Detailed analysis with evidence citations",
            narrative_type="threat_assessment",
            confidence_level="high",
            key_findings=["Suspicious activity detected"],
            supporting_hypotheses=[hypothesis],
            evidence_citations=[evidence_ref],
            analyst_confidence=0.85,
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        assert narrative.confidence_level == "high"
        assert len(narrative.supporting_hypotheses) == 1
        assert len(narrative.evidence_citations) == 1
    
    def test_finding_v1_schema_snapshot(self):
        """FindingV1 schema should be stable"""
        schema = FindingV1.model_json_schema()
        
        assert schema['properties']['finding_type']['enum'] == ['vulnerability', 'compromise', 'anomaly', 'pattern', 'risk']
        assert schema['properties']['severity']['enum'] == ['low', 'medium', 'high', 'critical']
        assert 'evidence_refs' in schema['required']
        assert 'affected_entities' in schema['required']
        
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        finding = FindingV1(
            finding_id=str(ulid.ULID()),
            title="Suspicious Login Activity",
            description="Multiple failed login attempts detected",
            finding_type="anomaly",
            severity="medium",
            confidence=0.7,
            evidence_refs=[evidence_ref],
            affected_entities=["user_123", "host_456"],
            impact_assessment="Potential credential stuffing attack",
            mitigation_suggestions=["Enable MFA", "Review access logs"],
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        assert finding.severity == "medium"
        assert len(finding.affected_entities) == 2
    
    def test_timeline_event_v1_schema_snapshot(self):
        """TimelineEventV1 schema should be stable"""
        schema = TimelineEventV1.model_json_schema()
        
        assert schema['properties']['timestamp_precision']['enum'] == ['exact', 'estimated', 'bounded']
        assert 'evidence_refs' in schema['required']
        assert 'entities_involved' in schema['required']
        
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        event = TimelineEventV1(
            event_id=str(ulid.ULID()),
            timestamp_utc=datetime.now(timezone.utc),
            timestamp_precision="exact",
            event_type="authentication_failure",
            description="Failed login attempt",
            entities_involved=["user_123", "host_456"],
            evidence_refs=[evidence_ref],
            confidence=0.9
        )
        
        assert event.timestamp_precision == "exact"
        assert len(event.entities_involved) == 2
    
    def test_timeline_v1_schema_snapshot(self):
        """TimelineV1 schema should be stable"""
        schema = TimelineV1.model_json_schema()
        
        assert 'events' in schema['required']
        assert 'time_bounds' in schema['required']
        assert 'subject_entity' in schema['required']
        
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        event = TimelineEventV1(
            event_id=str(ulid.ULID()),
            timestamp_utc=datetime.now(timezone.utc),
            timestamp_precision="exact",
            event_type="authentication_failure",
            description="Failed login attempt",
            entities_involved=["user_123"],
            evidence_refs=[evidence_ref],
            confidence=0.9
        )
        
        timeline = TimelineV1(
            timeline_id=str(ulid.ULID()),
            title="User Activity Timeline",
            description="Timeline of user authentication events",
            subject_entity="user_123",
            time_bounds={
                "start": datetime.now(timezone.utc),
                "end": datetime.now(timezone.utc)
            },
            events=[event],
            confidence_score=0.85,
            completeness_estimate=0.7,
            generated_at_utc=datetime.now(timezone.utc)
        )
        
        assert len(timeline.events) == 1
        assert timeline.subject_entity == "user_123"
    
    def test_conflict_v1_schema_snapshot(self):
        """ConflictV1 schema should be stable"""
        schema = ConflictV1.model_json_schema()
        
        assert schema['properties']['conflict_type']['enum'] == ['timestamp', 'evidence', 'interpretation', 'completeness']
        assert schema['properties']['resolution_status']['enum'] == ['unresolved', 'resolved', 'accepted_uncertainty']
        assert 'conflicting_items' in schema['required']
        assert 'evidence_refs' in schema['required']
        
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        conflict = ConflictV1(
            conflict_id=str(ulid.ULID()),
            conflict_type="timestamp",
            description="Conflicting timestamps between evidence sources",
            conflicting_items=[
                {"source": "logs", "timestamp": "2024-01-01T10:00:00Z"},
                {"source": "sensor", "timestamp": "2024-01-01T10:05:00Z"}
            ],
            evidence_refs=[evidence_ref],
            resolution_status="unresolved",
            uncertainty_bounds={"skew_seconds": 300},
            impact_assessment="5-minute timestamp skew affects event ordering",
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        assert conflict.conflict_type == "timestamp"
        assert len(conflict.conflicting_items) == 2
        assert conflict.resolution_status == "unresolved"
    
    def test_all_primitives_enforce_strict_validation(self):
        """All primitives should enforce strict validation"""
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        # Test that extra fields are forbidden
        with pytest.raises(ValidationError) as exc_info:
            EvidenceRefV1(
                evidence_id=str(ulid.ULID()),
                evidence_type="telemetry",
                source_id="event_123",
                tenant_id="tenant_demo",
                timestamp_utc=datetime.now(timezone.utc),
                hash_sha256="abc123",
                extra_field="not_allowed"  # This should cause validation error
            )
        
        assert "extra" in str(exc_info.value).lower()
    
    def test_ulid_validation_enforced(self):
        """ULID validation should be enforced"""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceRefV1(
                evidence_id="invalid-ulid",
                evidence_type="telemetry",
                source_id="event_123",
                tenant_id="tenant_demo",
                timestamp_utc=datetime.now(timezone.utc),
                hash_sha256="abc123"
            )
        
        assert "ulid" in str(exc_info.value).lower()
    
    def test_serialization_determinism(self):
        """JSON serialization should be deterministic"""
        evidence_ref = EvidenceRefV1(
            evidence_id=str(ulid.ULID()),
            evidence_type="telemetry",
            source_id="event_123",
            tenant_id="tenant_demo",
            timestamp_utc=datetime.now(timezone.utc),
            hash_sha256="abc123"
        )
        
        # Serialize multiple times and ensure consistency
        json1 = evidence_ref.model_dump_json()
        json2 = evidence_ref.model_dump_json()
        
        assert json1 == json2
        
        # Verify it's valid JSON
        parsed = json.loads(json1)
        assert parsed['schema_version'] == '1.0.0'
        assert parsed['evidence_type'] == 'telemetry'
