"""
Phase 2A Threat Classification Test Fixtures
Synthetic threat events for deterministic testing
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from exoarmur.decision.threat_classification_v2 import ThreatEventV2


@pytest.fixture
def synthetic_threat_events() -> Dict[str, ThreatEventV2]:
    """Synthetic threat events for comprehensive testing"""
    return {
        "malware_high_risk": ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AB",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 2, 0, 0, tzinfo=timezone.utc),  # Unusual time
            threat_type="malware",
            severity="critical",
            confidence_score=0.9,
            source_ip="192.0.2.100",  # Known bad IP
            target_asset="database_primary",
            indicators=["malware_hash_abc123", "c2_domain_evil.com"],
            correlation_id="corr_malware_001",
            trace_id="trace_malware_001"
        ),
        
        "phishing_medium_risk": ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AC",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),  # Business hours
            threat_type="phishing",
            severity="medium",
            confidence_score=0.6,
            source_ip="203.0.113.50",  # External IP
            target_asset="web_server_01",
            indicators=["phishing_url_suspicious.com"],
            correlation_id="corr_phishing_001",
            trace_id="trace_phishing_001"
        ),
        
        "anomaly_low_risk": ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AD",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),  # Business hours
            threat_type="anomaly",
            severity="low",
            confidence_score=0.2,
            source_ip="10.0.1.50",  # Internal IP
            target_asset="workstation_001",
            indicators=["unusual_login_pattern"],
            correlation_id="corr_anomaly_001",
            trace_id="trace_anomaly_001"
        ),
        
        "command_control_high_risk": ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AE",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 3, 0, 0, tzinfo=timezone.utc),  # Unusual time
            threat_type="command_control",
            severity="high",
            confidence_score=0.8,
            source_ip="192.0.2.200",  # Known bad IP
            target_asset="controller_primary",
            indicators=["c2_beacon", "encrypted_traffic"],
            correlation_id="corr_c2_001",
            trace_id="trace_c2_001"
        ),
        
        "data_exfiltration_critical": ThreatEventV2(
            event_id="01H8X9YZABCDEF1234567890AF",
            tenant_id="tenant_test",
            cell_id="cell_test_01",
            observed_at=datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),  # Unusual time
            threat_type="data_exfiltration",
            severity="critical",
            confidence_score=0.95,
            source_ip="192.0.2.150",  # Known bad IP
            target_asset="file_server_sensitive",
            indicators=["large_data_transfer", "suspicious_destination"],
            correlation_id="corr_exfil_001",
            trace_id="trace_exfil_001"
        )
    }


@pytest.fixture
def expected_classifications() -> Dict[str, str]:
    """Expected classifications for synthetic threat events"""
    return {
        "malware_high_risk": "ESCALATE",
        "phishing_medium_risk": "SIMULATE", 
        "anomaly_low_risk": "IGNORE",
        "command_control_high_risk": "ESCALATE",
        "data_exfiltration_critical": "ESCALATE"
    }


@pytest.fixture
def expected_authority_tiers() -> Dict[str, str]:
    """Expected authority tiers for synthetic threat events"""
    return {
        "malware_high_risk": "T1_SOFT_CONTAINMENT",
        "phishing_medium_risk": "T1_SOFT_CONTAINMENT",
        "anomaly_low_risk": "T0_OBSERVE",
        "command_control_high_risk": "T1_SOFT_CONTAINMENT", 
        "data_exfiltration_critical": "T1_SOFT_CONTAINMENT"
    }


@pytest.fixture
def expected_authorization_results() -> Dict[str, str]:
    """Expected authorization results for synthetic threat events"""
    return {
        "malware_high_risk": "REQUIRE_APPROVAL",
        "phishing_medium_risk": "ALLOW_AUTO",
        "anomaly_low_risk": "ALLOW_AUTO",
        "command_control_high_risk": "REQUIRE_APPROVAL",
        "data_exfiltration_critical": "REQUIRE_APPROVAL"
    }