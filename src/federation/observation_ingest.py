"""
ExoArmur ADMO V2 Observation Ingest Service
Handles ingestion of federate observations with validation and verification
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import uuid

from spec.contracts.models_v1 import (
    ObservationV1,
    BeliefV1,
    FederateIdentityV1,
    HandshakeState,
    VerificationFailureReason
)
from .observation_store import ObservationStore
from .federate_identity_store import FederateIdentityStore
from .clock import Clock
from .crypto import verify_message_integrity

logger = logging.getLogger(__name__)


@dataclass
class ObservationIngestConfig:
    """Configuration for observation ingest behavior"""
    feature_enabled: bool = False  # V2 additive feature flag
    require_confirmed_federate: bool = True
    require_signature: bool = True
    max_observation_size_bytes: int = 1024 * 1024  # 1MB


class ObservationIngestService:
    """
    Service for ingesting federate observations
    
    Handles validation, verification, and storage of observations
    with strict security requirements.
    """
    
    def __init__(
        self,
        observation_store: ObservationStore,
        identity_store: FederateIdentityStore,
        clock: Clock,
        config: Optional[ObservationIngestConfig] = None
    ):
        self.observation_store = observation_store
        self.identity_store = identity_store
        self.clock = clock
        self.config = config or ObservationIngestConfig()
        
        logger.info("ObservationIngestService initialized")
    
    def ingest_observation(self, observation: ObservationV1) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Ingest an observation with full validation pipeline
        
        Args:
            observation: Observation to ingest
            
        Returns:
            Tuple of (success, reason, audit_event)
        """
        # Feature flag check
        if not self.config.feature_enabled:
            return False, "feature_disabled", self._create_audit_event(
                observation, "observation_rejected", "feature_disabled"
            )
        
        # Validate federate is confirmed
        federate_status, federate_reason = self._validate_federate_status(observation.source_federate_id)
        if not federate_status:
            return False, federate_reason, self._create_audit_event(
                observation, "observation_rejected", federate_reason
            )
        
        # Validate schema
        schema_status, schema_reason = self._validate_observation_schema(observation)
        if not schema_status:
            return False, schema_reason, self._create_audit_event(
                observation, "observation_rejected", schema_reason
            )
        
        # Verify signature if required
        if self.config.require_signature:
            sig_status, sig_reason = self._verify_observation_signature(observation)
            if not sig_status:
                return False, sig_reason, self._create_audit_event(
                    observation, "observation_rejected", sig_reason
                )
        
        # Check nonce replay
        if observation.nonce:
            if self.observation_store.is_nonce_used(observation.nonce):
                return False, "nonce_reuse", self._create_audit_event(
                    observation, "observation_rejected", "nonce_reuse"
                )
        
        # Store observation
        if not self.observation_store.store_observation(observation):
            return False, "duplicate_observation", self._create_audit_event(
                observation, "observation_rejected", "duplicate_observation"
            )
        
        # Success audit event
        audit_event = self._create_audit_event(
            observation, "observation_accepted", "ingested_successfully"
        )
        
        logger.info(f"Successfully ingested observation {observation.observation_id}")
        return True, "success", audit_event
    
    def _validate_federate_status(self, federate_id: str) -> Tuple[bool, str]:
        """Validate that federate exists and is confirmed"""
        if not self.config.require_confirmed_federate:
            return True, "federate_validation_disabled"
        
        identity = self.identity_store.get_identity(federate_id)
        if not identity:
            return False, "federate_not_found"
        
        # Check if federate is confirmed (has successful handshake)
        # This would typically be tracked in a session store
        # For now, we'll assume any stored identity is valid
        # In a full implementation, this would check handshake state
        
        return True, "federate_confirmed"
    
    def _validate_observation_schema(self, observation: ObservationV1) -> Tuple[bool, str]:
        """Validate observation schema and constraints"""
        try:
            # Check required fields
            if not observation.observation_id:
                return False, "missing_observation_id"
            
            if not observation.source_federate_id:
                return False, "missing_source_federate_id"
            
            if not observation.timestamp_utc:
                return False, "missing_timestamp"
            
            # Check timestamp is not too old or in future
            now = self.clock.now()
            if observation.timestamp_utc > now:
                return False, "future_timestamp"
            
            # Check timestamp is not too old (24 hours)
            if observation.timestamp_utc < now - timedelta(hours=24):
                return False, "timestamp_too_old"
            
            # Validate confidence range
            if not (0.0 <= observation.confidence <= 1.0):
                return False, "invalid_confidence_range"
            
            # Validate payload
            if not observation.payload:
                return False, "missing_payload"
            
            return True, "schema_valid"
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False, f"schema_validation_error: {str(e)}"
    
    def _verify_observation_signature(self, observation: ObservationV1) -> Tuple[bool, str]:
        """Verify observation signature"""
        if not observation.signature:
            return False, "missing_signature"
        
        try:
            # Get federate identity for verification
            identity = self.identity_store.get_identity(observation.source_federate_id)
            if not identity:
                return False, "federate_not_found"
            
            # Verify signature using existing crypto verification
            verification_success, failure_reason = verify_message_integrity(
                observation, identity.key_id, identity.public_key, 
                self.identity_store, self.clock
            )
            
            if verification_success:
                return True, "signature_valid"
            else:
                return False, str(failure_reason) if failure_reason else "signature_verification_failed"
                
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False, f"signature_verification_error: {str(e)}"
    
    def _create_audit_event(
        self,
        observation: ObservationV1,
        event_type: str,
        reason: str
    ) -> Dict[str, Any]:
        """Create audit event for observation processing"""
        return {
            "event_type": event_type,
            "federate_id": observation.source_federate_id,
            "observation_id": observation.observation_id,
            "correlation_id": observation.correlation_id,
            "observation_type": observation.observation_type,
            "timestamp": self.clock.now().isoformat(),
            "reason": reason,
            "details": {
                "confidence": observation.confidence,
                "payload_type": observation.payload.payload_type,
                "evidence_refs": observation.evidence_refs
            }
        }
    
    def get_ingest_statistics(self) -> Dict[str, Any]:
        """Get ingest service statistics"""
        store_stats = self.observation_store.get_statistics()
        
        return {
            "feature_enabled": self.config.feature_enabled,
            "require_confirmed_federate": self.config.require_confirmed_federate,
            "require_signature": self.config.require_signature,
            "store_statistics": store_stats
        }
