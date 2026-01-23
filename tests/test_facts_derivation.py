"""
Unit tests for signal facts derivation
"""

import pytest
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

from src.analysis.facts_deriver import FactsDeriver
from models_v1 import TelemetryEventV1, SignalFactsV1


class TestFactsDerivation:
    """Test signal facts derivation from telemetry events"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.facts_deriver = FactsDeriver()
        
        # Create test telemetry event
        self.telemetry_event = TelemetryEventV1(
            schema_version="1.0.0",
            event_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            observed_at=datetime.utcnow(),
            received_at=datetime.utcnow(),
            source={
                "kind": "edr",
                "name": "crowdstrike",
                "host": "sensor-01",
                "sensor_id": "sensor-123"
            },
            event_type="process_start",
            severity="high",
            attributes={
                "process_name": "malware.exe",
                "process_path": "C:\\temp\\malware.exe",
                "command_line": "malware.exe -evil"
            },
            entity_refs=None,
            correlation_id="corr-123",
            trace_id="trace-123"
        )
    
    def test_facts_derivation_shape(self):
        """Test that derived facts have correct shape and required fields"""
        facts = self.facts_deriver.derive_facts(self.telemetry_event)
        
        # Verify required fields are present
        assert facts.schema_version == "1.0.0"
        assert facts.facts_id is not None
        assert facts.derived_from_event_ids == [self.telemetry_event.event_id]
        assert facts.tenant_id == self.telemetry_event.tenant_id
        assert facts.cell_id == self.telemetry_event.cell_id
        assert facts.correlation_id == self.telemetry_event.correlation_id
        assert facts.trace_id == self.telemetry_event.trace_id
    
    def test_facts_derivation_content(self):
        """Test that facts content is derived correctly from telemetry"""
        facts = self.facts_deriver.derive_facts(self.telemetry_event)
        
        # Verify subject structure
        assert "subject_type" in facts.subject
        assert "subject_id" in facts.subject
        assert facts.subject["subject_type"] == "host"
        
        # Verify claim hints
        assert isinstance(facts.claim_hints, list)
        assert "process_anomaly" in facts.claim_hints
        
        # Verify features contain telemetry data
        assert "event_type" in facts.features
        assert "severity" in facts.features
        assert "source_kind" in facts.features
        
        assert facts.features["event_type"] == self.telemetry_event.event_type
        assert facts.features["severity"] == self.telemetry_event.severity
        assert facts.features["source_kind"] == self.telemetry_event.source["kind"]
    
    def test_facts_derivation_different_severities(self):
        """Test facts derivation with different severity levels"""
        severities = ["low", "medium", "high", "critical"]
        
        for severity in severities:
            event = TelemetryEventV1(
                schema_version="1.0.0",
                event_id="01J4NR5X9Z8GABCDEF12345678",
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                observed_at=datetime.utcnow(),
                received_at=datetime.utcnow(),
                source={"kind": "edr", "name": "test"},
                event_type="process_start",
                severity=severity,
                attributes={},
                entity_refs=None,
                correlation_id="corr-123",
                trace_id="trace-123"
            )
            
            facts = self.facts_deriver.derive_facts(event)
            assert facts.features["severity"] == severity
    
    def test_facts_derivation_different_source_kinds(self):
        """Test facts derivation with different source kinds"""
        source_kinds = ["edr", "siem", "firewall", "ids"]
        
        for source_kind in source_kinds:
            event = TelemetryEventV1(
                schema_version="1.0.0",
                event_id="01J4NR5X9Z8GABCDEF12345678",
                tenant_id="tenant-acme",
                cell_id="cell-okc-01",
                observed_at=datetime.utcnow(),
                received_at=datetime.utcnow(),
                source={"kind": source_kind, "name": "test"},
                event_type="process_start",
                severity="medium",
                attributes={},
                entity_refs=None,
                correlation_id="corr-123",
                trace_id="trace-123"
            )
            
            facts = self.facts_deriver.derive_facts(event)
            assert facts.features["source_kind"] == source_kind
