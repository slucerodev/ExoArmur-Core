"""
Execution kernel with idempotency enforcement
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
from models_v1 import LocalDecisionV1, ExecutionIntentV1

logger = logging.getLogger(__name__)


class ExecutionKernel:
    """Execution kernel for ADMO intents"""
    
    def __init__(self, nats_client: Optional[Any] = None, approval_service: Optional[Any] = None, intent_store: Optional[Any] = None):
        self.nats_client = nats_client
        self.approval_service = approval_service
        self.intent_store = intent_store
        self.executed_intents: Dict[str, ExecutionIntentV1] = {}  # Simple idempotency cache
        
        logger.info("ExecutionKernel initialized")
    
    def create_execution_intent(
        self,
        local_decision: LocalDecisionV1,
        safety_verdict,
        idempotency_key: str
    ) -> ExecutionIntentV1:
        """Create execution intent from local decision and safety verdict"""
        logger.info(f"Creating execution intent for decision {local_decision.decision_id}")
        
        # Determine action class from safety verdict and local decision
        action_class = "A0_observe"  # Default
        if safety_verdict.verdict == "allow":
            if local_decision.classification == "malicious":
                action_class = "A2_hard_containment"
            elif local_decision.classification == "suspicious":
                action_class = "A1_soft_containment"
        
        intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id="01J4NR5X9Z8GABCDEF12345678",  # TODO: generate ULID
            tenant_id=local_decision.tenant_id,
            cell_id=local_decision.cell_id,
            idempotency_key=idempotency_key,
            subject=local_decision.subject,
            intent_type="isolate_host",  # TODO: derive from decision
            action_class=action_class,
            requested_at=datetime.utcnow(),
            parameters={"isolation_type": "network"},  # TODO: derive from decision
            policy_context={
                "bundle_hash_sha256": "abc123...",  # TODO: get actual bundle
                "rule_ids": ["rule-1"]
            },
            safety_context={
                "safety_verdict": safety_verdict.verdict,
                "rationale": safety_verdict.rationale,
                "quorum_status": "satisfied",  # TODO: compute actual status
                "human_approval_id": None
            },
            correlation_id=local_decision.correlation_id,
            trace_id=local_decision.trace_id
        )
        
        return intent
    
    async def execute_intent(self, intent: ExecutionIntentV1) -> bool:
        """Execute intent with idempotency enforcement"""
        logger.info(f"Executing intent {intent.intent_id}")
        
        # Check approval requirement for A1/A2/A3 actions
        if intent.action_class in ["A1_soft_containment", "A2_hard_containment", "A3_irreversible"]:
            approval_id = intent.safety_context.get("human_approval_id")
            
            if not approval_id:
                logger.warning(f"Execution blocked: intent {intent.intent_id} requires approval but none provided")
                return False
            
            # Verify approval is APPROVED and bound to this intent
            if not self._verify_approval_for_intent(intent, approval_id):
                logger.warning(f"Execution blocked: intent {intent.intent_id} approval verification failed")
                return False
        
        # A0_observe always allowed
        if intent.action_class == "A0_observe":
            pass  # Continue with execution
        
        # Check idempotency
        if intent.idempotency_key in self.executed_intents:
            logger.info(f"Intent {intent.intent_id} already executed (idempotency_key: {intent.idempotency_key})")
            return True
        
        # No-op execution for thin vertical slice
        logger.info(f"No-op execution for intent {intent.intent_id} (action_class: {intent.action_class})")
        
        # Record as executed
        self.executed_intents[intent.idempotency_key] = intent
        
        return True
    
    def _verify_approval_for_intent(self, intent: ExecutionIntentV1, approval_id: str) -> bool:
        """Verify that approval is APPROVED and bound to this specific intent"""
        if not self.approval_service or not self.intent_store:
            logger.error("Approval service or intent store not available for verification")
            return False
        
        # Check approval status
        try:
            status = self.approval_service.get_status(approval_id)
            if status != "APPROVED":
                logger.warning(f"Approval {approval_id} status is {status}, not APPROVED")
                return False
        except ValueError as e:
            logger.warning(f"Approval {approval_id} not found: {e}")
            return False
        
        # Verify intent binding matches
        if not self.intent_store.verify_intent_binding(approval_id, intent):
            logger.warning(f"Intent binding verification failed for approval {approval_id}")
            return False
        
        logger.info(f"Approval verification passed for intent {intent.intent_id}")
        return True
