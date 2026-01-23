"""
ExoArmur ADMO Intent Store
Stores frozen execution intents bound to approval requests
"""

import logging
import hashlib
import json
from typing import Dict, Optional
from datetime import datetime, timezone

# Import contract models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'spec', 'contracts'))
from models_v1 import ExecutionIntentV1

logger = logging.getLogger(__name__)


class IntentStore:
    """In-memory store for frozen execution intents"""
    
    def __init__(self):
        self._frozen_intents: Dict[str, ExecutionIntentV1] = {}  # approval_id -> intent
        self._approval_by_idempotency: Dict[str, str] = {}  # idempotency_key -> approval_id
        self._approval_by_intent_id: Dict[str, str] = {}  # intent_id -> approval_id
        self._approval_by_hash: Dict[str, str] = {}  # intent_hash -> approval_id
        
        logger.info("IntentStore initialized (in-memory)")
    
    def compute_intent_hash(self, intent: ExecutionIntentV1) -> str:
        """Compute deterministic hash of intent (excluding volatile fields)"""
        # Create canonical representation excluding timestamps and volatile fields
        intent_dict = intent.model_dump()
        
        # Remove volatile fields that shouldn't affect hash
        volatile_fields = ['created_at', 'updated_at', 'execution_started_at', 'execution_completed_at']
        for field in volatile_fields:
            intent_dict.pop(field, None)
        
        # Sort keys and use compact JSON for deterministic hash
        canonical_json = json.dumps(intent_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def freeze_intent(self, approval_id: str, intent: ExecutionIntentV1) -> None:
        """Store frozen intent keyed by approval_id"""
        intent_hash = self.compute_intent_hash(intent)
        
        # Store mappings for lookup
        self._frozen_intents[approval_id] = intent
        self._approval_by_idempotency[intent.idempotency_key] = approval_id
        self._approval_by_intent_id[intent.intent_id] = approval_id
        self._approval_by_hash[intent_hash] = approval_id
        
        logger.info(f"Frozen intent {intent.intent_id} for approval {approval_id} (hash: {intent_hash[:12]}...)")
    
    def get_intent_by_approval_id(self, approval_id: str) -> Optional[ExecutionIntentV1]:
        """Retrieve frozen intent by approval_id"""
        return self._frozen_intents.get(approval_id)
    
    def get_intent_by_idempotency_key(self, idempotency_key: str) -> Optional[ExecutionIntentV1]:
        """Retrieve frozen intent by idempotency_key"""
        approval_id = self._approval_by_idempotency.get(idempotency_key)
        return self._frozen_intents.get(approval_id) if approval_id else None
    
    def verify_intent_binding(self, approval_id: str, intent: ExecutionIntentV1) -> bool:
        """Verify that intent matches the frozen intent bound to approval_id"""
        frozen_intent = self._frozen_intents.get(approval_id)
        if not frozen_intent:
            logger.warning(f"No frozen intent found for approval {approval_id}")
            return False
        
        # Check critical fields match
        if frozen_intent.intent_id != intent.intent_id:
            logger.warning(f"Intent ID mismatch: expected {frozen_intent.intent_id}, got {intent.intent_id}")
            return False
        
        if frozen_intent.idempotency_key != intent.idempotency_key:
            logger.warning(f"Idempotency key mismatch for approval {approval_id}")
            return False
        
        # Check hash matches
        current_hash = self.compute_intent_hash(intent)
        stored_approval_id = self._approval_by_hash.get(current_hash)
        if stored_approval_id != approval_id:
            logger.warning(f"Intent hash mismatch for approval {approval_id}")
            return False
        
        return True
    
    def get_approval_id_by_intent_id(self, intent_id: str) -> Optional[str]:
        """Get approval_id by intent_id"""
        return self._approval_by_intent_id.get(intent_id)
    
    def get_approval_id_by_idempotency_key(self, idempotency_key: str) -> Optional[str]:
        """Get approval_id by idempotency_key"""
        return self._approval_by_idempotency.get(idempotency_key)
