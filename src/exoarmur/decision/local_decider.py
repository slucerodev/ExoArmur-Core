"""
Local decision generation from signal facts
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

import sys
import os
from spec.contracts.models_v1 import SignalFactsV1, LocalDecisionV1

logger = logging.getLogger(__name__)


class LocalDecider:
    """Generates local decisions from signal facts"""
    
    def decide(self, facts: SignalFactsV1) -> LocalDecisionV1:
        """Generate local decision from signal facts"""
        logger.info(f"Generating local decision from facts {facts.facts_id}")
        
        # Minimal heuristic scoring
        severity_score = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 0.95}
        confidence = severity_score.get(facts.features.get("severity", "low"), 0.2)
        
        classification = "benign"
        if confidence >= 0.8:
            classification = "malicious"
        elif confidence >= 0.5:
            classification = "suspicious"
        
        decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",  # TODO: generate ULID
            tenant_id=facts.tenant_id,
            cell_id=facts.cell_id,
            subject=facts.subject,
            classification=classification,
            severity=facts.features.get("severity", "low"),
            confidence=confidence,
            recommended_intents=[],
            evidence_refs={
                "event_ids": facts.derived_from_event_ids,
                "feature_hashes": ["hash-1"]  # TODO: compute actual hash
            },
            correlation_id=facts.correlation_id,
            trace_id=facts.trace_id
        )
        
        return decision
