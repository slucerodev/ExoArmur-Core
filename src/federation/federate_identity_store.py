"""
ExoArmur ADMO Federate Identity Store
Persistent storage for federation identities with deterministic behavior
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import threading
from collections import OrderedDict

# Import feature flags for V2 isolation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from feature_flags.feature_flags import get_feature_flags

# Import federation models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from spec.contracts.models_v1 import (
    FederateIdentityV1,
    FederateNonceV1,
    HandshakeSessionV1,
    FederationRole,
    CellStatus,
    HandshakeState
)
logger = logging.getLogger(__name__)


@dataclass
class NonceRecord:
    """Nonce tracking record for replay protection"""
    nonce: str
    federate_id: str
    created_at: datetime
    expires_at: datetime
    used: bool = False




class FederateIdentityStore:
    """Deterministic storage for federation identities with replay protection"""
    
    def __init__(self, nonce_ttl_seconds: int = 300, max_nonce_history: int = 1000, feature_flags=None):
        """
        Initialize federate identity store
        
        Args:
            nonce_ttl_seconds: Time-to-live for nonces (default 5 minutes)
            max_nonce_history: Maximum nonces to track per federate
            feature_flags: Optional feature flags instance (for dependency injection)
        """
        self._feature_flags = feature_flags or get_feature_flags()
        
        # In-memory storage with deterministic behavior
        self._identities: Dict[str, FederateIdentityV1] = {}  # federate_id -> FederateIdentityV1
        self._nonces: Dict[str, NonceRecord] = {}  # nonce -> NonceRecord
        self._active_sessions: Dict[str, HandshakeSessionV1] = {}  # session_id -> HandshakeSessionV1
        
        # Configuration
        self._nonce_ttl_seconds = nonce_ttl_seconds
        self._max_nonce_history = max_nonce_history
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"FederateIdentityStore initialized (in-memory, nonce_ttl={nonce_ttl_seconds}s)")
    
    def is_enabled(self) -> bool:
        """Check if V2 federation identity is enabled"""
        return self._feature_flags.is_enabled('v2_federation_enabled')
    
    def store_identity(self, identity: FederateIdentityV1) -> bool:
        """
        Store or update a federate identity
        
        Args:
            identity: Federate identity to store
            
        Returns:
            True if stored successfully, False if disabled
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            federate_id = identity.federate_id
            now = datetime.now(timezone.utc)
            
            # Always replace the identity entirely (contract-true behavior)
            self._identities[federate_id] = identity
            logger.info(f"Stored federate identity: {federate_id}")
            
            return True
    
    def get_identity(self, federate_id: str) -> Optional[FederateIdentityV1]:
        """
        Get a federate identity by ID
        
        Args:
            federate_id: Federate identifier
            
        Returns:
            FederateIdentityV1 if found, None otherwise
        """
        if not self.is_enabled():
            return None
        
        with self._lock:
            identity = self._identities.get(federate_id)
            if identity:
                identity.last_seen = datetime.now(timezone.utc)
                return identity
            return None
    
    def list_identities(self) -> List[FederateIdentityV1]:
        """
        List all stored federate identities
        
        Returns:
            List of all FederateIdentityV1 objects
        """
        if not self.is_enabled():
            return []
        
        with self._lock:
            return list(self._identities.values())
    
    def remove_identity(self, federate_id: str) -> bool:
        """
        Remove a federate identity
        
        Args:
            federate_id: Federate identifier to remove
            
        Returns:
            True if removed, False if not found
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            if federate_id in self._identities:
                # Clean up associated sessions (tracked separately)
                sessions_to_remove = []
                for session_id, session in self._active_sessions.items():
                    if session.initiator_cell_id == federate_id or hasattr(session, 'responder_cell_id') and session.responder_cell_id == federate_id:
                        sessions_to_remove.append(session_id)
                
                for session_id in sessions_to_remove:
                    self._active_sessions.pop(session_id, None)
                
                # Remove nonces for this federate
                nonces_to_remove = [nonce for nonce, record in self._nonces.items() 
                                  if record.federate_id == federate_id]
                for nonce in nonces_to_remove:
                    self._nonces.pop(nonce, None)
                
                # Remove identity
                del self._identities[federate_id]
                logger.info(f"Removed federate identity: {federate_id}")
                return True
            return False
    
    def delete_identity(self, federate_id: str) -> bool:
        """
        Delete a federate identity (alias for remove_identity)
        
        Args:
            federate_id: Federate identifier to delete
            
        Returns:
            True if deleted, False if not found
        """
        return self.remove_identity(federate_id)
    
    def create_handshake_session(self, session_id: str, initiator_cell_id: str, 
                                responder_cell_id: str) -> Optional[HandshakeSessionV1]:
        """
        Create a new handshake session
        
        Args:
            session_id: Unique session identifier
            initiator_cell_id: Initiator cell ID
            responder_cell_id: Responder cell ID
            
        Returns:
            HandshakeSessionV1 if created, None if disabled or exists
        """
        if not self.is_enabled():
            return None
        
        with self._lock:
            if session_id in self._active_sessions:
                logger.warning(f"Handshake session already exists: {session_id}")
                return None
            
            # Verify both identities exist
            if initiator_cell_id not in self._identities:
                logger.error(f"Initiator identity not found: {initiator_cell_id}")
                return None
            
            if responder_cell_id not in self._identities:
                logger.error(f"Responder identity not found: {responder_cell_id}")
                return None
            
            # Create session
            session = HandshakeSessionV1(
                correlation_id=session_id,
                federate_id=initiator_cell_id,
                state=HandshakeState.UNINITIALIZED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Store session
            self._active_sessions[session_id] = session
            
            # Note: Sessions are tracked in _active_sessions, not in identity objects
            # This avoids modifying the immutable FederateIdentityV1 contract
            
            logger.info(f"Created handshake session: {session_id} between {initiator_cell_id} and {responder_cell_id}")
            return session
    
    def get_handshake_session(self, session_id: str) -> Optional[HandshakeSessionV1]:
        """
        Get a handshake session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            HandshakeSessionV1 if found, None otherwise
        """
        if not self.is_enabled():
            return None
        
        with self._lock:
            return self._active_sessions.get(session_id)
    
    def update_handshake_session(self, session_id: str, new_state: HandshakeState) -> bool:
        """
        Update handshake session state
        
        Args:
            session_id: Session identifier
            new_state: New handshake state
            
        Returns:
            True if updated, False if not found
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return False
            
            old_state = session.state
            session.state = new_state
            session.step_index += 1
            session.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Updated session {session_id}: {old_state} -> {new_state}")
            return True
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired handshake sessions
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        if not self.is_enabled():
            return 0
        
        with self._lock:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=max_age_hours)
            
            expired_sessions = [
                session_id for session_id, session in self._active_sessions.items()
                if session.created_at < cutoff
            ]
            
            for session_id in expired_sessions:
                session = self._active_sessions.pop(session_id, None)
                # Sessions are tracked separately from identities
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired handshake sessions")
            return len(expired_sessions)
    
    def create_nonce(self, federate_id: str) -> str:
        """
        Create a new nonce for a federate
        
        Args:
            federate_id: Federate identifier
            
        Returns:
            Generated nonce string
        """
        if not self.is_enabled():
            return ""
        
        nonce = self._generate_nonce()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._nonce_ttl_seconds)
        
        with self._lock:
            # Store nonce
            self._nonces[nonce] = NonceRecord(
                nonce=nonce,
                federate_id=federate_id,
                created_at=now,
                expires_at=expires_at
            )
            
            # Nonce history is tracked separately, not in identity objects
        
        return nonce
    
    def is_nonce_available(self, federate_id: str, nonce: str) -> bool:
        """
        Check if a nonce is available for use (not used or expired)
        
        Args:
            federate_id: Federate identifier
            nonce: Nonce to check
            
        Returns:
            True if nonce is available, False otherwise
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            nonce_record = self._nonces.get(nonce)
            
            if nonce_record is None:
                # Nonce doesn't exist, so it's available
                return True
            
            # Check if nonce belongs to the federate
            if nonce_record.federate_id != federate_id:
                return False
            
            # Check if nonce is expired
            if nonce_record.expires_at < datetime.now(timezone.utc):
                return True  # Expired nonces are considered available
            
            # Check if nonce is already used
            if nonce_record.used:
                return False
            
            # Nonce exists and is available
            return True
    
    def mark_nonce_used(self, federate_id: str, nonce: str) -> bool:
        """
        Mark a nonce as used (for replay protection)
        
        Args:
            federate_id: Federate identifier
            nonce: Nonce to mark as used
            
        Returns:
            True if marked successfully, False otherwise
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            nonce_record = self._nonces.get(nonce)
            
            if nonce_record is None:
                # Create nonce record if it doesn't exist
                now = datetime.now(timezone.utc)
                nonce_record = NonceRecord(
                    nonce=nonce,
                    federate_id=federate_id,
                    created_at=now,
                    expires_at=now + timedelta(seconds=self._nonce_ttl_seconds),
                    used=True
                )
                self._nonces[nonce] = nonce_record
                return True
            
            # Check if nonce belongs to the federate
            if nonce_record.federate_id != federate_id:
                return False
            
            # Mark as used
            nonce_record.used = True
            return True
    
    def verify_and_consume_nonce(self, nonce: str, federate_id: str) -> bool:
        """
        Verify and consume a nonce (replay protection)
        
        Args:
            nonce: Nonce to verify
            federate_id: Federate identifier
            
        Returns:
            True if nonce is valid and consumed, False otherwise
        """
        if not self.is_enabled():
            return False
        
        with self._lock:
            nonce_record = self._nonces.get(nonce)
            
            if nonce_record is None:
                logger.warning(f"Nonce not found: {nonce}")
                return False
            
            # Check if nonce belongs to the federate
            if nonce_record.federate_id != federate_id:
                logger.warning(f"Nonce {nonce} does not belong to federate {federate_id}")
                return False
            
            # Check if nonce is expired
            if nonce_record.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Nonce expired: {nonce}")
                self._nonces.pop(nonce, None)
                return False
            
            # Check if nonce is already used
            if nonce_record.used:
                logger.warning(f"Nonce already used: {nonce}")
                return False
            
            # Mark nonce as used
            nonce_record.used = True
            logger.debug(f"Nonce verified and consumed: {nonce} for {federate_id}")
            return True
    
    def _cleanup_expired_nonces(self) -> int:
        """Clean up expired nonces"""
        now = datetime.now(timezone.utc)
        expired_nonces = [
            nonce for nonce, record in self._nonces.items()
            if now > record.expires_at
        ]
        
        for nonce in expired_nonces:
            self._nonces.pop(nonce, None)
        
        return len(expired_nonces)
    
    def _generate_nonce(self) -> str:
        """Generate a cryptographically random nonce"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_store_stats(self) -> Dict[str, int]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with store statistics
        """
        with self._lock:
            self._cleanup_expired_nonces()
            
            return {
                'total_identities': len(self._identities),
                'active_sessions': len(self._active_sessions),
                'active_nonces': len(self._nonces),
                'enabled': self.is_enabled()
            }
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get detailed store statistics
        
        Returns:
            Dictionary with detailed store statistics
        """
        with self._lock:
            identities = list(self._identities.values())
            
            # Count by role
            roles = {}
            for identity in identities:
                role = identity.federation_role.value if hasattr(identity.federation_role, 'value') else str(identity.federation_role)
                roles[role] = roles.get(role, 0) + 1
            
            # Count by status
            status_counts = {}
            for identity in identities:
                status = identity.status.value if hasattr(identity.status, 'value') else str(identity.status)
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_identities": len(identities),
                "federate_ids": [identity.federate_id for identity in identities],
                "roles": roles,
                "status_counts": status_counts
            }


# Global store instance
_federate_identity_store_instance: Optional[FederateIdentityStore] = None


def get_federate_identity_store() -> FederateIdentityStore:
    """Get the global federate identity store instance"""
    global _federate_identity_store_instance
    if _federate_identity_store_instance is None:
        _federate_identity_store_instance = FederateIdentityStore()
    return _federate_identity_store_instance
