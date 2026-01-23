"""
Unit tests for idempotency enforcement
"""

import pytest
from datetime import datetime

from src.execution.execution_kernel import ExecutionKernel

# Import contract models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))
from models_v1 import LocalDecisionV1, ExecutionIntentV1


class TestIdempotency:
    """Test idempotency enforcement in execution kernel"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.execution_kernel = ExecutionKernel()
        
        # Create test local decision
        self.local_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="malicious",
            severity="high",
            confidence=0.9,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        # Mock safety verdict
        class MockSafetyVerdict:
            def __init__(self):
                self.verdict = "allow"
                self.rationale = "Test allow"
                self.rule_ids = ["SG-401"]
        
        self.safety_verdict = MockSafetyVerdict()
    
    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key_does_not_reexecute(self):
        """Test that duplicate idempotency_key does not re-execute (idempotency test)"""
        idempotency_key = "test-idempotency-key-123"
        
        # Create execution intent
        intent = self.execution_kernel.create_execution_intent(
            local_decision=self.local_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key=idempotency_key
        )
        
        # Execute intent first time
        result1 = await self.execution_kernel.execute_intent(intent)
        assert result1 is True
        
        # Check that intent was recorded as executed
        assert idempotency_key in self.execution_kernel.executed_intents
        
        # Execute intent second time with same idempotency key
        result2 = await self.execution_kernel.execute_intent(intent)
        assert result2 is True  # Should still return True
        
        # Verify that the same intent object is stored (no new execution)
        stored_intent = self.execution_kernel.executed_intents[idempotency_key]
        assert stored_intent.intent_id == intent.intent_id
    
    @pytest.mark.asyncio
    async def test_different_idempotency_keys_execute_independently(self):
        """Test that different idempotency keys execute independently"""
        idempotency_key_1 = "test-idempotency-key-1"
        idempotency_key_2 = "test-idempotency-key-2"
        
        # Create first intent
        intent1 = self.execution_kernel.create_execution_intent(
            local_decision=self.local_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key=idempotency_key_1
        )
        
        # Create second intent
        intent2 = self.execution_kernel.create_execution_intent(
            local_decision=self.local_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key=idempotency_key_2
        )
        
        # Execute both intents
        result1 = await self.execution_kernel.execute_intent(intent1)
        result2 = await self.execution_kernel.execute_intent(intent2)
        
        assert result1 is True
        assert result2 is True
        
        # Verify both are stored separately
        assert idempotency_key_1 in self.execution_kernel.executed_intents
        assert idempotency_key_2 in self.execution_kernel.executed_intents
        assert len(self.execution_kernel.executed_intents) == 2
    
    def test_execution_intent_creation(self):
        """Test execution intent creation with proper fields"""
        idempotency_key = "test-idempotency-key-123"
        
        intent = self.execution_kernel.create_execution_intent(
            local_decision=self.local_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key=idempotency_key
        )
        
        # Verify required fields
        assert intent.schema_version == "1.0.0"
        assert intent.intent_id is not None
        assert intent.tenant_id == self.local_decision.tenant_id
        assert intent.cell_id == self.local_decision.cell_id
        assert intent.idempotency_key == idempotency_key
        assert intent.subject == self.local_decision.subject
        assert intent.correlation_id == self.local_decision.correlation_id
        assert intent.trace_id == self.local_decision.trace_id
        
        # Verify safety context
        assert intent.safety_context["safety_verdict"] == self.safety_verdict.verdict
        assert intent.safety_context["rationale"] == self.safety_verdict.rationale
        
        # Verify action class based on classification
        assert intent.action_class in ["A0_observe", "A1_soft_containment", "A2_hard_containment"]
    
    def test_execution_intent_action_class_mapping(self):
        """Test action class mapping from decision classification"""
        # Test benign classification
        benign_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="benign",
            severity="low",
            confidence=0.1,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        intent = self.execution_kernel.create_execution_intent(
            local_decision=benign_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key="test-key"
        )
        
        assert intent.action_class == "A0_observe"
        
        # Test suspicious classification
        suspicious_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="suspicious",
            severity="medium",
            confidence=0.6,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        intent = self.execution_kernel.create_execution_intent(
            local_decision=suspicious_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key="test-key"
        )
        
        assert intent.action_class == "A1_soft_containment"
        
        # Test malicious classification
        malicious_decision = LocalDecisionV1(
            schema_version="1.0.0",
            decision_id="01J4NR5X9Z8GABCDEF12345678",
            tenant_id="tenant-acme",
            cell_id="cell-okc-01",
            subject={"subject_type": "host", "subject_id": "host-123"},
            classification="malicious",
            severity="high",
            confidence=0.9,
            recommended_intents=[],
            evidence_refs={"event_ids": ["event-1"]},
            correlation_id="corr-123",
            trace_id="trace-123"
        )
        
        intent = self.execution_kernel.create_execution_intent(
            local_decision=malicious_decision,
            safety_verdict=self.safety_verdict,
            idempotency_key="test-key"
        )
        
        assert intent.action_class == "A2_hard_containment"
