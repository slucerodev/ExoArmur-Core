"""
Execution kernel with idempotency enforcement
Phase 5: Added execution gate enforcement for all side effects.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
import os
import ulid
from spec.contracts.models_v1 import LocalDecisionV1, ExecutionIntentV1
from exoarmur.clock import deterministic_timestamp
from exoarmur.audit.audit_logger import compute_idempotency_key
from exoarmur.replay.canonical_utils import canonical_json, stable_hash
from exoarmur.feature_flags.resolver import (
    load_v2_core_types,
    load_v2_diagnostics,
    load_v2_entry_gate,
)
from exoarmur.safety import enforce_execution_gate, ExecutionActionType, GateDecision

logger = logging.getLogger(__name__)


class ExecutionKernel:
    """Execution kernel for ADMO intents"""
    
    def __init__(
        self,
        nats_client: Optional[Any] = None,
        approval_service: Optional[Any] = None,
        intent_store: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
    ):
        self.nats_client = nats_client
        self.approval_service = approval_service
        self.intent_store = intent_store
        self.audit_logger = audit_logger
        self.executed_intents: Dict[str, ExecutionIntentV1] = {}  # Simple idempotency cache
        
        logger.info("ExecutionKernel initialized")
    
    def create_execution_intent(
        self,
        local_decision: LocalDecisionV1,
        safety_verdict,
        idempotency_identifier: str
    ) -> ExecutionIntentV1:
        """Create execution intent from local decision and safety verdict"""
        # DETECTION ONLY: Check if this domain logic access is outside V2EntryGate
        v2_diagnostics = load_v2_diagnostics()
        v2_diagnostics.check_domain_logic_access("ExecutionKernel", "create_execution_intent", v2_diagnostics.ViolationSeverity.HIGH)
        
        logger.info(f"Creating execution intent for decision {local_decision.decision_id}")
        
        # Determine action class from safety verdict and local decision
        action_class = "A0_observe"  # Default
        if safety_verdict.verdict == "allow":
            if local_decision.classification == "malicious":
                action_class = "A2_hard_containment"
            elif local_decision.classification == "suspicious":
                action_class = "A1_soft_containment"
        
        policy_seed = {
            "decision_id": local_decision.decision_id,
            "classification": local_decision.classification,
            "severity": local_decision.severity,
            "confidence": local_decision.confidence,
            "subject": local_decision.subject,
            "correlation_id": local_decision.correlation_id,
            "trace_id": local_decision.trace_id,
            "action_class": action_class,
            "intent_type": "isolate_host",
        }
        bundle_hash = stable_hash(canonical_json(policy_seed))

        rule_ids = [
            f"rule:classification:{local_decision.classification}",
            f"rule:severity:{local_decision.severity}",
            f"rule:action_class:{action_class}",
        ]

        intent_seed = {
            **policy_seed,
            "idempotency_key": idempotency_identifier,
        }
        intent_digest = hashlib.sha256(canonical_json(intent_seed).encode("utf-8")).digest()
        intent_id = str(ulid.ULID.from_bytes(intent_digest[:16]))

        intent = ExecutionIntentV1(
            schema_version="1.0.0",
            intent_id=intent_id,
            tenant_id=local_decision.tenant_id,
            cell_id=local_decision.cell_id,
            idempotency_key=idempotency_identifier,
            subject=local_decision.subject,
            intent_type="isolate_host",  # TODO: derive from decision
            action_class=action_class,
            requested_at=deterministic_timestamp(
                local_decision.decision_id,
                local_decision.correlation_id,
                local_decision.trace_id,
                idempotency_identifier,
                action_class,
                "requested_at",
            ),
            parameters={"isolation_type": "network"},  # TODO: derive from decision
            policy_context={
                "bundle_hash_sha256": bundle_hash,
                "rule_ids": rule_ids,
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
        """Execute intent through V2 Entry Gate - SINGLE MANDATORY PATH"""
        logger.info(f"Executing intent {intent.intent_id} through V2 Entry Gate")
        
        # Create V2 ExecutionRequest
        v2_entry_gate = load_v2_entry_gate()
        v2_core_types = load_v2_core_types()
        
        execution_request = v2_entry_gate.ExecutionRequest(
            module_id=v2_core_types.ModuleID("execution_kernel"),
            execution_context=v2_core_types.ModuleExecutionContext(
                execution_id=v2_core_types.ExecutionID(intent.intent_id[:26] + "0" * (26 - len(intent.intent_id[:26]))),
                module_id=v2_core_types.ModuleID("execution_kernel"),
                module_version=v2_core_types.ModuleVersion(1, 0, 0),
                deterministic_seed=v2_core_types.DeterministicSeed(hash(intent.intent_id) % (2**63)),
                logical_timestamp=int(datetime.now().timestamp()),
                dependency_hash=intent.correlation_id or "default"
            ),
            action_data={
                'action_class': intent.action_class,
                'action_type': intent.action_type,
                'subject': intent.subject,
                'parameters': intent.action_parameters,
                'tenant_id': intent.tenant_id,
                'correlation_id': intent.correlation_id,
                'trace_id': intent.trace_id
            },
            correlation_id=intent.correlation_id
        )

        # Execute through V2 Entry Gate - ONLY ALLOWED PATH
        result = v2_entry_gate.execute_module(execution_request)
        
        if result.success:
            logger.info(f"Intent executed via V2 Entry Gate: {intent.intent_id}")
            return True
        else:
            logger.error(f"V2 Entry Gate execution failed: {result.error}")
            return False
        
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
