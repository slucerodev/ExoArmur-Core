"""
Test factories for creating valid model instances
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from spec.contracts.models_v1 import (
    IdentitySubjectV1, 
    ObservationV1, 
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1,
    AnomalyDetectionPayloadV1,
    SystemHealthPayloadV1,
    NetworkActivityPayloadV1
)


def create_identity_subject(
    subject_id: str = "test-user",
    subject_type: str = "USER",
    tenant_id: str = "tenant_test",
    provider: str = "okta",
    last_activity_utc: datetime = None,
    **metadata
) -> IdentitySubjectV1:
    """Create a valid IdentitySubjectV1 instance with required fields"""
    if last_activity_utc is None:
        last_activity_utc = datetime(2026, 1, 23, 18, 0, 0, tzinfo=timezone.utc)
    
    # Move provider to metadata since it's not allowed as a direct field
    all_metadata = {"provider": provider}
    all_metadata.update(metadata)
    
    return IdentitySubjectV1(
        subject_id=subject_id,
        subject_type=subject_type,
        tenant_id=tenant_id,
        last_activity_utc=last_activity_utc,
        metadata=all_metadata
    )


def make_observation_v1(
    observation_type: ObservationType = ObservationType.TELEMETRY_SUMMARY,
    observation_id: str = "01J4NR5X9Z8GABCDEF12345678",
    source_federate_id: str = "test-federate",
    correlation_id: str = "test-corr",
    confidence: float = 0.9,
    evidence_refs: List[str] = None,
    timestamp_utc: datetime = None,
    **payload_overrides
) -> ObservationV1:
    """Create a valid ObservationV1 instance with proper payload"""
    if timestamp_utc is None:
        timestamp_utc = datetime(2026, 1, 23, 18, 0, 0, tzinfo=timezone.utc)
    
    if evidence_refs is None:
        evidence_refs = []
    
    # Create appropriate payload based on observation type
    if observation_type == ObservationType.TELEMETRY_SUMMARY:
        payload = TelemetrySummaryPayloadV1(
            payload_type="telemetry_summary",
            data={"summary": "telemetry summary data"},
            event_count=payload_overrides.get("event_count", 10),
            time_window_seconds=payload_overrides.get("time_window_seconds", 300),
            event_types=payload_overrides.get("event_types", ["process_start", "file_access"]),
            severity_distribution=payload_overrides.get("severity_distribution", {"low": 5, "medium": 3, "high": 2})
        )
    elif observation_type == ObservationType.THREAT_INTEL:
        payload = ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={"threat_data": "threat intelligence data"},
            ioc_count=payload_overrides.get("ioc_count", 5),
            threat_types=payload_overrides.get("threat_types", ["malware", "c2"]),
            confidence_score=payload_overrides.get("confidence_score", 0.8),
            sources=payload_overrides.get("sources", ["virustotal", "crowdstrike"])
        )
    elif observation_type == ObservationType.ANOMALY_DETECTION:
        payload = AnomalyDetectionPayloadV1(
            payload_type="anomaly_detection",
            data={"anomaly_data": "anomaly detection data"},
            anomaly_score=payload_overrides.get("anomaly_score", 0.7),
            affected_entities=payload_overrides.get("affected_entities", ["host-001", "user-001"]),
            anomaly_type=payload_overrides.get("anomaly_type", "behavioral"),
            baseline_deviation=payload_overrides.get("baseline_deviation", 0.3)
        )
    elif observation_type == ObservationType.SYSTEM_HEALTH:
        payload = SystemHealthPayloadV1(
            payload_type="system_health",
            data={"health_data": "system health data"},
            cpu_utilization=payload_overrides.get("cpu_utilization", 45.2),
            memory_utilization=payload_overrides.get("memory_utilization", 67.8),
            disk_utilization=payload_overrides.get("disk_utilization", 23.1),
            network_latency_ms=payload_overrides.get("network_latency_ms", 12.5),
            service_status=payload_overrides.get("service_status", {"web": "healthy", "db": "healthy"})
        )
    elif observation_type == ObservationType.NETWORK_ACTIVITY:
        payload = NetworkActivityPayloadV1(
            payload_type="network_activity",
            data={"network_data": "network activity data"},
            connection_count=payload_overrides.get("connection_count", 150),
            bytes_transferred=payload_overrides.get("bytes_transferred", 1048576),
            top_protocols=payload_overrides.get("top_protocols", ["http", "https", "dns"]),
            suspicious_ips=payload_overrides.get("suspicious_ips", ["192.168.1.100"])
        )
    else:
        raise ValueError(f"Unsupported observation type: {observation_type}")
    
    return ObservationV1(
        schema_version="2.0.0",
        observation_id=observation_id,
        source_federate_id=source_federate_id,
        timestamp_utc=timestamp_utc,
        correlation_id=correlation_id,
        observation_type=observation_type,
        confidence=confidence,
        evidence_refs=evidence_refs,
        payload=payload
    )
